"""Kennzahlen, Läufe (Handbeispiel, Live-Instanz, feste Messreihen) und Verdikt-Logik.

Jedes Verdikt der App ist eine reine Funktion `verdict_*(...) -> (Art, Text)`; die App ruft `getattr(st, Art)(Text)`, `tests/test_verdicts.py` prüft Schwellen und jede Zahl im Text.
Zahlen im Text kommen aus der Rechnung (f-String), nie aus dem Kopf. `analyse_instanz` ist die EINE Rechnung für eine Instanz: die Live-Rechnung der App und die festen Messreihen
(`tools/baender_erzeugen.py`) rufen dieselbe Funktion auf."""

import math
from dataclasses import dataclass
from fractions import Fraction

import ksp_algorithm as A
import ksp_constants as C
import ksp_master as M
import ksp_scenario as S

# ---------------------------------------------------------------------------------------------------------------------------------
# Zahlenformat (Dezimalkomma, geschütztes Leerzeichen als Tausendertrenner)
# ---------------------------------------------------------------------------------------------------------------------------------

NBSP = " "


def fmt_int(x) -> str:
    return f"{round(x):,}".replace(",", NBSP).replace("-", "−")


def fmt_dec(x, stellen: int = 1) -> str:
    return f"{float(x):,.{stellen}f}".replace(",", NBSP).replace(".", ",").replace("-", "−")


def fmt_pct(anteil, stellen: int = 1) -> str:
    """Anteil (0 bis 1) als Prozentangabe mit Dezimalkomma."""
    return fmt_dec(100 * anteil, stellen) + NBSP + "%"


def fmt_wert(x, stellen: int = 2) -> str:
    """Ganze Zahl ohne Nachkommastellen, echter Bruch als „83/3 (27,67)“, Gleitkommazahl mit Dezimalkomma."""
    if isinstance(x, Fraction) and x.denominator != 1:
        return f"{x.numerator}/{x.denominator}".replace("-", "−") + f" ({fmt_dec(float(x), stellen)})"
    if isinstance(x, (int, Fraction)):
        return fmt_int(x)
    xf = float(x)
    if abs(xf - round(xf)) < 1e-9:
        return fmt_int(round(xf))
    return fmt_dec(xf, stellen)


def weg_text(route) -> str:
    return " → ".join(str(j) for j in route) if route else "–"


def kante_text(kante) -> str:
    return f"{kante[0]}→{kante[1]}"


def anteil(zaehler, nenner):
    """Anteil zaehler / nenner; None bei Nenner 0 (dann gibt es nichts zu streichen oder zu vergleichen)."""
    return None if nenner == 0 else zaehler / nenner


# ---------------------------------------------------------------------------------------------------------------------------------
# Schwellen
# ---------------------------------------------------------------------------------------------------------------------------------

SCHWELLEN_NAMEN = {
    "ub1": "Lücke aus den Spalten (obere Schranke 1)", "ub2": "Lücke mit bester Route je Kante (obere Schranke 2)", "ub3": "exakte Lücke (Optimum)",
    "r0.5": "angenommen: 0,5 % von LB", "r1": "angenommen: 1 % von LB", "r2": "angenommen: 2 % von LB", "r5": "angenommen: 5 % von LB",
}


SCHWELLEN_KURZ = {"ub1": "UB1: Spalten", "ub2": "UB2: + beste Route je Kante", "ub3": "UB3: exaktes Optimum", "r0.5": "angenommen 0,5 %", "r1": "angenommen 1 %", "r2": "angenommen 2 %", "r5": "angenommen 5 %"}


def schwellen(lb: float, ub1: float, ub2: float, ub3: float) -> dict:
    """Die sieben Schwellen der Messreihe: die Lücken der drei oberen Schranken und angenommene 0,5, 1, 2 und 5 Prozent von LB (die letzten vier sind nicht garantiert)."""
    return {"ub1": ub1 - lb, "ub2": ub2 - lb, "ub3": ub3 - lb, "r0.5": 0.005 * lb, "r1": 0.01 * lb, "r2": 0.02 * lb, "r5": 0.05 * lb}


def gitter_zaehlung(P, lb: float) -> dict:
    """Zahl der Kanten mit zulässiger Route, deren Pfad-reduzierte Kosten höchstens x · LB betragen, für x in BAND_GRID (Schlüssel: Text des Anteils)."""
    kanten = A.kanten_mit_route(P)
    return {str(g): sum(1 for (i, j) in kanten if P[i][j] <= g * lb + C.TOL_SCHWELLE) for g in C.BAND_GRID}


# ---------------------------------------------------------------------------------------------------------------------------------
# Eine Instanz vollständig analysieren (Live-Rechnung und Messreihen)
# ---------------------------------------------------------------------------------------------------------------------------------

