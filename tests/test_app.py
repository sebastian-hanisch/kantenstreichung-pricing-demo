"""End-to-end-Rauchtest mit Streamlits AppTest: lädt app.py mit den Standardeinstellungen, klickt jeden Beispielszenario-Button, fährt jeden Regler an seine Grenzen, probiert jede Auswahl
und den Permalink und prüft, dass kein Python-Fehler auftritt und dass jedes Szenario die erwarteten Verdikt-Zeilen zeigt (DEMO-PLAYBOOK §11a Punkt 7).
Expander werden nie per Index, sondern per Titel angesprochen."""

import os

import pytest
from streamlit.testing.v1 import AppTest

import ksp_constants as C
import ksp_presets as P
import ksp_texte as T

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
TIMEOUT = int(os.environ.get("APPTEST_TIMEOUT", "300"))  # unter Last (parallele Läufe) reichen 180 s nicht immer; Umgebungsvariable zum Anpassen
NB = " "


def _fresh_app() -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    return at


def _verdicts(at) -> list:
    """Alle Verdikt- und Hinweisboxen (success, info, warning, error) als (Art, Text)."""
    return [(kind, e.value) for kind in ("success", "info", "warning", "error") for e in getattr(at, kind)]


def _expander(at, title):
    return next(e for e in at.expander if e.label == title)


def _regler(at, key):
    if key == "l_typ":
        return at.sidebar.radio(key=key)
    if key == "l_breite":
        return at.sidebar.select_slider(key=key)
    if key == "l_seed":
        return at.sidebar.number_input(key=key)
    return at.sidebar.slider(key=key)


def _wert(spec, rand):
    """Kleinster (0) oder größter (-1) zulässiger Wert eines Reglers."""
    if spec.choices is not None:
        return spec.choices[rand]
    return spec.lo if rand == 0 else spec.hi


def test_app_loads_without_exception_and_shows_the_default_verdicts():
    at = _fresh_app()
    texte = [t for _k, t in _verdicts(at)]
    assert any(t.startswith("**Kantenstreichung erhält das Optimum.** Bei der Schwelle 2 werden 13 von 31 Kanten") for t in texte)
    assert any(t.startswith(f"**Kantenstreichung erhält das Optimum.** Bei der exakten Lücke (0,90{NB}% von LB) sind es 47 von 77 Kanten") for t in texte)
    assert any(t.startswith(f"Bei der exakten Lücke (im Mittel 2,1 bis 3,6{NB}% von LB) werden im Mittel 46 bis 61{NB}%") for t in texte)
    assert not at.error


def test_every_button_click_does_not_raise():
    labels = [b.label for b in _fresh_app().button]
    assert labels, "keine Buttons gefunden"
    for index, label in enumerate(labels):
        at = _fresh_app()
        at.button[index].click().run(timeout=TIMEOUT)
        assert not at.exception, (label, [str(e) for e in at.exception])


@pytest.mark.parametrize("key", list(P.SETTING_SPECS))
def test_every_control_at_its_min_and_max_does_not_raise(key):
    spec = P.SETTING_SPECS[key]
    for rand in (0, -1):
        at = _fresh_app()
        _regler(at, key).set_value(_wert(spec, rand)).run(timeout=TIMEOUT)
        assert not at.exception, (key, rand, [str(e) for e in at.exception])
        assert not at.error, (key, rand, [e.value for e in at.error])


def test_all_minima_and_all_maxima_together_do_not_raise():
    for rand in (0, -1):
        at = _fresh_app()
        for key, spec in P.SETTING_SPECS.items():
            _regler(at, key).set_value(_wert(spec, rand))
        at.run(timeout=TIMEOUT)
        assert not at.exception, [str(e) for e in at.exception]
        assert not at.error, [e.value for e in at.error]


