"""Kern gegen Handrechnung auf der Mini-Instanz (Handbeispiel, siehe conftest.py): jede Einheit einzeln (Erweiterungsregel, Dominanzregel, Verbinden, Streichen, Master, Partitionierung),
dazu der Worst-Case am Regler-Maximum (Timeout statt Zeitprüfung, DEMO-PLAYBOOK §1c)."""

import concurrent.futures
import dataclasses
import math

import pytest

import ksp_algorithm as A
import ksp_constants as C
import ksp_evaluation as E
import ksp_master as M
import ksp_scenario as S
from conftest import HAND_DEPOT, HAND_DUAL, HAND_KUNDEN, HAND_LB, HAND_ZSTAR, manhattan, unabhaengige_routen


def _d(i, j):
    """Handbeispiel: Manhattan-Abstand zwischen zwei Knoten (0 = Depot)."""
    a = HAND_DEPOT if i == 0 else HAND_KUNDEN[i][0]
    b = HAND_DEPOT if j == 0 else HAND_KUNDEN[j][0]
    return manhattan(a, b)


def _hand_routen():
    n = 6
    frueh = {0: 0, **{i: HAND_KUNDEN[i][1][0] for i in HAND_KUNDEN}}
    spaet = {0: 40, **{i: HAND_KUNDEN[i][1][1] for i in HAND_KUNDEN}}
    last = {0: 0, **{i: HAND_KUNDEN[i][2] for i in HAND_KUNDEN}}
    return unabhaengige_routen(n, None, _d, frueh, spaet, last, 8, 40, 2)


# ---------------------------------------------------------------------------------------------------------------------------------
# Instanz und Routen
# ---------------------------------------------------------------------------------------------------------------------------------

def test_hand_instance_has_the_documented_data(hand):
    assert hand.n == 6 and hand.kapazitaet == 8 and hand.horizont == 40 and hand.bedienzeit == 2
    for i, (ort, fenster, bedarf) in HAND_KUNDEN.items():
        assert hand.punkte[i] == ort and (hand.frueh[i], hand.spaet[i]) == fenster and hand.last[i] == bedarf
    assert hand.dist[0][4] == 10 and hand.dist[1][3] == 4          # |5−10| + |5−0|, |1−1| + |4−0|


def test_route_edges_and_length_by_hand(hand):
    assert A.route_kanten((1, 3, 5)) == [(0, 1), (1, 3), (3, 5), (5, 0)]
    assert A.weg_laenge(hand, (1, 3, 5)) == _d(0, 1) + _d(1, 3) + _d(3, 5) + _d(5, 0) == 18
    assert A.weg_laenge(hand, (6,)) == 4 and A.weg_laenge(hand, (4, 2)) == 24


def test_reduced_cost_of_a_route_is_length_minus_the_prices(hand, hand_dual):
    assert A.route_kosten(hand, hand_dual, (1, 3, 5)) == 18 - (6 + 6 + 6) == 0
    assert A.route_kosten(hand, hand_dual, (4, 2)) == 24 - (16 + 6) == 2
    assert A.route_kosten(hand, hand_dual, (6,)) == 4 - 4 == 0


@pytest.mark.parametrize("route, ok, grund", [
    ((1, 3, 5), True, "optimale Route"),
    ((4, 2), True, "optimale Route"),
    ((1, 1), False, "Kunde zweimal"),
    ((1, 2, 4), False, "Last 9 über Kapazität 8"),
    ((2, 1), False, "Ankunft in 1 um 28 nach dem Fensterende 21"),
    ((), False, "leere Route"),
    ((7,), False, "Kunde gibt es nicht"),
])
def test_route_checker(hand, route, ok, grund):
    assert A.route_zulaessig(hand, route) is ok, grund


def test_the_enumeration_finds_the_45_routes_of_the_hand_calculation(hand):
    alle, vollstaendig = A.routen_aufzaehlen(hand, [0] * 7)
    assert vollstaendig and len(alle) == len(_hand_routen()) == 45
    assert {r for r, _ in alle} == set(_hand_routen())
    assert all(A.route_zulaessig(hand, r) for r, _ in alle)