def analyse_instanz(inst, k: int, max_routen: int = 300_000, milp_zeit: float = C.MILP_ZEIT, max_labels=None):
    """Spaltenerzeugung bis zur Konvergenz, obere Schranken in drei Stufen, Kantenwerte, Streichen bei sieben Schwellen und die Wirkung auf die Labels.

    Obere Schranken (alle mit ganzzahliger Partitionierung über elementare Routen): UB1 nur die Spalten der Spaltenerzeugung; UB2 plus die beste Route je Kante;
    UB3 plus die Aufzählung ALLER zulässigen elementaren Routen mit reduzierten Kosten höchstens UB2 − LB. Ist die Aufzählung vollständig und die Partitionierung bewiesen optimal,
    ist UB3 das exakte ganzzahlige Optimum (`ub3_exakt`); sonst gilt UB3 = UB2 und „nicht exakt“.
    Rückgabe (zeile, intern): `zeile` ist ein Wörterbuch mit Zahlen und Wahrheitswerten (JSON-fähig), `intern` hält Matrizen und Labels für die Anzeige.
    Eine abgebrochene Rechnung (Obergrenze der Labels) gibt zeile mit fertig = False und intern = None."""
    n = inst.n
    cg = M.spaltenerzeugung(inst, k, max_labels=max_labels)
    zeile = {"n": n, "k": k, "breite": inst.breite, "fertig": not cg["abgebrochen"]}
    if cg["abgebrochen"]:
        zeile["grund"] = "Spaltenerzeugung an der Obergrenze der Labels abgebrochen"
        return zeile, None
    lb, dual = cg["schranke"], cg["dual"]
    zeile.update(lb=lb, runden=cg["runden"], spalten=len(cg["spalten"]), labels_spaltenerzeugung=cg["labels"], dual_summe_abweichung=abs(sum(dual) - lb))
    ub1, _s1, opt1 = M.partition_ganzzahlig(inst, cg["spalten"], milp_zeit)
    F = A.vorwaerts_labeling(inst, dual, k, max_labels=max_labels)
    B = A.rueckwaerts_labeling(inst, dual, k, max_labels=max_labels)
    if F["abgebrochen"] or B["abgebrochen"] or ub1 is None:
        zeile.update(fertig=False, grund="Labeling an der Obergrenze der Labels abgebrochen" if (F["abgebrochen"] or B["abgebrochen"]) else "keine ganzzahlige Lösung aus den Spalten")
        return zeile, None
    P, beste = A.kantenwerte(inst, dual, F, B, mit_routen=True)
    zeile.update(ub1=ub1, ub1_optimal=opt1, labels_vorwaerts=F["erzeugt"], labels_rueckwaerts=B["erzeugt"], bester_wert_voll=F["bester_wert"])
    ub2, s2, opt2 = M.partition_ganzzahlig(inst, M.verkettet(cg["spalten"], beste.values()), milp_zeit)
    if ub2 is None:
        zeile.update(fertig=False, grund="keine ganzzahlige Lösung mit den Kantenrouten")
        return zeile, None
    aufz, vollstaendig = A.routen_bis(inst, dual, P, ub2 - lb + 1e-9, B, max_routen)
    ub3, s3, opt3 = M.partition_ganzzahlig(inst, M.verkettet(cg["spalten"], beste.values(), aufz), milp_zeit)
    exakt = bool(vollstaendig and opt3 and ub3 is not None)
    if ub3 is None or ub3 > ub2 + 1e-6 * max(1.0, abs(ub2)):   # Zeitgrenze der Partitionierung: nichts Besseres als UB2 gefunden (Unterschiede in der letzten Stelle zählen nicht)
        ub3, exakt, s3 = ub2, False, s2
    else:
        ub3 = min(ub3, ub2)
    zeile.update(ub2=ub2, ub2_optimal=opt2, ub3=ub3, ub3_exakt=exakt, aufzaehlung_vollstaendig=bool(vollstaendig), routen_aufgezaehlt=len(aufz))
    stat = A.statisch_zulaessig(inst)
    kanten = [(i, j) for i in range(n + 1) for j in range(n + 1) if i != j]
    mit = A.kanten_mit_route(P)
    zeile.update(kanten_gesamt=len(kanten), kanten_statisch=sum(1 for (i, j) in kanten if stat[i][j]), kanten_mit_route=len(mit), gitter=gitter_zaehlung(P, lb))
    wirkung = {}
    for name, schwelle in schwellen(lb, ub1, ub2, ub3).items():
        G = A.vorwaerts_labeling(inst, dual, k, erlaubt=A.erlaubt_matrix(n, P, schwelle), max_labels=max_labels)
        wirkung[name] = {"schwelle": schwelle, "entfernt": len(A.gestrichene_kanten(P, schwelle)), "labels": G["erzeugt"], "bester_wert": G["bester_wert"], "abgebrochen": bool(G["abgebrochen"])}
    zeile["wirkung"] = wirkung
    intern = dict(inst=inst, k=k, lb=lb, dual=dual, spalten=cg["spalten"], P=P, beste=beste, F=F, B=B, aufzaehlung=aufz, loesung=sorted(s3))
    return zeile, intern


