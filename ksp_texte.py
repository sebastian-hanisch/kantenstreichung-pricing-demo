"""Texte der App, die auch in der README stehen (ein Test vergleicht sie): Annahmen, Grenzen, bekannte Probleme, die Tabelle „Wo die Annahmen enden“ und die Mathematik.

Zahlen kommen aus den festen Messreihen (`ksp_baender`) und der Zählung der Gegenprobe, nie aus dem Kopf."""

import ksp_baender as B
import ksp_constants as C
from ksp_evaluation import NBSP, fmt_dec, fmt_int

LITERATUR = ("Irnich, S., Desaulniers, G., Desrosiers, J., Hadjar, A.: Path-Reduced Costs for Eliminating Arcs in Routing and Scheduling. INFORMS Journal on Computing 22(2), 2010, S. 297–313 "
             "(Titel und Fundstelle in Katalogeinträgen geprüft, Zusammenfassung gelesen, Volltext nicht gelesen; ihr bidirektionaler Algorithmus ist hier nicht nachgebaut).")


def _zahlen() -> dict:
    """Die Zahlen der Texte aus den Messreihen und der Gegenprobe."""
    z30 = B.zellen(30)
    ue = [B.zellen_uebersicht(z) for z in z30]
    s3, s1 = B.bereich(30, "ub3"), B.bereich(30, "ub1")
    z50 = {z["typ"]: B.zellen_uebersicht(z) for z in B.zellen(50)}
    g = B.gegenprobe()
    return dict(zellen=len(z30), instanzen=sum(u["instanzen"] for u in ue), fertig=sum(u["fertig"] for u in ue), abgebrochen=sum(u["abgebrochen"] for u in ue),
                exakt=sum(u["ub3_exakt"] for u in ue), s3=s3, s1=s1, z50=z50, g=g, vergleich=B.vergleich_mit_vormessung(), kanten_gesamt=ue[0]["kanten_gesamt"])


def _pct(x, stellen=0) -> str:
    return fmt_dec(100 * x, stellen)


def annahmen_tabelle() -> str:
    """Die Tabelle „🚧 Wo die Annahmen enden“."""
    z = _zahlen()
    s1, s3 = z["s1"], z["s3"]
    g = z["g"]
    z50g, z50z = z["z50"]["gruppiert"], z["z50"]["zufall"]
    return f"""| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Es gibt eine obere Schranke, und sie ist gut.** | Mit der Lücke aus den Spalten allein (obere Schranke 1) werden bei n = 30 im Mittel {_pct(s1['mittel_min'])} bis {_pct(s1['mittel_max'])}{NBSP}% der Kanten mit zulässiger Route gestrichen, mit dem exakten Optimum {_pct(s3['mittel_min'])} bis {_pct(s3['mittel_max'])}{NBSP}% ({C.VORBEHALT}). | Die Verfahren, die eine gute ganzzahlige Lösung liefern (Verzweigen, Heuristiken), sind nicht Gegenstand dieser Demo. |
| **Die Schwelle ist mindestens die echte Lücke.** | Eine zu kleine Schwelle streicht Kanten der optimalen Lösung: In der Zählung ging das Optimum bei der halben Lücke in {g['optimum_verloren_halb']} von {g['mit_luecke']} Fällen mit Lücke größer null verloren, bei der exakten Lücke in {g['optimum_verloren_exakt']} von {g['faelle']} Fällen. Eine angenommene Lücke (x{NBSP}% von LB) hat keine Garantie. | Nur eine echte obere Schranke gibt die Garantie. |
| **Die Dualpreise sind die der Konvergenz.** | Gemessen ist nur dieser Zeitpunkt: dort gibt es keine verbessernde Route mehr, das Pricing wäre in einer Spaltenerzeugung nicht mehr nötig. Der Nutzen in späteren Pricing-Aufrufen (nach Verzweigen oder Schnitten) und die nötige Neuberechnung der Kantenwerte bei geänderten Dualpreisen sind nicht gemessen. | Spätere Pricing-Aufrufe sind nicht gemessen. |
| **Das ng-Gedächtnis ist k = n (elementar).** | Bei k < n liegen die Pfad-reduzierten Kosten bei {g['wert_unter_wahrem_wert_bei_k_kleiner_n']} von {fmt_int(g['kanten_mit_route_bei_k_kleiner_n'])} Kanten mit Route (k = 5, n = 7 bis 10) unter dem wahren Wert der elementaren Routen: die Streichung bleibt gültig, streicht aber weniger. Die Lücke ist die zur ng-Schranke (k = 8), nicht zur elementaren. | Das Gedächtnis selbst behandelt die Demo zu ng-Routen. |
| **Das exakte Optimum ist erreichbar.** | Es braucht die Aufzählung aller Routen mit kleinen reduzierten Kosten und eine ganzzahlige Partitionierung: bei n = 30 in {z['exakt']} von {z['instanzen']} Instanzen bewiesen, bei n = 50 gruppiert nur in {z50g['ub3_exakt']} von {z50g['instanzen']}, zufällig in {z50z['ub3_exakt']} von {z50z['instanzen']}. | Größere Instanzen: nur die Schranken aus den Spalten (Stufen 1 und 2). |
| **Metrische Kosten, Partitionierungs-Master.** | Die Rechnung „Kosten einer Lösung = LB + Summe der reduzierten Kosten“ gilt für den Partitionierungs-Master. Für einen Überdeckungs-Master ist die Regel hier nicht nachgerechnet. | – |"""


