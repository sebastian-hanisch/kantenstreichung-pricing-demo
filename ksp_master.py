"""Master und Spaltenerzeugung: der Partitionierungs-Master (jeder Kunde genau einmal) und die Schleife aus Master und Pricing; dazu die ganzzahlige Partitionierung für obere Schranken.

Eine Spalte ist eine Route (Besuchsfolge); sie kostet ihre Weglänge. Zwei Master-Löser mit derselben Aufgabe:

* `master_lp`     HiGHS (scipy), Gleitkomma; für die Zufallsinstanzen,
* `master_exakt`  Simplex mit Brüchen auf dem Dualproblem (Regel von Bland), liefert Dualpreise exakt; für das Handbeispiel (ganzzahlige Kosten).

`spaltenerzeugung` ruft abwechselnd einen Master-Löser und das Pricing (Vorwärts-Labeling mit ng-Gedächtnis) auf, bis keine Route mit negativen reduzierten Kosten mehr kommt;
der Wert des letzten Masters ist dann die untere Schranke LB, und die Dualpreise sind die der Konvergenz. `partition_ganzzahlig` löst die Mengenpartitionierung über gegebene
elementare Routen ganzzahlig (obere Schranke bzw. exaktes Optimum)."""

import contextlib
import math
import os
from fractions import Fraction
from itertools import chain

import numpy as np

import ksp_algorithm as A
from ksp_constants import DP_MAX_N, MAX_NEUE_SPALTEN, MAX_RUNDEN, MILP_ZEIT, NEG_RC


@contextlib.contextmanager
def _ohne_c_ausgabe():
    """Schreibt der Löser (C-Code) auf Standardausgabe und Fehlerausgabe, geht das während des Aufrufs in die Leere. HiGHS meldet bei manchen Partitionierungen eine Debug-Zeile
    („transformNewIntegerFeasibleSolution“); in einem pytest-xdist-Arbeitsprozess läuft der Kanal zum Hauptprozess über genau diese Ausgabe, und die Zeile bricht ihn ab."""
    try:
        gesichert = [(fd, os.dup(fd)) for fd in (1, 2)]
        leer = os.open(os.devnull, os.O_WRONLY)
    except OSError:
        yield
        return
    try:
        for fd, _kopie in gesichert:
            os.dup2(leer, fd)
        yield
    finally:
        for fd, kopie in gesichert:
            os.dup2(kopie, fd)
            os.close(kopie)
        os.close(leer)


def _matrix(n: int, spalten: list):
    """Zeilen = Kunden 1..n, Spalten = Routen; Eintrag = Zahl der Besuche des Kunden in der Route (bei ng-Routen mit Kreis auch 2 oder mehr)."""
    a = np.zeros((n, len(spalten)))
    for c, route in enumerate(spalten):
        for j in route:
            a[j - 1, c] += 1
    return a


def master_lp(n: int, kosten: list, spalten: list):
    """Partitionierungs-Master  min c·x  mit  A x = 1, x ≥ 0  mit HiGHS. Rückgabe (Zielwert, Dualpreise mit Position 0 = Depot = 0, Mengen x)."""
    from scipy.optimize import linprog
    res = linprog(kosten, A_eq=_matrix(n, spalten), b_eq=np.ones(n), bounds=(0, None), method="highs")
    if res.status != 0:
        raise RuntimeError(f"Master nicht lösbar: {res.message}")
    return float(res.fun), [0.0] + [float(v) for v in res.eqlin.marginals], [float(v) for v in res.x]


def master_exakt(n: int, kosten: list, spalten: list):
    """Derselbe Master, exakt mit Brüchen: Simplex auf dem Dualen  max Σπ  mit  Aᵀπ ≤ c, π frei (π = u − v, Regel von Bland).

    `kosten` ganzzahlig, die Spalten elementar. Rückgabe (Zielwert, Dualpreise (Position 0 = Depot = 0), Mengen x) als Brüche."""
    m = len(spalten)
    nv = 2 * n
    ncol = nv + m
    tab = []
    for r, route in enumerate(spalten):
        zeile = [Fraction(0)] * (ncol + 1)
        for j in route:
            zeile[j - 1] += 1
            zeile[n + j - 1] -= 1
        zeile[nv + r] = Fraction(1)
        zeile[ncol] = Fraction(kosten[r])
        tab.append(zeile)
    ziel = [Fraction(1)] * n + [Fraction(-1)] * n + [Fraction(0)] * (m + 1)
    basis = [nv + r for r in range(m)]
    while True:
        e = next((j for j in range(ncol) if ziel[j] > 0), None)
        if e is None:
            break
        beste = None
        for r in range(m):
            if tab[r][e] > 0:
                schluessel = (tab[r][ncol] / tab[r][e], basis[r])
                if beste is None or schluessel < beste[0]:
                    beste = (schluessel, r)
        r = beste[1]
        piv = tab[r][e]
        tab[r] = [x / piv for x in tab[r]]
        for i in range(m):
            if i != r and tab[i][e] != 0:
                f = tab[i][e]
                tab[i] = [a - f * b for a, b in zip(tab[i], tab[r])]
        f = ziel[e]
        ziel = [a - f * b for a, b in zip(ziel, tab[r])]
        basis[r] = e
    loesung = [Fraction(0)] * ncol
    for r, b in enumerate(basis):
        loesung[b] = tab[r][ncol]
    dual = [Fraction(0)] + [loesung[i] - loesung[n + i] for i in range(n)]
    return -ziel[ncol], dual, [-ziel[nv + r] for r in range(m)]


