"""Kantenstreichung im Pricing – interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Welche Kanten eines Netzes können in keiner besseren ganzzahligen Lösung vorkommen, wenn die Spaltenerzeugung eine untere Schranke und Dualpreise geliefert hat und eine obere Schranke bekannt ist?
Handbeispiel Schritt für Schritt, eigene Instanz live, feste Messreihen, Gegenprobe mit zu kleiner Schwelle.

Lauffähig mit: streamlit run app.py
"""

import streamlit as st

import ksp_algorithm as A
import ksp_baender as B
import ksp_constants as C
import ksp_evaluation as E
import ksp_texte as T
import ksp_visualization as V
from ksp_layout import dunkles_design, kopf_css
from ksp_presets import (
    bounds,
    choices,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    sidebar_presets,
    sync_query_params,
)

st.set_page_config(page_title="Kantenstreichung im Pricing – Sebastian Hanisch", layout="wide")


# --- Zwischenspeicher: alle Eingaben stehen im Schlüssel ----------------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def _hand_basis():
    return E.hand_basis()


@st.cache_resource(show_spinner=False)
def _hand_schwelle(schwelle):
    return E.hand_schwelle(_hand_basis(), schwelle)


@st.cache_resource(show_spinner=False, max_entries=24)
def _live(n, typ, breite, seed, k):
    return E.live_lauf(E.LiveEinstellung(n, typ, breite, seed, k))


@st.cache_resource(show_spinner=False, max_entries=200)
def _live_schwelle(n, typ, breite, seed, k, schwelle):
    return E.live_schwelle(_live(n, typ, breite, seed, k), schwelle)


# --- kleine Hilfen für Tabellen -----------------------------------------------------------------------------------------------------------

GANZ = st.column_config.NumberColumn(format="%d")
PROZENT = st.column_config.NumberColumn(format="%.1f %%")
PROZENT2 = st.column_config.NumberColumn(format="%.2f %%")


def _kennzahl_text(k, faktor=100, stellen=1):
    """„Mittel (Minimum–Maximum)“ als Text mit Dezimalkomma; „–“ bei leerer Zelle."""
    if k["mittel"] is None:
        return "–"
    return f"{E.fmt_dec(faktor * k['mittel'], stellen)} ({E.fmt_dec(faktor * k['min'], stellen)}–{E.fmt_dec(faktor * k['max'], stellen)})"


def _zellenname(z):
    return f"{B.TYPEN[z['typ']]}, Breite {z['breite']} (n = {z['n']})"


# --- Kopf und Einleitung ------------------------------------------------------------------------------------------------------------------

st.html(kopf_css(dunkles_design()))
with st.container(key="kopf"):
    st.title("✂️ Kantenstreichung im Pricing: welche Kanten sind überflüssig?")
st.markdown(
    f"""
Die **Spaltenerzeugung** (zum Beispiel bei der Tourenplanung) endet mit einer **unteren Schranke** (dem Wert des Masters) und **Dualpreisen**, je einem Preis pro Kunde. Die **reduzierten Kosten** einer Route sind ihre Länge minus die Preise der besuchten Kunden;
bei der Konvergenz ist keine Route mehr negativ. Kennt man dazu irgendeine **obere Schranke** (den Wert einer gefundenen ganzzahligen Lösung), lässt sich für jede **Kante** des Netzes sagen, ob sie in einer besseren Lösung noch vorkommen kann:
Ist die beste Route durch die Kante (ihre **Pfad-reduzierten Kosten**) schlechter als die Lücke zwischen oberer und unterer Schranke, kann man die Kante streichen, ohne das Optimum zu verlieren.
Diese Demo fragt: **Wie viele Kanten fallen weg, wie viel weniger Labels braucht das Pricing danach, und was geschieht bei einer zu kleinen Schwelle?** Gemessen werden gestrichene Kanten und erzeugte Labels; die Wirkung ist {C.VORBEHALT}.

Weiter unten: fünf Abschnitte **🔬 Experiment**, dann **🚧 Wo die Annahmen enden** und die Expander **⚠️ Annahmen, Grenzen und bekannte Probleme** und **📐 Mathematische Formulierung**.
"""
)

