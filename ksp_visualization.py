"""Plotly-Abbildungen. Alle Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht am Diagramm hängen bleiben.

Beschriftungen stehen als Text auf Kategorienachsen (mit `type="category"`, damit Plotly keine lineare Achse mit Zwischenwerten anlegt, auch bei Beschriftungen wie „1“ oder „10 %“);
die Wertachsen haben feste Bereiche und nie eine logarithmische Achse (keine Nullen oder Unendlich in den Daten)."""

import math

import plotly.graph_objects as go

import ksp_algorithm as A
import ksp_constants as C
from ksp_evaluation import SCHWELLEN_KURZ, fmt_dec, fmt_int

ZELLEN_FARBEN = (C.COLOR_LINE, C.COLOR_LINE2, C.COLOR_LINE3, C.COLOR_LINE4)


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height=340, legende=True):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", y=-0.25) if legende else None, showlegend=legende)
    return lock_axes(fig)


def _stumm(fig):
    """Netzdarstellung: keine Achsenbeschriftung, kein Gitter."""
    fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=False)
    fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False)
    return fig


def _legende(fig, name, farbe, strich="solid", breite=3):
    """Legendeneintrag ohne Daten (für Pfeile, die als Anmerkung gezeichnet werden)."""
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=name, line=dict(color=farbe, width=breite, dash=strich), hoverinfo="skip"))


# ---------------------------------------------------------------------------------------------------------------------------------
# Netz des Handbeispiels
# ---------------------------------------------------------------------------------------------------------------------------------

