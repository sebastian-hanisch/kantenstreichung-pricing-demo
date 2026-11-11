"""Verdikte an von Hand gesetzten Werten (DEMO-PLAYBOOK §12): jede Zahl im Text und jede Schwelle der Art steht hier.

Ein Verdikt ist eine reine Funktion (Art, Text) und bekommt Wörterbücher, nicht Seeds. Damit prüft der Test jeden Zweig und jede genannte Zahl direkt.
Jeder Satz über die Wirkung (gestrichene Kanten, Labels) trägt den Vorbehalt „nur bei den Dualpreisen der Konvergenz gemessen …“ im selben Satz."""

import pytest

import ksp_constants as C
import ksp_evaluation as ev

NB = ev.NBSP
VORBEHALT = C.VORBEHALT


def _hand(schwelle, entfernt, z_rest, uebrig, fallen=(), luecke=2, zstar=46, mit_route=31):
    return dict(schwelle=schwelle, entfernt=entfernt, mit_route=mit_route, z_rest=z_rest, routen_uebrig=uebrig, zstar=zstar, luecke=luecke, loesung_faellt=list(fallen))


def test_hand_verdict_success_at_the_gap():
    kind, text = ev.verdict_hand(_hand(2, 13, 46, 16))
    assert kind == "success"
    assert text == (f"**Kantenstreichung erhält das Optimum.** Bei der Schwelle 2 werden 13 von 31 Kanten mit zulässiger Route gestrichen (41,9{NB}%). "
                    "Das ganzzahlige Optimum über die 16 verbleibenden Routen ist weiter 46.")


def test_hand_verdict_success_below_the_gap_says_it_is_luck():
    kind, text = ev.verdict_hand(_hand(1, 10, 46, 20))
    assert kind == "success" and "Die Schwelle liegt unter der Lücke (2); dass das Optimum hier trotzdem bleibt, ist ein Zufall dieses Netzes und keine Garantie." in text


def test_hand_verdict_lost_names_the_new_optimum_and_the_edges_that_fall():
    kind, text = ev.verdict_hand(_hand(1, 17, 50, 11, fallen=[(0, 4), (4, 2)]))
    assert kind == "warning"
    assert text.startswith("**Schwelle zu klein: Optimum verloren.** Bei der Schwelle 1 werden 17 von 31 Kanten mit zulässiger Route gestrichen (54,8")
    assert "ist 50 statt 46" in text and "über die 11 verbleibenden Routen" in text and "unter der Lücke (2)" in text and "fallen die Kanten 0→4, 4→2." in text


def test_hand_verdict_without_any_decomposition_left():
    kind, text = ev.verdict_hand(_hand(0, 31, None, 0, fallen=[(0, 1)]))
    assert kind == "warning" and "nicht mehr jeder Kunde genau einmal bedienen" in text and "100,0" in text


def test_hand_verdict_threshold_exactly_one_above_and_equal_gap_boundaries():
    assert ev.verdict_hand(_hand(2, 13, 46, 16))[0] == "success"          # Schwelle = Lücke
    assert ev.verdict_hand(_hand(2, 13, 47, 16))[0] == "warning"          # verloren, auch bei Schwelle = Lücke (würde der Regel widersprechen, wird aber gemeldet)


def _live(**kw):
    v = dict(fertig=True, grund=None, exakt=True, luecke_pct=0.9, entfernt=47, mit_route=77, labels_voll=185, labels_gestr=42, optimum_bleibt=True, zstar=326.03)
    v.update(kw)
    return v


def test_live_verdict_success_names_gap_edges_labels_and_the_caveat():
    kind, text = ev.verdict_live(_live())
    assert kind == "success"
    assert text.startswith(f"**Kantenstreichung erhält das Optimum.** Bei der exakten Lücke (0,90{NB}% von LB) sind es 47 von 77 Kanten mit zulässiger Route gestrichen (61,0{NB}%).")
    assert f"erzeugt im gestrichenen Graphen 42 statt 185 Labels (× 0,23; {VORBEHALT})." in text
    assert "Das ganzzahlige Optimum (326,03) bleibt." in text and "Das ist ein Einzelfall" in text