def test_the_enumeration_stops_at_the_cap_and_says_so(hand):
    alle, vollstaendig = A.routen_aufzaehlen(hand, [0] * 7, max_routen=10)
    assert not vollstaendig and len(alle) == 10


# ---------------------------------------------------------------------------------------------------------------------------------
# ng-Gedächtnis
# ---------------------------------------------------------------------------------------------------------------------------------

def test_ng_memory_of_k_equal_n_is_everybody(hand):
    alle = sum(1 << j for j in range(1, 7))
    assert A.ng_masken(hand, 6)[1:] == [alle] * 6


def test_ng_memory_of_k_two_is_the_customer_and_its_nearest_neighbour(hand):
    """Kunde 3 (1, 0): nächster Nachbar ist Kunde 5 (Abstand 1); Kunde 5: nächster ist Kunde 3; Kunde 4 (10, 0): nächster ist Kunde 6 oder 2 (Abstand 8, kleinere Nummer 2)."""
    m = A.ng_masken(hand, 2)
    assert m[3] == (1 << 3) | (1 << 5) and m[5] == (1 << 5) | (1 << 3)
    assert _d(4, 2) == _d(4, 5) == _d(4, 6) == 8 and m[4] == (1 << 4) | (1 << 2)


# ---------------------------------------------------------------------------------------------------------------------------------
# Erweiterungsregel und Dominanzregel
# ---------------------------------------------------------------------------------------------------------------------------------

def test_forward_extension_from_the_depot_to_customer_4(hand, hand_dual):
    """Ankunft 10, Fenster ab 16: die Bedienung beginnt um 16; Kosten 10 − Dualpreis 16 = −6; Last 4 (Beispiel der Handrechnung)."""
    neu = A.vorwaerts_erweitern(hand, hand_dual, A.ng_masken(hand, 6), A.vorwaerts_start(), 4)
    assert (neu[A.T], neu[A.K], neu[A.Q], neu[A.N]) == (max(_d(0, 4), 16), _d(0, 4) - 16, 4, 4) == (16, -6, 4, 4)
    assert neu[A.M] == 1 << 4


def test_forward_extension_checks_memory_load_and_window(hand, hand_dual):
    masken = A.ng_masken(hand, 6)
    start = A.vorwaerts_start()
    nach2 = A.vorwaerts_erweitern(hand, hand_dual, masken, start, 2)         # Beginn um 21
    assert nach2[A.T] == 21
    assert A.vorwaerts_erweitern(hand, hand_dual, masken, nach2, 2) is None   # Gedächtnis: Kunde 2 schon besucht
    assert A.vorwaerts_erweitern(hand, hand_dual, masken, nach2, 1) is None   # 21 + 2 + 5 = 28 nach dem Fensterende 21


def test_forward_extension_checks_the_capacity(hand, hand_dual):
    """Ein Label an Kunde 1 mit Last 6: Kunde 3 (Last 2) passt genau (8 = Kapazität), Kunde 4 (Last 4) nicht, obwohl das Fenster erreichbar wäre."""
    masken = A.ng_masken(hand, 6)
    label = [5.0, -1.0, 6, 1 << 1, 1, -1, False]
    assert A.vorwaerts_erweitern(hand, hand_dual, masken, label, 3)[A.Q] == 8
    assert A.vorwaerts_erweitern(hand, hand_dual, masken, label, 4) is None


