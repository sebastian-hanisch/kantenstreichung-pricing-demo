"""Presets (Schnellstart-Szenarien): Vollständigkeit, gültige Werte, Standard-Szenario = Standardeinstellungen, Permalink-Begrenzung."""

import pytest

import ksp_baender as B
import ksp_constants as C
import ksp_presets as P


def test_every_preset_has_help_and_sets_every_control():
    assert set(C.PRESETS) == set(C.PRESET_HELP)
    for name, preset in C.PRESETS.items():
        assert set(preset) == set(P.SETTING_SPECS), name
        assert C.PRESET_HELP[name]


def test_preset_values_are_valid_for_their_controls():
    for name, preset in C.PRESETS.items():
        for key, value in preset.items():
            spec = P.SETTING_SPECS[key]
            if spec.choices is not None:
                assert value in spec.choices, (name, key, value)
            else:
                assert spec.lo <= value <= spec.hi, (name, key, value)


def test_default_preset_equals_the_default_settings():
    first = next(iter(C.PRESETS.values()))
    assert {k: spec.default for k, spec in P.SETTING_SPECS.items()} == first


def test_presets_differ_from_each_other_in_at_least_one_control():
    werte = [tuple(sorted(p.items())) for p in C.PRESETS.values()]
    assert len(set(werte)) == len(werte)


def test_url_parameters_are_unique():
    params = [s.url_param for s in P.SETTING_SPECS.values()]
    assert len(params) == len(set(params))


@pytest.mark.parametrize("key, roh, erwartet", [
    ("l_n", "500", C.LIVE_N_MAX), ("l_n", "-3", C.LIVE_N_MIN), ("l_n", "abc", None), ("l_breite", "100", 100), ("l_breite", "70", None), ("l_breite", "200", None),
    ("l_typ", "gruppiert", "gruppiert"), ("l_typ", "egal", None), ("h_schwelle", "99", C.HAND_SCHWELLE_MAX), ("h_schwelle", "-1", C.HAND_SCHWELLE_MIN),
    ("l_k", "99", C.LIVE_K_MAX), ("l_k", "1", C.LIVE_K_MIN), ("l_seed", "12345678", C.SEED_MAX), ("l_seed", "-5", 0),
    ("l_luecke", "50", C.LUECKE_PCT_MAX), ("l_luecke", "0.1", C.LUECKE_PCT_MIN), ("l_luecke", "2.5", 2.5), ("l_luecke", "x", None),
])
def test_permalink_values_are_clamped_or_rejected(key, roh, erwartet):
    assert P._begrenzt(P.SETTING_SPECS[key], roh) == erwartet


def test_the_widths_of_the_fixed_series_are_widths_of_the_live_control():
    assert {z["breite"] for z in B.zellen()} <= set(C.LIVE_BREITEN)


def test_the_live_limits_keep_the_computation_small():
    assert C.LIVE_N_MAX <= C.DP_MAX_N and max(C.LIVE_BREITEN) <= 100 and C.LIVE_K_MAX == C.LIVE_N_MAX


def test_the_hand_threshold_range_covers_the_largest_edge_value():
    import ksp_evaluation as E
    b = E.hand_basis()
    assert C.HAND_SCHWELLE_MAX == max(round(b["P"][i][j]) for (i, j) in b["kanten"]) and C.HAND_DEFAULT_SCHWELLE == b["luecke"]