with st.expander("So funktioniert die Kantenstreichung", expanded=True):
    st.markdown(
        """
1. **Ausgangslage:** Die Spaltenerzeugung ist fertig. Der Master liefert die untere Schranke **LB** und je Kunde einen **Dualpreis** π; ihre Summe ist LB. Jede Route hat **reduzierte Kosten** = Länge minus die Preise ihrer Kunden, und keine ist negativ.
2. **Die Lücke:** Für jede ganzzahlige Lösung, in der jeder Kunde genau einmal vorkommt, gilt: Kosten = LB + Summe der reduzierten Kosten ihrer Routen. Kennt man eine ganzzahlige Lösung mit Kosten **UB** und will nur Lösungen mit Kosten bis UB, hat jede ihrer Routen reduzierte Kosten höchstens **UB − LB**, die **Lücke**.
3. **Pfad-reduzierte Kosten einer Kante:** die kleinsten reduzierten Kosten einer zulässigen Route, die die Kante benutzt. Man bekommt sie, indem man **Vorwärtslabels** (Teilwege vom Depot) mit **Rückwärtslabels** (Reste bis zum Depot) verbindet; zusammen müssen Zeit, Last und besuchte Kunden passen.
4. **Streichen:** Eine Kante fällt weg, wenn ihre Pfad-reduzierten Kosten größer sind als die Lücke. Das **ganzzahlige Optimum bleibt**, denn jede Route einer Lösung bis UB hat Kanten mit Werten höchstens ihrer reduzierten Kosten, also höchstens der Lücke.
5. **Gut zu wissen:** Die Lücke braucht eine **echte** obere Schranke. Eine zu kleine Schwelle darf Kanten der optimalen Lösung streichen (Experiment 5). Je besser die obere Schranke, desto kleiner die Lücke und desto mehr Kanten fallen weg (Experimente 3 und 4).
        """
    )

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

# --- Seitenleiste ------------------------------------------------------------------------------------------------------------------------

with st.sidebar:
    sidebar_presets()  # Schnellstart oben, das aktive Szenario ist hervorgehoben
    st.header("🧮 Handbeispiel")
    st.caption("Für Experiment 1 (sechs Kunden, zum Nachrechnen mit dem Stift).")
    h_schwelle = st.slider("Schwelle zum Streichen (Experiment 1)", *bounds("h_schwelle"), key="h_schwelle",
                           help="Kanten mit Pfad-reduzierten Kosten über dieser Schwelle werden gestrichen. Die Lücke des Handbeispiels ist 2; darunter geht das Optimum verloren.")
    st.header("🔧 Eigene Instanz")
    st.caption("Für die Experimente 2, 3 und 5: die ganze Spaltenerzeugung und das exakte Optimum auf einer zufälligen Instanz.")
    l_n = st.slider("Kunden n", *bounds("l_n"), key="l_n", help="Zahl der Kunden (Quadrat 100 × 100, Depot in der Mitte). Bis 12, weil die Rechnung alle zulässigen Routen aufzählt.")
    l_typ = st.radio("Lage der Kunden", choices("l_typ"), key="l_typ", horizontal=True, help="zufällig: gleichverteilt im Quadrat; gruppiert: fünf Gruppen von Kunden.")
    l_breite = st.select_slider("Breite der Zeitfenster", options=choices("l_breite"), key="l_breite",
                                help="Je breiter die Fenster, desto mehr Routen sind zulässig. Die Messreihen in Experiment 4 haben Breite 40 und 100.")
    l_k = st.slider("ng-Gedächtnis k", *bounds("l_k"), key="l_k",
                    help="Wie viele nächste Nachbarn sich ein Label merkt. Ab k = n ist die Rechnung elementar (jeder Kunde höchstens einmal); kleiner macht die Pfad-reduzierten Kosten schwächer, aber nie ungültig.")
    l_seed = st.number_input("Zufalls-Seed der Instanz", *bounds("l_seed"), key="l_seed", step=1)
    st.button("🎲 Neue Instanz generieren", width="stretch", on_click=randomize_seed)
    st.header("✂️ Angenommene Lücke")
    st.caption("Für Experiment 3: eine Schwelle in Prozent von LB, ohne Garantie.")
    l_luecke = st.slider("Angenommene Lücke in % von LB (Experiment 3)", *bounds("l_luecke"), key="l_luecke", step=C.LUECKE_PCT_SCHRITT,
                         help="Eine Schwelle, die nicht aus einer oberen Schranke folgt. Liegt sie unter der echten Lücke der Instanz, kann das Optimum verloren gehen.")

