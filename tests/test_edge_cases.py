"""Randfälle, an denen Kernroutinen erfahrungsgemäß brechen (DEMO-PLAYBOOK §12): ein Kunde, genau zwei Kunden, Last gleich Kapazität, Fenster ohne Spielraum, Kunden am selben Ort,
Dualpreise null, Lücke null, Schwelle sehr groß, Kante ohne zulässige Route, Horizont und Kapazität inklusive, kleinste und größte Live-Einstellung."""

import dataclasses
import math

import pytest

import ksp_algorithm as A
import ksp_constants as C
import ksp_evaluation as E
import ksp_master as M
import ksp_scenario as S


def _mini(punkte, last, frueh, spaet, kap=10, horizont=100.0, svc=1.0):
    """Handgebaute Instanz: Depot = punkte[0], euklidische Abstände (hier ganze Zahlen), Zeitfenster je Kunde."""
    n = len(punkte) - 1
    dist = tuple(tuple(math.dist(a, b) for b in punkte) for a in punkte)
    return S.Instanz(n, tuple(punkte), dist, tuple([0] + list(last)), tuple([0.0] + list(frueh)), tuple([horizont] + list(spaet)), horizont, svc, kap, 0.0)


def test_single_customer():
    """n = 1: eine Route, die untere Schranke ist ihre Länge, die Lücke null, zwei Kanten (D→1, 1→D), beide Pfad-reduzierten Kosten null."""
    inst = _mini([(0, 0), (3, 4)], [2], [0], [50])
    cg = M.spaltenerzeugung(inst, 1)
    assert cg["schranke"] == pytest.approx(10.0) and cg["dual"][1] == pytest.approx(10.0)
    F, B = A.vorwaerts_labeling(inst, cg["dual"], 1), A.rueckwaerts_labeling(inst, cg["dual"], 1)
    P, beste = A.kantenwerte(inst, cg["dual"], F, B, mit_routen=True)
    assert sorted(A.kanten_mit_route(P)) == [(0, 1), (1, 0)] and P[0][1] == pytest.approx(0) and P[1][0] == pytest.approx(0) and beste[(0, 1)] == (1,)
    assert A.gestrichene_kanten(P, 0.0) == set()
    assert M.partition_ganzzahlig(inst, [(1,)])[0] == pytest.approx(10.0)


def test_exactly_two_customers_that_do_not_fit_together_by_load():
    """n = 2: Last 6 + 6 über Kapazität 10, also keine Kante zwischen den Kunden; die Lösung sind zwei Einzelrouten (10 + 20), Lücke null."""
    inst = _mini([(0, 0), (3, 4), (6, 8)], [6, 6], [0, 0], [60, 60])
    assert A.statisch_zulaessig(inst)[1][2] is False
    cg = M.spaltenerzeugung(inst, 2)
    F, B = A.vorwaerts_labeling(inst, cg["dual"], 2), A.rueckwaerts_labeling(inst, cg["dual"], 2)
    P, _ = A.kantenwerte(inst, cg["dual"], F, B)
    assert math.isinf(P[1][2]) and math.isinf(P[2][1])
    assert sorted(A.kanten_mit_route(P)) == [(0, 1), (0, 2), (1, 0), (2, 0)]
    assert cg["schranke"] == pytest.approx(30.0) and M.partition_ganzzahlig(inst, [(1,), (2,)])[0] == pytest.approx(30.0)


def test_two_customers_that_fit_together_get_a_combined_route():
    inst = _mini([(0, 0), (3, 4), (6, 8)], [3, 3], [0, 0], [60, 60])
    cg = M.spaltenerzeugung(inst, 2)
    assert cg["schranke"] == pytest.approx(20.0)                         # die Sammelroute 0-1-2-0 (5 + 5 + 10) kostet 20 gegen 30 für die beiden Einzelfahrten
    alle, _ = A.routen_aufzaehlen(inst, cg["dual"])
    assert {r for r, _ in alle} == {(1,), (2,), (1, 2), (2, 1)}


def test_load_equal_to_the_capacity_is_allowed_and_one_more_is_not():
    for kap, erlaubt in ((10, True), (9, False)):
        inst = _mini([(0, 0), (3, 4), (6, 8)], [4, 6], [0, 0], [60, 60], kap=kap)
        assert A.route_zulaessig(inst, (1, 2)) is erlaubt
        assert (A.statisch_zulaessig(inst)[1][2]) is erlaubt


def test_time_window_without_slack_and_horizon_are_inclusive():
    """Fenster [10, 10]: eine Fahrt der Länge 10 kommt genau an. Rückkehr genau zum Horizont ist erlaubt, eine Zeiteinheit später nicht."""
    inst = _mini([(0, 0), (6, 8)], [1], [10], [10], horizont=21.0, svc=1.0)      # Ankunft 10, Bedienung 1, Rückfahrt 10: Rückkehr 21 = Horizont
    assert A.route_zulaessig(inst, (1,)) is True
    knapp = dataclasses.replace(inst, horizont=20.9)
    assert A.route_zulaessig(knapp, (1,)) is False
    assert A.routen_aufzaehlen(knapp, [0, 0])[0] == []
    assert A.routen_aufzaehlen(inst, [0, 0])[0] == [((1,), 20.0)]


