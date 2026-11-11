"""Jede Zahl der README steht hier (DEMO-PLAYBOOK §4, §11a): exakt für das Handbeispiel und die Zählungen, aus den gespeicherten Rohwerten in `data/` für die Messreihen (mit den
Auswertungsfunktionen der App), an den festen Zufalls-Seeds der Live-Voreinstellung. Zeiten werden nie festgeschrieben. Die Buchstaben A bis O sind die der Tabelle „Befunde“ in der README."""

import math

import pytest

import ksp_algorithm as A
import ksp_baender as B
import ksp_constants as C
import ksp_evaluation as E
import ksp_master as M

NB = E.NBSP


def _p(x, stellen=1):
    """Anteil als Text mit Dezimalkomma, ohne Prozentzeichen."""
    return E.fmt_dec(100 * x, stellen)


# ---------------------------------------------------------------------------------------------------------------------------------
# A bis D: das Handbeispiel
# ---------------------------------------------------------------------------------------------------------------------------------

def test_A_hand_example_master_optimum_and_gap():
    b = E.hand_basis()
    assert len(b["routen"]) == 45
    assert b["lb"] == 44 and [int(d) for d in b["dual"][1:]] == [6, 6, 6, 16, 6, 4] and sum(b["dual"]) == 44
    assert any(x.denominator != 1 for _r, x in b["x"])                                  # die LP-Lösung ist gebrochen
    rcs = [float(v) for v in b["rc"].values()]
    assert min(rcs) == 0 and sum(1 for v in rcs if v == 0) == 7
    assert b["zstar"] == 46 and sorted(b["loesung"]) == [(1, 3, 5), (4, 2), (6,)] and b["luecke"] == 2
    assert sorted(A.weg_laenge(b["inst"], r) for r in b["loesung"]) == [4, 18, 24]


def test_B_hand_example_labels_and_edges_with_a_route():
    b = E.hand_basis()
    assert (b["F"]["erzeugt"], sum(len(a) for a in b["F"]["ueberlebende"])) == (33, 21)
    assert (b["B"]["erzeugt"], sum(len(a) for a in b["B"]["ueberlebende"]) - 1) == (37, 18)
    assert len(b["kanten"]) == 31 and b["inst"].n * (b["inst"].n + 1) == 42


def test_C_hand_example_edge_values_by_hand_and_their_distribution():
    b = E.hand_basis()
    P = b["P"]
    assert P[4][5] == 4 and P[0][4] == 2
    haeufigkeit = {}
    for (i, j) in b["kanten"]:
        haeufigkeit[round(P[i][j])] = haeufigkeit.get(round(P[i][j]), 0) + 1
    assert haeufigkeit == {0: 14, 2: 4, 4: 8, 6: 5}


def test_D_hand_example_cutting_at_the_thresholds():
    b = E.hand_basis()
    erwartet = {0: (17, 11, 50), 1: (17, 11, 50), 2: (13, 16, 46), 3: (13, 16, 46), 4: (5, 32, 46), 5: (5, 32, 46), 6: (0, 45, 46)}
    for s, (entfernt, uebrig, z) in erwartet.items():
        h = E.hand_schwelle(b, s)
        assert (h["entfernt"], h["routen_uebrig"], h["z_rest"]) == (entfernt, uebrig, z), s
    h2 = E.hand_schwelle(b, 2)
    assert (h2["labels_voll"], h2["labels_gestr"]) == (33, 20) and E.fmt_dec(h2["labels_gestr"] / h2["labels_voll"], 2) == "0,61" and _p(13 / 31) == "41,9"
    assert h2["bester_voll"] == h2["bester_gestr"] == 0 and h2["loesung_faellt"] == []
    h1 = E.hand_schwelle(b, 1)
    assert h1["loesung_faellt"] == [(0, 4), (4, 2)] and h1["z_rest"] == 50


# ---------------------------------------------------------------------------------------------------------------------------------
# E: die Live-Voreinstellung
# ---------------------------------------------------------------------------------------------------------------------------------

