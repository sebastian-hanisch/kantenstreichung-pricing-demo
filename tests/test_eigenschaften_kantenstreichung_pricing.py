"""Eigenschaftstests (ORACLE-PLAYBOOK §5.2): Aussagen, die für das Verfahren gelten müssen, ohne dass man das richtige Ergebnis kennt.

Je Eigenschaft 12 bis 30 feste Zufallsinstanzen (Zufalls-Seeds im Test), dazu Randfälle:
* Monotonie: eine größere Schwelle streicht nie mehr Kanten; die gestrichenen Mengen sind ineinander geschachtelt.
* Jede Schwelle ab der Lücke erhält das Optimum (n = 7, 8, 9).
* Umnummerieren der Kunden ändert die Kantenwerte nicht (nur ihre Plätze), bei festen Dualpreisen.
* Skalieren aller Längen, Zeiten und Fenster mit λ > 0 skaliert die Kantenwerte mit λ, bei mit λ skalierten Dualpreisen.
* Je kleiner das ng-Gedächtnis, desto kleiner (nie größer) die Kantenwerte; k = n gibt die größten.
* Streichen erhält die kleinsten reduzierten Kosten über alle Endlabels des Labelings.
* Jede Regel wirkt auf mindestens einer Instanz (Zweig-Test): das Gedächtnis, das Streichen.
* Gleiche Zahlen in zwei Prozessen mit verschiedener Hash-Randomisierung."""

import dataclasses
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest

import ksp_algorithm as A
import ksp_evaluation as E
import ksp_master as M
import ksp_scenario as S

ROOT = Path(__file__).resolve().parent.parent
TOL = 1e-6


def _lauf(n, breite, gruppiert, seed, k=None):
    inst = S.make_instance(n, seed, breite, gruppiert=gruppiert)
    k = n if k is None else k
    cg = M.spaltenerzeugung(inst, k)
    F = A.vorwaerts_labeling(inst, cg["dual"], k)
    B = A.rueckwaerts_labeling(inst, cg["dual"], k)
    P, _ = A.kantenwerte(inst, cg["dual"], F, B)
    return inst, cg, F, P


def _faelle(n, anzahl):
    return [(n, b, g, 1500 + s) for b in (40, 100) for g in (False, True) for s in range(anzahl)]


@pytest.mark.parametrize("fall", _faelle(8, 3), ids=str)
def test_larger_threshold_removes_fewer_edges_and_the_sets_are_nested(fall):
    _inst, _cg, _F, P = _lauf(*fall)
    vorher = None
    for s in (0, 1, 2, 5, 10, 20, 50, 1000):
        weg = A.gestrichene_kanten(P, s)
        if vorher is not None:
            assert weg <= vorher
        vorher = weg
    assert vorher == set()                                  # bei sehr großer Schwelle bleibt jede Kante


@pytest.mark.parametrize("n", [7, 8, 9])
def test_every_threshold_from_the_gap_up_keeps_the_optimum(n):
    for b, g, seed in ((40, False, 1), (100, False, 2), (40, True, 3), (100, True, 4), (100, True, 5)):
        inst, cg, _F, P = _lauf(n, b, g, 1500 + seed)
        alle, _ = A.routen_aufzaehlen(inst, cg["dual"])
        zstar = M.partition_ganzzahlig(inst, [r for r, _ in alle])[0]
        luecke = zstar - cg["schranke"]
        for faktor in (1.0, 1.5, 3.0, 100.0):
            weg = A.gestrichene_kanten(P, faktor * luecke)
            z = M.partition_ganzzahlig(inst, [r for r, _ in alle if A.route_ohne(r, weg)])[0]
            assert z == pytest.approx(zstar, abs=TOL), (n, b, g, seed, faktor)


@pytest.mark.parametrize("fall", _faelle(8, 2), ids=str)
def test_renumbering_the_customers_permutes_the_edge_values(fall):
    n, b, g, seed = fall
    inst, cg, F, P = _lauf(*fall)
    perm = {0: 0, **{i: (i % n) + 1 for i in range(1, n + 1)}}                   # Kunde i wird Kunde i + 1 (zyklisch)
    umgekehrt = {v: k for k, v in perm.items()}
    neu = dataclasses.replace(
        inst, punkte=tuple(inst.punkte[umgekehrt[i]] for i in range(n + 1)), dist=tuple(tuple(inst.dist[umgekehrt[i]][umgekehrt[j]] for j in range(n + 1)) for i in range(n + 1)),
        last=tuple(inst.last[umgekehrt[i]] for i in range(n + 1)), frueh=tuple(inst.frueh[umgekehrt[i]] for i in range(n + 1)), spaet=tuple(inst.spaet[umgekehrt[i]] for i in range(n + 1)))
    dual_neu = [cg["dual"][umgekehrt[i]] for i in range(n + 1)]
    F2 = A.vorwaerts_labeling(neu, dual_neu, n)
    B2 = A.rueckwaerts_labeling(neu, dual_neu, n)
    P2, _ = A.kantenwerte(neu, dual_neu, F2, B2)
    for i in range(n + 1):
        for j in range(n + 1):
            if i != j:
                assert P2[perm[i]][perm[j]] == pytest.approx(P[i][j], abs=TOL) or (math.isinf(P2[perm[i]][perm[j]]) and math.isinf(P[i][j]))
    assert F2["bester_wert"] == pytest.approx(F["bester_wert"], abs=TOL)


