"""Konstanten: Regler-Grenzen, feste Annahmen, Farben und Presets.

Rechenaufwand am Regler-Maximum (DEMO-PLAYBOOK 1c): Die Live-Rechnung (Experimente 2, 3 und 5) führt die ganze Spaltenerzeugung bis zur Konvergenz aus, zählt danach ALLE zulässigen
elementaren Routen auf (Tiefensuche) und löst Mengenpartitionierungen über sie, bei höchstens DP_MAX_N Kunden durch Aufzählung über Kundenmengen (rund 3^n Schritte, bei n = 12 etwa 0,1 s),
darüber mit HiGHS. Die Zahl der zulässigen Routen wächst mit n und der Fensterbreite stark: bei n = 12 sind es bei Breite 100 bis rund 12 000, bei Breite 200 (gruppiert) rund 60 000 (gemessen
vor dem Bau); die Live-Rechnung dauert dort mehrere Sekunden (Labeling mit k = 12 und Aufzählung). Deshalb ist die Fensterbreite der Live-Rechnung auf höchstens 100 und n auf LIVE_N_MAX = 12
begrenzt; größere Fälle stehen als feste Messreihen in data/ (n = 30 und n = 50). Die Aufzählung ist auf LIVE_MAX_ROUTEN Routen begrenzt (feste Zahl statt Zeitgrenze, damit der Abbruch auf
jedem Rechner derselbe ist); bei Abbruch zeigt die App „nicht bewiesen“.
"""

# ---------------------------------------------------------------------------------------------------------------------------------
# Instanz (Solomon-artig, nicht die Originalinstanzen): Quadrat 100 x 100, Zeit = Entfernung, Depot in der Mitte
# ---------------------------------------------------------------------------------------------------------------------------------
HORIZONT = 300.0          # spätester Rückkehrzeitpunkt zum Depot
BEDIENZEIT = 10.0         # je Besuch
KAPAZITAET = 70           # Ladekapazität des Fahrzeugs
LAST_MIN, LAST_MAX = 5, 25   # Nachfrage (Last) je Kunde, ganze Zahlen
EPS = 1e-9                # Toleranz bei Vergleichen von Zeit und Kosten (Gleitkomma)
NEG_RC = -1e-7            # eine Route zählt als Spalte, wenn ihre reduzierten Kosten unter dieser Schwelle liegen
TOL_SCHWELLE = 1e-6       # eine Kante wird nur gestrichen, wenn ihr Wert die Schwelle um mehr als diese Toleranz übersteigt
RAUSCH = 1e-9             # Mengen im Master unter dieser Grenze zählen als null
MAX_NEUE_SPALTEN = 15     # höchstens so viele neue Spalten je Runde (die besten nach reduzierten Kosten)
MAX_RUNDEN = 400          # Sicherung der Spaltenerzeugung
DP_MAX_N = 14             # bis zu dieser Kundenzahl löst die Demo die ganzzahlige Partitionierung durch Aufzählung über Kundenmengen (rund 3^n Schritte), darüber mit HiGHS
MILP_ZEIT = 60.0          # Zeitgrenze (Sekunden) je Mengenpartitionierung; bei Ablauf gilt „nicht bewiesen“

# Handbeispiel (Experiment 1): Depot und sechs Kunden, ganze Zahlen
HAND_SCHWELLE_MIN, HAND_SCHWELLE_MAX, HAND_DEFAULT_SCHWELLE = 0, 6, 2

# Live-Rechnung (Experimente 2, 3 und 5)
LIVE_N_MIN, LIVE_N_MAX, LIVE_DEFAULT_N = 5, 12, 10
LIVE_K_MIN, LIVE_K_MAX, LIVE_DEFAULT_K = 2, 12, 8     # Größe des ng-Gedächtnisses; ab k = n ist die Rechnung elementar
LIVE_TYPEN = ("zufällig", "gruppiert")
LIVE_BREITEN = (20, 40, 60, 100)                      # Breite der Zeitfenster
LIVE_DEFAULT_TYP, LIVE_DEFAULT_BREITE = "zufällig", 100
SEED_MAX, LIVE_DEFAULT_SEED = 999999, 0
LIVE_MAX_ROUTEN = 400_000                              # Obergrenze der Aufzählung aller zulässigen Routen
LUECKE_PCT_MIN, LUECKE_PCT_MAX, LUECKE_DEFAULT_PCT = 0.5, 10.0, 2.0   # Experiment 3: angenommene Lücke in Prozent von LB
LUECKE_PCT_SCHRITT = 0.5

# ---------------------------------------------------------------------------------------------------------------------------------
# Vorbehalt der Wirkungsaussagen: steht im selben Satz wie jede Zahl über gestrichene Kanten und Labels (App und README)
# ---------------------------------------------------------------------------------------------------------------------------------
VORBEHALT = "nur bei den Dualpreisen der Konvergenz gemessen, der Nutzen in späteren Pricing-Aufrufen (nach Verzweigen oder Schnitten) ist nicht gemessen"