# ---------------------------------------------------------------------------------------------------------------------------------
# Einstellungen der Live-Rechnung
# ---------------------------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class LiveEinstellung:
    n: int = C.LIVE_DEFAULT_N
    typ: str = C.LIVE_DEFAULT_TYP
    breite: int = C.LIVE_DEFAULT_BREITE
    seed: int = C.LIVE_DEFAULT_SEED
    k: int = C.LIVE_DEFAULT_K


def live_instanz(e: LiveEinstellung):
    """Instanz und wirksames ng-Gedächtnis (höchstens n: ab k = n ist die Rechnung elementar) zu den Einstellungen."""
    return S.make_instance(e.n, e.seed, e.breite, gruppiert=(e.typ == "gruppiert")), min(e.k, e.n)


# ---------------------------------------------------------------------------------------------------------------------------------
# Handbeispiel (Experiment 1)
# ---------------------------------------------------------------------------------------------------------------------------------

def hand_basis() -> dict:
    """Das Handbeispiel einmal durchrechnen: alle zulässigen elementaren Routen, Master-LP über alle Routen exakt mit Brüchen (untere Schranke LB und Dualpreise),
    ganzzahliges Optimum z* durch Aufzählung aller Zerlegungen, Vorwärts- und Rückwärtslabels bei den Dualpreisen (k = n, elementar) und Pfad-reduzierte Kosten je Kante.
    Ganze Zahlen; die Dualpreise sind exakte Brüche, hier ganzzahlig."""
    inst = S.handbeispiel()
    n = inst.n
    alle, _ok = A.routen_aufzaehlen(inst, [0] * (n + 1))
    routen = sorted((r for r, _rc in alle), key=lambda r: (len(r), r))
    kosten = [round(A.weg_laenge(inst, r)) for r in routen]
    lb, dual, x = M.master_exakt(n, kosten, routen)
    dual_ganz = tuple(int(d) if d.denominator == 1 else d for d in dual)
    rc = {r: A.weg_laenge(inst, r) - sum(dual[j] for j in r) for r in routen}
    zstar, loesung = M.partition_brute(inst, routen)
    zstar = round(zstar)
    F = A.vorwaerts_labeling(inst, dual_ganz, n)
    B = A.rueckwaerts_labeling(inst, dual_ganz, n)
    P, beste = A.kantenwerte(inst, dual_ganz, F, B, mit_routen=True)
    lb_ganz = int(lb) if lb.denominator == 1 else lb
    return dict(inst=inst, routen=routen, kosten=kosten, rc=rc, lb=lb_ganz, dual=dual_ganz, x=[(r, xv) for r, xv in zip(routen, x) if xv > 0], zstar=zstar, loesung=sorted(loesung),
                luecke=zstar - lb_ganz, F=F, B=B, P=P, beste=beste, kanten=A.kanten_mit_route(P))


def hand_schwelle(b: dict, schwelle) -> dict:
    """Streichen im Handbeispiel bei einer Schwelle: gestrichene Kanten, Routen ohne gestrichene Kante, das ganzzahlige Optimum über diese Routen (None: keine Zerlegung mehr möglich),
    Kanten der optimalen Lösung, die dabei fallen, und das Vorwärts-Labeling im gestrichenen Graphen."""
    inst = b["inst"]
    weg = A.gestrichene_kanten(b["P"], schwelle)
    uebrig = [r for r in b["routen"] if A.route_ohne(r, weg)]
    z_rest, _loesung = M.partition_brute(inst, uebrig) if uebrig else (None, [])
    loesung_kanten = {e for r in b["loesung"] for e in A.route_kanten(r)}
    G = A.vorwaerts_labeling(inst, b["dual"], inst.n, erlaubt=A.erlaubt_matrix(inst.n, b["P"], schwelle))
    return dict(schwelle=schwelle, gestrichen=weg, entfernt=len(weg), mit_route=len(b["kanten"]), routen_uebrig=len(uebrig), z_rest=None if z_rest is None else round(z_rest),
                zstar=b["zstar"], luecke=b["luecke"], loesung_faellt=sorted(loesung_kanten & weg), labels_voll=b["F"]["erzeugt"], labels_gestr=G["erzeugt"],
                bester_voll=b["F"]["bester_wert"], bester_gestr=G["bester_wert"], F_gestr=G)


# ---------------------------------------------------------------------------------------------------------------------------------
# Live-Instanz (Experimente 2, 3 und 5)
# ---------------------------------------------------------------------------------------------------------------------------------