def test_customers_at_the_same_place_have_distance_zero_and_the_ng_neighbourhood_is_still_defined():
    inst = _mini([(0, 0), (3, 4), (3, 4), (6, 8)], [2, 2, 2], [0, 0, 0], [80, 80, 80])
    masken = A.ng_masken(inst, 2)
    assert masken[1] & (1 << 1) and masken[2] & (1 << 2)
    cg = M.spaltenerzeugung(inst, 3)
    assert cg["schranke"] == pytest.approx(20.0)                         # Sammelroute 1-2-3: 5 + 0 + 5 + 10 = 20 gegen 40 für drei Einzelfahrten
    F, B = A.vorwaerts_labeling(inst, cg["dual"], 3), A.rueckwaerts_labeling(inst, cg["dual"], 3)
    P, _ = A.kantenwerte(inst, cg["dual"], F, B)
    assert math.isfinite(P[1][2]) and math.isfinite(P[2][1])


def test_zero_duals_give_the_route_length_as_the_edge_value():
    inst = S.make_instance(7, 3, 100)
    dual = [0.0] * 8
    F, B = A.vorwaerts_labeling(inst, dual, 7), A.rueckwaerts_labeling(inst, dual, 7)
    P, _ = A.kantenwerte(inst, dual, F, B)
    for (i, j) in A.kanten_mit_route(P):
        untergrenze = inst.dist[i][j] + (inst.dist[0][i] if i and j else 0.0) + (inst.dist[j][0] if i and j else 0.0)
        assert P[i][j] >= untergrenze - 1e-9                               # Dreiecksungleichung: jede Route über die Kante ist mindestens so lang
    alle, _ = A.routen_aufzaehlen(inst, dual)
    assert F["bester_wert"] == pytest.approx(min(A.weg_laenge(inst, r) for r, _ in alle))      # ohne Dualpreise ist die kürzeste Route die einzelne Fahrt zum nächsten Kunden


def test_a_very_large_threshold_removes_nothing_and_a_negative_one_removes_everything_with_a_route(hand, hand_dual):
    F, B = A.vorwaerts_labeling(hand, hand_dual, 6), A.rueckwaerts_labeling(hand, hand_dual, 6)
    P, _ = A.kantenwerte(hand, hand_dual, F, B)
    assert A.gestrichene_kanten(P, 1e9) == set()
    assert A.gestrichene_kanten(P, -1.0) == set(A.kanten_mit_route(P))


def test_gap_zero_instance_keeps_only_zero_edges_and_labels_still_find_the_best_value():
    """Instanz mit Lücke null (n = 7, Breite 40, Zufalls-Seed 70, k = 7): bei der exakten Lücke bleiben nur Kanten mit Wert null."""
    live = E.live_lauf(E.LiveEinstellung(7, "zufällig", 40, 70, 7))
    assert live["fertig"] and live["luecke"] == pytest.approx(0.0, abs=1e-9)
    s = E.live_schwelle(live, live["luecke"])
    assert s["optimum_bleibt"] is True
    P = live["intern"]["P"]
    bleibt = [e for e in A.kanten_mit_route(P) if e not in s["gestrichen"]]
    assert bleibt and all(abs(P[i][j]) <= 1e-6 for (i, j) in bleibt)


def test_live_run_with_the_smallest_and_the_largest_n_and_widths():
    for e in (E.LiveEinstellung(C.LIVE_N_MIN, "zufällig", min(C.LIVE_BREITEN), 0, C.LIVE_K_MIN), E.LiveEinstellung(C.LIVE_N_MIN, "gruppiert", max(C.LIVE_BREITEN), C.SEED_MAX, C.LIVE_K_MAX)):
        live = E.live_lauf(e)
        assert live["fertig"] and live["zeile"]["ub3_exakt"] and live["fehler"] is None
        assert live["k"] <= e.n


def test_ng_memory_larger_than_n_is_capped_at_n():
    inst, k = E.live_instanz(E.LiveEinstellung(6, "zufällig", 40, 1, 12))
    assert k == 6 and inst.n == 6


def test_label_cap_marks_the_analysis_as_not_finished():
    inst = S.make_instance(10, 1, 100)
    zeile, intern = E.analyse_instanz(inst, 10, max_labels=20)
    assert zeile["fertig"] is False and intern is None and "Obergrenze" in zeile["grund"]
    v = E.verdict_live(E.eingabe_live({"zeile": zeile, "fertig": False}, None))
    assert v[0] == "error" and "nicht fertig" in v[1]


def test_route_enumeration_cap_makes_the_optimum_unproven():
    inst = S.make_instance(9, 1, 100, gruppiert=True)
    zeile, _ = E.analyse_instanz(inst, 9, max_routen=5)
    assert zeile["fertig"] and zeile["ub3_exakt"] is False and zeile["aufzaehlung_vollstaendig"] is False and zeile["ub3"] <= zeile["ub2"] + 1e-9


def test_percent_helpers_do_not_divide_by_zero():
    assert E.anteil(0, 0) is None and E.anteil(1, 4) == 0.25
    assert E.nullen(-1e-13) == 0.0 and E.fmt_dec(E.nullen(-1e-13), 2) == "0,00"
    assert E.satz_labels(0, 0).startswith("Im vollen Graphen werden keine Labels erzeugt")
