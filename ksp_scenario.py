"""Szenario: Instanzen im Stil von Solomon (eigener Generator, nicht die Originalinstanzen) und das Handbeispiel mit sechs Kunden.

Alle Instanzen sind unveränderlich (Tupel). Zufall kommt nur über einen `random.Random`, der aus dem Zufalls-Seed gebildet wird;
das ist derselbe Generator in derselben Reihenfolge der Ziehungen wie in der Messung vor dem Bau, damit die festen Messreihen in data/ nachrechenbar bleiben
(Abschnitt „Abweichungen“ der README: nicht SplitMix64)."""

import math
import random
from dataclasses import dataclass

import ksp_constants as C


@dataclass(frozen=True)
class Instanz:
    """Depot = Knoten 0, Kunden 1..n. Zeit und Entfernung sind gleich; `last` ist die Nachfrage (Index 0 = Depot = 0)."""

    n: int
    punkte: tuple          # ((x, y), ...) mit dem Depot zuerst
    dist: tuple            # Entfernungsmatrix (n + 1) x (n + 1), zugleich Fahrzeit und Kosten
    last: tuple
    frueh: tuple           # früheste Bedienung je Kunde (Fensteranfang)
    spaet: tuple           # späteste Ankunft je Kunde (Fensterende); beim Depot der Horizont
    horizont: float
    bedienzeit: float
    kapazitaet: int
    breite: float = 0.0


def _matrix(punkte, metrik):
    return tuple(tuple(metrik(a, b) for b in punkte) for a in punkte)


def make_instance(n: int, seed: int, breite: float, gruppiert: bool = False, horizont: float = C.HORIZONT, kapazitaet: int = C.KAPAZITAET) -> Instanz:
    """Solomon-artige Instanz: Depot (50, 50), n Kunden im Quadrat 100 x 100, Nachfrage 5 bis 25, Zeitfenster der Breite `breite`.

    Der Fenstermittelpunkt wird gleichverteilt zwischen frühestmöglicher und spätestmöglicher Ankunft gezogen und die Breite darum gelegt
    (an Anfang und Ende auf die erreichbaren Zeiten begrenzt). `gruppiert`: fünf Zentren, Kunden normalverteilt (Streuung 6) um ein Zentrum."""
    rng = random.Random(seed)
    if gruppiert:
        zentren = [(rng.uniform(15, 85), rng.uniform(15, 85)) for _ in range(5)]
        kunden = []
        for _ in range(n):
            cx, cy = rng.choice(zentren)
            kunden.append((min(100.0, max(0.0, rng.gauss(cx, 6))), min(100.0, max(0.0, rng.gauss(cy, 6)))))
    else:
        kunden = [(rng.uniform(0, 100), rng.uniform(0, 100)) for _ in range(n)]
    punkte = tuple([(50.0, 50.0)] + kunden)
    dist = _matrix(punkte, math.dist)
    last = tuple([0] + [rng.randint(C.LAST_MIN, C.LAST_MAX) for _ in range(n)])
    frueh = [0.0] * (n + 1)
    spaet = [horizont] * (n + 1)
    for i in range(1, n + 1):
        lo = dist[0][i]
        hi = horizont - C.BEDIENZEIT - dist[0][i]
        mitte = rng.uniform(lo, hi)
        frueh[i] = max(lo, mitte - breite / 2)
        spaet[i] = min(hi, mitte + breite / 2)
    return Instanz(n, punkte, dist, last, tuple(frueh), tuple(spaet), horizont, C.BEDIENZEIT, kapazitaet, float(breite))


# ---------------------------------------------------------------------------------------------------------------------------------
# Handbeispiel: Depot (5, 5) und sechs Kunden, Manhattan-Abstand, Fahrzeit = Entfernung = Kosten (zum Nachrechnen mit dem Stift; ganze Zahlen)
# ---------------------------------------------------------------------------------------------------------------------------------
HAND_PUNKTE = ((5, 5), (1, 4), (3, 1), (1, 0), (10, 0), (2, 0), (7, 5))
HAND_LAST = (0, 2, 3, 2, 4, 2, 3)
HAND_FRUEH = (0, 5, 21, 10, 16, 21, 9)
HAND_SPAET = (40, 21, 32, 22, 28, 30, 25)
HAND_BEDIENZEIT, HAND_HORIZONT, HAND_KAPAZITAET = 2, 40, 8


def handbeispiel() -> Instanz:
    """Das Handbeispiel als Instanz (ganze Zahlen); Zeitfenster in `frueh` und `spaet`, der Horizont steht als Fensterende des Depots."""
    dist = _matrix(HAND_PUNKTE, lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1]))
    return Instanz(6, HAND_PUNKTE, dist, HAND_LAST, HAND_FRUEH, HAND_SPAET, HAND_HORIZONT, HAND_BEDIENZEIT, HAND_KAPAZITAET, 0.0)