def test_live_verdict_gap_zero_is_stated_as_zero_and_not_as_minus_zero():
    kind, text = ev.verdict_live(_live(luecke_pct=-1e-12))
    assert kind == "success" and "Die Lücke ist null (das Optimum erreicht die untere Schranke)" in text and "−0" not in text


def test_live_verdict_not_proven_uses_the_gap_of_bound_two():
    kind, text = ev.verdict_live(_live(exakt=False, luecke_pct=3.5, optimum_bleibt=None))
    assert kind == "info" and "nicht bewiesen" in text and f"(3,50{NB}% von LB)" in text and VORBEHALT in text


def test_live_verdict_proven_but_not_checked_and_the_impossible_case():
    kind, text = ev.verdict_live(_live(optimum_bleibt=None))
    assert kind == "info" and "nicht geprüft" in text and "(0,90" in text
    kind, text = ev.verdict_live(_live(optimum_bleibt=False))
    assert kind == "error" and "Prüfung fehlgeschlagen" in text


def test_live_verdict_unfinished_run():
    assert ev.verdict_live({"fertig": False, "grund": "Obergrenze erreicht"}) == ("error", "Die Rechnung wurde nicht fertig: Obergrenze erreicht.")


def _schwelle(**kw):
    v = dict(pct=2.0, luecke_pct=0.9, entfernt=43, mit_route=77, bleibt=True, zstar=326.03, z_rest=326.03)
    v.update(kw)
    return v


def test_threshold_verdict_above_the_true_gap_keeps_the_optimum():
    kind, text = ev.verdict_schwelle(_schwelle())
    assert kind == "success" and text.startswith(f"Bei der angenommenen Lücke von 2,0{NB}% von LB werden 43 von 77 Kanten mit zulässiger Route gestrichen (55,8{NB}%).")
    assert f"mehr als die echte Lücke dieser Instanz (0,90{NB}% von LB)" in text and "(326,03) bleibt" in text and "Eine Garantie gibt nur eine echte obere Schranke" in text


def test_threshold_verdict_equal_to_the_gap_counts_as_not_below():
    assert ev.verdict_schwelle(_schwelle(pct=0.9))[0] == "success"
    assert ev.verdict_schwelle(_schwelle(pct=0.89, bleibt=False, z_rest=326.5))[0] == "warning"


def test_threshold_verdict_below_the_gap_lost_and_kept():
    kind, text = ev.verdict_schwelle(_schwelle(pct=0.5, bleibt=False, z_rest=326.56))
    assert kind == "warning" and text.startswith("**Angenommene Lücke zu klein: Optimum verloren.**")
    assert "ist 326,56 statt 326,03" in text and f"Die echte Lücke dieser Instanz ist 0,90{NB}% von LB" in text
    kind, text = ev.verdict_schwelle(_schwelle(pct=0.5, bleibt=True))
    assert kind == "info" and "ein Zufall dieser Instanz und keine Garantie" in text
    kind, text = ev.verdict_schwelle(_schwelle(pct=0.5, bleibt=False, z_rest=None))
    assert kind == "warning" and "es gibt keine Zerlegung mehr" in text


def test_threshold_verdict_unproven_and_impossible_cases():
    kind, text = ev.verdict_schwelle(_schwelle(luecke_pct=None, bleibt=None))
    assert kind == "info" and "nicht bewiesen" in text
    assert ev.verdict_schwelle(_schwelle(pct=3.0, bleibt=False, z_rest=330.0))[0] == "error"


def _stufen(a, b, c, exakt=True, n=77):
    return dict(mit_route=n, exakt=exakt, ub1=dict(luecke_pct=a[0], entfernt=a[1]), ub2=dict(luecke_pct=b[0], entfernt=b[1]), ub3=dict(luecke_pct=c[0], entfernt=c[1]))


