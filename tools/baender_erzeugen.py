"""Feste Messreihen der Demo erzeugen: `data/baender_kanten.json` und `data/gegenprobe_zaehlung.json`.

Alle Reihen werden mit dem Kern DIESER Demo gerechnet (`ksp_evaluation.analyse_instanz`, dieselbe Funktion wie die Live-Rechnung der App) und danach Zahl für Zahl mit den Rohdateien der Messung
vor dem Bau verglichen (`out_v14_*.txt`, `out_v14n50m_*.txt`); die Zahl der verglichenen und der abweichenden Werte steht je Zelle in der Datei. Jede Zelle nennt ihre Quelle, die Zahl der
fertigen und der abgebrochenen Läufe und die Seeds. Die Reihen entstehen nicht beim Start der App und nicht in den Tests; die Tests rechnen Stichproben nach.

Aufruf (aus dem Ordner der Demo, mit dem Test-venv):
  python tools/baender_erzeugen.py n30                      alle vier Zellen mit n = 30 (je 12 Instanzen) -> data/baender_kanten.json (ersetzt die Zellen gleicher Kennung)
  python tools/baender_erzeugen.py zelle zufall_100_n50 --out FRAGMENT.json   eine Zelle in eine eigene Datei (für lange Läufe nebeneinander)
  python tools/baender_erzeugen.py zusammen FRAGMENT.json ...                Fragmente in data/baender_kanten.json einfügen
  python tools/baender_erzeugen.py gegenprobe               die Zählung der Gegenprobe (n = 7 bis 10, 384 Fälle) -> data/gegenprobe_zaehlung.json
Die Rohdateien der Messung vor dem Bau liegen im Ordner `label-setting-planung/vormessung` neben den Demo-Ordnern (Option --vormessung)."""

import argparse
import json
import math
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import ksp_algorithm as A  # noqa: E402
import ksp_constants as C  # noqa: E402
import ksp_evaluation as E  # noqa: E402
import ksp_master as M  # noqa: E402
import ksp_scenario as S  # noqa: E402

SEED0 = 1400
ZELLEN = {  # Kennung: (Typ, Breite, n, Zahl der Instanzen, Rohdatei der Messung vor dem Bau)
    "zufall_40_n30": ("zufall", 40, 30, 12, "out_v14_zufall_40.txt"),
    "zufall_100_n30": ("zufall", 100, 30, 12, "out_v14_zufall_100.txt"),
    "gruppiert_40_n30": ("gruppiert", 40, 30, 12, "out_v14_gruppiert_40.txt"),
    "gruppiert_100_n30": ("gruppiert", 100, 30, 12, "out_v14_gruppiert_100.txt"),
    "zufall_100_n50": ("zufall", 100, 50, 10, "out_v14n50m_zufall_100.txt"),
    "gruppiert_100_n50": ("gruppiert", 100, 50, 8, "out_v14n50m_gruppiert_100.txt"),
}
K_NG = 8
SCHWELLE_ZUORDNUNG = {"gap1": "ub1", "gap2": "ub2", "gap3": "ub3", "r0.5": "r0.5", "r1": "r1", "r2": "r2", "r5": "r5"}