def test_forward_extension_is_inclusive_at_the_window_end_and_the_capacity(hand, hand_dual):
    masken = A.ng_masken(hand, 6)
    nach1 = A.vorwaerts_erweitern(hand, hand_dual, masken, A.vorwaerts_start(), 1)     # Beginn um 5
    nach13 = A.vorwaerts_erweitern(hand, hand_dual, masken, nach1, 3)                  # 5 + 2 + 4 = 11 ≥ 10: Beginn 11
    assert nach13[A.T] == 11 and nach13[A.Q] == 4
    nach134 = A.vorwaerts_erweitern(hand, hand_dual, masken, nach13, 4)                # Last 8 = Kapazität erlaubt, 11 + 2 + 9 = 22
    assert nach134 is not None and nach134[A.Q] == 8 and nach134[A.T] == 22
    knapp = dataclasses.replace(hand, spaet=tuple(11 if i == 3 else x for i, x in enumerate(hand.spaet)))   # Fensterende von Kunde 3 genau bei der Ankunft 11
    assert A.vorwaerts_erweitern(knapp, hand_dual, masken, nach1, 3) is not None
    zu_knapp = dataclasses.replace(hand, spaet=tuple(10 if i == 3 else x for i, x in enumerate(hand.spaet)))
    assert A.vorwaerts_erweitern(zu_knapp, hand_dual, masken, nach1, 3) is None


def test_forward_dominance_rule_component_by_component():
    a = [10, -5.0, 4, 0b0010, 1, -1, False]
    assert A.vorwaerts_dominiert(a, [10, -5.0, 4, 0b0010, 1, -1, False])      # gleich: dominiert (Gleichstand zählt)
    assert A.vorwaerts_dominiert(a, [11, -4.0, 5, 0b0110, 1, -1, False])      # in allem besser oder gleich, Gedächtnis Teilmenge
    assert not A.vorwaerts_dominiert(a, [9, -5.0, 4, 0b0010, 1, -1, False])   # später
    assert not A.vorwaerts_dominiert(a, [10, -6.0, 4, 0b0010, 1, -1, False])  # teurer
    assert not A.vorwaerts_dominiert(a, [10, -5.0, 3, 0b0010, 1, -1, False])  # schwerer
    assert not A.vorwaerts_dominiert(a, [10, -5.0, 4, 0b0001, 1, -1, False])  # merkt sich einen Kunden, den das andere nicht kennt


def test_backward_extension_to_customer_2(hand, hand_dual):
    """Rest „2, dann Depot“: spätester Beginn min(Fensterende 32, 40 − 2 − 6) = 32; Kosten d(2,0) = 6 (ohne den Dualpreis des Anfangskunden); Last 3."""
    neu = A.rueckwaerts_erweitern(hand, hand_dual, A.ng_masken(hand, 6), A.rueckwaerts_start(hand), 2)
    assert (neu[A.T], neu[A.K], neu[A.Q]) == (min(32, 40 - 2 - _d(2, 0)), _d(2, 0), 3) == (32, 6, 3)
    nach_1 = A.rueckwaerts_erweitern(hand, hand_dual, A.ng_masken(hand, 6), neu, 1)    # Kunde 1 vor Kunde 2: 32 − 2 − 5 = 25, Fensterende 21 → 21
    assert nach_1[A.T] == 21 and nach_1[A.K] == 6 + _d(1, 2) - hand_dual[2] == 5 and nach_1[A.Q] == 5


def test_backward_extension_rejects_a_start_before_the_window_opens(hand, hand_dual):
    masken = A.ng_masken(hand, 6)
    nach_2 = A.rueckwaerts_erweitern(hand, hand_dual, masken, A.rueckwaerts_start(hand), 2)
    assert A.rueckwaerts_erweitern(hand, hand_dual, masken, nach_2, 2) is None          # Gedächtnis
    nach_6 = A.rueckwaerts_erweitern(hand, hand_dual, masken, A.rueckwaerts_start(hand), 6)   # spätester Beginn min(25, 40 − 2 − 2) = 25
    assert nach_6[A.T] == 25
    assert A.rueckwaerts_erweitern(hand, hand_dual, masken, nach_2, 6) is not None