def test_upper_bound_verdict_names_the_three_stages():
    kind, text = ev.verdict_obere_schranken(_stufen((64.46, 0), (10.13, 7), (8.2, 7), n=89))
    assert kind == "success"
    assert f"obere Schranke 1, Lücke 64,46{NB}% von LB) fallen 0 von 89 Kanten (0,0{NB}%)" in text and f"(Schranke 2, 10,13{NB}%) 7 (7,9{NB}%)" in text and f"(Schranke 3, 8,20{NB}%) 7 (7,9{NB}%)" in text
    assert text.endswith("Je besser die obere Schranke, desto mehr Kanten fallen weg.")


def test_upper_bound_verdict_when_the_stages_agree_or_the_optimum_is_not_proven():
    kind, text = ev.verdict_obere_schranken(_stufen((0.9, 47), (0.9, 47), (0.9, 47)))
    assert kind == "info" and "streichen gleich viel" in text
    kind, text = ev.verdict_obere_schranken(_stufen((9.0, 10), (5.0, 20), (5.0, 20), exakt=False))
    assert kind == "info" and "nicht bewiesen, Schranke 3 ist dann gleich Schranke 2" in text


def _baender():
    return dict(instanzen=48, zellen=4, exakt=48, luecke_ub3=dict(mittel_min=0.0211, mittel_max=0.0361), streichen_ub3=dict(mittel_min=0.46, mittel_max=0.609, einzel_min=0.104, einzel_max=0.83),
                streichen_ub1=dict(mittel_min=0.22, mittel_max=0.417), labels_ub3=dict(mittel_min=0.342, mittel_max=0.522), labels_ub1=dict(mittel_min=0.563, mittel_max=0.799), kurve_abstand=3.97)


def test_band_verdict_names_ranges_counts_and_the_caveat():
    kind, text = ev.verdict_baender(_baender())
    assert kind == "success"
    assert f"(im Mittel 2,1 bis 3,6{NB}% von LB) werden im Mittel 46 bis 61{NB}% der Kanten mit zulässiger Route gestrichen (Spanne über die Instanzen 10 bis 83{NB}%)" in text
    assert "im Mittel 0,34 bis 0,52 der Labels des vollen Graphen" in text and f"nur 22 bis 42{NB}% der Kanten und 0,56 bis 0,80 der Labels" in text
    assert "n = 30 Kunden, ng-Gedächtnis k = 8, Partitionierungs-Master, eigene Instanzen, 4 Zellen mit zusammen 48 Instanzen, 48 von 48 mit bewiesenem Optimum" in text
    assert VORBEHALT in text and "höchstens 4,0 Prozentpunkte auseinander" in text


def test_band_verdict_for_n50_reports_the_unproven_instances():
    v = {"zufall": dict(instanzen=10, fertig=10, exakt=9, streichen_ub1=dict(mittel=0.278), streichen_ub2=dict(mittel=0.555), streichen_ub3=dict(mittel=0.652, zahl=9)),
         "gruppiert": dict(instanzen=8, fertig=8, exakt=3, streichen_ub1=dict(mittel=0.168), streichen_ub2=dict(mittel=0.398), streichen_ub3=dict(mittel=0.535, zahl=3))}
    kind, text = ev.verdict_baender_n50(v)
    assert kind == "info"
    assert "zufällig: 9 von 10 Instanzen mit bewiesenem Optimum" in text and f"28{NB}% mit Schranke 1, 56{NB}% mit Schranke 2, bei der exakten Lücke 65{NB}% (nur 9 Instanzen" in text
    assert "gruppiert: 3 von 8" in text and "(nur 3 Instanzen" in text and VORBEHALT in text
    v["gruppiert"]["streichen_ub3"] = dict(mittel=None, zahl=0)
    assert "bei der exakten Lücke kein bewiesenes Optimum" in ev.verdict_baender_n50(v)[1]


def _zeilen(verloren_ab=None, z_rest=326.56):
    zeilen = []
    for f in ev.GEGENPROBE_FAKTOREN:
        bleibt = True if verloren_ab is None or f > verloren_ab else False
        zeilen.append(dict(faktor=f, entfernt=47, anteil=47 / 77, bleibt=bleibt, z_rest=326.03 if bleibt else z_rest, zstar=326.03))
    return zeilen