def optimum_ohne_gestrichene(inst, alle: list, gestrichen: set, lb: float, zstar: float, zeit: float = C.MILP_ZEIT):
    """Ganzzahliges Optimum über die zulässigen elementaren Routen ohne gestrichene Kante. `alle` sind ALLE zulässigen Routen als (Route, reduzierte Kosten).

    Jede Zerlegung vom Wert z ≤ U besteht nur aus Routen mit reduzierten Kosten ≤ U − LB (Summe der Dualpreise gleich LB). Gerechnet wird deshalb mit den Routen unter einer Grenze, die
    bei z* − LB beginnt und wächst, bis sie die gefundene Lösung abdeckt: Das spart Spalten, ohne das Ergebnis zu ändern. Rückgabe (Wert oder None, wenn keine Zerlegung mehr möglich, bewiesen?)."""
    zugelassen = [(r, rc) for r, rc in alle if A.route_ohne(r, gestrichen)]
    if not zugelassen:
        return None, True
    hoechst = max(rc for _r, rc in zugelassen)
    grenze = max(zstar - lb, 0.0) + C.TOL_SCHWELLE
    while True:
        spalten = [r for r, rc in zugelassen if rc <= grenze]
        z, _s, opt = M.partition_ganzzahlig(inst, spalten, zeit) if spalten else (None, [], True)
        if z is not None:
            noetig = z - lb + C.TOL_SCHWELLE
            if noetig <= grenze + 1e-9 or grenze >= hoechst:
                return z, opt
            grenze = noetig
        elif grenze >= hoechst:
            return None, True
        else:
            grenze = min(hoechst, 2 * grenze + 1.0)


def live_lauf(e: LiveEinstellung) -> dict:
    """Die Live-Instanz vollständig: `analyse_instanz` plus Aufzählung ALLER zulässigen elementaren Routen (bis LIVE_MAX_ROUTEN) und das exakte Optimum z* (wenn bewiesen).
    Jede Spalte und die Route der Lösung werden mit dem unabhängigen Prüfer `route_zulaessig` kontrolliert; `fehler` nennt den ersten Verstoß."""
    inst, k = live_instanz(e)
    zeile, intern = analyse_instanz(inst, k, max_routen=C.LIVE_MAX_ROUTEN)
    res = dict(e=e, inst=inst, k=k, zeile=zeile, intern=intern, fertig=zeile["fertig"], fehler=None, alle=[], alle_vollstaendig=False, zstar=None, luecke=None)
    if not zeile["fertig"]:
        return res
    alle, vollstaendig = A.routen_aufzaehlen(inst, intern["dual"], C.LIVE_MAX_ROUTEN)
    res.update(alle=alle, alle_vollstaendig=vollstaendig)
    for r, _rc in alle[:200]:
        if not A.route_zulaessig(inst, r):
            res["fehler"] = f"Aufgezählte Route {weg_text(r)} ist nach dem unabhängigen Prüfer nicht zulässig."
            break
    if zeile["ub3_exakt"]:
        res.update(zstar=zeile["ub3"], luecke=zeile["ub3"] - zeile["lb"])
    return res


def live_schwelle(live: dict, schwelle: float) -> dict:
    """Streichen auf der Live-Instanz bei einer Schwelle (absolute reduzierte Kosten): gestrichene Kanten, Labels im gestrichenen Graphen, Optimum über die verbleibenden Routen
    (nur, wenn z* bewiesen ist; sonst None)."""
    inst, intern, zeile = live["inst"], live["intern"], live["zeile"]
    P, dual, k, lb = intern["P"], intern["dual"], intern["k"], intern["lb"]
    weg = A.gestrichene_kanten(P, schwelle)
    G = A.vorwaerts_labeling(inst, dual, k, erlaubt=A.erlaubt_matrix(inst.n, P, schwelle))
    z_rest, bewiesen, bleibt = None, False, None
    if live["zstar"] is not None and live["alle_vollstaendig"]:
        z_rest, bewiesen = optimum_ohne_gestrichene(inst, live["alle"], weg, lb, live["zstar"])
        bleibt = None if not bewiesen else bool(z_rest is not None and z_rest <= live["zstar"] + 1e-6)
    return dict(schwelle=schwelle, gestrichen=weg, entfernt=len(weg), mit_route=zeile["kanten_mit_route"], labels_voll=zeile["labels_vorwaerts"], labels_gestr=G["erzeugt"],
                z_rest=z_rest, optimum_bewiesen=bewiesen, optimum_bleibt=bleibt, zstar=live["zstar"], lb=lb)


def live_kurve(live: dict) -> list:
    """Anteil der Kanten mit zulässiger Route mit Pfad-reduzierten Kosten höchstens x % von LB für x = 0, 0,5, 1 … 10 (Punkte der Kurve der Live-Instanz)."""
    P, lb = live["intern"]["P"], live["intern"]["lb"]
    kanten = A.kanten_mit_route(P)
    xs = [i * 0.5 for i in range(0, 21)]
    return [(x, sum(1 for (i, j) in kanten if P[i][j] <= x / 100 * lb + C.TOL_SCHWELLE) / len(kanten)) for x in xs]


