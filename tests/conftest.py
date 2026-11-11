"""Gemeinsame Fixtures: die Mini-Instanz, an der jede Einheit von Hand geprüft wird (DEMO-PLAYBOOK §1b), und ein unabhängiger Rechenweg für die Orakel.

Die Mini-Instanz ist das **Handbeispiel**: Depot (5, 5), sechs Kunden, Manhattan-Abstand, Bedienzeit 2, Horizont 40, Kapazität 8. Die Erwartungswerte der Tests stammen aus einer
Handrechnung in einem eigenen Skript der Planung (nur Standardbibliothek, Aufzählung aller 45 zulässigen Routen, Master-LP exakt mit Brüchen); im Test stehen sie als Rechnung.

Der unabhängige Rechenweg (`unabhaengige_routen`, `unabhaengige_partition`) benutzt nichts aus `ksp_algorithm` und `ksp_master`: eine eigene Tiefensuche mit Stapel, eine eigene
Zulässigkeitsprüfung durch Nachfahren der Route, eine eigene Zerlegung durch Rekursion über den kleinsten offenen Kunden."""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ksp_scenario as S  # noqa: E402

# Handbeispiel: Kunde -> (Lage, Fenster, Bedarf)
HAND_KUNDEN = {1: ((1, 4), (5, 21), 2), 2: ((3, 1), (21, 32), 3), 3: ((1, 0), (10, 22), 2), 4: ((10, 0), (16, 28), 4), 5: ((2, 0), (21, 30), 2), 6: ((7, 5), (9, 25), 3)}
HAND_DEPOT = (5, 5)
HAND_DUAL = {1: 6, 2: 6, 3: 6, 4: 16, 5: 6, 6: 4}      # Dualpreise der Konvergenz (Master-LP über alle 45 Routen), Summe 44 = LB
HAND_LB, HAND_ZSTAR = 44, 46


@pytest.fixture
def hand():
    """Das Handbeispiel als Instanz."""
    return S.handbeispiel()


@pytest.fixture
def hand_dual():
    """Dualpreise der Konvergenz im Handbeispiel (Position 0 = Depot = 0)."""
    return [0] + [HAND_DUAL[i] for i in range(1, 7)]


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def unabhaengige_routen(n, ort, dist, frueh, spaet, last, kap, horizont, bedienzeit):
    """Alle zulässigen elementaren Routen durch Tiefensuche mit Stapel; unabhängig vom Kern. `ort[0]` ist das Depot; `dist(i, j)` die Entfernung. Rückgabe: Liste von Tupeln."""
    routen = []
    stapel = [((), 0, 0.0, 0)]            # (Route, letzter Knoten, Zeit der Bedienung dort, Last)
    while stapel:
        route, i, zeit, ladung = stapel.pop()
        if route and zeit + bedienzeit + dist(i, 0) <= horizont + 1e-9:
            routen.append(route)
        for j in range(1, n + 1):
            if j in route or ladung + last[j] > kap:
                continue
            ankunft = zeit + (bedienzeit if i != 0 else 0.0) + dist(i, j)
            if ankunft > spaet[j] + 1e-9:
                continue
            stapel.append((route + (j,), j, max(ankunft, frueh[j]), ladung + last[j]))
    return routen


def unabhaengige_partition(n, kosten):
    """Kleinste Kosten einer Zerlegung aller Kunden in Routen aus `kosten` ({Route: Kosten}) durch Rekursion über den kleinsten offenen Kunden; (Wert oder None, Routen)."""
    nach_erstem = {}
    for r, c in kosten.items():
        nach_erstem.setdefault(min(r), []).append((r, c, frozenset(r)))

    gemerkt = {}

    def loese(offen):
        if not offen:
            return 0.0, []
        if offen in gemerkt:
            return gemerkt[offen]
        i = min(offen)
        bester = (math.inf, None)
        for r, c, s in nach_erstem.get(i, []):
            if s <= offen:
                rest, wahl = loese(offen - s)
                if rest + c < bester[0] - 1e-12:
                    bester = (rest + c, [r] + wahl)
        gemerkt[offen] = bester
        return bester

    wert, wahl = loese(frozenset(range(1, n + 1)))
    return (None, []) if wert == math.inf else (wert, wahl)