def spaltenerzeugung(inst, k: int, max_neu: int = MAX_NEUE_SPALTEN, max_runden: int = MAX_RUNDEN, max_labels=None) -> dict:
    """Spaltenerzeugung mit Partitionierungs-Master (HiGHS) und ng-Pricing (Gedächtnis k): Start mit den Einzelfahrten Depot-i-Depot, je Runde Master und Pricing.

    Je Runde kommen bis zu `max_neu` neue Routen (die besten nach reduzierten Kosten unter NEG_RC, noch nicht im Master) als Spalten dazu. `max_labels`: Obergrenze der erzeugten Labels
    in ALLEN Pricing-Aufrufen zusammen (None = unbegrenzt); bei Erreichen bricht die Rechnung ab.
    Rückgabe: schranke (Wert des letzten Masters oder None bei Abbruch), dual (Dualpreise der Konvergenz), spalten (alle Routen, die ersten n sind die Einzelfahrten), kosten,
    runden, labels (erzeugte Labels in allen Pricing-Aufrufen), abgebrochen."""
    n = inst.n
    spalten = [(j,) for j in range(1, n + 1)]
    kosten = [A.weg_laenge(inst, r) for r in spalten]
    bekannt = set(spalten)
    labels, wert, dual = 0, None, None
    for runde in range(1, max_runden + 1):
        wert, dual, _x = master_lp(n, kosten, spalten)
        rest = None if max_labels is None else max_labels - labels
        res = A.vorwaerts_labeling(inst, dual, k, max_labels=rest, mit_ende=True)
        labels += res["erzeugt"]
        if res["abgebrochen"]:
            return dict(schranke=None, dual=dual, spalten=spalten, kosten=kosten, runden=runde, labels=labels, abgebrochen=True)
        gefunden = {}
        for rc, li in res["ende"]:
            if rc < NEG_RC:
                route = A.vorwaerts_route(res, li)
                if route not in gefunden:
                    gefunden[route] = rc
        neue = [r for _rc, r in sorted((rc, r) for r, rc in gefunden.items())[:max_neu] if r not in bekannt]
        if not neue:
            return dict(schranke=wert, dual=dual, spalten=spalten, kosten=kosten, runden=runde, labels=labels, abgebrochen=False)
        for r in neue:
            spalten.append(r)
            kosten.append(A.weg_laenge(inst, r))
            bekannt.add(r)
    return dict(schranke=None, dual=dual, spalten=spalten, kosten=kosten, runden=max_runden, labels=labels, abgebrochen=True)


def partition_teilmengen(inst, routen):
    """Ganzzahlige Mengenpartitionierung durch Aufzählung über Kundenmengen (dynamische Programmierung über Teilmengen), exakt und ohne scipy: je Kundenmenge zählt nur die billigste
    elementare Route; f(M) ist der kleinste Wert einer Zerlegung der Menge M, wobei die Route des kleinsten Kunden von M gewählt wird. Aufwand rund 3^n, deshalb nur für wenige Kunden.

    Rückgabe (Zielwert oder None, gewählte Routen, True): das Ergebnis ist immer bewiesen optimal."""
    n = inst.n
    bestes = {}
    for r in routen:
        r = tuple(r)
        if not r or len(set(r)) != len(r):
            continue
        maske = sum(1 << (j - 1) for j in r)
        c = A.weg_laenge(inst, r)
        if maske not in bestes or (c, r) < bestes[maske]:
            bestes[maske] = (c, r)
    voll = (1 << n) - 1
    f = [math.inf] * (voll + 1)
    wahl = [0] * (voll + 1)
    f[0] = 0.0
    for m in range(1, voll + 1):
        tiefster = m & -m
        rest = m ^ tiefster
        t = rest
        while True:
            s = t | tiefster
            if s in bestes:
                c = bestes[s][0] + f[m ^ s]
                if c < f[m] - 1e-12:
                    f[m], wahl[m] = c, s
            if t == 0:
                break
            t = (t - 1) & rest
    if f[voll] == math.inf:
        return None, [], True
    gewaehlt, m = [], voll
    while m:
        gewaehlt.append(bestes[wahl[m]][1])
        m ^= wahl[m]
    return float(f[voll]), gewaehlt, True