# ---------------------------------------------------------------------------------------------------------------------------------
# Verdikte (reine Funktionen: (Art, Text))
# ---------------------------------------------------------------------------------------------------------------------------------

def nullen(x: float, tol: float = 1e-9) -> float:
    """Rundungsreste als null (damit keine „−0,00“ erscheinen)."""
    return 0.0 if abs(x) < tol else x


def satz_labels(voll: int, gestr: int) -> str:
    """Satz über die Wirkung auf die Labels, immer mit dem Vorbehalt im selben Satz."""
    if voll <= 0:
        return f"Im vollen Graphen werden keine Labels erzeugt ({C.VORBEHALT})."
    return (f"Das Vorwärts-Labeling erzeugt im gestrichenen Graphen {fmt_int(gestr)} statt {fmt_int(voll)} Labels (× {fmt_dec(gestr / voll, 2)}; "
            f"{C.VORBEHALT}).")


def verdict_hand(h: dict) -> tuple:
    """Verdikt des Handbeispiels aus `hand_schwelle`: bleibt das ganzzahlige Optimum über die Routen ohne gestrichene Kante erhalten?"""
    s, luecke, zstar, z = h["schwelle"], h["luecke"], h["zstar"], h["z_rest"]
    kopf = f"Bei der Schwelle {fmt_int(s)} werden {h['entfernt']} von {h['mit_route']} Kanten mit zulässiger Route gestrichen ({fmt_pct(h['entfernt'] / h['mit_route'])})."
    if z is not None and z == zstar:
        text = f"**Kantenstreichung erhält das Optimum.** {kopf} Das ganzzahlige Optimum über die {h['routen_uebrig']} verbleibenden Routen ist weiter {fmt_int(zstar)}."
        if s < luecke:
            text += f" Die Schwelle liegt unter der Lücke ({fmt_int(luecke)}); dass das Optimum hier trotzdem bleibt, ist ein Zufall dieses Netzes und keine Garantie."
        return "success", text
    fallen = ", ".join(kante_text(e) for e in h["loesung_faellt"])
    folge = ("Über die verbleibenden Routen lässt sich nicht mehr jeder Kunde genau einmal bedienen" if z is None
             else f"Das ganzzahlige Optimum über die {h['routen_uebrig']} verbleibenden Routen ist {fmt_int(z)} statt {fmt_int(zstar)}")
    return "warning", (f"**Schwelle zu klein: Optimum verloren.** {kopf} {folge}. Die Schwelle liegt unter der Lücke ({fmt_int(luecke)})"
                       + (f"; von der optimalen Lösung fallen die Kanten {fallen}." if fallen else "."))


def verdict_live(v: dict) -> tuple:
    """Verdikt der Live-Instanz bei der exakten Lücke. `v`: fertig, grund, exakt, luecke_pct (Lücke in % von LB; bei exakt die exakte, sonst die aus Schranke 2), entfernt, mit_route,
    labels_voll, labels_gestr, optimum_bleibt, zstar."""
    if not v["fertig"]:
        return "error", f"Die Rechnung wurde nicht fertig: {v['grund']}."
    anteil_txt = fmt_pct(v["entfernt"] / v["mit_route"])
    null = nullen(v["luecke_pct"], 1e-7) == 0
    lueck = "null" if null else fmt_dec(v["luecke_pct"], 2) + NBSP + "%"
    wirkung = f"{v['entfernt']} von {v['mit_route']} Kanten mit zulässiger Route gestrichen ({anteil_txt}). " + satz_labels(v["labels_voll"], v["labels_gestr"])
    if not v["exakt"]:
        return "info", (f"Das exakte Optimum ist für diese Einstellung nicht bewiesen (Aufzählung oder Partitionierung an der Grenze). Mit der Lücke der besten bekannten oberen Schranke "
                        f"({lueck} von LB) sind {wirkung}")
    if v["optimum_bleibt"] is None:
        return "info", (f"Das Optimum ist bewiesen; bei der exakten Lücke ({lueck} von LB) sind {wirkung} Ob es über die verbleibenden Routen erhalten bleibt, ist nicht geprüft "
                        "(die Aufzählung aller Routen erreichte ihre Obergrenze).")
    if v["optimum_bleibt"]:
        luecke_satz = "Die Lücke ist null (das Optimum erreicht die untere Schranke): es sind " if null else f"Bei der exakten Lücke ({lueck} von LB) sind es "
        return "success", (f"**Kantenstreichung erhält das Optimum.** {luecke_satz}{wirkung} Das ganzzahlige Optimum ({fmt_dec(v['zstar'], 2)}) bleibt. "
                           "Das ist ein Einzelfall; die Messreihen in Experiment 4 zeigen die Streuung.")
    return "error", "Prüfung fehlgeschlagen: bei der exakten Lücke ging das Optimum verloren. Das darf nach der Regel nicht vorkommen."