def test_seed_extremes_and_the_new_instance_button_do_not_raise():
    for seed in (0, C.SEED_MAX):
        at = _fresh_app()
        at.sidebar.number_input(key="l_seed").set_value(seed).run(timeout=TIMEOUT)
        assert not at.exception, seed
    at = _fresh_app()
    at.sidebar.button(key=next(b.key for b in at.sidebar.button if b.label.startswith("🎲"))).click().run(timeout=TIMEOUT)
    assert not at.exception and 0 <= at.session_state["l_seed"] <= C.SEED_MAX


@pytest.mark.parametrize("n", [30, 50])
def test_the_series_selection_does_not_raise_and_shows_its_cells(n):
    at = _fresh_app()
    at.radio(key="b_n").set_value(n).run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    texte = [t for _k, t in _verdicts(at)]
    if n == 50:
        assert any(t.startswith("n = 50, Fensterbreite 100, kleine Reihe: zufällig: 9 von 10 Instanzen mit bewiesenem Optimum") and "gruppiert: 3 von 8" in t for t in texte)
    else:
        assert any(t.startswith("Bei der exakten Lücke (im Mittel") for t in texte)


def test_permalink_sets_the_controls_and_unusable_values_fall_back_to_the_default():
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.query_params["n"] = "12"
    at.query_params["w"] = "40"
    at.query_params["typ"] = "gruppiert"
    at.query_params["hs"] = "99"
    at.query_params["k"] = "gibt es nicht"
    at.query_params["lp"] = "3.5"
    at.run(timeout=TIMEOUT)
    assert not at.exception
    s = at.session_state
    assert (s["l_n"], s["l_breite"], s["l_typ"], s["h_schwelle"], s["l_k"], s["l_luecke"]) == (12, 40, "gruppiert", C.HAND_SCHWELLE_MAX, C.LIVE_DEFAULT_K, 3.5)


# je Szenario: erwartete Verdikt-Zeilen (Art, Satzanfang oder Teilsatz); die Zahlen kommen aus dem Kern (siehe test_claims.py)
ERWARTET = {
    "Grundfall: Schwelle gleich der Lücke": [
        ("success", "**Kantenstreichung erhält das Optimum.** Bei der Schwelle 2 werden 13 von 31 Kanten mit zulässiger Route gestrichen"),
        ("success", f"Bei der exakten Lücke (0,90{NB}% von LB) sind es 47 von 77 Kanten mit zulässiger Route gestrichen"),
        ("success", f"Bei der angenommenen Lücke von 2,0{NB}% von LB werden 43 von 77 Kanten"),
        ("warning", "**Schwelle zu klein: Optimum verloren.** Auf dieser Instanz geht das Optimum erstmals bei einer Schwelle von 90 % der Lücke verloren")],
    "Zu kleine Schwelle: Optimum verloren": [
        ("warning", "**Schwelle zu klein: Optimum verloren.** Bei der Schwelle 1 werden 17 von 31 Kanten"),
        ("warning", f"**Angenommene Lücke zu klein: Optimum verloren.** Bei der angenommenen Lücke von 0,5{NB}% von LB werden 48 von 77 Kanten")],
    "Keine Streichung: sehr große Schwelle": [
        ("success", "**Kantenstreichung erhält das Optimum.** Bei der Schwelle 6 werden 0 von 31 Kanten"),
        ("success", f"Bei der angenommenen Lücke von 10,0{NB}% von LB werden 16 von 77 Kanten")],
    "Gruppiert: schwache obere Schranke aus den Spalten": [
        ("success", f"Bei der exakten Lücke (8,20{NB}% von LB) sind es 7 von 89 Kanten"),
        ("success", f"Aus den Spalten allein (obere Schranke 1, Lücke 64,46{NB}% von LB) fallen 0 von 89 Kanten"),
        ("info", f"Bei der angenommenen Lücke von 5,0{NB}% von LB werden 17 von 89 Kanten")],
    "Lücke null": [
        ("success", "**Kantenstreichung erhält das Optimum.** Die Lücke ist null (das Optimum erreicht die untere Schranke): es sind 55 von 80 Kanten"),
        ("info", "Die Lücke dieser Instanz ist null: jede Schwelle zwischen 0 und der Lücke ist null, es gibt nichts zu senken.")],
    "Größte Einstellung (n = 12, k = 12)": [
        ("success", f"Bei der exakten Lücke (9,52{NB}% von LB) sind es 3 von 125 Kanten"),
        ("success", f"Aus den Spalten allein (obere Schranke 1, Lücke 22,13{NB}% von LB) fallen 0 von 125 Kanten"),
        ("info", f"Bei der angenommenen Lücke von 2,0{NB}% von LB werden 31 von 125 Kanten")],
}


