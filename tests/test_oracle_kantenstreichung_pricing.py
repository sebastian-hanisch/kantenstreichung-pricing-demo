"""Orakel-Test: Pfad-reduzierte Kosten, Streichregel und Optimum gegen einen UNABHÄNGIGEN Rechenweg (DEMO-PLAYBOOK §12, ORACLE-PLAYBOOK §2 und §5).

Der Rechenweg des Orakels benutzt nichts aus `ksp_algorithm` und `ksp_master`: eine eigene Tiefensuche mit Stapel (`unabhaengige_routen`, conftest.py) zählt alle zulässigen elementaren Routen,
die reduzierten Kosten rechnet der Test selbst, das Master-LP löst `scipy.optimize.linprog` über alle Routen (Dualpreise und Wert der Konvergenz kommen aus der Spaltenerzeugung der Demo und
werden gegen dieses LP geprüft), das ganzzahlige Optimum liefert eine eigene Rekursion über den kleinsten offenen Kunden (`unabhaengige_partition`).

Geprüft wird je Instanz (n = 6 bis 8, Fensterbreite 40 und 100, zufällig und gruppiert, feste Zufalls-Seeds), mit ng-Gedächtnis k = n (elementar) und k = 3:
A  Gültigkeit: Pfad-reduzierte Kosten nie größer als die kleinsten reduzierten Kosten der aufgezählten Routen über die Kante (Toleranz 1e-6); endlich genau dort, wo eine Route existiert;
B  k = n: Gleichheit mit dem wahren Wert;
C  Dualzulässigkeit der Dualpreise gegen ALLE aufgezählten Routen und Summe der Dualpreise = Wert des Masters = Wert des unabhängigen LP über alle Routen;
D  Streichen mit der exakten Lücke z* − LB: keine Route mit reduzierten Kosten ≤ Lücke verliert eine Kante, das Optimum über die Routen ohne gestrichene Kante ist z*;
E  Gegenprobe (Trennschärfe): bei der halben Lücke geht das Optimum in mindestens einem Fall verloren, sonst wäre der Test zu schwach;
F  das beste Endlabel des Vorwärts-Labelings (k = n) ist die kleinste reduzierte Kosten aller aufgezählten Routen."""

import math

import numpy as np
import pytest

import ksp_algorithm as A
import ksp_master as M
import ksp_scenario as S
from conftest import unabhaengige_partition, unabhaengige_routen

TOL = 1e-6


def _fall(n, breite, gruppiert, seed, k):
    """Eine Instanz durchrechnen: Demo-Kern gegen den unabhängigen Rechenweg. Rückgabe ein Wörterbuch mit den Zahlen für die Prüfungen."""
    inst = S.make_instance(n, seed, breite, gruppiert=gruppiert)
    d = lambda i, j: inst.dist[i][j]                                          # noqa: E731
    routen = unabhaengige_routen(n, None, d, inst.frueh, inst.spaet, inst.last, inst.kapazitaet, inst.horizont, inst.bedienzeit)
    cg = M.spaltenerzeugung(inst, k)
    dual = cg["dual"]
    rc = {r: sum(d(a, b) for a, b in zip((0,) + r, r + (0,))) - sum(dual[j] for j in r) for r in routen}
    laenge = {r: sum(d(a, b) for a, b in zip((0,) + r, r + (0,))) for r in routen}
    F = A.vorwaerts_labeling(inst, dual, k)
    B = A.rueckwaerts_labeling(inst, dual, k)
    P, _ = A.kantenwerte(inst, dual, F, B)
    wahr = {}
    for r, wert in rc.items():
        for a, b in zip((0,) + r, r + (0,)):
            wahr[(a, b)] = min(wert, wahr.get((a, b), math.inf))
    zstar, _ = unabhaengige_partition(n, laenge)
    return dict(inst=inst, routen=routen, cg=cg, dual=dual, rc=rc, laenge=laenge, F=F, P=P, wahr=wahr, zstar=zstar, k=k, n=n)


def _optimum_ohne(f, schwelle):
    """Optimum über die Routen ohne gestrichene Kante (Streichen mit der Schwelle, eigene Rechnung): Rückgabe (Wert oder None, Zahl der Routen mit rc ≤ Schwelle an einer gestrichenen Kante)."""
    P, wahr = f["P"], f["wahr"]
    weg = {e for e in wahr if P[e[0]][e[1]] > schwelle + TOL}
    uebrig = {r: c for r, c in f["laenge"].items() if not any(e in weg for e in zip((0,) + r, r + (0,)))}
    verletzt = sum(1 for r, w in f["rc"].items() if w <= schwelle + TOL and r not in uebrig)
    return unabhaengige_partition(f["n"], uebrig)[0], verletzt


FAELLE = [(n, b, g, 1400 + s + 10 * n) for n in (6, 7, 8) for b in (40, 100) for g in (False, True) for s in range(5)]


