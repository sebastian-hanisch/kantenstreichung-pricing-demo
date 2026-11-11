"""Feste Messreihen (data/*.json): Zellen auswählen und Kennzahlen bilden (Mittel, Minimum, Maximum, Median, Zahl fertiger und abgebrochener Läufe).

Nichts hier rechnet das Label-Setting neu. Die Rohwerte je Instanz stehen in `data/baender_kanten.json`; `tools/baender_erzeugen.py` hat sie mit dem Kern dieser Demo gerechnet und
mit den Rohdateien der Messung vor dem Bau verglichen (je Zelle `vergleich`). Gerechnet wird hier nur über die Instanzen einer Zelle.
Abgebrochene Läufe (`fertig` = False) zählen in keine Kennzahl; für die Schwelle „exakte Lücke“ zählen nur Instanzen mit bewiesenem Optimum (`ub3_exakt`)."""

import json
from functools import lru_cache
from pathlib import Path
from statistics import mean, median

import ksp_constants as C

DATA = Path(__file__).resolve().parent / "data"
TYPEN = {"zufall": "zufällig", "gruppiert": "gruppiert"}


@lru_cache(maxsize=None)
def _lade(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def zellen(n: int | None = None) -> list:
    """Alle Zellen der Datei (optional nur die mit n Kunden), Reihenfolge der Datei."""
    return [z for z in _lade(C.BAND_FILE)["zellen"] if n is None or z["n"] == n]


def zelle(zid: str) -> dict:
    return next(z for z in zellen() if z["id"] == zid)


def fertige(z: dict) -> list:
    return [r for r in z["zeilen"] if r["fertig"]]


def zeilen_fuer(z: dict, schwelle: str) -> list:
    """Instanzen, die für die Schwelle zählen: fertige; bei der exakten Lücke („ub3“) nur die mit bewiesenem Optimum."""
    ok = fertige(z)
    return [r for r in ok if r["ub3_exakt"]] if schwelle == "ub3" else ok


def luecke(r: dict, stufe: str) -> float:
    """Lücke (UB − LB) / LB einer Instanz für „ub1“, „ub2“ oder „ub3“ als Anteil."""
    return (r[stufe] - r["lb"]) / r["lb"]


def streichanteile(z: dict, schwelle: str) -> list:
    """Anteil der Kanten mit zulässiger Route, die bei der Schwelle gestrichen werden, je Instanz."""
    return [r["wirkung"][schwelle]["entfernt"] / r["kanten_mit_route"] for r in zeilen_fuer(z, schwelle)]


def label_verhaeltnisse(z: dict, schwelle: str) -> list:
    """Erzeugte Vorwärtslabels im gestrichenen Graphen geteilt durch die im vollen Graphen (bei denselben Dualpreisen), je Instanz."""
    return [r["wirkung"][schwelle]["labels"] / r["labels_vorwaerts"] for r in zeilen_fuer(z, schwelle)]


def kennzahlen(xs: list) -> dict:
    """Mittel, Minimum, Maximum, Median und Zahl der Werte; bei leerer Liste lauter None."""
    if not xs:
        return {"mittel": None, "min": None, "max": None, "median": None, "zahl": 0}
    return {"mittel": mean(xs), "min": min(xs), "max": max(xs), "median": median(xs), "zahl": len(xs)}


def zellen_uebersicht(z: dict) -> dict:
    """Aufbau einer Zelle: Instanzen, fertige und abgebrochene Läufe, Zahl bewiesener Optima, vollständiger Aufzählungen, Median der Kanten und der vollen Labels, Lücken der drei Stufen."""
    ok = fertige(z)
    return {
        "id": z["id"], "typ": z["typ"], "breite": z["breite"], "n": z["n"], "k": z["k"], "instanzen": len(z["zeilen"]), "fertig": len(ok), "abgebrochen": len(z["zeilen"]) - len(ok),
        "ub3_exakt": sum(1 for r in ok if r["ub3_exakt"]), "aufzaehlung_vollstaendig": sum(1 for r in ok if r["aufzaehlung_vollstaendig"]),
        "kanten_gesamt": ok[0]["kanten_gesamt"] if ok else None, "kanten_statisch_median": median(r["kanten_statisch"] for r in ok) if ok else None,
        "kanten_mit_route_median": median(r["kanten_mit_route"] for r in ok) if ok else None, "labels_voll_median": median(r["labels_vorwaerts"] for r in ok) if ok else None,
        "luecke": {s: kennzahlen([luecke(r, s) for r in zeilen_fuer(z, s)]) for s in ("ub1", "ub2", "ub3")},
    }


def streichtabelle(z: dict) -> dict:
    """Je Schwelle der Messreihe: Streichanteile und Label-Verhältnisse (Kennzahlen) der Zelle."""
    return {s: {"streichen": kennzahlen(streichanteile(z, s)), "labels": kennzahlen(label_verhaeltnisse(z, s))} for s in C.BAND_SCHWELLEN}


def gitterkurve(z: dict) -> list:
    """Mittel über die fertigen Instanzen: Anteil der Kanten mit zulässiger Route, deren Pfad-reduzierte Kosten höchstens x · LB betragen, für x in BAND_GRID."""
    ok = fertige(z)
    return [mean(r["gitter"][str(g)] / r["kanten_mit_route"] for r in ok) for g in C.BAND_GRID]


def bereich(n: int, schwelle: str, groesse: str = "streichen") -> dict:
    """Über die Zellen mit n Kunden: kleinster und größter Zellenmittelwert sowie kleinster und größter Einzelwert; `groesse` ist „streichen“ oder „labels“."""
    zs = zellen(n)
    tab = [streichtabelle(z)[schwelle][groesse] for z in zs]
    return {"mittel_min": min(t["mittel"] for t in tab), "mittel_max": max(t["mittel"] for t in tab), "einzel_min": min(t["min"] for t in tab), "einzel_max": max(t["max"] for t in tab),
            "instanzen": sum(t["zahl"] for t in tab), "zellen": len(zs)}


def luecke_bereich(n: int, stufe: str) -> dict:
    """Mittlere Lücke (Anteil) je Zelle: kleinster und größter Zellenmittelwert; größter Einzelwert."""
    tab = [zellen_uebersicht(z)["luecke"][stufe] for z in zellen(n)]
    return {"mittel_min": min(t["mittel"] for t in tab), "mittel_max": max(t["mittel"] for t in tab), "einzel_max": max(t["max"] for t in tab)}


def kanten_median_bereich(n: int) -> tuple:
    """Kleinster und größter Median der Kanten mit zulässiger Route über die Zellen."""
    xs = [zellen_uebersicht(z)["kanten_mit_route_median"] for z in zellen(n)]
    return min(xs), max(xs)


def vergleich_mit_vormessung() -> dict:
    """Summe über alle Zellen: Zahl der Werte, die mit der Rohdatei der Messung vor dem Bau verglichen wurden, und Zahl der abweichenden."""
    return {"verglichen": sum(z["vergleich"]["verglichen"] for z in zellen()), "abweichend": sum(z["vergleich"]["abweichend"] for z in zellen())}


def vormessung_hinweise() -> list:
    """Die aufgelisteten Abweichungen der Zellen (leer, wenn es keine gibt)."""
    return [f"{z['id']}: {t}" for z in zellen() for t in z["vergleich"]["abweichungen"]]


# ---------------------------------------------------------------------------------------------------------------------------------
# Zählung der Gegenprobe
# ---------------------------------------------------------------------------------------------------------------------------------

def gegenprobe() -> dict:
    """Zusammenfassung der Zählung der Gegenprobe (data/gegenprobe_zaehlung.json)."""
    return _lade(C.ORAKEL_FILE)["zusammenfassung"]


def gegenprobe_faelle() -> list:
    return _lade(C.ORAKEL_FILE)["faelle"]
