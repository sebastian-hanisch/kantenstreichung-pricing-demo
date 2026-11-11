"""Kern der Demo: Label-Setting vorwärts und rückwärts mit ng-Gedächtnis, Pfad-reduzierte Kosten je Kante, Streichen, Aufzählung zulässiger Routen.

Kopie des Messkerns der Vormessung (`ls_kanten.py`), umbenannt und in kleine Einheiten zerlegt (DEMO-PLAYBOOK §1b): jede Regel ist eine Funktion mit expliziten Ein- und Ausgaben,
kein versteckter Zustand, kein Zufall (die Instanz kommt fertig herein). Gezählt werden Labels (Messgröße); Sekunden spielen im Kern keine Rolle.

Begriffe:
* Ein **Label** ist ein Teilweg ab dem Depot (vorwärts) bzw. ein Rest bis zum Depot (rückwärts) mit Zeit, reduzierten Kosten, Last und ng-Gedächtnis.
* Die **reduzierten Kosten** einer Route sind ihre Weglänge minus die Summe der Dualpreise der besuchten Kunden (Dualpreis des Depots = 0).
* Die **Pfad-reduzierten Kosten** einer Kante (i, j) sind die kleinsten reduzierten Kosten einer zulässigen Route, die die Kante benutzt (Ergebnis des Verbindens eines
  Vorwärtslabels in i mit einem Rückwärtslabel in j; bei ng-Gedächtnis k < n nie größer als der wahre Wert der elementaren Routen, bei k = n gleich).
Label: Liste [Zeit, Kosten, Last, Gedächtnis (Bitmaske), Knoten, Vorgänger-Nummer, dominiert?]."""

import heapq
import math

import numpy as np

from ksp_constants import EPS, TOL_SCHWELLE

T, K, Q, M, N, V, D = range(7)   # Positionen im Label: Zeit, Kosten, Last, Gedächtnis, Knoten, Vorgänger, dominiert


# ---------------------------------------------------------------------------------------------------------------------------------
# Routen: Länge, reduzierte Kosten, Kanten, unabhängiger Zulässigkeitsprüfer
# ---------------------------------------------------------------------------------------------------------------------------------

def route_kanten(route) -> list:
    """Kanten einer Route einschließlich der Fahrten ab und zum Depot: Route (a, b) hat die Kanten (0, a), (a, b), (b, 0)."""
    folge = (0,) + tuple(route) + (0,)
    return list(zip(folge, folge[1:]))


def weg_laenge(inst, route) -> float:
    """Länge (= Kosten) der Route: Summe der Entfernungen aller ihrer Kanten."""
    return sum(inst.dist[a][b] for a, b in route_kanten(route))


def route_kosten(inst, dual, route) -> float:
    """Reduzierte Kosten der Route: Länge minus die Dualpreise der besuchten Kunden (`dual[0]` ist der des Depots, 0)."""
    return weg_laenge(inst, route) - sum(dual[j] for j in route)


def route_zulaessig(inst, route) -> bool:
    """Unabhängiger Prüfer (läuft auch in der App): jeder Kunde höchstens einmal, Last höchstens Kapazität, Ankunft vor jedem Fensterende, Rückkehr bis zum Horizont.

    Wartet das Fahrzeug vor dem Fensteranfang, zählt die Bedienung ab dem Fensteranfang."""
    route = tuple(route)
    if not route or len(set(route)) != len(route) or any(not 1 <= j <= inst.n for j in route):
        return False
    if sum(inst.last[j] for j in route) > inst.kapazitaet:
        return False
    zeit, ort = 0.0, 0
    for j in route:
        ankunft = zeit + (inst.bedienzeit if ort != 0 else 0.0) + inst.dist[ort][j]
        if ankunft > inst.spaet[j] + EPS:
            return False
        zeit, ort = max(ankunft, inst.frueh[j]), j
    return zeit + inst.bedienzeit + inst.dist[ort][0] <= inst.horizont + EPS


# ---------------------------------------------------------------------------------------------------------------------------------
# ng-Gedächtnis
# ---------------------------------------------------------------------------------------------------------------------------------