def assumptions_markdown() -> str:
    """Annahmen, Grenzen und bekannte Probleme (Expander der App und README, gleicher Wortlaut)."""
    z = _zahlen()
    z50g, z50z = z["z50"]["gruppiert"], z["z50"]["zufall"]
    v = z["vergleich"]
    return f"""**Annahmen**

- Die Instanzen sind eigene, Solomon-artige Instanzen (nicht die Originalinstanzen von Solomon): Quadrat 100 × 100, Depot in der Mitte, Zeit = Entfernung = Kosten (euklidisch, also metrisch), Bedienzeit 10, Horizont 300, Kapazität 70, Nachfrage 5 bis 25, Zeitfenster der Breite 20 bis 100, zufällig verteilt oder in fünf Gruppen. Das Handbeispiel hat sechs Kunden, Manhattan-Abstände, Bedienzeit 2, Kapazität 8, Horizont 40 und ganze Zahlen.
- Der Master ist ein Partitionierungs-Master (jeder Kunde genau einmal). Gerechnet wird mit HiGHS, im Handbeispiel exakt mit Brüchen. Das Pricing ist ein Vorwärts-Labeling mit ng-Gedächtnis (Voreinstellung k = 8; ab k = n elementar). Die Spaltenerzeugung läuft bis zur Konvergenz; ihr Wert ist die untere Schranke LB, ihre Dualpreise sind die der Konvergenz.
- Eine Kante wird gestrichen, wenn ihre Pfad-reduzierten Kosten (die kleinsten reduzierten Kosten einer zulässigen Route über die Kante) größer sind als die Schwelle. Garantiert ist das nur, wenn die Schwelle mindestens UB − LB beträgt, mit einer echten oberen Schranke UB, also dem Wert einer gefundenen ganzzahligen Lösung. „Angenommen x{NBSP}% von LB“ ist keine echte Schranke.
- Die drei oberen Schranken sind: 1 der beste ganzzahlige Wert aus den Spalten der Spaltenerzeugung, 2 dazu die beste Route je Kante, 3 dazu die Aufzählung aller elementaren Routen mit reduzierten Kosten höchstens UB2 − LB. Nur wenn die Aufzählung vollständig und die Partitionierung bewiesen optimal ist, ist Schranke 3 das exakte ganzzahlige Optimum.
- Gezählt werden Kanten und erzeugte Labels; Sekunden zeigt die App nicht.

**Grenzen**

- Die Wirkung ist {C.VORBEHALT}. Bei den Dualpreisen der Konvergenz gibt es keine verbessernde Route mehr; bei geänderten Dualpreisen müssten die Kantenwerte neu berechnet werden (nicht gemessen).
- Die feste Messreihe zu n = 30 hat {z['zellen']} Zellen (zufällig und gruppiert, Fensterbreite 40 und 100) mit je 12 Instanzen, zusammen {z['instanzen']}; die Spannen über die Instanzen sind groß, Mittelwerte gelten nicht für Einzelinstanzen. Die Reihe zu n = 50 (nur Breite 100) hat {z50z['instanzen']} zufällige und {z50g['instanzen']} gruppierte Instanzen, davon mit bewiesenem Optimum {z50z['ub3_exakt']} und {z50g['ub3_exakt']}.
- „Exaktes Optimum“ heißt: ganzzahliges Optimum der Partitionierung über alle elementaren Routen mit reduzierten Kosten höchstens UB2 − LB, nur bei vollständiger Aufzählung und bewiesen optimaler Partitionierung gezählt. Eine echte Verzweigungsrechnung hätte zu dem Zeitpunkt nur eine heuristische obere Schranke; wie viel dort gestrichen würde, ist nicht gemessen.
- Die Lücke ist die zur ng-Schranke bei k = 8 im Wurzelknoten, nicht zur LP-Schranke der elementaren Routen. Die Kosten sind metrisch, der Master ein Partitionierungs-Master.
- Das Verbinden nicht dominierter Vorwärts- und Rückwärtslabels mit disjunkten Gedächtnissen ist eine eigene, einfache Umsetzung und nicht der bidirektionale Algorithmus der Literatur.
- Die Live-Rechnung ist auf 12 Kunden begrenzt, weil sie alle zulässigen Routen aufzählt; größere Fälle stehen nur als feste Messreihen da.

**Bekannte Probleme und Unsicherheiten**

- Die Instanzen entstehen mit dem Zufallsgenerator von Python (`random.Random`), damit sie mit den festen Messreihen übereinstimmen; die Tests rechnen Stichproben der Messreihen nach.
- Die festen Messreihen sind mit dem Kern dieser Demo neu gerechnet (Python 3.14, SciPy 1.18.1, Windows) und mit den Rohdateien der Messung vor dem Bau verglichen: {fmt_int(v['verglichen'])} Werte verglichen, {v['abweichend']} Abweichungen. Die Zahl gestrichener Kanten und Labels hängt von den Dualpreisen ab; bei mehreren gleich guten Master-Lösungen kann HiGHS auf einem anderen Rechner andere Dualpreise liefern, die Schranken nicht.
- Bei n = 50 hängt es von den Zeitgrenzen ab (60 Sekunden je Partitionierung), ob das Optimum bewiesen wird; auf einem anderen Rechner kann das anders ausgehen.
- Erklärungen mit „weil“ sind Deutungen, soweit nicht ausdrücklich gemessen.
- Die Diagramme haben keine Auswahlfunktion; ein Mausklick auf sie bewirkt nichts."""