@pytest.fixture(scope="module")
def faelle():
    return {(n, b, g, seed, k): _fall(n, b, g, seed, k) for (n, b, g, seed) in FAELLE for k in (n, 3)}


def test_A_B_pathrc_is_valid_and_equal_to_the_true_value_for_elementary_memory(faelle):
    mit_abstand = 0
    for (n, _b, _g, _seed, k), f in faelle.items():
        P, wahr = f["P"], f["wahr"]
        for i in range(n + 1):
            for j in range(n + 1):
                if i == j:
                    continue
                if (i, j) in wahr:
                    assert P[i][j] <= wahr[(i, j)] + TOL, (f["k"], i, j)       # A: nie über dem wahren Wert, und endlich
                    if k == n:
                        assert abs(P[i][j] - wahr[(i, j)]) <= TOL, (n, i, j)   # B: bei k = n gleich
                    elif P[i][j] < wahr[(i, j)] - TOL:
                        mit_abstand += 1
                else:
                    assert P[i][j] == math.inf, (k, i, j)                      # keine zulässige Route: unendlich
    assert mit_abstand > 0                                                    # die Prüfung A ist nicht leer: bei k = 3 liegt der Wert an einigen Kanten echt darunter


def test_C_duals_are_dual_feasible_against_all_routes_and_sum_to_the_master_value(faelle):
    from scipy.optimize import linprog
    for (n, _b, _g, _seed, k), f in faelle.items():
        assert min(f["rc"].values()) >= -1e-6, (n, k)                           # Dualzulässigkeit gegen alle aufgezählten elementaren Routen
        assert sum(f["dual"]) == pytest.approx(f["cg"]["schranke"], abs=1e-6)
        if k == n:
            routen = list(f["routen"])
            a = np.zeros((n, len(routen)))
            for c, r in enumerate(routen):
                for j in r:
                    a[j - 1, c] = 1
            lp = linprog([f["laenge"][r] for r in routen], A_eq=a, b_eq=np.ones(n), bounds=(0, None), method="highs")
            assert f["cg"]["schranke"] == pytest.approx(lp.fun, abs=1e-6)       # die Schranke der Spaltenerzeugung ist der Wert des LP über alle Routen
        assert f["cg"]["schranke"] <= f["zstar"] + 1e-6                          # untere Schranke


def test_D_cutting_at_the_exact_gap_keeps_every_cheap_route_and_the_optimum(faelle):
    luecken = 0
    for f in faelle.values():
        luecke = f["zstar"] - f["cg"]["schranke"]
        assert luecke >= -1e-6
        z, verletzt = _optimum_ohne(f, luecke)
        assert verletzt == 0 and z == pytest.approx(f["zstar"], abs=1e-6), (f["n"], f["k"])
        luecken += luecke > 1e-6
    assert luecken > 20                                                        # genug Fälle mit Lücke größer null, sonst prüft D fast nichts


def test_E_cutting_at_half_the_gap_loses_the_optimum_in_some_cases(faelle):
    verloren = 0
    for f in faelle.values():
        luecke = f["zstar"] - f["cg"]["schranke"]
        if luecke <= 1e-6:
            continue
        z, _ = _optimum_ohne(f, 0.5 * luecke)
        verloren += z is None or z > f["zstar"] + 1e-6
    assert verloren >= 5                                                       # Trennschärfe: eine zu kleine Schwelle wird bemerkt


def test_F_best_end_label_is_the_smallest_reduced_cost_of_all_routes(faelle):
    for (n, _b, _g, _seed, k), f in faelle.items():
        if k == n:
            assert f["F"]["bester_wert"] == pytest.approx(min(f["rc"].values()), abs=1e-6)


def test_G_the_demo_partition_agrees_with_the_independent_recursion_and_highs(faelle):
    for f in list(faelle.values())[:40]:
        wert, loesung, bewiesen = M.partition_ganzzahlig(f["inst"], list(f["routen"]))
        assert bewiesen and wert == pytest.approx(f["zstar"], abs=1e-6)
        assert sum(f["laenge"][r] for r in loesung) == pytest.approx(wert, abs=1e-6)
        assert sorted(j for r in loesung for j in r) == list(range(1, f["n"] + 1))


def test_H_kept_edges_contain_every_edge_of_every_route_with_small_reduced_cost(faelle):
    """Umkehrung von D auf Kantenebene: bei Schwelle gleich der Lücke bleibt jede Kante jeder Route mit reduzierten Kosten höchstens Lücke erhalten."""
    for f in faelle.values():
        luecke = f["zstar"] - f["cg"]["schranke"]
        weg = A.gestrichene_kanten(f["P"], luecke)
        for r, w in f["rc"].items():
            if w <= luecke + TOL:
                assert not any(e in weg for e in A.route_kanten(r))


def test_the_orakel_covers_60_instances_with_two_memory_sizes_each(faelle):
    assert len(FAELLE) == 60 and len(faelle) == 120 and {f["k"] for f in faelle.values()} == {3, 6, 7, 8}