def test_every_preset_has_expected_verdict_lines():
    assert set(ERWARTET) == set(C.PRESETS)


@pytest.mark.parametrize("name", list(C.PRESETS), ids=[f"preset{i}" for i in range(len(C.PRESETS))])
def test_each_preset_shows_the_expected_verdict_lines(name):
    at = _fresh_app()
    at.sidebar.button(key=f"preset_{name}").click().run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert not at.error, [e.value for e in at.error]
    texte = _verdicts(at)
    for art, anfang in ERWARTET[name]:
        assert any(k == art and anfang in t for k, t in texte), (name, art, anfang, [t[:100] for _k, t in texte])
    for key, value in C.PRESETS[name].items():
        assert at.session_state[key] == value


def test_every_sentence_with_a_number_about_removed_edges_or_labels_carries_the_caveat():
    """In jedem Verdikt, das gestrichene Kanten oder Labels nennt und aus Messungen oder Läufen mit Dualpreisen der Konvergenz stammt, steht der Vorbehalt."""
    at = _fresh_app()
    for kind, text in _verdicts(at):
        if "Labels" in text and ("gestrichen" in text or "Vorwärts-Labeling" in text):
            assert C.VORBEHALT in text, text[:120]


def test_the_expanders_are_found_by_title_and_the_math_one_starts_with_the_reading_aid():
    at = _fresh_app()
    titel = [e.label for e in at.expander]
    assert "So funktioniert die Kantenstreichung" in titel and "⚠️ Annahmen, Grenzen und bekannte Probleme" in titel
    mathe = _expander(at, "📐 Mathematische Formulierung")
    assert mathe.markdown[0].value.startswith("\n**Gegeben:**") or mathe.markdown[0].value.lstrip().startswith("**Gegeben:**")
    assert "$$" in mathe.markdown[1].value
    assert mathe.markdown[1].value.count("$$") % 2 == 0


def test_app_text_of_assumptions_is_the_text_of_the_function():
    at = _fresh_app()
    assert _expander(at, "⚠️ Annahmen, Grenzen und bekannte Probleme").markdown[0].value == T.assumptions_markdown()
    assert any(m.value == T.annahmen_tabelle() for m in at.markdown)


def test_every_figure_has_a_unique_id_fixed_axes_no_log_axis_and_no_non_finite_numbers():
    """Plotly-Meldungen „Expected length, -Infinity“ oder NaN entstehen durch Log-Achsen mit Nullen und nicht finite Werte; hier: feste Achsen, keine Log-Achse, keine nicht endlichen Zahlen im JSON."""
    import json
    at = _fresh_app()
    figuren = at.get("plotly_chart")
    ids = [p.proto.id for p in figuren]
    assert len(figuren) >= 7 and len(set(ids)) == len(ids)
    for p in figuren:
        spec = json.loads(p.proto.spec)
        layout = spec["layout"]
        assert layout["xaxis"]["fixedrange"] is True and layout["yaxis"]["fixedrange"] is True
        assert layout["xaxis"].get("type") != "log" and layout["yaxis"].get("type") != "log"
        assert "NaN" not in p.proto.spec and "Infinity" not in p.proto.spec