def test_backward_dominance_rule_component_by_component():
    a = [20, 3.0, 4, 0b0010, 1, -1, False]
    assert A.rueckwaerts_dominiert(a, [20, 3.0, 4, 0b0010, 1, -1, False])
    assert A.rueckwaerts_dominiert(a, [19, 4.0, 5, 0b0110, 1, -1, False])
    assert not A.rueckwaerts_dominiert(a, [21, 3.0, 4, 0b0010, 1, -1, False])   # darf später beginnen
    assert not A.rueckwaerts_dominiert(a, [20, 2.0, 4, 0b0010, 1, -1, False])
    assert not A.rueckwaerts_dominiert(a, [20, 3.0, 3, 0b0010, 1, -1, False])
    assert not A.rueckwaerts_dominiert(a, [20, 3.0, 4, 0b0001, 1, -1, False])


# ---------------------------------------------------------------------------------------------------------------------------------
# Labeling im Handbeispiel
# ---------------------------------------------------------------------------------------------------------------------------------

def test_hand_labeling_counts_forward_and_backward(hand, hand_dual):
    F = A.vorwaerts_labeling(hand, hand_dual, 6)
    B = A.rueckwaerts_labeling(hand, hand_dual, 6)
    assert (F["erzeugt"], sum(len(a) for a in F["ueberlebende"])) == (33, 21)
    assert (B["erzeugt"], sum(len(a) for a in B["ueberlebende"]) - 1) == (37, 18)
    assert F["bester_wert"] == 0 and not F["abgebrochen"]
    assert F["dominiert"] == (F["erzeugt"] - 1) - 21 == 11            # erzeugte Labels ohne den Start = überlebende + dominierte


def test_hand_forward_survivors_at_customer_4(hand, hand_dual):
    """Drei Labels am Kunden 4 (Handrechnung): (16, −6, 4, {4}), (19, −10, 7, {4, 6}), (22, −10, 8, {1, 3, 4})."""
    F = A.vorwaerts_labeling(hand, hand_dual, 6)
    labels = sorted((F["labels"][x][A.T], F["labels"][x][A.K], F["labels"][x][A.Q], A.vorwaerts_route(F, x)) for x in F["ueberlebende"][4])
    assert labels == [(16, -6, 4, (4,)), (19, -10, 7, (6, 4)), (22, -10, 8, (1, 3, 4))]


def test_hand_forward_pricing_finds_no_negative_route_at_the_duals_of_convergence(hand, hand_dual):
    F = A.vorwaerts_labeling(hand, hand_dual, 6, mit_ende=True)
    assert F["bester_wert"] == 0 and all(rc >= 0 for rc, _ in F["ende"])
    routen = {A.vorwaerts_route(F, li) for rc, li in F["ende"] if rc == 0}
    assert (1, 3, 5) in routen and (6,) in routen and (6, 4) in routen


def test_label_cap_stops_the_labeling_and_says_so(hand, hand_dual):
    F = A.vorwaerts_labeling(hand, hand_dual, 6, max_labels=5)
    assert F["abgebrochen"] and F["erzeugt"] < 33
    B = A.rueckwaerts_labeling(hand, hand_dual, 6, max_labels=5)
    assert B["abgebrochen"]


# ---------------------------------------------------------------------------------------------------------------------------------
# Verbinden, Streichen
# ---------------------------------------------------------------------------------------------------------------------------------

@pytest.fixture
def hand_werte(hand, hand_dual):
    F = A.vorwaerts_labeling(hand, hand_dual, 6)
    B = A.rueckwaerts_labeling(hand, hand_dual, 6)
    P, beste = A.kantenwerte(hand, hand_dual, F, B, mit_routen=True)
    return P, beste, F, B


def test_path_reduced_costs_of_two_edges_by_hand(hand_werte):
    P, beste, _F, _B = hand_werte
    assert P[4][5] == (_d(4, 5) + _d(0, 4) + _d(5, 0)) - (HAND_DUAL[4] + HAND_DUAL[5]) == 4        # Route 4 → 5: 10 + 8 + 8 = 26, minus 22
    assert P[0][4] == (_d(0, 4) + _d(4, 2) + _d(2, 0)) - (HAND_DUAL[4] + HAND_DUAL[2]) == 2        # Route 4 → 2: 10 + 8 + 6 = 24, minus 22
    assert beste[(4, 5)] == (4, 5) and beste[(0, 4)] == (4, 2)