def partition_ganzzahlig(inst, routen, zeit: float = MILP_ZEIT):
    """Ganzzahlige Mengenpartitionierung (jeder Kunde genau einmal) über die gegebenen Routen; nur elementare Routen zählen, Doppelte entfallen.

    Bis DP_MAX_N Kunden durch Aufzählung über Kundenmengen (`partition_teilmengen`, immer bewiesen optimal), darüber mit `scipy.optimize.milp` (HiGHS) mit Zeitgrenze `zeit`.
    Rückgabe (Zielwert oder None, gewählte Routen, bewiesen optimal?). Wert None, wenn das Modell keine Lösung hat oder die Zeitgrenze ohne Lösung endet."""
    if inst.n <= DP_MAX_N:
        return partition_teilmengen(inst, routen)
    from scipy.optimize import Bounds, LinearConstraint, milp
    n = inst.n
    gesehen, cols = set(), []
    for r in routen:
        r = tuple(r)
        if r and len(set(r)) == len(r) and r not in gesehen:
            gesehen.add(r)
            cols.append(r)
    if not cols:
        return None, [], False
    kosten = np.array([A.weg_laenge(inst, r) for r in cols])
    with _ohne_c_ausgabe():
        res = milp(c=kosten, constraints=LinearConstraint(_matrix(n, cols), np.ones(n), np.ones(n)), integrality=np.ones(len(cols)), bounds=Bounds(0, 1), options={"time_limit": zeit})
    if res.x is None:
        return None, [], False
    gewaehlt = [cols[c] for c in range(len(cols)) if res.x[c] > 0.5]
    return float(res.fun), gewaehlt, bool(res.status == 0)


def partition_milp(inst, routen, zeit: float = MILP_ZEIT):
    """Dieselbe Aufgabe immer mit `scipy.optimize.milp` (auch für wenige Kunden); Gegenprobe zur Aufzählung über Kundenmengen."""
    from scipy.optimize import Bounds, LinearConstraint, milp
    n = inst.n
    cols = sorted({tuple(r) for r in routen if r and len(set(r)) == len(r)})
    if not cols:
        return None, [], False
    kosten = np.array([A.weg_laenge(inst, r) for r in cols])
    with _ohne_c_ausgabe():
        res = milp(c=kosten, constraints=LinearConstraint(_matrix(n, cols), np.ones(n), np.ones(n)), integrality=np.ones(len(cols)), bounds=Bounds(0, 1), options={"time_limit": zeit})
    if res.x is None:
        return None, [], False
    return float(res.fun), [cols[c] for c in range(len(cols)) if res.x[c] > 0.5], bool(res.status == 0)


def partition_brute(inst, routen):
    """Kleinste Kosten einer Zerlegung aller Kunden in Routen aus `routen` durch Aufzählung (nur für wenige Kunden und Routen; Gegenprobe zu `partition_ganzzahlig`, ohne scipy).

    Rückgabe (Zielwert oder None, gewählte Routen)."""
    n = inst.n
    nach_erstem = {i: [] for i in range(1, n + 1)}
    for r in routen:
        r = tuple(r)
        if r and len(set(r)) == len(r):
            nach_erstem[min(r)].append((r, A.weg_laenge(inst, r), sum(1 << (v - 1) for v in r)))
    bester = [None, []]

    def tiefe(abgedeckt, kosten, gewaehlt):
        if abgedeckt == (1 << n) - 1:
            if bester[0] is None or kosten < bester[0] - 1e-12:
                bester[0], bester[1] = kosten, list(gewaehlt)
            return
        i = next(i for i in range(1, n + 1) if not (abgedeckt >> (i - 1)) & 1)
        for r, c, maske in nach_erstem[i]:
            if maske & abgedeckt:
                continue
            gewaehlt.append(r)
            tiefe(abgedeckt | maske, kosten + c, gewaehlt)
            gewaehlt.pop()

    tiefe(0, 0.0, [])
    return bester[0], bester[1]


def alle_elementar(spalten) -> list:
    """Nur die elementaren Spalten (jeder Kunde höchstens einmal)."""
    return [r for r in spalten if len(set(r)) == len(r)]


def verkettet(*listen) -> list:
    """Mehrere Routenlisten zu einer Liste (Reihenfolge erhalten)."""
    return list(chain(*listen))
