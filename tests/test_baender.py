"""Feste Messreihen (data/*.json): Aufbau, Quellenangaben, Vergleich mit der Messung vor dem Bau und Stichproben, die mit dem Kern dieser Demo nachgerechnet werden.

Die JSON-Dateien hat `tools/baender_erzeugen.py` mit dem Kern dieser Demo gerechnet. Die Stichproben hier rechnen Zellen noch einmal: Schranken müssen auf 1e-6 (relativ) stimmen
(der Wert der Schranken hängt nicht vom Weg der Spaltenerzeugung ab); Zahl gestrichener Kanten und Labels hängen von den Dualpreisen des Master-Lösers ab und werden nur in einem Band
geprüft (DEMO-PLAYBOOK §4: Plattformabhängiges nie exakt)."""

import re

import pytest

import ksp_algorithm as A
import ksp_baender as B
import ksp_constants as C
import ksp_evaluation as E
import ksp_scenario as S

ZELLEN = {"zufall_40_n30": 12, "zufall_100_n30": 12, "gruppiert_40_n30": 12, "gruppiert_100_n30": 12, "zufall_100_n50": 10, "gruppiert_100_n50": 8}


def test_the_file_has_the_six_documented_cells_with_their_seeds():
    assert [z["id"] for z in B.zellen()] == list(ZELLEN)
    for z in B.zellen():
        assert len(z["zeilen"]) == z["instanzen"] == ZELLEN[z["id"]]
        assert [r["seed"] for r in z["zeilen"]] == list(range(1400, 1400 + z["instanzen"])) and z["seeds"] == [1400, 1399 + z["instanzen"]]
        assert z["k"] == 8 and z["master"] == "Partitionierung" and z["neu_gerechnet"] is True


def test_every_cell_names_its_source_and_its_comparison_file():
    for z in B.zellen():
        assert "neu gerechnet mit dem Kern dieser Demo" in z["quelle"] and z["vergleich"]["datei"] in z["quelle"]
        assert re.fullmatch(r"out_v14(n50m)?_(zufall|gruppiert)_(40|100)\.txt", z["vergleich"]["datei"])
        assert z["vergleich"]["verglichen"] > 0


def test_every_row_has_its_fields_and_the_bounds_are_ordered():
    for z in B.zellen():
        for r in z["zeilen"]:
            assert r["fertig"] is True and r["seed"] and r["n"] == z["n"] and r["k"] == 8
            assert {"lb", "ub1", "ub2", "ub3", "ub3_exakt", "aufzaehlung_vollstaendig", "kanten_mit_route", "kanten_statisch", "kanten_gesamt", "labels_vorwaerts", "gitter", "wirkung"} <= set(r)
            assert r["ub1"] >= r["ub2"] - 1e-6 >= r["ub3"] - 2e-6 >= r["lb"] - 3e-6              # obere Schranken sinken von Stufe zu Stufe, über LB
            assert r["kanten_gesamt"] == z["n"] * (z["n"] + 1) and r["kanten_mit_route"] <= r["kanten_statisch"] <= r["kanten_gesamt"]
            assert r["dual_summe_abweichung"] < 1e-8
            assert set(r["wirkung"]) == set(C.BAND_SCHWELLEN) and set(r["gitter"]) == {str(g) for g in C.BAND_GRID}


def test_the_stages_cut_more_edges_the_smaller_the_gap_and_never_more_labels_than_the_full_graph():
    for z in B.zellen():
        for r in z["zeilen"]:
            w = r["wirkung"]
            assert w["ub1"]["entfernt"] <= w["ub2"]["entfernt"] <= w["ub3"]["entfernt"] <= r["kanten_mit_route"]
            assert w["r0.5"]["entfernt"] >= w["r1"]["entfernt"] >= w["r2"]["entfernt"] >= w["r5"]["entfernt"]
            assert all(v["labels"] <= r["labels_vorwaerts"] and not v["abgebrochen"] for v in w.values())
            g = [r["gitter"][str(x)] for x in C.BAND_GRID]
            assert g == sorted(g) and g[-1] <= r["kanten_mit_route"]