@pytest.mark.parametrize("fall", _faelle(7, 2), ids=str)
@pytest.mark.parametrize("lam", [0.5, 3.0])
def test_scaling_lengths_times_and_duals_scales_the_edge_values(fall, lam):
    n, b, g, seed = fall
    inst, cg, F, P = _lauf(*fall)
    gross = dataclasses.replace(
        inst, dist=tuple(tuple(lam * x for x in zeile) for zeile in inst.dist), frueh=tuple(lam * x for x in inst.frueh), spaet=tuple(lam * x for x in inst.spaet),
        horizont=lam * inst.horizont, bedienzeit=lam * inst.bedienzeit)
    dual = [lam * p for p in cg["dual"]]
    F2 = A.vorwaerts_labeling(gross, dual, n)
    B2 = A.rueckwaerts_labeling(gross, dual, n)
    P2, _ = A.kantenwerte(gross, dual, F2, B2)
    for i in range(n + 1):
        for j in range(n + 1):
            if i != j and math.isfinite(P[i][j]):
                assert P2[i][j] == pytest.approx(lam * P[i][j], abs=1e-6 * lam), (i, j)
            elif i != j:
                assert math.isinf(P2[i][j])


@pytest.mark.parametrize("fall", _faelle(9, 2), ids=str)
def test_a_smaller_ng_memory_never_raises_a_path_value(fall):
    n, b, g, seed = fall
    inst = S.make_instance(n, seed, b, gruppiert=g)
    dual = M.spaltenerzeugung(inst, n)["dual"]                                  # feste Dualpreise (elementar), nur das Gedächtnis ändert sich
    werte = {}
    for k in (2, 4, n):
        F = A.vorwaerts_labeling(inst, dual, k)
        B = A.rueckwaerts_labeling(inst, dual, k)
        werte[k] = A.kantenwerte(inst, dual, F, B)[0]
    for i in range(n + 1):
        for j in range(n + 1):
            if i != j:
                assert werte[2][i][j] <= werte[4][i][j] + TOL and werte[4][i][j] <= werte[n][i][j] + TOL


def test_the_ng_memory_changes_the_values_on_at_least_one_instance():
    """Zweig-Test: k < n weicht auf mindestens einer Instanz von k = n ab (sonst würde das Gedächtnis nie wirken)."""
    abweichend = 0
    for fall in _faelle(9, 3):
        n, b, g, seed = fall
        inst = S.make_instance(n, seed, b, gruppiert=g)
        dual = M.spaltenerzeugung(inst, n)["dual"]
        P = {k: A.kantenwerte(inst, dual, A.vorwaerts_labeling(inst, dual, k), A.rueckwaerts_labeling(inst, dual, k))[0] for k in (2, n)}
        abweichend += any(P[2][i][j] < P[n][i][j] - TOL for i in range(n + 1) for j in range(n + 1) if i != j and math.isfinite(P[n][i][j]))
    assert abweichend >= 1


def test_cutting_keeps_the_best_end_label_and_removes_labels_on_some_instances():
    weniger = 0
    for fall in _faelle(10, 3):
        inst, cg, F, P = _lauf(*fall, k=8)
        alle, _ = A.routen_aufzaehlen(inst, cg["dual"])
        luecke = M.partition_ganzzahlig(inst, [r for r, _ in alle])[0] - cg["schranke"]
        G = A.vorwaerts_labeling(inst, cg["dual"], 8, erlaubt=A.erlaubt_matrix(inst.n, P, luecke))
        assert G["bester_wert"] == pytest.approx(F["bester_wert"], abs=TOL)
        assert G["erzeugt"] <= F["erzeugt"]
        weniger += G["erzeugt"] < F["erzeugt"]
    assert weniger >= 3


def test_zero_gap_keeps_only_edges_with_value_zero():
    gefunden = 0
    for s in range(30):
        inst = S.make_instance(7, 1600 + s, 40)
        cg = M.spaltenerzeugung(inst, 7)
        alle, _ = A.routen_aufzaehlen(inst, cg["dual"])
        zstar = M.partition_ganzzahlig(inst, [r for r, _ in alle])[0]
        if zstar - cg["schranke"] > 1e-6:
            continue
        gefunden += 1
        F, B = A.vorwaerts_labeling(inst, cg["dual"], 7), A.rueckwaerts_labeling(inst, cg["dual"], 7)
        P, _ = A.kantenwerte(inst, cg["dual"], F, B)
        bleibt = [(i, j) for (i, j) in A.kanten_mit_route(P) if (i, j) not in A.gestrichene_kanten(P, 0.0)]
        assert bleibt and all(abs(P[i][j]) <= 1e-6 for (i, j) in bleibt)
    assert gefunden >= 3


def _prozess(hashseed):
    code = (
        "import json, ksp_evaluation as E, ksp_scenario as S\n"
        "b = E.hand_basis(); h = E.hand_schwelle(b, 2)\n"
        "z, _ = E.analyse_instanz(S.make_instance(9, 1503, 100, gruppiert=True), 9)\n"
        "print(json.dumps([b['lb'], b['zstar'], h['entfernt'], h['labels_gestr'], round(z['lb'], 6), z['kanten_mit_route'], z['wirkung']['ub3']['entfernt'], z['wirkung']['ub3']['labels']]))\n")
    env = {**os.environ, "PYTHONHASHSEED": str(hashseed), "PYTHONIOENCODING": "utf-8"}
    p = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=240)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_same_numbers_in_two_processes_with_different_hash_randomization():
    a, b = _prozess(1), _prozess(2)
    assert a == b and a[:4] == [44, 46, 13, 20]