def test_E_default_live_instance():
    live = E.live_lauf(E.LiveEinstellung())
    z = live["zeile"]
    assert (z["n"], z["k"], z["breite"]) == (10, 8, 100.0) and z["ub3_exakt"] and live["fehler"] is None
    assert round(z["lb"], 2) == 323.13 and round(z["ub3"], 2) == 326.03 and E.fmt_dec(100 * live["luecke"] / z["lb"], 2) == "0,90"
    assert z["kanten_mit_route"] == 77 and z["kanten_gesamt"] == 110
    assert (z["wirkung"]["ub1"]["entfernt"], z["wirkung"]["ub2"]["entfernt"], z["wirkung"]["ub3"]["entfernt"]) == (47, 47, 47)         # alle drei Stufen gleich
    assert (z["labels_vorwaerts"], z["wirkung"]["ub3"]["labels"]) == (185, 42) and _p(47 / 77) == "61,0"
    stufen = {f: E.live_schwelle(live, f * live["luecke"]) for f in (1.0, 0.9)}
    assert stufen[1.0]["optimum_bleibt"] is True and stufen[1.0]["entfernt"] == 47
    assert stufen[0.9]["optimum_bleibt"] is False and stufen[0.9]["entfernt"] == 48 and round(stufen[0.9]["z_rest"], 2) == 326.56
    zwei = E.live_schwelle(live, 0.02 * z["lb"])
    assert (zwei["entfernt"], zwei["optimum_bleibt"]) == (43, True)
    halb = E.live_schwelle(live, 0.005 * z["lb"])
    assert (halb["entfernt"], halb["optimum_bleibt"]) == (48, False)


# ---------------------------------------------------------------------------------------------------------------------------------
# F bis K: die feste Reihe mit n = 30
# ---------------------------------------------------------------------------------------------------------------------------------

def test_F_series_n30_structure_and_control():
    zs = B.zellen(30)
    ue = [B.zellen_uebersicht(z) for z in zs]
    assert [u["instanzen"] for u in ue] == [12, 12, 12, 12] and sum(u["fertig"] for u in ue) == 48 and sum(u["abgebrochen"] for u in ue) == 0
    assert sum(u["ub3_exakt"] for u in ue) == 48 and sum(u["aufzaehlung_vollstaendig"] for u in ue) == 48
    assert {u["kanten_gesamt"] for u in ue} == {930} and 30 * 29 + 60 == 930
    assert [u["kanten_mit_route_median"] for u in ue] == [412.5, 605.5, 483.5, 665.5] and [u["kanten_statisch_median"] for u in ue] == [412.5, 605.5, 483.5, 665.5]
    assert [u["labels_voll_median"] for u in ue] == [1517, 4964, 3622, 10585.5]
    assert max(r["dual_summe_abweichung"] for z in zs for r in z["zeilen"]) < 1e-9
    assert [(z["typ"], z["breite"]) for z in zs] == [("zufall", 40), ("zufall", 100), ("gruppiert", 40), ("gruppiert", 100)]


def test_G_series_n30_gaps_of_the_three_upper_bounds():
    for stufe, (lo, hi, mx) in {"ub1": ("4,3", "8,7", "21,8"), "ub2": ("2,6", "4,3", "10,3"), "ub3": ("2,1", "3,6", "8,2")}.items():
        b = B.luecke_bereich(30, stufe)
        assert (_p(b["mittel_min"]), _p(b["mittel_max"]), _p(b["einzel_max"])) == (lo, hi, mx), stufe


def test_H_series_n30_share_of_removed_edges():
    erwartet = {"ub1": (22, 42, 0, 83), "ub2": (41, 56, 1, 83), "ub3": (46, 61, 10, 83)}
    for s, (m1, m2, e1, e2) in erwartet.items():
        b = B.bereich(30, s)
        assert (round(100 * b["mittel_min"]), round(100 * b["mittel_max"]), round(100 * b["einzel_min"]), round(100 * b["einzel_max"])) == (m1, m2, e1, e2), s
    for s, (m1, m2) in {"r0.5": (76, 78), "r1": (70, 71), "r2": (58, 60), "r5": (30, 33)}.items():
        b = B.bereich(30, s)
        assert (round(100 * b["mittel_min"]), round(100 * b["mittel_max"])) == (m1, m2), s