def test_the_best_end_value_is_the_same_in_the_cut_and_the_full_graph_in_all_cases():
    """Kontrolle der Messung: die kleinsten reduzierten Kosten über alle Endlabels bleiben beim Streichen gleich (n = 30: 48 Instanzen × 7 Schwellen = 336 Fälle, n = 50: 18 × 7 = 126)."""
    zaehler = {30: 0, 50: 0}
    for z in B.zellen():
        for r in z["zeilen"]:
            for v in r["wirkung"].values():
                assert abs(v["bester_wert"] - r["bester_wert_voll"]) <= 1e-6
                zaehler[z["n"]] += 1
    assert zaehler == {30: 336, 50: 126}


def test_comparison_with_the_measurement_before_the_build_n30_without_deviation():
    for z in B.zellen(30):
        assert z["vergleich"]["verglichen"] == 252 and z["vergleich"]["abweichend"] == 0 and z["vergleich"]["abweichungen"] == []
        assert all(r["ub3_exakt"] and r["aufzaehlung_vollstaendig"] for r in z["zeilen"])


def test_the_deviations_of_n50_all_concern_instances_without_a_proven_optimum_and_only_the_exact_stage():
    gesamt = B.vergleich_mit_vormessung()
    assert gesamt == {"verglichen": 1386, "abweichend": 9}
    for z in B.zellen(50):
        nicht_exakt = {r["seed"] for r in z["zeilen"] if not r["ub3_exakt"]}
        assert z["vergleich"]["abweichend"] == len(z["vergleich"]["abweichungen"])
        for text in z["vergleich"]["abweichungen"]:
            m = re.match(r"Seed (\d+) (UB3|gestrichen bei ub3|Labels bei ub3):", text)
            assert m and int(m.group(1)) in nicht_exakt, text
        assert sum(1 for r in z["zeilen"] if r["ub3_exakt"]) == {"zufall": 9, "gruppiert": 3}[z["typ"]]


def test_the_comparison_hints_list_every_deviation_with_its_cell():
    hinweise = B.vormessung_hinweise()
    assert len(hinweise) == 9 and all(re.match(r"(zufall|gruppiert)_100_n50: Seed \d+ ", h) for h in hinweise)


@pytest.mark.parametrize("zid, seed", [("zufall_40_n30", 1400), ("gruppiert_100_n30", 1405), ("gruppiert_40_n30", 1408), ("zufall_100_n30", 1409)])
def test_sample_of_the_series_recomputed_with_the_kernel(zid, seed):
    z = B.zelle(zid)
    zeile = next(r for r in z["zeilen"] if r["seed"] == seed)
    inst = S.make_instance(z["n"], seed, z["breite"], gruppiert=z["typ"] == "gruppiert")
    neu, _ = E.analyse_instanz(inst, z["k"])
    for feld in ("lb", "ub1", "ub2", "ub3"):
        assert neu[feld] == pytest.approx(zeile[feld], rel=1e-6), feld
    assert neu["ub3_exakt"] is zeile["ub3_exakt"] and neu["kanten_mit_route"] == zeile["kanten_mit_route"] and neu["kanten_gesamt"] == zeile["kanten_gesamt"]
    # Zahlen, die von den Dualpreisen des Master-Lösers abhängen: im Band von 10 % der Kanten bzw. 25 % der Labels
    band = 0.10 * zeile["kanten_mit_route"]
    for s in C.BAND_SCHWELLEN:
        assert abs(neu["wirkung"][s]["entfernt"] - zeile["wirkung"][s]["entfernt"]) <= band, s
        assert neu["wirkung"][s]["labels"] == pytest.approx(zeile["wirkung"][s]["labels"], rel=0.25), s


def test_one_cell_of_n50_is_recomputed_for_its_bounds():
    """Eine kleine Instanz der Reihe mit n = 50 (zufällig, Zufalls-Seed 1405, Optimum bewiesen) wird ganz nachgerechnet."""
    z = B.zelle("zufall_100_n50")
    zeile = next(r for r in z["zeilen"] if r["seed"] == 1405)
    neu, _ = E.analyse_instanz(S.make_instance(50, 1405, 100), 8)
    assert neu["ub3_exakt"] is True and zeile["ub3_exakt"] is True
    for feld in ("lb", "ub1", "ub2", "ub3"):
        assert neu[feld] == pytest.approx(zeile[feld], rel=1e-6), feld


# ---------------------------------------------------------------------------------------------------------------------------------
# Auswertungsfunktionen an einer von Hand gebauten Zelle
# ---------------------------------------------------------------------------------------------------------------------------------