def test_every_path_value_is_the_minimum_over_the_enumerated_routes(hand_werte, hand):
    """Gegenprobe zur Handrechnung: kleinste reduzierte Kosten aller aufgezählten Routen über die Kante; Kanten ohne Route haben den Wert unendlich."""
    P = hand_werte[0]
    kleinste = {}
    for r in _hand_routen():
        rc = sum(_d(a, b) for a, b in A.route_kanten(r)) - sum(HAND_DUAL[j] for j in r)
        for e in A.route_kanten(r):
            kleinste[e] = min(rc, kleinste.get(e, math.inf))
    for i in range(7):
        for j in range(7):
            if i != j:
                assert P[i][j] == kleinste.get((i, j), math.inf), (i, j)
    assert len(A.kanten_mit_route(P)) == len(kleinste) == 31


def test_each_best_route_of_an_edge_is_feasible_uses_the_edge_and_has_the_value(hand_werte, hand, hand_dual):
    P, beste, _F, _B = hand_werte
    for (i, j), r in beste.items():
        assert A.route_zulaessig(hand, r) and (i, j) in A.route_kanten(r)
        assert A.route_kosten(hand, hand_dual, r) == P[i][j]


def test_statically_feasible_edges_contain_every_edge_with_a_route(hand, hand_werte):
    stat = A.statisch_zulaessig(hand)
    assert all(stat[i][j] for (i, j) in A.kanten_mit_route(hand_werte[0]))
    assert stat[1][4] is True                            # 5 + 2 + 13 = 20 ≤ 28 und Last 6 ≤ 8: für sich zulässig
    assert stat[2][1] is False                           # 21 + 2 + 5 = 28 > 21


def test_threshold_two_removes_13_of_31_edges_and_keeps_the_optimal_solution(hand_werte):
    P = hand_werte[0]
    weg = A.gestrichene_kanten(P, 2)
    assert len(weg) == 13 and len(A.kanten_mit_route(P)) == 31
    assert weg == {(0, 2), (0, 5), (1, 0), (1, 4), (1, 6), (3, 0), (3, 1), (3, 6), (4, 5), (6, 1), (6, 2), (6, 3), (6, 5)}
    loesung = {e for r in [(1, 3, 5), (4, 2), (6,)] for e in A.route_kanten(r)}
    assert not (loesung & weg)


@pytest.mark.parametrize("schwelle, entfernt", [(0, 17), (1, 17), (2, 13), (3, 13), (4, 5), (5, 5), (6, 0), (100, 0)])
def test_number_of_removed_edges_by_threshold(hand_werte, schwelle, entfernt):
    assert len(A.gestrichene_kanten(hand_werte[0], schwelle)) == entfernt


def test_removal_is_monotone_in_the_threshold(hand_werte):
    P = hand_werte[0]
    vorher = None
    for s in range(0, 8):
        weg = A.gestrichene_kanten(P, s)
        if vorher is not None:
            assert weg <= vorher
        vorher = weg


def test_the_allowed_matrix_and_the_removed_set_are_complements_among_the_edges_with_a_route(hand_werte):
    P = hand_werte[0]
    erl = A.erlaubt_matrix(6, P, 2)
    weg = A.gestrichene_kanten(P, 2)
    for (i, j) in A.kanten_mit_route(P):
        assert erl[i][j] == ((i, j) not in weg)
    assert not any(erl[i][j] for i in range(7) for j in range(7) if (i, j) not in A.kanten_mit_route(P))


def test_labeling_in_the_cut_graph_creates_20_labels_instead_of_33_with_the_same_best_value(hand, hand_dual, hand_werte):
    P = hand_werte[0]
    G = A.vorwaerts_labeling(hand, hand_dual, 6, erlaubt=A.erlaubt_matrix(6, P, 2))
    assert (G["erzeugt"], sum(len(a) for a in G["ueberlebende"])) == (20, 18)
    assert G["bester_wert"] == 0 == A.vorwaerts_labeling(hand, hand_dual, 6)["bester_wert"]