def verdict_schwelle(v: dict) -> tuple:
    """Verdikt zu Experiment 3. `v`: pct (angenommene Lücke in % von LB), luecke_pct (exakte Lücke in % von LB oder None), entfernt, mit_route, bleibt (True, False oder None), zstar, z_rest."""
    pct = v["pct"]
    wirkung = f"werden {v['entfernt']} von {v['mit_route']} Kanten mit zulässiger Route gestrichen ({fmt_pct(v['entfernt'] / v['mit_route'])})"
    kopf = f"Bei der angenommenen Lücke von {fmt_dec(pct, 1)}{NBSP}% von LB {wirkung}."
    if v["luecke_pct"] is None or v["bleibt"] is None:
        return "info", f"{kopf} Das exakte Optimum ist für diese Einstellung nicht bewiesen; ob es bleibt, ist hier nicht geprüft."
    luecke = nullen(v["luecke_pct"], 1e-7)
    echt = f"{fmt_dec(luecke, 2)}{NBSP}%"
    if pct + 1e-9 >= luecke:
        if v["bleibt"]:
            return "success", (f"{kopf} Das ist mehr als die echte Lücke dieser Instanz ({echt} von LB); das ganzzahlige Optimum ({fmt_dec(v['zstar'], 2)}) bleibt. "
                               "Eine Garantie gibt nur eine echte obere Schranke; eine angenommene Lücke ist nur so gut wie die Annahme.")
        return "error", "Prüfung fehlgeschlagen: bei einer Schwelle über der exakten Lücke ging das Optimum verloren. Das darf nach der Regel nicht vorkommen."
    if v["bleibt"]:
        return "info", (f"{kopf} Das ist weniger als die echte Lücke dieser Instanz ({echt} von LB), das Optimum ({fmt_dec(v['zstar'], 2)}) bleibt hier trotzdem: "
                        "ein Zufall dieser Instanz und keine Garantie.")
    folge = "es gibt keine Zerlegung mehr" if v["z_rest"] is None else f"das beste ganzzahlige Ergebnis über die verbleibenden Routen ist {fmt_dec(v['z_rest'], 2)} statt {fmt_dec(v['zstar'], 2)}"
    return "warning", f"**Angenommene Lücke zu klein: Optimum verloren.** {kopf} Die echte Lücke dieser Instanz ist {echt} von LB; {folge}."


def verdict_obere_schranken(v: dict) -> tuple:
    """Verdikt zum Vergleich der drei oberen Schranken auf der Live-Instanz. `v`: je Stufe („ub1“, „ub2“, „ub3“) ein Wörterbuch mit luecke_pct und entfernt, dazu mit_route und exakt."""
    a, b, c = v["ub1"], v["ub2"], v["ub3"]
    n = v["mit_route"]
    teile = (f"Aus den Spalten allein (obere Schranke 1, Lücke {fmt_dec(nullen(a['luecke_pct'], 1e-7), 2)}{NBSP}% von LB) fallen {a['entfernt']} von {n} Kanten ({fmt_pct(a['entfernt'] / n)}), "
             f"mit der besten Route je Kante (Schranke 2, {fmt_dec(nullen(b['luecke_pct'], 1e-7), 2)}{NBSP}%) {b['entfernt']} ({fmt_pct(b['entfernt'] / n)}), "
             f"mit dem exakten Optimum (Schranke 3, {fmt_dec(nullen(c['luecke_pct'], 1e-7), 2)}{NBSP}%) {c['entfernt']} ({fmt_pct(c['entfernt'] / n)}).")
    if not v["exakt"]:
        return "info", teile + " Das Optimum ist hier nicht bewiesen, Schranke 3 ist dann gleich Schranke 2."
    if a["entfernt"] == c["entfernt"]:
        return "info", teile + " Hier ist die obere Schranke aus den Spalten schon so gut wie das Optimum: die drei Stufen streichen gleich viel."
    return "success", teile + " Je besser die obere Schranke, desto mehr Kanten fallen weg."