def ng_masken(inst, k: int) -> list:
    """Nachbarschaft NG(j) als Bitmaske: die k nächsten Kunden von j einschließlich j selbst (Gleichstand: kleinere Nummer zuerst). k = n heißt: alle, also elementar."""
    masken = [0] * (inst.n + 1)
    for j in range(1, inst.n + 1):
        ordnung = sorted(range(1, inst.n + 1), key=lambda i: inst.dist[j][i])
        m = 0
        for i in ordnung[:k]:
            m |= 1 << i
        masken[j] = m | (1 << j)
    return masken


# ---------------------------------------------------------------------------------------------------------------------------------
# Vorwärts-Labeling
# ---------------------------------------------------------------------------------------------------------------------------------

def vorwaerts_start() -> list:
    """Startlabel am Depot: Zeit 0, Kosten 0, Last 0, leeres Gedächtnis."""
    return [0.0, 0.0, 0, 0, 0, -1, False]


def vorwaerts_erweitern(inst, dual, masken, label, j):
    """Erweiterungsregel: das Label um die Kante (Knoten des Labels → j) verlängern; None, wenn j im Gedächtnis steht, die Last die Kapazität übersteigt
    oder die Ankunft nach dem Fensterende liegt. Wartet das Fahrzeug, beginnt die Bedienung am Fensteranfang."""
    i = label[N]
    if j == i or (label[M] >> j) & 1:
        return None
    last = label[Q] + inst.last[j]
    if last > inst.kapazitaet:
        return None
    ankunft = label[T] + (inst.bedienzeit if i != 0 else 0.0) + inst.dist[i][j]
    if ankunft > inst.spaet[j] + EPS:
        return None
    return [max(ankunft, inst.frueh[j]), label[K] + inst.dist[i][j] - dual[j], last, (label[M] & masken[j]) | (1 << j), j, -1, False]


def vorwaerts_dominiert(a, b) -> bool:
    """Dominanz am selben Kunden: a dominiert b, wenn a höchstens so teuer, so spät und so schwer ist und sich nicht mehr Kunden merkt (Gedächtnis von a ist Teilmenge)."""
    return a[K] <= b[K] + EPS and a[T] <= b[T] + EPS and a[Q] <= b[Q] and (a[M] & ~b[M]) == 0


def vorwaerts_ende(inst, label):
    """Reduzierte Kosten der Route, die am Knoten des Labels endet und zum Depot zurückfährt; None, wenn die Rückkehr nach dem Horizont läge (oder das Label das Depot ist)."""
    i = label[N]
    if i == 0 or label[T] + inst.bedienzeit + inst.dist[i][0] > inst.horizont + EPS:
        return None
    return label[K] + inst.dist[i][0]


def _einfuegen(labels, am_knoten, neu, dominiert_von):
    """Neues Label einfügen oder verwerfen. Rückgabe (Zahl sofort verworfen: 0 oder 1, Zahl verdrängter Labels); das neue Label kommt in `labels` und `am_knoten[Knoten]`, wenn es bleibt.

    `dominiert_von(a, b)`: a dominiert b. Ein neues Label, das von einem lebenden dominiert wird, entfällt; sonst verdrängt es alle lebenden, die es dominiert."""
    liste = am_knoten[neu[N]]
    for oi in liste:
        alt = labels[oi]
        if not alt[D] and dominiert_von(alt, neu):
            return 1, 0
    uebrig, verdraengt = [], 0
    for oi in liste:
        alt = labels[oi]
        if alt[D]:
            continue
        if dominiert_von(neu, alt):
            alt[D] = True
            verdraengt += 1
        else:
            uebrig.append(oi)
    labels.append(neu)
    uebrig.append(len(labels) - 1)
    am_knoten[neu[N]] = uebrig
    return 0, verdraengt


