"""Permalink (Begrenzen), Presets und Zufalls-Seed-Button (Standardmuster aus dem Demo-Portfolio).

Alle Regler stehen in SETTING_SPECS (Name im Session State -> Adressparameter, Typ, Standard, Grenzen oder zulässige Werte). Das aktive Beispielszenario wird zustandslos bestimmt:
eines ist aktiv, wenn jeder Regler dem Wert des Szenarios entspricht."""

import random
from dataclasses import dataclass

import streamlit as st

import ksp_constants as C


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: type
    default: object
    lo: float | None = None
    hi: float | None = None
    choices: tuple | None = None   # zulässige Werte (Auswahlregler); sonst gelten lo und hi


SETTING_SPECS = {
    "h_schwelle": SettingSpec("hs", int, C.HAND_DEFAULT_SCHWELLE, C.HAND_SCHWELLE_MIN, C.HAND_SCHWELLE_MAX),
    "l_n": SettingSpec("n", int, C.LIVE_DEFAULT_N, C.LIVE_N_MIN, C.LIVE_N_MAX),
    "l_typ": SettingSpec("typ", str, C.LIVE_DEFAULT_TYP, choices=C.LIVE_TYPEN),
    "l_breite": SettingSpec("w", int, C.LIVE_DEFAULT_BREITE, choices=C.LIVE_BREITEN),
    "l_seed": SettingSpec("seed", int, C.LIVE_DEFAULT_SEED, 0, C.SEED_MAX),
    "l_k": SettingSpec("k", int, C.LIVE_DEFAULT_K, C.LIVE_K_MIN, C.LIVE_K_MAX),
    "l_luecke": SettingSpec("lp", float, C.LUECKE_DEFAULT_PCT, C.LUECKE_PCT_MIN, C.LUECKE_PCT_MAX),
}
PRESET_KEYS = {key: key for key in SETTING_SPECS}   # Presets nennen dieselben Schlüssel wie der Session State


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def choices(state_key) -> tuple:
    return SETTING_SPECS[state_key].choices


def _begrenzt(spec: SettingSpec, raw):
    """Wert aus der Adresszeile auf Typ, zulässige Werte und Reglergrenzen bringen; None, wenn er unbrauchbar ist."""
    try:
        value = spec.caster(raw)
    except (ValueError, TypeError):
        return None
    if spec.choices is not None:
        return value if value in spec.choices else None
    if spec.lo is not None:
        value = max(spec.lo, value)
    if spec.hi is not None:
        value = min(spec.hi, value)
    return value


def load_permalink_settings():
    """Einmal je Sitzung: Werte aus der Adresszeile übernehmen, auf die Reglergrenzen begrenzt; unbrauchbare Werte bleiben beim Standard."""
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            value = _begrenzt(spec, qp[spec.url_param])
            if value is not None:
                st.session_state[state_key] = value
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """`values`: {state_key: aktueller Wert}; die Adresszeile spiegelt die Konfiguration."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(value)
    except Exception:
        pass


def apply_preset(name):
    for state_key in SETTING_SPECS:
        if state_key in C.PRESETS[name]:
            st.session_state[state_key] = C.PRESETS[name][state_key]


def aktives_preset():
    """Name des Szenarios, dessen Werte GENAU den aktuellen Einstellungen entsprechen, sonst None.

    Zustandslos: verglichen wird jeder Regler aus SETTING_SPECS (ein Szenario ohne Eintrag für einen Regler meint dessen Standardwert) mit dem Session State.
    Ein später ergänzter Regler braucht nur seinen Eintrag in SETTING_SPECS, dann hebt auch seine Änderung die Markierung auf (tests/test_layout.py prüft das für jeden Regler)."""
    for name, preset in C.PRESETS.items():
        if all(st.session_state.get(state_key, spec.default) == preset.get(state_key, spec.default) for state_key, spec in SETTING_SPECS.items()):
            return name
    return None


def sidebar_presets():
    """Schnellstart oben in der Seitenleiste; das aktive Szenario ist hervorgehoben (`type="primary"`)."""
    if not C.PRESETS:
        return
    st.header("🎯 Schnellstart")
    st.caption("Ein Beispielszenario laden (setzt alle Regler):")
    aktiv = aktives_preset()
    for name in C.PRESETS:
        st.button(
            name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP.get(name, ""), key=f"preset_{name}",
            type="primary" if aktiv == name else "secondary",
        )


def randomize_seed():
    st.session_state["l_seed"] = random.randint(0, C.SEED_MAX)