def _zeile(seed, lb, ub1, ub2, ub3, exakt, mit_route, labels, entfernt, labels_gestr, fertig=True):
    w = {s: {"schwelle": 0.0, "entfernt": e, "labels": lg, "bester_wert": 0.0, "abgebrochen": False} for s, e, lg in zip(C.BAND_SCHWELLEN, entfernt, labels_gestr)}
    return {"seed": seed, "fertig": fertig, "lb": lb, "ub1": ub1, "ub2": ub2, "ub3": ub3, "ub3_exakt": exakt, "aufzaehlung_vollstaendig": exakt, "kanten_mit_route": mit_route, "kanten_statisch": mit_route,
            "kanten_gesamt": 100, "labels_vorwaerts": labels, "wirkung": w, "gitter": {str(g): (mit_route * (i + 1)) // len(C.BAND_GRID) for i, g in enumerate(C.BAND_GRID)}}


HAND_ZELLE = {"id": "x", "typ": "zufall", "breite": 40, "n": 9, "k": 8, "zeilen": [
    _zeile(1, 100.0, 110.0, 105.0, 104.0, True, 50, 200, [10, 15, 20, 30, 25, 20, 10], [180, 150, 100, 60, 80, 120, 190]),
    _zeile(2, 200.0, 220.0, 210.0, 208.0, False, 40, 100, [4, 8, 10, 30, 25, 20, 10], [90, 80, 70, 40, 50, 60, 95]),
    _zeile(3, 50.0, 55.0, 52.0, 51.0, True, 10, 50, [2, 4, 6, 8, 7, 5, 3], [45, 40, 30, 20, 25, 35, 48]),
    {"seed": 4, "fertig": False},
]}


def test_cell_figures_on_a_hand_built_cell():
    assert [r["seed"] for r in B.fertige(HAND_ZELLE)] == [1, 2, 3]
    assert [r["seed"] for r in B.zeilen_fuer(HAND_ZELLE, "ub3")] == [1, 3] and [r["seed"] for r in B.zeilen_fuer(HAND_ZELLE, "ub1")] == [1, 2, 3]
    assert B.streichanteile(HAND_ZELLE, "ub1") == [10 / 50, 4 / 40, 2 / 10]
    assert B.streichanteile(HAND_ZELLE, "ub3") == [20 / 50, 6 / 10]                        # nur Instanzen mit bewiesenem Optimum
    assert B.label_verhaeltnisse(HAND_ZELLE, "ub2") == [150 / 200, 80 / 100, 40 / 50]
    assert B.luecke(HAND_ZELLE["zeilen"][0], "ub1") == pytest.approx(0.10) and B.luecke(HAND_ZELLE["zeilen"][1], "ub3") == pytest.approx(0.04)
    k = B.kennzahlen([0.2, 0.1, 0.6])
    assert k == {"mittel": pytest.approx(0.3), "min": 0.1, "max": 0.6, "median": 0.2, "zahl": 3}
    assert B.kennzahlen([])["mittel"] is None and B.kennzahlen([])["zahl"] == 0
    u = B.zellen_uebersicht(HAND_ZELLE)
    assert (u["instanzen"], u["fertig"], u["abgebrochen"], u["ub3_exakt"]) == (4, 3, 1, 2)
    assert u["kanten_mit_route_median"] == 40 and u["labels_voll_median"] == 100
    assert u["luecke"]["ub3"]["zahl"] == 2 and u["luecke"]["ub3"]["mittel"] == pytest.approx((0.04 + 0.02) / 2)
    kurve = B.gitterkurve(HAND_ZELLE)
    assert len(kurve) == len(C.BAND_GRID)
    assert kurve[0] == pytest.approx((6 / 50 + 5 / 40 + 1 / 10) / 3)                 # Zähler: Zahl der Kanten · 1/8 abgerundet (6, 5, 1)
    assert kurve[-1] == pytest.approx(1.0) and kurve == sorted(kurve)


def test_the_ranges_over_the_cells_are_min_and_max_of_the_cell_means():
    b = B.bereich(30, "ub3")
    mittel = [B.streichtabelle(z)["ub3"]["streichen"]["mittel"] for z in B.zellen(30)]
    assert b["mittel_min"] == min(mittel) and b["mittel_max"] == max(mittel) and b["instanzen"] == 48 and b["zellen"] == 4
    assert B.kanten_median_bereich(30) == (min(B.zellen_uebersicht(z)["kanten_mit_route_median"] for z in B.zellen(30)), max(B.zellen_uebersicht(z)["kanten_mit_route_median"] for z in B.zellen(30)))