def verdict_baender(v: dict) -> tuple:
    """Verdikt zu Experiment 4 (n = 30). `v`: instanzen, zellen, exakt (Zahl der Instanzen mit bewiesenem Optimum), luecke_ub3 (mittel_min, mittel_max), streichen_ub3 und streichen_ub1
    (mittel_min, mittel_max, einzel_min, einzel_max), labels_ub3 und labels_ub1 (mittel_min, mittel_max), kurve_abstand (größter Abstand der Zellenmittel in Prozentpunkten)."""
    s3, s1, l3, l1 = v["streichen_ub3"], v["streichen_ub1"], v["labels_ub3"], v["labels_ub1"]
    return "success", (
        f"Bei der exakten Lücke (im Mittel {fmt_dec(100 * v['luecke_ub3']['mittel_min'], 1)} bis {fmt_dec(100 * v['luecke_ub3']['mittel_max'], 1)}{NBSP}% von LB) werden im Mittel "
        f"{fmt_dec(100 * s3['mittel_min'], 0)} bis {fmt_dec(100 * s3['mittel_max'], 0)}{NBSP}% der Kanten mit zulässiger Route gestrichen (Spanne über die Instanzen {fmt_dec(100 * s3['einzel_min'], 0)} bis "
        f"{fmt_dec(100 * s3['einzel_max'], 0)}{NBSP}%), und das Vorwärts-Labeling erzeugt dann im Mittel {fmt_dec(l3['mittel_min'], 2)} bis {fmt_dec(l3['mittel_max'], 2)} der Labels des vollen Graphen. "
        f"Mit der Lücke aus den Spalten allein (obere Schranke 1) sind es nur {fmt_dec(100 * s1['mittel_min'], 0)} bis {fmt_dec(100 * s1['mittel_max'], 0)}{NBSP}% der Kanten und "
        f"{fmt_dec(l1['mittel_min'], 2)} bis {fmt_dec(l1['mittel_max'], 2)} der Labels. Die exakte Lücke setzt ein schon bewiesenes Optimum voraus, also einen Bestwert der Methode; die Schranken 1 und 2 kommen ohne Aufzählung der Routen aus. Alle Werte: n = 30 Kunden, ng-Gedächtnis k = 8, Partitionierungs-Master, eigene Instanzen, "
        f"{v['zellen']} Zellen mit zusammen {v['instanzen']} Instanzen, {v['exakt']} von {v['instanzen']} mit bewiesenem Optimum; {C.VORBEHALT}. "
        f"Die vier Zellenmittel der Kurve „Kanten mit Wert höchstens x % von LB“ liegen an allen Rasterpunkten höchstens {fmt_dec(v['kurve_abstand'], 1)} Prozentpunkte auseinander; "
        "für Einzelinstanzen gilt das nicht.")


def verdict_gegenprobe(zeilen: list, zaehlung: dict, luecke_pct) -> tuple:
    """Verdikt zu Experiment 5. `zeilen`: je Schwelle {faktor, entfernt, anteil, bleibt (True, False, None), z_rest, zstar}, absteigend von 1,0; `zaehlung`: Zusammenfassung der Gegenprobe;
    `luecke_pct`: exakte Lücke in % von LB oder None."""
    z = zaehlung
    orakel = (f" In der Zählung mit n = 7 bis 10 ({z['faelle']} Fälle, je zur Hälfte elementar und mit ng-Gedächtnis k = 5) ging das Optimum bei der exakten Lücke in "
              f"{z['optimum_verloren_exakt']} Fällen verloren, bei der halben Lücke in {z['optimum_verloren_halb']} von {z['mit_luecke']} Fällen mit Lücke größer null.")
    if luecke_pct is None:
        return "info", "Das exakte Optimum ist für diese Einstellung nicht bewiesen, die Gegenprobe ist hier nicht möglich." + orakel
    if nullen(luecke_pct, 1e-7) == 0:
        return "info", "Die Lücke dieser Instanz ist null: jede Schwelle zwischen 0 und der Lücke ist null, es gibt nichts zu senken." + orakel
    verloren = [r for r in zeilen if r["bleibt"] is False]
    if not verloren:
        return "info", (f"Auf dieser Instanz bleibt das Optimum bei allen {len(zeilen)} geprüften Schwellen bis herab zu {round(100 * zeilen[-1]['faktor'])} % der Lücke erhalten: "
                        "ein Zufall dieser Instanz, die Streichung ist unter der Lücke nicht garantiert." + orakel)
    erste = verloren[0]
    folge = "es gibt keine Zerlegung mehr" if erste["z_rest"] is None else f"das beste ganzzahlige Ergebnis ist {fmt_dec(erste['z_rest'], 2)} statt {fmt_dec(erste['zstar'], 2)}"
    return "warning", (f"**Schwelle zu klein: Optimum verloren.** Auf dieser Instanz geht das Optimum erstmals bei einer Schwelle von {round(100 * erste['faktor'])} % der Lücke verloren "
                       f"({folge}; dort werden {erste['entfernt']} Kanten gestrichen)." + orakel)


# ---------------------------------------------------------------------------------------------------------------------------------
# Eingaben der Verdikte aus den Läufen (reine Funktionen, getrennt testbar)
# ---------------------------------------------------------------------------------------------------------------------------------

GEGENPROBE_FAKTOREN = tuple(round(1 - i / 10, 1) for i in range(11))   # Schwelle in Anteilen der Lücke: 1,0 / 0,9 / … / 0,0