sync_query_params({k_: st.session_state[k_] for k_ in ("h_schwelle", "l_n", "l_typ", "l_breite", "l_k", "l_seed", "l_luecke")})

# ======================================================================================================================================
# Experiment 1: Handbeispiel
# ======================================================================================================================================

st.subheader("🔬 Experiment 1: Kantenwerte Schritt für Schritt – das Handbeispiel")
b = _hand_basis()
h = _hand_schwelle(int(h_schwelle))
inst_h = b["inst"]
st.markdown(
    f"""
Ein Depot (D) und **sechs Kunden** auf einem Gitter, Entfernung = Manhattan-Abstand = Fahrzeit = Kosten, Bedienzeit {inst_h.bedienzeit}, Kapazität {inst_h.kapazitaet}, späteste Rückkehr {inst_h.horizont}. Alle Zahlen sind ganz und lassen sich mit dem Stift nachrechnen.
Der Master ist über **alle {len(b['routen'])} zulässigen Routen** exakt mit Brüchen gerechnet; so entstehen die untere Schranke und die Dualpreise der Konvergenz.
"""
)
st.dataframe(
    [{"Kunde": i, "Lage": f"({inst_h.punkte[i][0]}, {inst_h.punkte[i][1]})", "Zeitfenster": f"[{inst_h.frueh[i]}, {inst_h.spaet[i]}]", "Bedarf": inst_h.last[i],
      "Einzelroute D → Kunde → D": E.fmt_int(A.weg_laenge(inst_h, (i,))), "Dualpreis π": E.fmt_wert(b["dual"][i])} for i in range(1, inst_h.n + 1)],
    hide_index=True, width="stretch",
)
rcs = list(b["rc"].values())
st.caption(
    f"Depot bei ({inst_h.punkte[0][0]}, {inst_h.punkte[0][1]}). **Untere Schranke LB = {E.fmt_wert(b['lb'])}**, Summe der Dualpreise {E.fmt_wert(sum(b['dual'][1:]))}. Die Lösung des Masters ist gebrochen: "
    + "; ".join(f"Route {E.weg_text(r)} mit Menge {E.fmt_wert(x)}" for r, x in b["x"]) + ". "
    f"Dualzulässigkeit: die kleinsten reduzierten Kosten aller Routen sind {E.fmt_wert(min(rcs))} (bei {sum(1 for v in rcs if v == min(rcs))} Routen), keine ist negativ. "
    f"**Ganzzahliges Optimum z\\* = {E.fmt_int(b['zstar'])}** durch Aufzählung aller Zerlegungen, mit den Routen " + ", ".join(E.weg_text(r) for r in b["loesung"]) +
    f"; die **Lücke** ist z\\* − LB = {E.fmt_int(b['luecke'])}."
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Schwelle", E.fmt_int(h["schwelle"]), delta=f"Lücke: {E.fmt_int(b['luecke'])}", delta_color="off")
m2.metric("Gestrichen", f"{h['entfernt']} von {h['mit_route']}", delta=E.fmt_pct(h["entfernt"] / h["mit_route"]) + " der Kanten mit Route", delta_color="off")
m3.metric("Optimum danach", "keines" if h["z_rest"] is None else E.fmt_int(h["z_rest"]), delta=f"{h['routen_uebrig']} von {len(b['routen'])} Routen übrig", delta_color="off")
m4.metric("Erzeugte Vorwärtslabels", E.fmt_int(h["labels_gestr"]), delta=f"{h['labels_gestr'] - h['labels_voll']:+d} gegen voll ({E.fmt_int(h['labels_voll'])})", delta_color="inverse")
c1, c2 = st.columns([3, 2])
with c1:
    st.plotly_chart(V.build_netz_hand(b, h), width="stretch", key="hand_netz")
    st.caption(f"Pfeile: Kanten mit mindestens einer zulässigen Route ({h['mit_route']} von {inst_h.n * (inst_h.n + 1)} gerichteten Kanten). Die Zahl am Pfeil sind die Pfad-reduzierten Kosten. Grün bleibt, rot wird gestrichen, orange unterlegt sind die Kanten der optimalen Lösung.")
with c2:
    loes = {e for r in b["loesung"] for e in A.route_kanten(r)}
    st.dataframe(
        [{"Kante": E.kante_text(e), "Wert": round(b["P"][e[0]][e[1]]), "beste Route über die Kante": E.weg_text(b["beste"][e]), "Entscheidung": "gestrichen" if e in h["gestrichen"] else "bleibt",
          "optimale Lösung": "ja" if e in loes else ""} for e in sorted(b["kanten"], key=lambda e: (b["P"][e[0]][e[1]], e))],
        hide_index=True, width="stretch", height=380,
        column_config={"Wert": st.column_config.NumberColumn("Pfad-reduzierte Kosten", format="%d")},
    )
    st.caption("„0→4“ heißt: vom Depot (0) zu Kunde 4. Beispiel zum Nachrechnen: Kante 4→5, beste Route 4 → 5: Länge 10 + 8 + 8 = 26, minus die Dualpreise π₄ + π₅ = 22, ergibt 4.")
kind, text = E.verdict_hand(h)
getattr(st, kind)(text)
st.caption(E.satz_labels(h["labels_voll"], h["labels_gestr"]) + " Beide Läufe finden dieselben kleinsten reduzierten Kosten über alle Endlabels: "
           f"{E.fmt_wert(h['bester_voll'])} im vollen, {E.fmt_wert(h['bester_gestr'])} im gestrichenen Graphen.")
with st.expander("📋 Die Labels bei den Dualpreisen (alle nicht dominierten, nichts abgeschnitten)"):
    st.markdown(f"**Vorwärtslabels:** {b['F']['erzeugt']} erzeugt, {sum(len(a) for a in b['F']['ueberlebende'])} überleben. Ein Label ist ein Teilweg vom Depot mit Zeit, reduzierten Kosten, Last und besuchten Kunden.")
    st.dataframe([{"Knoten": v, "Teilweg": E.weg_text(A.vorwaerts_route(b["F"], x)), "Zeit": b["F"]["labels"][x][0], "reduzierte Kosten": E.fmt_wert(b["F"]["labels"][x][1]), "Last": b["F"]["labels"][x][2]}
                  for v in range(1, inst_h.n + 1) for x in b["F"]["ueberlebende"][v] if not b["F"]["labels"][x][6]], hide_index=True, width="stretch")
    st.markdown(f"**Rückwärtslabels:** {b['B']['erzeugt']} erzeugt, {sum(len(a) for a in b['B']['ueberlebende']) - 1} überleben. Ein Label ist ein Rest bis zum Depot; die Zeit ist der späteste Beginn der Bedienung am ersten Kunden des Rests, die Kosten enthalten den Dualpreis dieses ersten Kunden nicht (er gehört zur Kante, die ihn betritt).")
    st.dataframe([{"Knoten": v, "Rest bis zum Depot": E.weg_text(A.rueckwaerts_route(b["B"], x)), "späteste Zeit": b["B"]["labels"][x][0], "Kosten": E.fmt_wert(b["B"]["labels"][x][1]), "Last": b["B"]["labels"][x][2]}
                  for v in range(1, inst_h.n + 1) for x in b["B"]["ueberlebende"][v] if not b["B"]["labels"][x][6]], hide_index=True, width="stretch")
st.markdown("---")

# ======================================================================================================================================
# Experiment 2: eigene Instanz
# ======================================================================================================================================

st.subheader("🔬 Experiment 2: Eine eigene Instanz – exakte Lücke, gestrichene Kanten, Labels")
st.markdown(
    f"""
Eine zufällige Instanz mit **{l_n} Kunden** ({l_typ}, Zufalls-Seed {l_seed}), Zeitfenster der Breite {l_breite}, ng-Gedächtnis k = {min(l_k, l_n)}{' (elementar)' if l_k >= l_n else ''}. Die Spaltenerzeugung läuft bis zur Konvergenz (Partitionierungs-Master);
danach wird mit **drei oberen Schranken** gearbeitet: 1 der beste ganzzahlige Wert aus den Spalten, 2 dazu die beste Route je Kante, 3 dazu die Aufzählung aller Routen mit kleinen reduzierten Kosten: das ist das **exakte Optimum**.
Es wird mit der Lücke des exakten Optimums gestrichen (Schwelle = z\\* − LB). Jede aufgezählte Route wird vor der Anzeige unabhängig geprüft.
"""
)
with st.spinner("Spaltenerzeugung, Kantenwerte und exaktes Optimum werden gerechnet (die größten Einstellungen brauchen einige Sekunden) …"):
    live = _live(int(l_n), l_typ, int(l_breite), int(l_seed), int(l_k))
z = live["zeile"]
if live["fehler"]:
    st.error("Prüfung fehlgeschlagen: " + live["fehler"])
sch_exakt = None
if live["fertig"] and live["zstar"] is not None:
    sch_exakt = _live_schwelle(int(l_n), l_typ, int(l_breite), int(l_seed), int(l_k), float(live["luecke"]))
v_live = E.eingabe_live(live, sch_exakt)
if live["fertig"]:
    stufe = "ub3" if z["ub3_exakt"] else "ub2"
    w = z["wirkung"][stufe]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Untere Schranke LB", E.fmt_dec(z["lb"], 2), delta=f"{z['runden']} Runden, {z['spalten']} Spalten", delta_color="off")
    m2.metric("Obere Schranke" + (" (exaktes Optimum)" if z["ub3_exakt"] else " 2 (Optimum nicht bewiesen)"), E.fmt_dec(z[stufe], 2), delta=f"Lücke {E.fmt_dec(E.nullen(v_live['luecke_pct'], 1e-7), 2)} % von LB", delta_color="off")
    m3.metric("Gestrichene Kanten", f"{w['entfernt']} von {z['kanten_mit_route']}", delta=E.fmt_pct(w["entfernt"] / z["kanten_mit_route"]) + " der Kanten mit Route", delta_color="off")
    m4.metric("Erzeugte Vorwärtslabels", E.fmt_int(w["labels"]), delta=f"{w['labels'] - z['labels_vorwaerts']:+d} gegen voll ({E.fmt_int(z['labels_vorwaerts'])})", delta_color="inverse")
    c1, c2 = st.columns([3, 2])
    sch_netz = sch_exakt if sch_exakt is not None else _live_schwelle(int(l_n), l_typ, int(l_breite), int(l_seed), int(l_k), float(w["schwelle"]))
    with c1:
        st.plotly_chart(V.build_netz_live(live, sch_netz), width="stretch", key="live_netz")
        st.caption("Alle Kanten mit mindestens einer zulässigen Route (Richtung nicht gezeigt); gestrichelt rot die gestrichenen, grün die bleibenden, orange die Routen der besten bekannten Lösung.")
    with c2:
        st.plotly_chart(V.build_labels(z["labels_vorwaerts"], w["labels"]), width="stretch", key="live_labels")
        st.dataframe([
            {"Schranke": "untere Schranke LB", "Wert": z["lb"], "Lücke zu LB": None, "gestrichen": None, "Labels": z["labels_vorwaerts"]},
            {"Schranke": "obere Schranke 1: Spalten", "Wert": z["ub1"], "Lücke zu LB": E.nullen(100 * (z["ub1"] - z["lb"]) / z["lb"], 1e-7), "gestrichen": z["wirkung"]["ub1"]["entfernt"], "Labels": z["wirkung"]["ub1"]["labels"]},
            {"Schranke": "obere Schranke 2: + beste Route je Kante", "Wert": z["ub2"], "Lücke zu LB": E.nullen(100 * (z["ub2"] - z["lb"]) / z["lb"], 1e-7), "gestrichen": z["wirkung"]["ub2"]["entfernt"], "Labels": z["wirkung"]["ub2"]["labels"]},
            {"Schranke": "obere Schranke 3: Optimum" + ("" if z["ub3_exakt"] else " (nicht bewiesen)"), "Wert": z["ub3"], "Lücke zu LB": E.nullen(100 * (z["ub3"] - z["lb"]) / z["lb"], 1e-7), "gestrichen": z["wirkung"]["ub3"]["entfernt"], "Labels": z["wirkung"]["ub3"]["labels"]},
        ], hide_index=True, width="stretch", column_config={"Wert": st.column_config.NumberColumn(format="%.2f"), "Lücke zu LB": PROZENT2, "gestrichen": GANZ, "Labels": GANZ})
    st.caption(
        f"Aufzählung: {E.fmt_int(len(live['alle']))} zulässige elementare Routen insgesamt, {E.fmt_int(z['routen_aufgezaehlt'])} mit reduzierten Kosten höchstens UB2 − LB"
        f"{'' if z['aufzaehlung_vollstaendig'] else ' (die Aufzählung erreichte ihre Obergrenze)'}. Die Spalten der Spaltenerzeugung erzeugten {E.fmt_int(z['labels_spaltenerzeugung'])} Labels in {z['runden']} Pricing-Aufrufen."
    )
kind, text = E.verdict_live(v_live)
getattr(st, kind)(text)
st.markdown("---")

# ======================================================================================================================================
# Experiment 3: wie gut muss die obere Schranke sein?
# ======================================================================================================================================

st.subheader("🔬 Experiment 3: Wie gut muss die obere Schranke sein?")
st.markdown(
    """
Die Schwelle bestimmt, wie viele Kanten fallen. Die Kurve zeigt, **welcher Anteil der Kanten mit zulässiger Route Pfad-reduzierte Kosten höchstens x % von LB hat**: die Instanz aus Experiment 2 (schwarz) und die Mittel der vier festen Messreihen mit n = 30 (Fensterbreite 40 und 100, zufällig und gruppiert).
Senkrechte Marken: die Lücken der drei oberen Schranken dieser Instanz (soweit sie unter 10 % liegen) und die gewählte angenommene Lücke.
"""
)
if live["fertig"]:
    lb = z["lb"]
    sch3 = _live_schwelle(int(l_n), l_typ, int(l_breite), int(l_seed), int(l_k), float(l_luecke / 100 * lb))
    marken = [(f"Schranke {i}", 100 * z["wirkung"][s]["schwelle"] / lb) for i, s in enumerate(("ub1", "ub2", "ub3"), start=1)]
    zellen30 = [(_zellenname(zz), B.gitterkurve(zz)) for zz in B.zellen(30)]
    st.plotly_chart(V.build_kurve(E.live_kurve(live), zellen30, marken, float(l_luecke)), width="stretch", key="kurve")
    st.caption("Waagerecht: die Schwelle in Prozent von LB; senkrecht: der Anteil der Kanten mit zulässiger Route, deren Pfad-reduzierte Kosten höchstens so groß sind.")
    m1, m2, m3 = st.columns(3)
    m1.metric("Angenommene Lücke", f"{E.fmt_dec(l_luecke, 1)} % von LB", delta=f"Schwelle {E.fmt_dec(l_luecke / 100 * lb, 2)}", delta_color="off")
    m2.metric("Gestrichen", f"{sch3['entfernt']} von {sch3['mit_route']}", delta=E.fmt_pct(sch3["entfernt"] / sch3["mit_route"]) + " der Kanten mit Route", delta_color="off")
    m3.metric("Optimum danach", "nicht geprüft" if sch3["z_rest"] is None and sch3["optimum_bleibt"] is None else ("keines" if sch3["z_rest"] is None else E.fmt_dec(sch3["z_rest"], 2)),
              delta="bleibt" if sch3["optimum_bleibt"] else ("verloren" if sch3["optimum_bleibt"] is False else "–"), delta_color="off")
    kind, text = E.verdict_schwelle(E.eingabe_schwelle(live, sch3, float(l_luecke)))
    getattr(st, kind)(text)
    kind, text = E.verdict_obere_schranken(E.eingabe_obere(live))
    getattr(st, kind)(text)
    st.caption(f"Eine Instanz ist ein Einzelfall. Wie weit die Anteile in den Messreihen streuen, zeigt Experiment 4 ({C.VORBEHALT}).")
else:
    st.warning("Die Live-Rechnung ist nicht fertig geworden: " + z.get("grund", "unbekannter Grund") + ".")
st.markdown("---")

# ======================================================================================================================================
# Experiment 4: Bänder
# ======================================================================================================================================

st.subheader("🔬 Experiment 4: Messreihen mit vielen Instanzen (Bänder)")
st.markdown(
    f"""
Feste Messreihen, mit dem Kern dieser Demo gerechnet und danach Zahl für Zahl mit der Messung vor dem Bau verglichen ({E.fmt_int(B.vergleich_mit_vormessung()['verglichen'])} Werte, {B.vergleich_mit_vormessung()['abweichend']} Abweichungen): Spaltenerzeugung bis zur Konvergenz
mit ng-Gedächtnis k = 8, Partitionierungs-Master, eigene Instanzen mit den Zufalls-Seeds 1400 ff. Je Schwelle stehen der Anteil gestrichener Kanten (an den Kanten mit zulässiger Route) und das Verhältnis der erzeugten Vorwärtslabels
im gestrichenen zum vollen Graphen, jeweils Mittel und Spanne (Minimum bis Maximum) über die Instanzen. Alle Werte gelten {C.VORBEHALT}.
"""
)
b_n = st.radio("Reihe", (30, 50), key="b_n", horizontal=True, format_func=lambda n: f"n = {n} Kunden" + (" (vier Zellen, je 12 Instanzen)" if n == 30 else " (nur Breite 100, kleine Reihe)"))
zs = B.zellen(b_n)
ue = [B.zellen_uebersicht(zz) for zz in zs]
st.markdown("**Aufbau der Reihe** (abgebrochene Läufe zählen in keine Kennzahl)")
st.dataframe(
    [{"Zelle": _zellenname(zz), "Instanzen": u["instanzen"], "fertig": u["fertig"], "abgebrochen": u["abgebrochen"], "Optimum bewiesen": u["ub3_exakt"],
      "Kanten gesamt": u["kanten_gesamt"], "Kanten mit zulässiger Route (Median)": E.fmt_wert(u["kanten_mit_route_median"], 1), "volle Labels (Median)": E.fmt_wert(u["labels_voll_median"], 1),
      "Lücke Schranke 1 (Mittel, Max.)": f"{E.fmt_dec(100 * u['luecke']['ub1']['mittel'], 2)} % ({E.fmt_dec(100 * u['luecke']['ub1']['max'], 1)})",
      "Lücke Schranke 2": f"{E.fmt_dec(100 * u['luecke']['ub2']['mittel'], 2)} % ({E.fmt_dec(100 * u['luecke']['ub2']['max'], 1)})",
      "Lücke exakt": "–" if u["luecke"]["ub3"]["mittel"] is None else f"{E.fmt_dec(100 * u['luecke']['ub3']['mittel'], 2)} % ({E.fmt_dec(100 * u['luecke']['ub3']['max'], 1)})"} for zz, u in zip(zs, ue)],
    hide_index=True, width="stretch", column_config={"Kanten gesamt": GANZ},
)
tab = {zz["id"]: B.streichtabelle(zz) for zz in zs}
st.markdown("**Gestrichene Kanten** in % der Kanten mit zulässiger Route: Mittel (Minimum–Maximum). Bei „UB3: exaktes Optimum“ zählen nur Instanzen mit bewiesenem Optimum.")
st.dataframe([{"Schwelle": E.SCHWELLEN_KURZ[s], **{_zellenname(zz): _kennzahl_text(tab[zz["id"]][s]["streichen"]) + (f" [n = {tab[zz['id']][s]['streichen']['zahl']}]" if s == "ub3" else "") for zz in zs}}
              for s in C.BAND_SCHWELLEN], hide_index=True, width="stretch")
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Gestrichen (%)**, Mittel mit Spanne")
    st.plotly_chart(V.build_baender_streichen([(_zellenname(zz), {s: {k: (v * 100 if k != "zahl" and v is not None else v) for k, v in tab[zz["id"]][s]["streichen"].items()} for s in C.BAND_SCHWELLEN}) for zz in zs]), width="stretch", key=f"band_streichen_{b_n}")
with c2:
    st.markdown("**Labels im gestrichenen / vollen Graphen**, Mittel mit Spanne")
    st.plotly_chart(V.build_baender_labels([(_zellenname(zz), {s: tab[zz["id"]][s]["labels"] for s in C.BAND_SCHWELLEN}) for zz in zs]), width="stretch", key=f"band_labels_{b_n}")
st.markdown("**Verhältnis der erzeugten Vorwärtslabels** (gestrichen / voll): Mittel (Minimum–Maximum)")
st.dataframe([{"Schwelle": E.SCHWELLEN_KURZ[s], **{_zellenname(zz): _kennzahl_text(tab[zz["id"]][s]["labels"], 1, 2) for zz in zs}} for s in C.BAND_SCHWELLEN], hide_index=True, width="stretch")
if b_n == 30:
    kind, text = E.verdict_baender(E.eingabe_baender(30))
else:
    kind, text = E.verdict_baender_n50({zz["typ"]: {"instanzen": u["instanzen"], "fertig": u["fertig"], "exakt": u["ub3_exakt"], "streichen_ub1": tab[zz["id"]]["ub1"]["streichen"],
                                                    "streichen_ub2": tab[zz["id"]]["ub2"]["streichen"], "streichen_ub3": tab[zz["id"]]["ub3"]["streichen"]} for zz, u in zip(zs, ue)})
getattr(st, kind)(text)
hinweise = B.vormessung_hinweise()
if hinweise:
    st.caption("Abweichungen von der Messung vor dem Bau (bei Instanzen ohne bewiesenes Optimum möglich, etwa wenn der Löser seine Zeitgrenze erreicht): " + "; ".join(hinweise[:6]) + (" …" if len(hinweise) > 6 else ""))
st.caption("Je Zelle stehen 8 bis 12 Instanzen, die Spannen über die Instanzen sind groß; Mittelwerte gelten nicht für Einzelinstanzen und sind kein Konfidenzmaß.")
st.markdown("---")

# ======================================================================================================================================
# Experiment 5: Gegenprobe
# ======================================================================================================================================

st.subheader("🔬 Experiment 5: Die Gegenprobe – ab wann geht das Optimum verloren?")
st.markdown(
    """
Die Streichregel ist nur mit einer Schwelle von mindestens der Lücke garantiert. Hier wird die Schwelle der Instanz aus Experiment 2 schrittweise unter die Lücke gesenkt (100 % bis 0 % der Lücke z\\* − LB); zu jeder Schwelle steht das beste ganzzahlige Ergebnis über die Routen ohne gestrichene Kante.
Daneben die Zählung der Gegenprobe an kleinen Instanzen (n = 7 bis 10), mit dem Kern dieser Demo gerechnet.
"""
)
zaehl = B.gegenprobe()
if live["fertig"]:
    zeilen5 = E.gegenprobe_zeilen(live, lambda s: _live_schwelle(int(l_n), l_typ, int(l_breite), int(l_seed), int(l_k), float(s)))
    if zeilen5:
        st.plotly_chart(V.build_gegenprobe(zeilen5), width="stretch", key="gegenprobe")
        st.dataframe([{"Schwelle (% der Lücke)": round(100 * r["faktor"]), "Schwelle": r["schwelle"], "gestrichen": r["entfernt"], "Anteil": 100 * r["anteil"],
                       "Optimum": "bleibt" if r["bleibt"] else ("verloren" if r["bleibt"] is False else "nicht geprüft"),
                       "bestes ganzzahliges Ergebnis": r["z_rest"], "Labels (gestrichen)": r["labels_gestr"]} for r in zeilen5], hide_index=True, width="stretch",
                     column_config={"Schwelle": st.column_config.NumberColumn(format="%.2f"), "Anteil": PROZENT, "bestes ganzzahliges Ergebnis": st.column_config.NumberColumn(format="%.2f"), "gestrichen": GANZ, "Labels (gestrichen)": GANZ})
    luecke_pct = None if live["luecke"] is None else 100 * live["luecke"] / z["lb"]
    kind, text = E.verdict_gegenprobe(zeilen5, zaehl, luecke_pct)
    getattr(st, kind)(text)
else:
    st.warning("Die Live-Rechnung ist nicht fertig geworden: " + z.get("grund", "unbekannter Grund") + ".")
st.caption(
    f"Zählung (n = 7, 8, 9, 10, Fensterbreite 40 und 100, zufällig und gruppiert, je Größe 12 Instanzen × 2 Gedächtnisse, {zaehl['faelle']} Fälle; das exakte Optimum in allen bewiesen): "
    f"Die Pfad-reduzierten Kosten lagen in {zaehl['wert_ueber_wahrem_wert']} Fällen über dem wahren Wert der elementaren Routen; bei k = n sind sie gleich ({zaehl['wert_unter_wahrem_wert_bei_k_gleich_n']} Kanten abweichend), "
    f"bei k = 5 lagen sie bei {zaehl['wert_unter_wahrem_wert_bei_k_kleiner_n']} von {E.fmt_int(zaehl['kanten_mit_route_bei_k_kleiner_n'])} Kanten mit Route darunter. Streichen mit der exakten Lücke verlor das Optimum in {zaehl['optimum_verloren_exakt']} Fällen."
)
st.markdown("---")

# ======================================================================================================================================
# Grenzen, Annahmen, Mathematik
# ======================================================================================================================================

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(T.annahmen_tabelle())

with st.expander("⚠️ Annahmen, Grenzen und bekannte Probleme"):
    st.markdown(T.assumptions_markdown())

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(T.MATH_LESEHILFE)
    st.markdown(T.MATH_FORMELN)

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zur Reihe: [Ressourcenwege: von der Grenze zur Verfahrenswahl](https://sebastianhanisch.net/konzepte-ressourcenwege.html)."
)