def test_I_series_n30_label_ratio():
    erwartet = {"ub1": ("0,56", "0,80"), "ub2": ("0,39", "0,58"), "ub3": ("0,34", "0,52"), "r0.5": ("0,11", "0,16"), "r1": ("0,20", "0,25"), "r2": ("0,37", "0,42"), "r5": ("0,71", "0,75")}
    for s, (lo, hi) in erwartet.items():
        b = B.bereich(30, s, "labels")
        assert (E.fmt_dec(b["mittel_min"], 2), E.fmt_dec(b["mittel_max"], 2)) == (lo, hi), s
    b3 = B.bereich(30, "ub3", "labels")
    assert (E.fmt_dec(b3["einzel_min"], 2), E.fmt_dec(b3["einzel_max"], 2)) == ("0,05", "0,94")


def test_J_series_n30_single_instances_with_the_smallest_and_the_largest_share():
    zeilen = [(r["wirkung"]["ub3"]["entfernt"] / r["kanten_mit_route"], z["id"], r["seed"], B.luecke(r, "ub3"), r["wirkung"]["ub3"]["labels"] / r["labels_vorwaerts"]) for z in B.zellen(30) for r in z["zeilen"]]
    klein, gross = min(zeilen), max(zeilen)
    assert (klein[1], klein[2], _p(klein[0]), _p(klein[3], 2), E.fmt_dec(klein[4], 2)) == ("gruppiert_100_n30", 1403, "10,4", "8,22", "0,94")
    assert (gross[1], gross[2], _p(gross[0]), _p(abs(gross[3]), 2), E.fmt_dec(gross[4], 2)) == ("gruppiert_40_n30", 1408, "83,0", "0,00", "0,06")


def test_K_series_n30_curve_edges_with_value_up_to_x_percent_of_lb():
    kurven = [B.gitterkurve(z) for z in B.zellen(30)]
    erwartet = {0.005: ("21,8", "23,8"), 0.01: ("28,6", "30,4"), 0.02: ("39,7", "41,9"), 0.03: ("49,7", "51,4"), 0.05: ("67,3", "70,2"), 0.10: ("93,1", "95,8")}
    for x, (lo, hi) in erwartet.items():
        i = C.BAND_GRID.index(x)
        assert (_p(min(k[i] for k in kurven)), _p(max(k[i] for k in kurven))) == (lo, hi), x
    abstand = max(max(k[i] for k in kurven) - min(k[i] for k in kurven) for i in range(len(C.BAND_GRID)))
    assert E.fmt_dec(100 * abstand, 1) == "4,0" and len(C.BAND_GRID) == 8


# ---------------------------------------------------------------------------------------------------------------------------------
# L, M: n = 50 und der Vergleich mit der Messung vor dem Bau
# ---------------------------------------------------------------------------------------------------------------------------------

def test_L_series_n50_small_series_with_few_proven_optima():
    z = {zz["typ"]: zz for zz in B.zellen(50)}
    u = {t: B.zellen_uebersicht(zz) for t, zz in z.items()}
    assert (u["zufall"]["instanzen"], u["zufall"]["ub3_exakt"], u["zufall"]["aufzaehlung_vollstaendig"], u["zufall"]["fertig"]) == (10, 9, 10, 10)
    assert (u["gruppiert"]["instanzen"], u["gruppiert"]["ub3_exakt"], u["gruppiert"]["aufzaehlung_vollstaendig"], u["gruppiert"]["fertig"]) == (8, 3, 5, 8)
    t = {k: B.streichtabelle(zz) for k, zz in z.items()}
    assert [_p(t["zufall"][s]["streichen"]["mittel"]) for s in ("ub1", "ub2", "ub3")] == ["27,8", "55,5", "65,2"] and t["zufall"]["ub3"]["streichen"]["zahl"] == 9
    assert [_p(t["gruppiert"][s]["streichen"]["mittel"]) for s in ("ub1", "ub2", "ub3")] == ["16,8", "39,8", "53,5"] and t["gruppiert"]["ub3"]["streichen"]["zahl"] == 3
    assert [E.fmt_dec(t["zufall"][s]["labels"]["mittel"], 2) for s in ("ub3",)] == ["0,33"] and E.fmt_dec(t["gruppiert"]["ub3"]["labels"]["mittel"], 2) == "0,45"
    assert [_p(u["zufall"]["luecke"][s]["mittel"], 2) for s in ("ub1", "ub2", "ub3")] == ["4,78", "2,00", "1,35"]
    assert [_p(u["gruppiert"]["luecke"][s]["mittel"], 2) for s in ("ub1", "ub2", "ub3")] == ["8,88", "3,05", "2,06"]
    assert u["zufall"]["kanten_gesamt"] == 50 * 49 + 100 == 2550