def _pfeil(p, q, versatz=0.09, kuerzung=0.30):
    """Anfang und Ende eines Pfeils von p nach q, beidseitig gekürzt und senkrecht versetzt, damit Hin- und Rückrichtung nebeneinander liegen."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    laenge = math.hypot(dx, dy) or 1.0
    ux, uy = dx / laenge, dy / laenge
    nx, ny = -uy, ux
    return (p[0] + ux * kuerzung + nx * versatz, p[1] + uy * kuerzung + ny * versatz), (q[0] - ux * kuerzung + nx * versatz, q[1] - uy * kuerzung + ny * versatz)


def build_netz_hand(b: dict, h: dict):
    """Das Netz des Handbeispiels: Pfeile je Kante mit zulässiger Route, beschriftet mit den Pfad-reduzierten Kosten; gestrichene Kanten rot, bleibende grün,
    die Kanten der optimalen Lösung orange unterlegt."""
    inst, P = b["inst"], b["P"]
    pt = inst.punkte
    loesung = {e for r in b["loesung"] for e in A.route_kanten(r)}
    fig = go.Figure()
    for (i, j) in b["kanten"]:
        if (i, j) in loesung:
            p, q = _pfeil(pt[i], pt[j])
            fig.add_annotation(x=q[0], y=q[1], ax=p[0], ay=p[1], xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=0, arrowwidth=7, arrowcolor=C.COLOR_OPT, opacity=0.45)
    for (i, j) in b["kanten"]:
        weg = (i, j) in h["gestrichen"]
        p, q = _pfeil(pt[i], pt[j])
        fig.add_annotation(x=q[0], y=q[1], ax=p[0], ay=p[1], xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=2, arrowsize=1.1, arrowwidth=1.6,
                           arrowcolor=C.COLOR_REMOVED if weg else C.COLOR_KEPT, opacity=0.85)
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        fig.add_annotation(x=mx, y=my, text=f"{round(P[i][j])}", showarrow=False, font=dict(size=9, color=C.COLOR_REMOVED if weg else C.COLOR_KEPT),
                           bgcolor="rgba(255,255,255,0.75)", borderpad=0)
    kunden = list(range(1, inst.n + 1))
    fig.add_trace(go.Scatter(x=[pt[i][0] for i in kunden], y=[pt[i][1] for i in kunden], mode="markers+text", text=[str(i) for i in kunden], textposition="middle center",
                             marker=dict(size=24, color="white", line=dict(color="#444", width=1.5)), textfont=dict(color="#111", size=12), name="Kunde", showlegend=False,
                             hovertext=[f"Kunde {i}: Fenster [{inst.frueh[i]}, {inst.spaet[i]}], Bedarf {inst.last[i]}" for i in kunden], hoverinfo="text"))
    fig.add_trace(go.Scatter(x=[pt[0][0]], y=[pt[0][1]], mode="markers+text", text=["D"], textposition="middle center", marker=dict(size=28, symbol="square", color="#dddddd", line=dict(color="#444", width=1.5)),
                             textfont=dict(color="#111", size=12), name="Depot", showlegend=False, hovertext=["Depot"], hoverinfo="text"))
    _legende(fig, "bleibt", C.COLOR_KEPT)
    _legende(fig, "gestrichen", C.COLOR_REMOVED)
    _legende(fig, "Kante der optimalen Lösung (unterlegt)", C.COLOR_OPT, breite=7)
    fig.update_xaxes(range=[-0.8, 11.2])
    fig.update_yaxes(range=[-1.0, 6.0])
    _stumm(fig)
    return _base(fig, height=380)


# ---------------------------------------------------------------------------------------------------------------------------------
# Netz der Live-Instanz
# ---------------------------------------------------------------------------------------------------------------------------------

def _linien(pt, kanten):
    xs, ys = [], []
    for (i, j) in kanten:
        xs += [pt[i][0], pt[j][0], None]
        ys += [pt[i][1], pt[j][1], None]
    return xs, ys


def build_netz_live(live: dict, sch: dict):
    """Die Live-Instanz: Kanten mit zulässiger Route (Richtung nicht gezeigt), gestrichene gestrichelt rot, bleibende grün, die Routen der exakten Lösung orange."""
    inst, intern = live["inst"], live["intern"]
    pt = inst.punkte
    kanten = A.kanten_mit_route(intern["P"])
    bleibt = [e for e in kanten if e not in sch["gestrichen"]]
    weg = [e for e in kanten if e in sch["gestrichen"]]
    fig = go.Figure()
    xs, ys = _linien(pt, weg)
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=C.COLOR_REMOVED, width=1, dash="dot"), opacity=0.55, name=f"gestrichen ({len(weg)})", hoverinfo="skip"))
    xs, ys = _linien(pt, bleibt)
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=C.COLOR_KEPT, width=1.4), opacity=0.75, name=f"bleibt ({len(bleibt)})", hoverinfo="skip"))
    sol = [e for r in intern["loesung"] for e in A.route_kanten(r)]
    xs, ys = _linien(pt, sol)
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=C.COLOR_OPT, width=4), opacity=0.55, name="Routen der besten bekannten Lösung", hoverinfo="skip"))
    kunden = list(range(1, inst.n + 1))
    fig.add_trace(go.Scatter(x=[pt[i][0] for i in kunden], y=[pt[i][1] for i in kunden], mode="markers+text", text=[str(i) for i in kunden], textposition="middle center",
                             marker=dict(size=20, color="white", line=dict(color="#444", width=1.2)), textfont=dict(color="#111", size=11), showlegend=False,
                             hovertext=[f"Kunde {i}: Fenster [{fmt_dec(inst.frueh[i], 0)}, {fmt_dec(inst.spaet[i], 0)}], Bedarf {inst.last[i]}" for i in kunden], hoverinfo="text"))
    fig.add_trace(go.Scatter(x=[pt[0][0]], y=[pt[0][1]], mode="markers+text", text=["D"], textposition="middle center", marker=dict(size=24, symbol="square", color="#dddddd", line=dict(color="#444", width=1.2)),
                             textfont=dict(color="#111", size=11), showlegend=False, hovertext=["Depot"], hoverinfo="text"))
    fig.update_xaxes(range=[-5, 105])
    fig.update_yaxes(range=[-5, 105])
    _stumm(fig)
    return _base(fig, height=420)


# ---------------------------------------------------------------------------------------------------------------------------------
# Labels voll gegen gestrichen
# ---------------------------------------------------------------------------------------------------------------------------------

def build_labels(voll: int, gestr: int):
    """Erzeugte Vorwärtslabels im vollen und im gestrichenen Graphen (bei denselben Dualpreisen)."""
    xs = ["voller Graph", "gestrichener Graph"]
    fig = go.Figure(go.Bar(x=xs, y=[voll, gestr], marker_color=[C.COLOR_GREY, C.COLOR_KEPT], text=[fmt_int(voll), fmt_int(gestr)], textposition="outside", cliponaxis=False,
                           hovertemplate="%{x}: %{y} Labels<extra></extra>"))
    fig.update_xaxes(type="category")
    fig.update_yaxes(title_text="erzeugte Labels", range=[0, max(voll, 1) * 1.2])
    return _base(fig, height=280, legende=False)


# ---------------------------------------------------------------------------------------------------------------------------------
# Experiment 3: Kurve „Kanten mit Wert höchstens x % von LB“
# ---------------------------------------------------------------------------------------------------------------------------------

def build_kurve(live_punkte: list, zellen: list, marken: list, aktuell_pct: float):
    """Anteil der Kanten mit zulässiger Route, deren Pfad-reduzierte Kosten höchstens x % von LB betragen: die Live-Instanz (dicke Linie) und die Mittel der festen Messreihen.

    `zellen`: [(Name, [Anteil je Punkt von BAND_GRID])]; `marken`: [(Name, Lücke in % von LB)] der drei oberen Schranken; `aktuell_pct`: die gewählte angenommene Lücke."""
    fig = go.Figure()
    for (name, ys), farbe in zip(zellen, ZELLEN_FARBEN):
        fig.add_trace(go.Scatter(x=[100 * g for g in C.BAND_GRID], y=[100 * y for y in ys], mode="lines+markers", name=name, line=dict(color=farbe, width=1.5), marker=dict(size=5),
                                 hovertemplate=name + "<br>%{x} % von LB: %{y:.1f} % der Kanten<extra></extra>"))
    fig.add_trace(go.Scatter(x=[p[0] for p in live_punkte], y=[100 * p[1] for p in live_punkte], mode="lines", name="diese Instanz", line=dict(color="#111111", width=4),
                             hovertemplate="diese Instanz<br>%{x} % von LB: %{y:.1f} % der Kanten<extra></extra>"))
    fig.add_shape(type="line", x0=aktuell_pct, x1=aktuell_pct, y0=0, y1=100, line=dict(color=C.COLOR_OPT, width=2))
    fig.add_annotation(x=aktuell_pct, y=100, text="gewählt", showarrow=False, yshift=10, font=dict(size=10, color=C.COLOR_OPT))
    stufe = 0
    for name, pct in marken:
        if 0 <= pct <= C.LUECKE_PCT_MAX:
            fig.add_shape(type="line", x0=pct, x1=pct, y0=0, y1=100, line=dict(color="#888888", width=1, dash="dot"))
            fig.add_annotation(x=pct, y=4 + 9 * stufe, text=name, showarrow=False, xshift=2, xanchor="left", font=dict(size=10))
        stufe += 1
    # Die Schwelle steht als Tickbeschriftung „2 %“ und in der Bildunterschrift der App, nicht als Achsentitel: bei winziger Anfangsbreite des Diagramms (erster Aufbau im Browser) rechnet Plotly
    # die Lage des x-Achsentitels aus keiner einzigen Tickbeschriftung und meldet „attribute y: Expected length, -Infinity“.
    fig.update_xaxes(range=[0, C.LUECKE_PCT_MAX], ticksuffix=" %")
    fig.update_yaxes(title_text="Kanten ≤ Schwelle (%)", range=[0, 106])
    return _base(fig, height=380)


# ---------------------------------------------------------------------------------------------------------------------------------
# Experiment 4: Bänder
# ---------------------------------------------------------------------------------------------------------------------------------

def _gruppiert(zeilen: list, einheit: str, obergrenze: float):
    """Balken je Schwelle und Zelle (Mittel) mit Fehlerbalken von Minimum bis Maximum; `zeilen`: [(Zellenname, {Schwelle: Kennzahlen})]."""
    fig = go.Figure()
    xs = [SCHWELLEN_KURZ[s] for s in C.BAND_SCHWELLEN]
    for (name, tab), farbe in zip(zeilen, ZELLEN_FARBEN):
        mitt = [tab[s]["mittel"] for s in C.BAND_SCHWELLEN]
        lo = [tab[s]["mittel"] - tab[s]["min"] for s in C.BAND_SCHWELLEN]
        hi = [tab[s]["max"] - tab[s]["mittel"] for s in C.BAND_SCHWELLEN]
        fig.add_trace(go.Bar(x=xs, y=mitt, name=name, marker_color=farbe, error_y=dict(type="data", symmetric=False, array=hi, arrayminus=lo, thickness=1.2, width=3),
                             hovertemplate=name + "<br>%{x}: Mittel %{y:.1f}" + einheit + "<extra></extra>"))
    fig.update_layout(barmode="group")
    fig.update_xaxes(type="category")
    fig.update_yaxes(range=[0, obergrenze])
    return fig


def build_baender_streichen(zeilen: list):
    """Streichanteil (% der Kanten mit zulässiger Route) je Schwelle, Mittel je Zelle, Fehlerbalken Minimum bis Maximum der Instanzen. `zeilen`: [(Zellenname, {Schwelle: Prozent-Kennzahlen})]."""
    fig = _gruppiert(zeilen, " %", 102)
    fig.update_yaxes(title_text="gestrichen (% der Kanten mit zulässiger Route)")
    return _base(fig, height=380)


def build_baender_labels(zeilen: list):
    """Verhältnis der erzeugten Vorwärtslabels (gestrichener gegen voller Graph) je Schwelle, Mittel je Zelle, Fehlerbalken Minimum bis Maximum der Instanzen."""
    fig = _gruppiert(zeilen, "", 1.05)
    fig.update_yaxes(title_text="Labels gestrichen / voll")
    return _base(fig, height=380)


# ---------------------------------------------------------------------------------------------------------------------------------
# Experiment 5: Gegenprobe
# ---------------------------------------------------------------------------------------------------------------------------------

def build_gegenprobe(zeilen: list):
    """Gestrichener Anteil je Schwelle (in % der Lücke), Balken rot, wo das Optimum verloren geht. `zeilen`: [{"faktor", "anteil" (Anteil 0..1), "bleibt" (True, False oder None)}]."""
    xs = [f"{round(100 * z['faktor'])} %" for z in zeilen]
    farben = [C.COLOR_KEPT if z["bleibt"] else (C.COLOR_REMOVED if z["bleibt"] is False else C.COLOR_GREY) for z in zeilen]
    fig = go.Figure(go.Bar(x=xs, y=[100 * z["anteil"] for z in zeilen], marker_color=farben, text=[("Optimum bleibt" if z["bleibt"] else ("verloren" if z["bleibt"] is False else "?")) for z in zeilen],
                           textposition="outside", cliponaxis=False, hovertemplate="Schwelle %{x} der Lücke: %{y:.1f} % gestrichen<extra></extra>"))
    fig.update_xaxes(type="category", title_text="Schwelle in % der Lücke (UB − LB)")
    fig.update_yaxes(title_text="gestrichen (% der Kanten mit Route)", range=[0, 118])
    return _base(fig, height=340, legende=False)