def eingabe_live(live: dict, sch) -> dict:
    """Eingabe für `verdict_live`: bei bewiesenem Optimum die exakte Lücke, sonst die der Schranke 2. `sch` ist `live_schwelle` bei dieser Schwelle (None, wenn nicht bewiesen)."""
    z = live["zeile"]
    if not live["fertig"]:
        return {"fertig": False, "grund": z.get("grund", "unbekannt")}
    exakt = bool(z["ub3_exakt"])
    w = z["wirkung"]["ub3" if exakt else "ub2"]
    return dict(fertig=True, grund=None, exakt=exakt, luecke_pct=100 * w["schwelle"] / z["lb"], entfernt=w["entfernt"], mit_route=z["kanten_mit_route"], labels_voll=z["labels_vorwaerts"],
                labels_gestr=w["labels"], optimum_bleibt=None if sch is None else sch["optimum_bleibt"], zstar=live["zstar"])


def eingabe_schwelle(live: dict, sch: dict, pct: float) -> dict:
    """Eingabe für `verdict_schwelle`: `sch` ist `live_schwelle` bei pct % von LB."""
    z = live["zeile"]
    return dict(pct=pct, luecke_pct=None if live["luecke"] is None else 100 * live["luecke"] / z["lb"], entfernt=sch["entfernt"], mit_route=sch["mit_route"], bleibt=sch["optimum_bleibt"],
                zstar=live["zstar"], z_rest=sch["z_rest"])


def eingabe_obere(live: dict) -> dict:
    """Eingabe für `verdict_obere_schranken`: Lücke (in % von LB) und Zahl gestrichener Kanten der drei Stufen."""
    z = live["zeile"]
    stufen = {s: dict(luecke_pct=100 * z["wirkung"][s]["schwelle"] / z["lb"], entfernt=z["wirkung"][s]["entfernt"]) for s in ("ub1", "ub2", "ub3")}
    return dict(mit_route=z["kanten_mit_route"], exakt=bool(z["ub3_exakt"]), **stufen)


def gegenprobe_zeilen(live: dict, schwelle_fn) -> list:
    """Experiment 5: je Faktor in GEGENPROBE_FAKTOREN die Schwelle faktor · Lücke (nur bei bewiesenem Optimum), `schwelle_fn(schwelle)` liefert `live_schwelle`."""
    if live["luecke"] is None:
        return []
    zeilen = []
    for f in GEGENPROBE_FAKTOREN:
        s = schwelle_fn(f * live["luecke"])
        zeilen.append(dict(faktor=f, schwelle=f * live["luecke"], entfernt=s["entfernt"], anteil=s["entfernt"] / s["mit_route"], bleibt=s["optimum_bleibt"], z_rest=s["z_rest"], zstar=live["zstar"],
                           labels_gestr=s["labels_gestr"]))
    return zeilen


def eingabe_baender(n: int = 30) -> dict:
    """Eingabe für `verdict_baender` aus den festen Messreihen mit n Kunden."""
    import ksp_baender as B
    ue = [B.zellen_uebersicht(z) for z in B.zellen(n)]
    kurven = [B.gitterkurve(z) for z in B.zellen(n)]
    abstand = max(max(k[i] for k in kurven) - min(k[i] for k in kurven) for i in range(len(C.BAND_GRID)))
    lb = B.luecke_bereich(n, "ub3")
    return dict(instanzen=sum(u["instanzen"] for u in ue), zellen=len(ue), exakt=sum(u["ub3_exakt"] for u in ue), luecke_ub3=lb, streichen_ub3=B.bereich(n, "ub3"), streichen_ub1=B.bereich(n, "ub1"),
                labels_ub3=B.bereich(n, "ub3", "labels"), labels_ub1=B.bereich(n, "ub1", "labels"), kurve_abstand=100 * abstand)


def verdict_baender_n50(v: dict) -> tuple:
    """Verdikt zur Reihe mit n = 50 (nur Breite 100). `v`: je Typ („zufall“, „gruppiert“) ein Wörterbuch mit instanzen, fertig, exakt und den Kennzahlen streichen_ub1, streichen_ub2 und
    streichen_ub3 (Mittel als Anteil, Zahl der Instanzen)."""
    teile = []
    for typ in ("zufall", "gruppiert"):
        t = v[typ]
        ub3 = t["streichen_ub3"]
        s3 = (f"bei der exakten Lücke {fmt_dec(100 * ub3['mittel'], 0)}{NBSP}% (nur {ub3['zahl']} Instanzen mit bewiesenem Optimum)" if ub3["zahl"] else "bei der exakten Lücke kein bewiesenes Optimum")
        teile.append(f"{'zufällig' if typ == 'zufall' else 'gruppiert'}: {t['exakt']} von {t['instanzen']} Instanzen mit bewiesenem Optimum, gestrichen im Mittel "
                     f"{fmt_dec(100 * t['streichen_ub1']['mittel'], 0)}{NBSP}% mit Schranke 1, {fmt_dec(100 * t['streichen_ub2']['mittel'], 0)}{NBSP}% mit Schranke 2, {s3}")
    return "info", ("n = 50, Fensterbreite 100, kleine Reihe: " + "; ".join(teile) + f". Wo das Optimum nicht bewiesen ist, gelten die Mittel der exakten Lücke nur für die bewiesenen Instanzen ({C.VORBEHALT}).")