MATH_LESEHILFE = r"""
**Gegeben:** ein Netz mit Depot und Kunden, Fahrzeiten und Kosten $d_{ij}$, Zeitfenster, Lasten, und die Spaltenerzeugung am Ende (bei Konvergenz): eine untere Schranke $LB$ und Dualpreise $\pi_i$.
**Gesucht:** die Kanten $(i,j)$, die in keiner ganzzahligen Lösung mit Wert höchstens $UB$ vorkommen können, damit das Pricing sie nicht mehr betrachten muss.

| Symbol | Bedeutung |
|---|---|
| $r$ | eine zulässige Route (Kunden in Besuchsfolge, vom Depot zum Depot) |
| $c_r$ | Kosten (Länge) der Route $r$ |
| $a_{ir}$ | 1, wenn die Route Kunde $i$ besucht, sonst 0 |
| $x_r$ | Menge der Route $r$ in der Lösung |
| $\pi_i$ | Dualpreis von Kunde $i$ (aus dem Master der Konvergenz) |
| $LB$ | Wert des Masters der Konvergenz, untere Schranke |
| $\mathrm{rc}_r$ | reduzierte Kosten der Route $r$ |
| $UB$ | Wert irgendeiner ganzzahligen Lösung, obere Schranke |
| $\Delta$ | die Lücke $UB - LB$ |
| $\tilde c_{ij}$ | Pfad-reduzierte Kosten der Kante $(i,j)$ |
"""

MATH_FORMELN = r"""
**Master (Partitionierung) und Dualpreise.** Der Master wählt Mengen $x_r$, so dass jeder Kunde genau einmal bedient wird:

$$\min \sum_r c_r x_r \quad \text{mit} \quad \sum_r a_{ir} x_r = 1 \;\; \text{für jeden Kunden } i, \qquad x_r \ge 0 .$$

Sein Wert ist $LB = \sum_i \pi_i$. Die **reduzierten Kosten** einer Route sind

$$\mathrm{rc}_r = c_r - \sum_i a_{ir}\,\pi_i .$$

Bei Konvergenz gilt $\mathrm{rc}_r \ge 0$ für jede Route des Pricings (Dualzulässigkeit).

**Warum man streichen darf.** Für jede ganzzahlige Partitionierung $x$ gilt, weil jeder Kunde genau einmal vorkommt ($\sum_r a_{ir} x_r = 1$):

$$\sum_r c_r x_r = \sum_r \mathrm{rc}_r\, x_r + \sum_i \pi_i \sum_r a_{ir} x_r = LB + \sum_r \mathrm{rc}_r\, x_r .$$

Soll der Wert höchstens $UB$ sein, so ist $\sum_r \mathrm{rc}_r x_r \le UB - LB = \Delta$. Wegen $\mathrm{rc}_r \ge 0$ hat dann **jede** Route der Lösung reduzierte Kosten höchstens $\Delta$.

**Pfad-reduzierte Kosten.** Für eine Kante $(i,j)$ sei

$$\tilde c_{ij} = \min \{ \mathrm{rc}_r : r \text{ zulässige Route, die die Kante } (i,j) \text{ benutzt} \} .$$

Berechnet wird sie aus den Labels: das Minimum über alle verträglichen Paare aus einem Vorwärtslabel in $i$ und einem Rückwärtslabel in $j$ von

$$c_F + d_{ij} - \pi_j + c_B .$$

Verträglich heißt: die Zeit reicht, die Lasten passen zusammen in die Kapazität, und die Gedächtnisse haben keinen gemeinsamen Kunden.

**Streichregel.** Eine Kante fällt weg, wenn $\tilde c_{ij} > \Delta$. Jede Route einer Lösung mit Wert höchstens $UB$ benutzt nur Kanten mit $\tilde c_{ij} \le \mathrm{rc}_r \le \Delta$, bleibt also erhalten; das ganzzahlige Optimum ändert sich nicht. Bei einer Schwelle unter $\Delta$ gilt das nicht (Experiment 5).

**Literatur.** """ + LITERATUR + "\n"