def _json_sicher(x):
    """inf und nan als None (gültiges JSON)."""
    if isinstance(x, float) and not math.isfinite(x):
        return None
    if isinstance(x, dict):
        return {k: _json_sicher(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_json_sicher(v) for v in x]
    return x


def rechne_zelle(zid: str, vormessung: Path) -> dict:
    typ, breite, n, anzahl, datei = ZELLEN[zid]
    zeilen = []
    for s in range(anzahl):
        seed = SEED0 + s
        inst = S.make_instance(n, seed, breite, gruppiert=(typ == "gruppiert"))
        zeile, _intern = E.analyse_instanz(inst, K_NG)
        zeile["seed"] = seed
        zeilen.append(_json_sicher(zeile))
        print(zid, seed, "fertig" if zeile["fertig"] else "ABGEBROCHEN: " + zeile.get("grund", ""), flush=True)
    zelle = {
        "id": zid, "typ": typ, "breite": breite, "n": n, "k": K_NG, "master": "Partitionierung", "instanzen": anzahl, "seeds": [SEED0, SEED0 + anzahl - 1],
        "quelle": f"neu gerechnet mit dem Kern dieser Demo (tools/baender_erzeugen.py, ksp_evaluation.analyse_instanz); verglichen mit {datei} der Messung vor dem Bau",
        "neu_gerechnet": True, "zeilen": zeilen,
        "vergleich": vergleiche(zeilen, vormessung / datei, datei),
    }
    return zelle


def lade_vormessung(pfad: Path) -> dict:
    """Zeilen der Rohdatei (JSON je Zeile) nach Seed."""
    out = {}
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if zeile.startswith("{"):
            d = json.loads(zeile)
            out[d["seed"]] = d
    return out


def _gleich(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool) or isinstance(a, int) and isinstance(b, int):
        return a == b
    return abs(float(a) - float(b)) <= 1e-6 * max(1.0, abs(float(b)))


def vergleiche(zeilen: list, pfad: Path, name: str) -> dict:
    """Werte je Instanz mit der Rohdatei der Messung vor dem Bau vergleichen: LB, die drei oberen Schranken, ob UB3 exakt ist, Zahl der Kanten mit Route, Vorwärtslabels
    und je Schwelle die Zahl gestrichener Kanten und die Labels im gestrichenen Graphen. Rückgabe: Datei, Zahl verglichener und abweichender Werte, die ersten Abweichungen."""
    if not pfad.exists():
        return {"datei": name, "verglichen": 0, "abweichend": 0, "abweichungen": [], "hinweis": "Rohdatei nicht gefunden"}
    roh = lade_vormessung(pfad)
    verglichen, abweichend, liste = 0, 0, []

    def pruefen(seed, name_, mein, ref):
        nonlocal verglichen, abweichend
        verglichen += 1
        if not _gleich(mein, ref):
            abweichend += 1
            if len(liste) < 30:
                liste.append(f"Seed {seed} {name_}: hier {mein}, Messung vor dem Bau {ref}")

    for z in zeilen:
        r = roh.get(z["seed"])
        if r is None or r.get("aborted") or not z["fertig"]:
            continue
        pruefen(z["seed"], "LB", z["lb"], r["LB"])
        pruefen(z["seed"], "UB1", z["ub1"], r["UB1"])
        pruefen(z["seed"], "UB2", z["ub2"], r["UB2"])
        pruefen(z["seed"], "UB3", z["ub3"], r["UB3"])
        pruefen(z["seed"], "UB3 exakt", z["ub3_exakt"], r["UB3_exakt"])
        pruefen(z["seed"], "Kanten mit Route", z["kanten_mit_route"], r["edges_route_feasible"])
        pruefen(z["seed"], "Vorwärtslabels", z["labels_vorwaerts"], r["F_generated"])
        for alt, neu in SCHWELLE_ZUORDNUNG.items():
            pruefen(z["seed"], f"gestrichen bei {neu}", z["wirkung"][neu]["entfernt"], r["wirkung"][alt]["removed"])
            pruefen(z["seed"], f"Labels bei {neu}", z["wirkung"][neu]["labels"], r["wirkung"][alt]["labels"])
    return {"datei": name, "verglichen": verglichen, "abweichend": abweichend, "abweichungen": liste}


def meta() -> dict:
    import numpy
    import scipy
    return {"python": platform.python_version(), "scipy": scipy.__version__, "numpy": numpy.__version__, "system": platform.system()}


def schreibe_zellen(zellen: list, ziel: Path):
    """Zellen in die Datei einfügen (gleiche Kennung ersetzt), Reihenfolge wie in ZELLEN."""
    vorhanden = {}
    if ziel.exists():
        vorhanden = {z["id"]: z for z in json.loads(ziel.read_text(encoding="utf-8"))["zellen"]}
    for z in zellen:
        vorhanden[z["id"]] = z
    daten = {"beschreibung": "Feste Messreihen der Kantenstreichung (Zufalls-Seeds 1400 ff., ng-Gedächtnis k = 8, Partitionierungs-Master, eigene Solomon-artige Instanzen).",
             "erzeugt_mit": meta(), "zellen": [vorhanden[k] for k in ZELLEN if k in vorhanden]}
    ziel.write_text(json.dumps(daten, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------------------------------------------------------------
# Zählung der Gegenprobe (Orakel der Messung vor dem Bau, mit dem Kern dieser Demo gerechnet)
# ---------------------------------------------------------------------------------------------------------------------------------

def gegenprobe_fall(n: int, breite: int, gruppiert: bool, seed: int, k: int) -> dict:
    """Ein Fall: Spaltenerzeugung, Kantenwerte, Aufzählung ALLER zulässigen elementaren Routen, ganzzahliges Optimum z*; Streichen mit Schwelle z* − LB und mit der halben Lücke;
    das Optimum über die Routen ohne gestrichene Kante. Rückgabe: Zahlen des Falls."""
    inst = S.make_instance(n, seed, breite, gruppiert=gruppiert)
    cg = M.spaltenerzeugung(inst, k)
    lb, dual = cg["schranke"], cg["dual"]
    F = A.vorwaerts_labeling(inst, dual, k)
    B = A.rueckwaerts_labeling(inst, dual, k)
    P, _ = A.kantenwerte(inst, dual, F, B)
    alle, vollstaendig = A.routen_aufzaehlen(inst, dual)
    routen = [r for r, _rc in alle]
    zstar, _w, opt = M.partition_ganzzahlig(inst, routen)
    luecke = zstar - lb
    zeile = {"n": n, "breite": breite, "typ": "gruppiert" if gruppiert else "zufall", "seed": seed, "k": k, "lb": lb, "zstar": zstar, "zstar_optimal": bool(opt and vollstaendig), "luecke": luecke,
             "routen": len(routen)}
    for name, schwelle in (("exakt", luecke), ("halb", 0.5 * luecke)):
        weg = A.gestrichene_kanten(P, schwelle)
        behalten = [r for r in routen if A.route_ohne(r, weg)]
        z_rest, _w2, _o2 = M.partition_ganzzahlig(inst, behalten)
        verletzt = sum(1 for r, rc in alle if rc <= schwelle + C.TOL_SCHWELLE and not A.route_ohne(r, weg))
        zeile[name] = {"entfernt": len(weg), "optimum_verloren": bool(z_rest is None or z_rest > zstar + 1e-6), "routen_mit_rc_unter_schwelle_an_gestrichener_kante": verletzt}
    wahr = {}
    for r, rc in alle:
        for e in A.route_kanten(r):
            wahr[e] = min(rc, wahr.get(e, math.inf))
    zeile["kanten_mit_route"] = len(wahr)
    zeile["wert_ueber_wahrem_wert"] = sum(1 for e, w in wahr.items() if P[e[0]][e[1]] > w + C.TOL_SCHWELLE)
    zeile["wert_unter_wahrem_wert"] = sum(1 for e, w in wahr.items() if P[e[0]][e[1]] < w - C.TOL_SCHWELLE)
    zeile["endlich_ohne_route"] = sum(1 for (i, j) in A.kanten_mit_route(P) if (i, j) not in wahr)
    return zeile


def rechne_gegenprobe(seeds_je_zelle: int = 12) -> dict:
    """n = 7, 8, 9, 10, Fensterbreite 40 und 100, zufällig und gruppiert, je `seeds_je_zelle` Instanzen, je Instanz k = n (elementar) und k = 5."""
    faelle = []
    for n in (7, 8, 9, 10):
        for breite in (40, 100):
            for gruppiert in (False, True):
                for s in range(seeds_je_zelle):
                    for k in (n, 5):
                        faelle.append(gegenprobe_fall(n, breite, gruppiert, SEED0 + s + 10 * n, k))
        print("n =", n, "fertig", flush=True)
    mit_luecke = [f for f in faelle if f["luecke"] > 1e-6]
    return {
        "beschreibung": "Zählung der Gegenprobe: Streichen mit der exakten Lücke z* − LB und mit der halben Lücke; z* über ALLE zulässigen elementaren Routen (Tiefensuche) ganzzahlig gelöst.",
        "quelle": "neu gerechnet mit dem Kern dieser Demo (tools/baender_erzeugen.py gegenprobe); die Messung vor dem Bau (out_v14_orakel.txt) zählte 384 Fälle, davon 81 mit verlorenem Optimum bei halber Lücke",
        "erzeugt_mit": meta(), "faelle": faelle,
        "zusammenfassung": {
            "faelle": len(faelle), "mit_ng_gleich_n": sum(1 for f in faelle if f["k"] == f["n"]), "mit_luecke": len(mit_luecke),
            "optimum_verloren_exakt": sum(1 for f in faelle if f["exakt"]["optimum_verloren"]), "optimum_verloren_halb": sum(1 for f in faelle if f["halb"]["optimum_verloren"]),
            "streichung_verletzt_routen_exakt": sum(f["exakt"]["routen_mit_rc_unter_schwelle_an_gestrichener_kante"] for f in faelle),
            "wert_ueber_wahrem_wert": sum(f["wert_ueber_wahrem_wert"] for f in faelle), "wert_unter_wahrem_wert_bei_k_kleiner_n": sum(f["wert_unter_wahrem_wert"] for f in faelle if f["k"] < f["n"]),
            "wert_unter_wahrem_wert_bei_k_gleich_n": sum(f["wert_unter_wahrem_wert"] for f in faelle if f["k"] == f["n"]),
            "kanten_mit_route_bei_k_kleiner_n": sum(f["kanten_mit_route"] for f in faelle if f["k"] < f["n"]),
            "endlich_ohne_route": sum(f["endlich_ohne_route"] for f in faelle), "zstar_nicht_bewiesen": sum(1 for f in faelle if not f["zstar_optimal"]),
        },
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("modus", choices=["n30", "zelle", "zusammen", "gegenprobe"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--out", default=None, help="Zieldatei (Standard: data/baender_kanten.json bzw. data/gegenprobe_zaehlung.json)")
    ap.add_argument("--vormessung", default=str(ROOT.parent / "label-setting-planung" / "vormessung"))
    a = ap.parse_args()
    vor = Path(a.vormessung)
    if a.modus == "n30":
        zellen = [rechne_zelle(z, vor) for z in ZELLEN if z.endswith("_n30")]
        schreibe_zellen(zellen, Path(a.out) if a.out else ROOT / "data" / C.BAND_FILE)
    elif a.modus == "zelle":
        zellen = [rechne_zelle(z, vor) for z in a.args]
        schreibe_zellen(zellen, Path(a.out) if a.out else ROOT / "data" / C.BAND_FILE)
    elif a.modus == "zusammen":
        zellen = []
        for f in a.args:
            zellen += json.loads(Path(f).read_text(encoding="utf-8"))["zellen"]
        schreibe_zellen(zellen, Path(a.out) if a.out else ROOT / "data" / C.BAND_FILE)
    else:
        daten = rechne_gegenprobe()
        ziel = Path(a.out) if a.out else ROOT / "data" / C.ORAKEL_FILE
        ziel.write_text(json.dumps(_json_sicher(daten), ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps(daten["zusammenfassung"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