def test_M_comparison_with_the_measurement_before_the_build():
    assert B.vergleich_mit_vormessung() == {"verglichen": 1386, "abweichend": 9}
    abw = {z["id"]: sorted({int(t.split()[1]) for t in z["vergleich"]["abweichungen"]}) for z in B.zellen() if z["vergleich"]["abweichungen"]}
    assert abw == {"zufall_100_n50": [1408], "gruppiert_100_n50": [1400, 1401]}
    assert sum(z["vergleich"]["verglichen"] for z in B.zellen(30)) == 1008 and sum(z["vergleich"]["abweichend"] for z in B.zellen(30)) == 0


# ---------------------------------------------------------------------------------------------------------------------------------
# N, O: die Zählung der Gegenprobe und die Kontrolle der besten Endwerte
# ---------------------------------------------------------------------------------------------------------------------------------

def test_N_counter_check_counts_of_the_small_instances():
    z = B.gegenprobe()
    assert (z["faelle"], z["mit_ng_gleich_n"], z["mit_luecke"], z["optimum_verloren_exakt"], z["optimum_verloren_halb"]) == (384, 192, 168, 0, 81)
    assert (z["streichung_verletzt_routen_exakt"], z["wert_ueber_wahrem_wert"], z["wert_unter_wahrem_wert_bei_k_gleich_n"], z["endlich_ohne_route"], z["zstar_nicht_bewiesen"]) == (0, 0, 0, 0, 0)
    assert (z["wert_unter_wahrem_wert_bei_k_kleiner_n"], z["kanten_mit_route_bei_k_kleiner_n"]) == (150, 10134)
    faelle = B.gegenprobe_faelle()
    assert len(faelle) == 384 and sum(1 for f in faelle if f["halb"]["optimum_verloren"]) == 81 and sum(1 for f in faelle if f["luecke"] > 1e-6) == 168
    assert all(f["halb"]["optimum_verloren"] <= (f["luecke"] > 1e-6) for f in faelle)            # ohne Lücke kann nichts verloren gehen
    assert {(f["n"], f["breite"], f["typ"]) for f in faelle} == {(n, b, t) for n in (7, 8, 9, 10) for b in (40, 100) for t in ("zufall", "gruppiert")}


def test_O_best_end_value_is_kept_when_cutting_in_all_cases():
    n30 = [v["bester_wert"] - r["bester_wert_voll"] for z in B.zellen(30) for r in z["zeilen"] for v in r["wirkung"].values()]
    n50 = [v["bester_wert"] - r["bester_wert_voll"] for z in B.zellen(50) for r in z["zeilen"] for v in r["wirkung"].values()]
    assert (len(n30), len(n50)) == (336, 126) and all(abs(d) <= 1e-6 for d in n30 + n50)