# ---------------------------------------------------------------------------------------------------------------------------------
# Feste Messreihen (data/)
# ---------------------------------------------------------------------------------------------------------------------------------
BAND_FILE = "baender_kanten.json"
ORAKEL_FILE = "gegenprobe_zaehlung.json"
BAND_GRID = (0.005, 0.01, 0.02, 0.03, 0.04, 0.05, 0.075, 0.10)   # Anteile von LB für die Kurve „Kanten mit Wert höchstens x % von LB“
BAND_SCHWELLEN = ("ub1", "ub2", "ub3", "r0.5", "r1", "r2", "r5")  # Schwellen der festen Messreihe
BAND_TYPEN = ("zufall", "gruppiert")
BAND_BREITEN = (40, 100)

# ---------------------------------------------------------------------------------------------------------------------------------
# Farben (hell und dunkel lesbar)
# ---------------------------------------------------------------------------------------------------------------------------------
COLOR_KEPT = "#2F6B65"
COLOR_REMOVED = "#d1495b"
COLOR_OPT = "#f2a900"
COLOR_GREY = "rgba(150,150,150,0.55)"
COLOR_LINE = "#4c78a8"
COLOR_LINE2 = "#e45756"
COLOR_LINE3 = "#f58518"
COLOR_LINE4 = "#72b7b2"

# ---------------------------------------------------------------------------------------------------------------------------------
# Presets (Schnellstart): jedes setzt ALLE Regler
# ---------------------------------------------------------------------------------------------------------------------------------
_BASIS = {
    "h_schwelle": HAND_DEFAULT_SCHWELLE,
    "l_n": LIVE_DEFAULT_N, "l_typ": LIVE_DEFAULT_TYP, "l_breite": LIVE_DEFAULT_BREITE, "l_seed": LIVE_DEFAULT_SEED, "l_k": LIVE_DEFAULT_K,
    "l_luecke": LUECKE_DEFAULT_PCT,
}
PRESETS = {
    "Grundfall: Schwelle gleich der Lücke": dict(_BASIS),
    "Zu kleine Schwelle: Optimum verloren": {**_BASIS, "h_schwelle": 1, "l_luecke": 0.5},
    "Keine Streichung: sehr große Schwelle": {**_BASIS, "h_schwelle": HAND_SCHWELLE_MAX, "l_luecke": LUECKE_PCT_MAX},
    "Gruppiert: schwache obere Schranke aus den Spalten": {**_BASIS, "l_typ": "gruppiert", "l_seed": 5, "l_luecke": 5.0},
    "Lücke null": {**_BASIS, "l_typ": "gruppiert", "l_seed": 1, "l_luecke": 0.5},
    "Größte Einstellung (n = 12, k = 12)": {**_BASIS, "l_n": LIVE_N_MAX, "l_typ": "gruppiert", "l_k": LIVE_K_MAX, "l_seed": 5},
}
PRESET_HELP = {
    "Grundfall: Schwelle gleich der Lücke": "Handbeispiel mit der Schwelle 2, das ist die Lücke z* − LB: 13 von 31 Kanten mit zulässiger Route werden gestrichen, das ganzzahlige Optimum 46 bleibt. Eigene Instanz: 10 zufällige Kunden, Fensterbreite 100, Zufalls-Seed 0 (eine Instanz), angenommene Lücke 2 % von LB.",
    "Zu kleine Schwelle: Optimum verloren": "Handbeispiel mit der Schwelle 1, der Hälfte der Lücke: 17 Kanten fallen, darunter 0→4 und 4→2 der optimalen Lösung, das beste ganzzahlige Ergebnis ist 50 statt 46. Eigene Instanz wie im Grundfall, aber mit einer angenommenen Lücke von nur 0,5 % von LB: in diesem Beispiel (eine Instanz) liegt sie unter der echten Lücke.",
    "Keine Streichung: sehr große Schwelle": "Handbeispiel mit der Schwelle 6, dem größten Wert einer Kante: es wird keine Kante gestrichen. Eigene Instanz wie im Grundfall, angenommene Lücke 10 % von LB.",
    "Gruppiert: schwache obere Schranke aus den Spalten": "Eigene Instanz mit 10 gruppierten Kunden, Fensterbreite 100, Zufalls-Seed 5 (eine Instanz): hier ist die Lücke der oberen Schranke aus den Spalten größer als die exakte Lücke; Experiment 3 zeigt den Unterschied der Stufen. Angenommene Lücke 5 % von LB.",
    "Lücke null": "Eigene Instanz mit 10 gruppierten Kunden, Fensterbreite 100, Zufalls-Seed 1 (eine Instanz): das Optimum erreicht die untere Schranke, die Lücke ist null; nur Kanten mit Pfad-reduzierten Kosten null bleiben.",
    "Größte Einstellung (n = 12, k = 12)": "Größte Live-Rechnung: 12 gruppierte Kunden, elementar (k = 12), Fensterbreite 100, Zufalls-Seed 5 (eine Instanz); rechnet einige Sekunden, weil alle zulässigen Routen aufgezählt werden.",
}