ZAEHLUNG = dict(faelle=384, mit_luecke=168, optimum_verloren_exakt=0, optimum_verloren_halb=81)


def test_counter_check_verdict_names_the_first_loss_and_the_count_of_the_enumeration():
    kind, text = ev.verdict_gegenprobe(_zeilen(verloren_ab=0.9), ZAEHLUNG, 0.9)
    assert kind == "warning" and "erstmals bei einer Schwelle von 90 % der Lücke verloren (das beste ganzzahlige Ergebnis ist 326,56 statt 326,03; dort werden 47 Kanten gestrichen)." in text
    assert "384 Fälle" in text and "bei der exakten Lücke in 0 Fällen verloren, bei der halben Lücke in 81 von 168 Fällen mit Lücke größer null" in text


def test_counter_check_verdict_without_a_loss_without_a_gap_and_unproven():
    kind, text = ev.verdict_gegenprobe(_zeilen(), ZAEHLUNG, 2.0)
    assert kind == "info" and "bei allen 11 geprüften Schwellen bis herab zu 0 % der Lücke" in text and "Zufall dieser Instanz" in text
    kind, text = ev.verdict_gegenprobe(_zeilen(), ZAEHLUNG, 1e-12)
    assert kind == "info" and "Die Lücke dieser Instanz ist null" in text
    kind, text = ev.verdict_gegenprobe([], ZAEHLUNG, None)
    assert kind == "info" and "nicht möglich" in text
    kind, text = ev.verdict_gegenprobe(_zeilen(verloren_ab=0.9, z_rest=None), ZAEHLUNG, 0.9)
    assert "es gibt keine Zerlegung mehr" in text


def test_label_sentence_always_carries_the_caveat_and_handles_zero():
    assert ev.satz_labels(33, 20) == f"Das Vorwärts-Labeling erzeugt im gestrichenen Graphen 20 statt 33 Labels (× 0,61; {VORBEHALT})."
    assert VORBEHALT in ev.satz_labels(0, 0)


def test_number_formats():
    assert ev.fmt_int(1234567) == f"1{NB}234{NB}567" and ev.fmt_dec(-0.5, 1) == "−0,5" and ev.fmt_pct(0.419) == f"41,9{NB}%"
    assert ev.fmt_wert(44) == "44" and ev.fmt_wert(44.0) == "44" and ev.fmt_wert(44.25) == "44,25"
    from fractions import Fraction
    assert ev.fmt_wert(Fraction(83, 3)) == "83/3 (27,67)" and ev.fmt_wert(Fraction(6, 1)) == "6"
    assert ev.weg_text((4, 2)) == "4 → 2" and ev.weg_text(()) == "–" and ev.kante_text((0, 4)) == "0→4"


def test_inputs_of_the_verdicts_from_a_real_run_and_the_gap_stage_choice():
    live = ev.live_lauf(ev.LiveEinstellung(7, "zufällig", 40, 70, 7))
    sch = ev.live_schwelle(live, live["luecke"])
    v = ev.eingabe_live(live, sch)
    assert v["exakt"] and v["luecke_pct"] == pytest.approx(0.0, abs=1e-6) and v["entfernt"] == sch["entfernt"] and v["optimum_bleibt"] is True
    assert ev.eingabe_live(live, None)["optimum_bleibt"] is None
    o = ev.eingabe_obere(live)
    assert o["ub1"]["entfernt"] <= o["ub2"]["entfernt"] <= o["ub3"]["entfernt"] and o["exakt"] is True
    s = ev.eingabe_schwelle(live, ev.live_schwelle(live, 0.01 * live["zeile"]["lb"]), 1.0)
    assert s["pct"] == 1.0 and s["luecke_pct"] == pytest.approx(0.0, abs=1e-6) and s["bleibt"] is True
    zeilen = ev.gegenprobe_zeilen(live, lambda x: ev.live_schwelle(live, x))
    assert [r["faktor"] for r in zeilen] == [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0]
    nicht_exakt = dict(live, luecke=None, zstar=None)
    assert ev.gegenprobe_zeilen(nicht_exakt, lambda x: None) == []