def test_P_the_numbers_of_the_app_texts_come_from_the_same_functions():
    """Die Zahlen der Hilfetexte der Szenarien und des Bänder-Verdikts stammen aus den Läufen: hier die Zahlen der Hilfen gegen den Kern."""
    b = E.hand_basis()
    h1, h2, h6 = E.hand_schwelle(b, 1), E.hand_schwelle(b, 2), E.hand_schwelle(b, 6)
    assert (h2["entfernt"], h2["mit_route"], b["zstar"]) == (13, 31, 46) and "13 von 31 Kanten" in C.PRESET_HELP["Grundfall: Schwelle gleich der Lücke"] and "Optimum 46" in C.PRESET_HELP["Grundfall: Schwelle gleich der Lücke"]
    zu_klein = C.PRESET_HELP["Zu kleine Schwelle: Optimum verloren"]
    assert h1["entfernt"] == 17 and "17 Kanten fallen" in zu_klein and "0→4 und 4→2" in zu_klein and h1["z_rest"] == 50 and "50 statt 46" in zu_klein
    assert h6["entfernt"] == 0 and "Schwelle 6" in C.PRESET_HELP["Keine Streichung: sehr große Schwelle"] and C.HAND_SCHWELLE_MAX == 6
    assert math.isclose(b["luecke"], 2) and "Schwelle 2" in C.PRESET_HELP["Grundfall: Schwelle gleich der Lücke"]
    live = E.live_lauf(E.LiveEinstellung(10, "gruppiert", 100, 5, 8))
    z = live["zeile"]
    assert (z["ub1"] - z["lb"]) > live["luecke"] > 0                                           # Hilfe: „Lücke aus den Spalten größer als die exakte Lücke“
    assert E.live_lauf(E.LiveEinstellung(10, "gruppiert", 100, 1, 8))["luecke"] == pytest.approx(0.0, abs=1e-9)           # Hilfe „Lücke null“
    assert M.partition_ganzzahlig(live["inst"], [r for r, _ in live["alle"]])[0] == pytest.approx(live["zstar"])


def test_Q_instance_model_and_control_ranges_named_in_the_readme():
    assert (C.HORIZONT, C.BEDIENZEIT, C.KAPAZITAET, C.LAST_MIN, C.LAST_MAX) == (300.0, 10.0, 70, 5, 25)
    assert (C.LIVE_N_MIN, C.LIVE_N_MAX, C.LIVE_K_MIN, C.LIVE_K_MAX, C.LIVE_BREITEN, C.LIVE_TYPEN) == (5, 12, 2, 12, (20, 40, 60, 100), ("zufällig", "gruppiert"))
    assert (C.LIVE_DEFAULT_N, C.LIVE_DEFAULT_TYP, C.LIVE_DEFAULT_BREITE, C.LIVE_DEFAULT_SEED, C.LIVE_DEFAULT_K, C.LUECKE_DEFAULT_PCT) == (10, "zufällig", 100, 0, 8, 2.0)
    assert (C.LUECKE_PCT_MIN, C.LUECKE_PCT_MAX, C.LUECKE_PCT_SCHRITT, C.MAX_NEUE_SPALTEN, C.DP_MAX_N) == (0.5, 10.0, 0.5, 15, 14)
    assert (C.HAND_SCHWELLE_MIN, C.HAND_SCHWELLE_MAX, C.HAND_DEFAULT_SCHWELLE) == (0, 6, 2) and C.BAND_GRID == (0.005, 0.01, 0.02, 0.03, 0.04, 0.05, 0.075, 0.10)
    assert C.MILP_ZEIT == 60.0 and C.LIVE_MAX_ROUTEN == 400_000
    import ksp_scenario as S
    h = S.handbeispiel()
    assert (h.bedienzeit, h.kapazitaet, h.horizont, h.n, h.punkte[0]) == (2, 8, 40, 6, (5, 5))
    gruppen = S.make_instance(40, 1, 50, gruppiert=True)
    assert len({(round(x / 20), round(y / 20)) for x, y in gruppen.punkte[1:]}) < 25        # gruppierte Kunden liegen in wenigen Feldern des Quadrats


def test_R_limits_of_the_enumeration_and_the_solver():
    import inspect
    assert inspect.signature(E.analyse_instanz).parameters["max_routen"].default == 300_000
    assert inspect.signature(E.analyse_instanz).parameters["milp_zeit"].default == 60.0 == C.MILP_ZEIT