def vorwaerts_labeling(inst, dual, k, erlaubt=None, max_labels=None, mit_ende=False) -> dict:
    """Vorwärts-Labeling ab dem Depot bei den Dualpreisen `dual`, ng-Gedächtnis k, optional mit Kantenfilter `erlaubt[i][j]` (False = Kante gestrichen).

    Rückgabe: labels (alle erzeugten, die Nummer ist der Index), ueberlebende (je Knoten die Nummern der nicht dominierten), erzeugt, dominiert (sofort verworfen plus verdrängt),
    bester_wert (kleinste reduzierte Kosten über alle Endlabels, inf wenn keine Route), ende (Liste (reduzierte Kosten, Label-Nr) der Endlabels, falls `mit_ende`),
    abgebrochen (True, wenn `max_labels` erreicht wurde; dann sind die Zahlen unvollständig)."""
    n = inst.n
    masken = ng_masken(inst, k)
    labels = [vorwaerts_start()]
    am_knoten = [[] for _ in range(n + 1)]
    halde = [(0.0, 0)]
    erzeugt, dominiert = 1, 0
    bester, ende, abgebrochen = math.inf, [], False
    while halde:
        _, li = heapq.heappop(halde)
        label = labels[li]
        if label[D]:
            continue
        if max_labels is not None and erzeugt >= max_labels:
            abgebrochen = True
            break
        i = label[N]
        if erlaubt is None or erlaubt[i][0]:
            wert = vorwaerts_ende(inst, label)
            if wert is not None:
                bester = min(bester, wert)
                if mit_ende:
                    ende.append((wert, li))
        for j in range(1, n + 1):
            if erlaubt is not None and not erlaubt[i][j]:
                continue
            neu = vorwaerts_erweitern(inst, dual, masken, label, j)
            if neu is None:
                continue
            neu[V] = li
            erzeugt += 1
            verworfen, verdraengt = _einfuegen(labels, am_knoten, neu, vorwaerts_dominiert)
            dominiert += verworfen + verdraengt
            if not verworfen:
                heapq.heappush(halde, (neu[T], len(labels) - 1))
    return dict(labels=labels, ueberlebende=am_knoten, erzeugt=erzeugt, dominiert=dominiert, bester_wert=bester, ende=ende, abgebrochen=abgebrochen)


# ---------------------------------------------------------------------------------------------------------------------------------
# Rückwärts-Labeling
# ---------------------------------------------------------------------------------------------------------------------------------

def rueckwaerts_start(inst) -> list:
    """Startlabel am Depot: späteste Zeit = Horizont, Kosten 0, Last 0, leeres Gedächtnis."""
    return [inst.horizont, 0.0, 0, 0, 0, -1, False]


def rueckwaerts_erweitern(inst, dual, masken, label, i):
    """Erweiterungsregel rückwärts: dem Rest, der bei Knoten j beginnt, den Kunden i vorschalten (Kante i → j). Die Zeit ist der späteste Beginn der Bedienung in i, so dass der Rest zulässig bleibt;
    die Kosten des Labels enthalten den Dualpreis des Anfangsknotens nicht (er gehört zur Kante, die ihn betritt). None bei Gedächtnis, Last oder zu spätem Fensteranfang."""
    j = label[N]
    if i == j or (label[M] >> i) & 1:
        return None
    last = label[Q] + inst.last[i]
    if last > inst.kapazitaet:
        return None
    spaetest = min(inst.spaet[i], label[T] - inst.bedienzeit - inst.dist[i][j])
    if spaetest < inst.frueh[i] - EPS:
        return None
    preis_j = dual[j] if j != 0 else 0.0
    return [spaetest, label[K] + inst.dist[i][j] - preis_j, last, (label[M] & masken[i]) | (1 << i), i, -1, False]


def rueckwaerts_dominiert(a, b) -> bool:
    """Dominanz rückwärts: a dominiert b, wenn a höchstens so teuer und so schwer ist, höchstens so viele Kunden merkt und mindestens so spät beginnen darf."""
    return a[K] <= b[K] + EPS and a[T] >= b[T] - EPS and a[Q] <= b[Q] and (a[M] & ~b[M]) == 0