def test_routes_without_a_removed_edge_are_16_of_45(hand_werte):
    weg = A.gestrichene_kanten(hand_werte[0], 2)
    assert sum(1 for r in _hand_routen() if A.route_ohne(r, weg)) == 16


def test_routes_up_to_the_threshold_are_exactly_the_routes_with_small_reduced_cost(hand, hand_dual, hand_werte):
    P, _b, _F, B = hand_werte
    gefunden, vollstaendig = A.routen_bis(hand, hand_dual, P, 2, B)
    erwartet = {r for r in _hand_routen() if sum(_d(a, b) for a, b in A.route_kanten(r)) - sum(HAND_DUAL[j] for j in r) <= 2}
    assert vollstaendig and set(gefunden) == erwartet and len(gefunden) == len(erwartet)


def test_the_cap_of_the_bounded_enumeration_is_reported(hand, hand_dual, hand_werte):
    P, _b, _F, B = hand_werte
    gefunden, vollstaendig = A.routen_bis(hand, hand_dual, P, 100, B, max_routen=5)
    assert not vollstaendig and len(gefunden) == 5


# ---------------------------------------------------------------------------------------------------------------------------------
# Master und ganzzahlige Partitionierung
# ---------------------------------------------------------------------------------------------------------------------------------

def test_exact_master_gives_lb_44_and_the_duals_of_the_hand_calculation(hand):
    routen = sorted(_hand_routen(), key=lambda r: (len(r), r))
    kosten = [A.weg_laenge(hand, r) for r in routen]
    lb, dual, x = M.master_exakt(6, kosten, routen)
    assert lb == HAND_LB and [int(d) for d in dual[1:]] == [HAND_DUAL[i] for i in range(1, 7)] and dual[0] == 0
    assert sum(dual) == lb
    for i in range(1, 7):                                  # Partitionierung: jeder Kunde genau einmal
        assert sum(xv for r, xv in zip(routen, x) if i in r) == 1
    assert sum(c * xv for c, xv in zip(kosten, x)) == lb
    assert any(xv.denominator != 1 for xv in x)            # die LP-Lösung ist gebrochen


def test_hand_duals_are_dual_feasible_for_every_route(hand_dual, hand):
    assert all(A.route_kosten(hand, hand_dual, r) >= 0 for r in _hand_routen())
    assert sum(1 for r in _hand_routen() if A.route_kosten(hand, hand_dual, r) == 0) == 7


def test_exact_master_agrees_with_highs_on_the_value(hand):
    routen = sorted(_hand_routen(), key=lambda r: (len(r), r))
    kosten = [A.weg_laenge(hand, r) for r in routen]
    lb_exakt = M.master_exakt(6, kosten, routen)[0]
    lb_highs, dual, _x = M.master_lp(6, kosten, routen)
    assert lb_highs == pytest.approx(float(lb_exakt), abs=1e-9) and sum(dual) == pytest.approx(lb_highs, abs=1e-9)


def test_integer_optimum_is_46_with_the_three_routes_of_the_hand_calculation(hand):
    routen = _hand_routen()
    for verfahren in (M.partition_teilmengen, M.partition_milp, M.partition_ganzzahlig):
        wert, loesung, bewiesen = verfahren(hand, routen)
        assert wert == pytest.approx(HAND_ZSTAR) and bewiesen and sorted(loesung) == [(1, 3, 5), (4, 2), (6,)]
    assert M.partition_brute(hand, routen)[0] == HAND_ZSTAR


def test_integer_optimum_without_the_removed_edges_stays_46_and_with_threshold_one_it_is_50(hand, hand_werte):
    P = hand_werte[0]
    for schwelle, erwartet in ((2, 46), (1, 50)):
        weg = A.gestrichene_kanten(P, schwelle)
        uebrig = [r for r in _hand_routen() if A.route_ohne(r, weg)]
        assert M.partition_ganzzahlig(hand, uebrig)[0] == pytest.approx(erwartet) == pytest.approx(M.partition_brute(hand, uebrig)[0])