def rueckwaerts_labeling(inst, dual, k, max_labels=None) -> dict:
    """Rückwärts-Labeling ab dem Depot: Reste j → … → Depot. Rückgabe wie beim Vorwärts-Labeling (ohne Endlabels); `ueberlebende[0]` ist das Startlabel am Depot."""
    n = inst.n
    masken = ng_masken(inst, k)
    labels = [rueckwaerts_start(inst)]
    am_knoten = [[] for _ in range(n + 1)]
    halde = [(-inst.horizont, 0)]
    erzeugt, dominiert, abgebrochen = 1, 0, False
    while halde:
        _, li = heapq.heappop(halde)
        label = labels[li]
        if label[D]:
            continue
        if max_labels is not None and erzeugt >= max_labels:
            abgebrochen = True
            break
        for i in range(1, n + 1):
            neu = rueckwaerts_erweitern(inst, dual, masken, label, i)
            if neu is None:
                continue
            neu[V] = li
            erzeugt += 1
            verworfen, verdraengt = _einfuegen(labels, am_knoten, neu, rueckwaerts_dominiert)
            dominiert += verworfen + verdraengt
            if not verworfen:
                heapq.heappush(halde, (-neu[T], len(labels) - 1))
    am_knoten[0] = [0]
    return dict(labels=labels, ueberlebende=am_knoten, erzeugt=erzeugt, dominiert=dominiert, bester_wert=None, ende=[], abgebrochen=abgebrochen)


# ---------------------------------------------------------------------------------------------------------------------------------
# Verbinden: Pfad-reduzierte Kosten je Kante
# ---------------------------------------------------------------------------------------------------------------------------------

def _lebende(res, knoten) -> list:
    """Nummern der nicht dominierten Labels eines Knotens (am Depot nur das Startlabel)."""
    if knoten == 0:
        return [0]
    return [x for x in res["ueberlebende"][knoten] if not res["labels"][x][D]]


def _felder(res, knoten):
    """Zeit, Kosten, Last, Gedächtnis und Nummern der lebenden Labels eines Knotens als Felder (für das vektorisierte Verbinden)."""
    idx = _lebende(res, knoten)
    a = np.array([[res["labels"][x][T], res["labels"][x][K], res["labels"][x][Q], res["labels"][x][M]] for x in idx], dtype=float).reshape(-1, 4)
    return a[:, 0], a[:, 1], a[:, 2], a[:, 3].astype(np.int64), np.array(idx, dtype=np.int64)