def test_partition_reports_no_solution_when_a_customer_cannot_be_covered(hand):
    assert M.partition_ganzzahlig(hand, [(1,), (2,), (3,)])[0] is None
    assert M.partition_milp(hand, [(1,), (2,), (3,)])[0] is None
    assert M.partition_brute(hand, [(1,), (2,), (3,)])[0] is None
    assert M.partition_ganzzahlig(hand, [])[0] is None


def test_the_subset_enumeration_agrees_with_highs_on_random_small_instances():
    for seed in range(20):
        inst = S.make_instance(7, seed, 100, gruppiert=seed % 2 == 1)
        alle, _ = A.routen_aufzaehlen(inst, [0] * 8)
        routen = [r for r, _ in alle]
        a = M.partition_teilmengen(inst, routen)
        b = M.partition_milp(inst, routen)
        assert a[0] == pytest.approx(b[0], rel=1e-9) and a[2] and b[2], seed


def test_column_generation_on_the_hand_example_reaches_lb_44_and_dual_feasible_duals(hand):
    cg = M.spaltenerzeugung(hand, 6)
    assert not cg["abgebrochen"] and cg["schranke"] == pytest.approx(HAND_LB, abs=1e-9)
    assert sum(cg["dual"]) == pytest.approx(cg["schranke"], abs=1e-9)
    assert all(A.route_kosten(hand, cg["dual"], r) >= -1e-7 for r in _hand_routen())
    assert cg["labels"] > 0 and cg["runden"] >= 2


def test_column_generation_stops_at_the_label_cap(hand):
    cg = M.spaltenerzeugung(hand, 6, max_labels=10)
    assert cg["abgebrochen"] and cg["schranke"] is None


# ---------------------------------------------------------------------------------------------------------------------------------
# Instanzen
# ---------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("gruppiert", [False, True])
def test_generator_is_deterministic_and_windows_are_consistent(gruppiert):
    a = S.make_instance(12, 7, 40, gruppiert=gruppiert)
    b = S.make_instance(12, 7, 40, gruppiert=gruppiert)
    assert a == b and a != S.make_instance(12, 8, 40, gruppiert=gruppiert)
    assert a.punkte[0] == (50.0, 50.0) and a.n == 12 and len(a.punkte) == 13
    for i in range(1, 13):
        assert C.LAST_MIN <= a.last[i] <= C.LAST_MAX
        assert a.frueh[i] >= a.dist[0][i] - 1e-9 and a.spaet[i] <= a.horizont - a.bedienzeit - a.dist[0][i] + 1e-9
        assert a.frueh[i] <= a.spaet[i] and a.spaet[i] - a.frueh[i] <= 40 + 1e-9
        assert 0 <= a.punkte[i][0] <= 100 and 0 <= a.punkte[i][1] <= 100


def test_every_customer_is_served_by_its_single_route():
    for seed in range(10):
        inst = S.make_instance(12, seed, 20)
        assert all(A.route_zulaessig(inst, (i,)) for i in range(1, 13))


# ---------------------------------------------------------------------------------------------------------------------------------
# Worst-Case am Regler-Maximum: darf nicht hängen (Timeout statt Zeitprüfung)
# ---------------------------------------------------------------------------------------------------------------------------------

def test_the_largest_live_setting_finishes_and_is_exact():
    e = E.LiveEinstellung(C.LIVE_N_MAX, "gruppiert", max(C.LIVE_BREITEN), 5, C.LIVE_K_MAX)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        live = pool.submit(E.live_lauf, e).result(timeout=240)
        assert live["fertig"] and live["zeile"]["ub3_exakt"] and live["fehler"] is None
        luecke = live["luecke"]
        for f in (1.0, 0.5, 0.0):
            s = pool.submit(E.live_schwelle, live, f * luecke).result(timeout=240)
            assert s["optimum_bewiesen"]
            if f == 1.0:
                assert s["optimum_bleibt"]