def kantenwerte(inst, dual, F, B, mit_routen=False):
    """Pfad-reduzierte Kosten aller Kanten (i, j), i ≠ j, als Matrix (inf = keine zulässige Route über die Kante) und, falls verlangt, die beste Route je Kante.

    `F` und `B` sind die Ergebnisse von Vorwärts- und Rückwärts-Labeling bei denselben Dualpreisen. Die Route ist die Aneinanderreihung der Kette des Vorwärtslabels
    und der des Rückwärtslabels ohne Depot, als Tupel von Kunden."""
    n = inst.n
    kap = inst.kapazitaet
    FA = [_felder(F, i) for i in range(n + 1)]
    BA = [_felder(B, i) for i in range(n + 1)]
    P = np.full((n + 1, n + 1), math.inf)
    beste = {}
    for i in range(n + 1):
        Ft, Fc, Fq, Fm, Fx = FA[i]
        if len(Ft) == 0:
            continue
        for j in range(n + 1):
            if i == j:
                continue
            Bl, Bc, Bq, Bm, Bx = BA[j]
            if len(Bl) == 0:
                continue
            versatz = (inst.bedienzeit if i != 0 else 0.0) + inst.dist[i][j]
            kosten_kante = inst.dist[i][j] - (dual[j] if j != 0 else 0.0)
            vor = (Ft + versatz <= Bl.max() + EPS) & (Fq + Bq.min() <= kap) & (((Fm >> j) & 1) == 0)
            if not vor.any():
                continue
            rueck = (Bl >= Ft[vor].min() + versatz - EPS) & (Bq + Fq[vor].min() <= kap) & (((Bm >> i) & 1) == 0)
            if not rueck.any():
                continue
            ft, fc, fq, fm, fx = Ft[vor], Fc[vor], Fq[vor], Fm[vor], Fx[vor]
            bl, bc, bq, bm, bx = Bl[rueck], Bc[rueck], Bq[rueck], Bm[rueck], Bx[rueck]
            wert, paar = math.inf, None
            schritt = max(1, int(4_000_000 // max(1, len(bl))))
            for s in range(0, len(ft), schritt):
                sl = slice(s, s + schritt)
                ok = ((ft[sl, None] + versatz <= bl[None, :] + EPS) & (fq[sl, None] + bq[None, :] <= kap) & ((fm[sl, None] & bm[None, :]) == 0))
                kosten = np.where(ok, fc[sl, None] + bc[None, :] + kosten_kante, math.inf)
                m = float(kosten.min())
                if m < wert:
                    wert = m
                    if mit_routen:
                        r, c = np.unravel_index(int(kosten.argmin()), kosten.shape)
                        paar = (int(fx[sl][r]), int(bx[c]))
            if wert < math.inf:
                P[i][j] = wert
                if mit_routen:
                    beste[(i, j)] = tuple(v for v in _kette_vor(F, paar[0]) + _kette_rueck(B, paar[1]) if v != 0)
    return (P, beste) if mit_routen else (P, None)


def _kette_vor(F, li) -> list:
    """Knotenfolge eines Vorwärtslabels vom Depot bis zum Knoten des Labels (beginnt mit 0)."""
    folge = []
    while li != -1:
        folge.append(F["labels"][li][N])
        li = F["labels"][li][V]
    return folge[::-1]


def _kette_rueck(B, li) -> list:
    """Knotenfolge eines Rückwärtslabels vom Anfangsknoten bis zum Depot (endet mit 0)."""
    folge = []
    while li != -1:
        folge.append(B["labels"][li][N])
        li = B["labels"][li][V]
    return folge


def rueckwaerts_route(B, li) -> tuple:
    """Rest (Kunden ohne Depot) eines Rückwärtslabels: vom Anfangsknoten des Labels bis zum Depot."""
    return tuple(v for v in _kette_rueck(B, li) if v != 0)


def vorwaerts_route(F, li) -> tuple:
    """Route (Kunden ohne Depot) eines Vorwärtslabels."""
    return tuple(_kette_vor(F, li))[1:]


# ---------------------------------------------------------------------------------------------------------------------------------
# Streichen
# ---------------------------------------------------------------------------------------------------------------------------------

def statisch_zulaessig(inst) -> list:
    """Kanten, die für sich allein zulässig sind (Zeitfenster und Last), ohne Rücksicht auf Dualpreise; Matrix von Wahrheitswerten."""
    n = inst.n
    ok = [[False] * (n + 1) for _ in range(n + 1)]
    for j in range(1, n + 1):
        ok[0][j] = inst.dist[0][j] <= inst.spaet[j] + EPS
        ok[j][0] = inst.frueh[j] + inst.bedienzeit + inst.dist[j][0] <= inst.horizont + EPS
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            if i != j:
                ok[i][j] = (inst.frueh[i] + inst.bedienzeit + inst.dist[i][j] <= inst.spaet[j] + EPS and inst.last[i] + inst.last[j] <= inst.kapazitaet)
    return ok


def kanten_mit_route(P) -> list:
    """Kanten mit mindestens einer zulässigen Route (endlicher Wert), als Liste (i, j)."""
    n1 = len(P)
    return [(i, j) for i in range(n1) for j in range(n1) if i != j and P[i][j] < math.inf]


def gestrichene_kanten(P, schwelle) -> set:
    """Streichregel: alle Kanten mit zulässiger Route, deren Pfad-reduzierte Kosten die Schwelle übersteigen (um mehr als die Toleranz)."""
    return {(i, j) for (i, j) in kanten_mit_route(P) if P[i][j] > schwelle + TOL_SCHWELLE}


def erlaubt_matrix(n, P, schwelle) -> list:
    """Kantenfilter für das Labeling im gestrichenen Graphen: True nur für Kanten mit zulässiger Route und Wert höchstens Schwelle (+ Toleranz)."""
    erl = [[False] * (n + 1) for _ in range(n + 1)]
    for (i, j) in kanten_mit_route(P):
        if P[i][j] <= schwelle + TOL_SCHWELLE:
            erl[i][j] = True
    return erl


def route_ohne(route, gestrichen) -> bool:
    """Enthält die Route keine gestrichene Kante?"""
    return not any(e in gestrichen for e in route_kanten(route))


# ---------------------------------------------------------------------------------------------------------------------------------
# Aufzählung zulässiger elementarer Routen (Tiefensuche)
# ---------------------------------------------------------------------------------------------------------------------------------

def routen_aufzaehlen(inst, dual, max_routen=None):
    """Alle zulässigen elementaren Routen mit ihren reduzierten Kosten (Tiefensuche, ohne Dominanz). Rückgabe ([(Route, reduzierte Kosten)], vollständig?);
    bei Erreichen von `max_routen` bricht die Suche ab (vollständig = False)."""
    n = inst.n
    out = []
    zustand = {"ok": True}

    def tiefe(i, t, q, besucht, weg, kosten):
        if not zustand["ok"]:
            return
        if i != 0 and t + inst.bedienzeit + inst.dist[i][0] <= inst.horizont + EPS:
            if max_routen is not None and len(out) >= max_routen:
                zustand["ok"] = False
                return
            out.append((tuple(weg), kosten + inst.dist[i][0]))
        for j in range(1, n + 1):
            if (besucht >> j) & 1:
                continue
            q2 = q + inst.last[j]
            if q2 > inst.kapazitaet:
                continue
            ankunft = t + (inst.bedienzeit if i != 0 else 0.0) + inst.dist[i][j]
            if ankunft > inst.spaet[j] + EPS:
                continue
            tiefe(j, max(ankunft, inst.frueh[j]), q2, besucht | (1 << j), weg + [j], kosten + inst.dist[i][j] - dual[j])

    tiefe(0, 0.0, 0, 0, [], 0.0)
    return out, zustand["ok"]


def kleinste_rueckkosten(B) -> list:
    """Kleinste Kosten eines nicht dominierten Rückwärtslabels je Knoten (inf, wenn keines): untere Schranke für den Rest einer Route ab dem Knoten (ohne dessen Dualpreis)."""
    m = [math.inf] * len(B["ueberlebende"])
    for j in range(1, len(m)):
        for x in B["ueberlebende"][j]:
            if not B["labels"][x][D]:
                m[j] = min(m[j], B["labels"][x][K])
    return m


def routen_bis(inst, dual, P, schwelle, B, max_routen=300_000):
    """Alle zulässigen elementaren Routen mit reduzierten Kosten höchstens `schwelle` (Tiefensuche). Beschnitten wird mit der Kantenmatrix P (Kante nur, wenn ihr Wert ≤ Schwelle)
    und mit „Kosten bisher + kleinste Rückwärtskosten am Knoten ≤ Schwelle“. Rückgabe ([Routen], vollständig?); bei Erreichen von `max_routen` vollständig = False."""
    n = inst.n
    rest = kleinste_rueckkosten(B)
    grenze = schwelle + TOL_SCHWELLE
    out = []
    zustand = {"ok": True}

    def tiefe(i, t, q, besucht, weg, kosten):
        if not zustand["ok"]:
            return
        if len(out) >= max_routen:
            zustand["ok"] = False
            return
        if i != 0 and t + inst.bedienzeit + inst.dist[i][0] <= inst.horizont + EPS and P[i][0] <= grenze and kosten + inst.dist[i][0] <= grenze:
            out.append(tuple(weg))
        for j in range(1, n + 1):
            if (besucht >> j) & 1 or P[i][j] > grenze:
                continue
            q2 = q + inst.last[j]
            if q2 > inst.kapazitaet:
                continue
            ankunft = t + (inst.bedienzeit if i != 0 else 0.0) + inst.dist[i][j]
            if ankunft > inst.spaet[j] + EPS:
                continue
            k2 = kosten + inst.dist[i][j] - dual[j]
            if k2 + rest[j] > grenze:
                continue
            tiefe(j, max(ankunft, inst.frueh[j]), q2, besucht | (1 << j), weg + [j], k2)

    tiefe(0, 0.0, 0, 0, [], 0.0)
    return out, zustand["ok"]
