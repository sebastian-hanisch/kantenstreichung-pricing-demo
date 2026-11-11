# Kantenstreichung im Pricing: welche Kanten sind überflüssig? – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-kantenstreichung-pricing-demo.streamlit.app/)**

Interaktive **Konzepte-Demo** der Reihe „Ressourcenwege und Spaltenerzeugung“ im Portfolio von [Sebastian Hanisch](https://sebastianhanisch.net) (Operations Research und Machine Learning).
Die **Spaltenerzeugung** (zum Beispiel bei der Tourenplanung) endet mit einer **unteren Schranke LB** (dem Wert des Masters) und **Dualpreisen**, je einem Preis pro Kunde; die **reduzierten Kosten** einer Route sind ihre Länge minus die Preise ihrer Kunden.
Kennt man dazu irgendeine **obere Schranke UB** (den Wert einer gefundenen ganzzahligen Lösung), lässt sich für jede **Kante** des Netzes sagen, ob sie in einer besseren Lösung noch vorkommen kann: Ist die beste Route durch die Kante (ihre **Pfad-reduzierten Kosten**) schlechter als die **Lücke** UB − LB,
kann man die Kante streichen, ohne das ganzzahlige Optimum zu verlieren. Diese Demo zeigt, **wie viele Kanten dabei wegfallen, wie viel weniger Labels das Pricing danach erzeugt und was bei einer zu kleinen Schwelle geschieht**.

Die Grundlagen stehen in den Nachbardemos der Reihe: [weg-mit-grenzen-demo](https://github.com/sebastian-hanisch/weg-mit-grenzen-demo) (ein Weg mit Grenze), [dominanz-labels-demo](https://github.com/sebastian-hanisch/dominanz-labels-demo) (die Dominanzregel),
[zeitfenster-labeling-demo](https://github.com/sebastian-hanisch/zeitfenster-labeling-demo) (Zeitfenster und Warten), [mehrere-grenzen-demo](https://github.com/sebastian-hanisch/mehrere-grenzen-demo) (mehrere Grenzen) und
[pricing-dualpreise-demo](https://github.com/sebastian-hanisch/pricing-dualpreise-demo) (das Pricing aus Dualpreisen, der Master und die Schleife); hier sind sie vorausgesetzt. Das Gedächtnis der Labels behandeln [elementar-pricing-demo](https://github.com/sebastian-hanisch/elementar-pricing-demo),
[kreise-im-pricing-demo](https://github.com/sebastian-hanisch/kreise-im-pricing-demo) und [ng-routen-demo](https://github.com/sebastian-hanisch/ng-routen-demo). Rückwärtslabels, die hier zum Verbinden gebraucht werden, und Eimer verkleinern die Arbeit **innerhalb** eines Pricing-Aufrufs:
[bidirektional-labeling-demo](https://github.com/sebastian-hanisch/bidirektional-labeling-demo) und [eimer-labeling-demo](https://github.com/sebastian-hanisch/eimer-labeling-demo); hier wird dagegen der **Graph** verkleinert, für alle späteren Aufrufe.
Als Anwendung dient [crew-pairing-demo](https://github.com/sebastian-hanisch/crew-pairing-demo) (Pricing mit Labeling; ob und wie dort Kanten gestrichen werden könnten, ist hier nicht untersucht; aus der README gelesen, im Code nicht geprüft).
**Abgrenzung:** [hub-labeling-demo](https://github.com/sebastian-hanisch/hub-labeling-demo) (Kürzeste-Wege-Reihe) meint mit „Label“ etwas anderes, nämlich eine Liste von Hubs für Abstandsabfragen; hier ist ein Label ein Teilweg samt Kosten, Zeit und Last.
[mcf-column-generation-demo](https://github.com/sebastian-hanisch/mcf-column-generation-demo) hat eine untere Schranke aus den kleinsten reduzierten Kosten je Gut, streicht aber keine Kanten: ein verwandter, anderer Gedanke.

## Kernfrage

**Wenn die Spaltenerzeugung eine untere Schranke und Dualpreise geliefert hat und man irgendwie eine obere Schranke kennt: Welche Kanten des Netzes können dann in keiner besseren ganzzahligen Lösung vorkommen, und wie viel weniger Labels erzeugt das Pricing ohne sie?**
Gemessen werden **gestrichene Kanten** (in % der Kanten mit mindestens einer zulässigen Route) und **erzeugte Vorwärtslabels** im gestrichenen gegen den vollen Graphen bei denselben Dualpreisen; Sekunden zeigt die App nicht.
Alle Messungen: eigene Solomon-artige Instanzen (nicht die Originalinstanzen), Partitionierungs-Master, metrische Kosten, Python. **Alle Aussagen über die Wirkung gelten nur bei den Dualpreisen der Konvergenz der Spaltenerzeugung; der Nutzen in späteren Pricing-Aufrufen (nach Verzweigen oder Schnitten) ist nicht gemessen.**

## Befunde und Korrekturen gegenüber dem Plan

- **Alle Messreihen sind mit dem Kern dieser Demo neu gerechnet** (nicht aus der Messung vor dem Bau übernommen) und danach mit deren Rohdateien verglichen: 1 386 Werte, 9 Abweichungen (Tabellenzeile M). Die 9 Abweichungen stehen in drei Instanzen der Reihe mit n = 50 (je ein Seed zufällig, zwei gruppiert), in denen das Optimum nicht bewiesen ist (Zeitgrenze der Partitionierung von 60 Sekunden oder abgebrochene Aufzählung;
  die Ursache ist nicht eigens geprüft): dort ist die obere Schranke 3 hier ein besserer gültiger Wert als in der Messung vor dem Bau. Diese Instanzen zählen bei der „exakten Lücke“ nicht mit. Alle 48 Instanzen mit n = 30 stimmen in jedem verglichenen Wert überein (1 008 Werte).
- **Die Reihe n = 50 ist klein und beim gruppierten Typ schwach:** Das exakte Optimum ist dort nur in 3 von 8 Instanzen bewiesen (zufällig 9 von 10), weil die Aufzählung bei 3 von 8 Instanzen an ihre Obergrenze von 300 000 Routen stößt und bei 2 weiteren die Partitionierung nicht bewiesen wird (Tabellenzeile L). Die Mittel der exakten Lücke stehen deshalb dort mit der Zahl der Instanzen daneben.
- **Rückkehr zum Depot mit Toleranz:** Die Spaltenerzeugung der Messung vor dem Bau prüfte die Rückkehr ohne Toleranz, das Labeling mit Toleranz von 1e-9. Hier gilt überall dieselbe Regel (mit Toleranz); in den 1 386 verglichenen Werten ergibt sich daraus kein Unterschied. Ebenso gilt eine obere Schranke 3, die der Schranke 2 nur in der letzten Stelle überlegen ist, nicht als Zeitgrenzen-Artefakt (Toleranz 1e-6, relativ).
- **Die ganzzahlige Partitionierung läuft bis 14 Kunden durch Aufzählung über Kundenmengen** (exakt, ohne Löser; die Live-Rechnung und die Zählung der Gegenprobe), darüber mit HiGHS (die Reihen n = 30 und n = 50), weil HiGHS bei 12 Kunden mit wenigen tausend Spalten Sekunden brauchte (einmalige Messung dieser README, nicht im Test), die Aufzählung Hundertstelsekunden. Beide Wege sind gegeneinander getestet.
- **Die Live-Rechnung ist auf 12 Kunden und Fensterbreiten bis 100 begrenzt** (der Plan nannte n bis 12; die Breite 200 entfällt, weil dort bis zu rund 60 000 zulässige Routen aufzuzählen sind und die Rechnung mehrere Sekunden dauert). Größere Fälle stehen als feste Messreihen da.
- **Instanzen mit dem Zufallsgenerator von Python (`random.Random`) statt SplitMix64:** Die festen Messreihen stammen aus Instanzen, die `random.Random` erzeugt; damit sie nachrechenbar bleiben, benutzt die Demo denselben Generator in derselben Reihenfolge der Ziehungen.
- **Der Vorbehalt steht im selben Satz wie die Zahl:** Jeder Satz der App und dieser README, der gestrichene Kanten oder Labels nennt, sagt, dass die Wirkung nur bei den Dualpreisen der Konvergenz gemessen ist.

## Modell

- **Instanz:** eigene, Solomon-artige Instanzen, nicht die Originalinstanzen: Quadrat 100 × 100, Depot in der Mitte, Zeit = Entfernung = Kosten (euklidisch, also metrisch), Bedienzeit 10, Horizont 300, Kapazität 70, Nachfrage 5 bis 25, Zeitfenster der Breite 20 bis 100, zufällig verteilt oder in fünf Gruppen. Dazu das **Handbeispiel**:
  Depot (5, 5) und sechs Kunden auf einem Gitter, Manhattan-Abstand, Bedienzeit 2, Kapazität 8, Horizont 40, ganze Zahlen; sein Master ist über alle 45 zulässigen Routen exakt mit Brüchen gelöst.
- **Master und Pricing:** Partitionierungs-Master (jeder Kunde genau einmal), Start mit den Einzelfahrten, je Runde bis zu 15 neue Spalten; Pricing als Vorwärts-Labeling mit ng-Gedächtnis (Voreinstellung k = 8; ab k = n elementar). Die Spaltenerzeugung läuft bis zur Konvergenz: ihr Wert ist LB, ihre Dualpreise sind die der Konvergenz.
- **Pfad-reduzierte Kosten einer Kante (i, j):** die kleinsten reduzierten Kosten einer zulässigen Route über die Kante, berechnet als Minimum über die verträglichen Paare aus einem Vorwärtslabel in i und einem Rückwärtslabel in j (Zeit passt, Lasten passen in die Kapazität, die Gedächtnisse haben keinen gemeinsamen Kunden).
  Bei ng-Gedächtnis k < n ist der Wert nie größer als der wahre Wert der elementaren Routen, bei k = n gleich (Tabellenzeile N).
- **Streichregel:** Eine Kante fällt weg, wenn ihr Wert die Schwelle übersteigt. Mit der Schwelle UB − LB bleibt das ganzzahlige Optimum erhalten (Beweis im Expander „📐 Mathematische Formulierung“, Prüfung in Experiment 5 und im Orakel-Test).
- **Drei obere Schranken** (Experiment 2): 1 der beste ganzzahlige Wert aus den Spalten der Spaltenerzeugung; 2 dazu die beste Route je Kante; 3 dazu die Aufzählung aller elementaren Routen mit reduzierten Kosten höchstens UB2 − LB, das **exakte Optimum**, wenn die Aufzählung vollständig und die Partitionierung bewiesen optimal ist.

## Methodik

- **Experiment 1 (Handbeispiel):** Netz mit Pfeilen und Kantenwerten, Tabelle der Kanten mit bester Route, Regler „Schwelle“ (0 bis 6, Voreinstellung = Lücke 2): gestrichene Kanten rot, Kanten der optimalen Lösung orange unterlegt, Optimum über die verbleibenden Routen, Labels im gestrichenen Graphen; im Expander alle Vorwärts- und Rückwärtslabels.
- **Experiment 2 (eigene Instanz):** 5 bis 12 Kunden, zufällig oder gruppiert, Fensterbreite 20, 40, 60 oder 100, ng-Gedächtnis 2 bis 12: untere Schranke, drei obere Schranken, exakte Lücke, gestrichene Kanten, Labels voll gegen gestrichen. Jede aufgezählte Route wird vor der Anzeige unabhängig geprüft.
- **Experiment 3 (wie gut muss die obere Schranke sein?):** Kurve „Anteil der Kanten mit Wert höchstens x % von LB“ für die Live-Instanz und die vier Zellen der Reihe n = 30, die Lücken der drei Schranken als Marken, Regler „angenommene Lücke“ (0,5 bis 10 % von LB, ohne Garantie) mit Verdikt, ob das Optimum bleibt.
- **Experiment 4 (Bänder):** die Reihe n = 30 (vier Zellen mit je 12 Instanzen) und die kleine Reihe n = 50: Aufbau (fertige und abgebrochene Läufe, bewiesene Optima), Streichanteil und Label-Verhältnis je Schwelle mit Mittel und Spanne.
- **Experiment 5 (Gegenprobe):** die Schwelle der Live-Instanz von 100 % bis 0 % der Lücke in Zehntelschritten, zu jeder das beste ganzzahlige Ergebnis über die Routen ohne gestrichene Kante; daneben die Zählung an kleinen Instanzen.
- **Kern:** `ksp_algorithm.py` (Vorwärts- und Rückwärts-Labeling, Verbinden, Streichen, Aufzählung; jede Regel eine Funktion, Kopie des Messkerns der Vormessung, umbenannt) und `ksp_master.py` (Master mit HiGHS und exakt mit Brüchen, Spaltenerzeugung, ganzzahlige Partitionierung).
  `ksp_evaluation.analyse_instanz` ist die eine Rechnung für eine Instanz; die Live-Rechnung und `tools/baender_erzeugen.py` rufen dieselbe Funktion auf.

## Befunde (gemessen, keine Behauptungen)

„Mittel“ und „Bereich“ gelten über die Zellen: der kleinste und der größte Mittelwert der vier Zellen (zufällig und gruppiert, Fensterbreite 40 und 100), „Einzelwerte“ über alle Instanzen. Die Zufalls-Seeds sind 1400 ff. (12 Instanzen je Zelle bei n = 30; 10 und 8 bei n = 50). Alle Reihen gelten für ng-Gedächtnis k = 8, Partitionierungs-Master, metrische Kosten und
**sind nur bei den Dualpreisen der Konvergenz gemessen; der Nutzen in späteren Pricing-Aufrufen ist nicht gemessen.** Die Zahl gestrichener Kanten und von Labels hängt von den Dualpreisen des Master-Lösers ab und kann auf einem anderen Rechner leicht abweichen; die Schranken nicht (siehe Tests).

| Frage | Befund | Test |
|---|---|---|
| **Handbeispiel** (6 Kunden, 45 zulässige Routen, Partitionierung): Welche untere Schranke, welche Dualpreise, welches Optimum? | Untere Schranke LB = 44, Dualpreise (6, 6, 6, 16, 6, 4) mit Summe 44, bei 7 Routen reduzierte Kosten 0, keine negativ; die LP-Lösung ist gebrochen. Ganzzahliges Optimum z\* = 46 mit den Routen (1, 3, 5), (4, 2) und (6) (Längen 18, 24, 4), Lücke z\* − LB = 2. | A |
| Handbeispiel: Wie viele Labels, wie viele Kanten haben eine zulässige Route? | Vorwärts 33 erzeugte Labels, 21 überleben; rückwärts 37 erzeugt, 18 überleben. 31 von 42 gerichteten Kanten haben mindestens eine zulässige Route, der Rest ist schon wegen Fenstern, Last oder Horizont unzulässig. | B |
| Handbeispiel: Welche Pfad-reduzierten Kosten haben die Kanten? | Kante 4→5: 4 (beste Route 4 → 5, Länge 26 minus Dualpreise 22); Kante 0→4: 2 (beste Route 4 → 2, Länge 24 minus 22). Verteilung über die 31 Kanten: Wert 0 bei 14, Wert 2 bei 4, Wert 4 bei 8, Wert 6 bei 5 Kanten. Jeder Wert gleicht dem Minimum über die 45 aufgezählten Routen. | C |
| Handbeispiel: Was geschieht bei den Schwellen 0 bis 6? | Schwelle 2 (= Lücke): 13 von 31 Kanten gestrichen (41,9 %), 16 von 45 Routen bleiben, das Optimum bleibt 46; das Vorwärts-Labeling erzeugt 20 statt 33 Labels (× 0,61), die kleinsten reduzierten Kosten über alle Endlabels sind in beiden Läufen 0. Schwelle 1 (halbe Lücke): 17 Kanten gestrichen, darunter 0→4 und 4→2 der optimalen Lösung, das beste ganzzahlige Ergebnis ist 50 statt 46. Schwelle 0: 17 Kanten, 50. Schwelle 3: 13, 46; Schwelle 4 und 5: 5, 46; Schwelle 6: nichts gestrichen, 46. | D |
| **Live-Voreinstellung** (10 Kunden, zufällig, Fensterbreite 100, Zufalls-Seed 0, k = 8, eine Instanz): Was zeigt sie? | LB 323,13, Optimum 326,03, Lücke 0,90 % von LB; 77 von 110 Kanten haben eine zulässige Route, 47 werden gestrichen (61,0 %), alle drei oberen Schranken streichen gleich viel; 42 statt 185 Labels. Bei 90 % der Lücke geht das Optimum verloren (beste Lösung 326,56, 48 Kanten gestrichen); eine angenommene Lücke von 2 % von LB streicht 43 Kanten und erhält das Optimum, eine von 0,5 % streicht 48 und verliert es. | E |
| **Reihe n = 30** (je 12 Instanzen in 4 Zellen, zufällig und gruppiert, Breite 40 und 100, k = 8): Wie ist sie aufgebaut? | 48 Instanzen, alle fertig, keine abgebrochen; das Optimum ist in 48 von 48 bewiesen, die Aufzählung in 48 von 48 vollständig. 930 gerichtete Kanten (30 · 29 plus 60 Depotkanten); mit zulässiger Route im Median je Zelle 412,5 / 605,5 / 483,5 / 665,5; volle Vorwärtslabels im Median 1 517 / 4 964 / 3 622 / 10 585,5. Die Summe der Dualpreise weicht von LB um höchstens 4,6e-13 ab. | F |
| Reihe n = 30: Wie groß sind die Lücken der drei oberen Schranken? | Mittlere Lücke (Bereich über die vier Zellen, in % von LB): Schranke 1 (nur Spalten) 4,3 bis 8,7, größter Einzelwert 21,8; Schranke 2 (mit bester Route je Kante) 2,6 bis 4,3, größter Einzelwert 10,3; exaktes Optimum 2,1 bis 3,6, größter Einzelwert 8,2. | G |
| Reihe n = 30: Wie viele Kanten mit zulässiger Route werden gestrichen? | Bei der exakten Lücke (Optimum schon bewiesen, also ein Bestwert der Methode) im Mittel 46 bis 61 % (Einzelwerte 10 bis 83 %); mit Schranke 2, die ohne Aufzählung der Routen auskommt, 41 bis 56 % (1 bis 83 %); mit Schranke 1 nur 22 bis 42 % (0 bis 83 %). Bei angenommenen 0,5 / 1 / 2 / 5 % von LB (ohne Garantie): 76 bis 78 / 70 bis 71 / 58 bis 60 / 30 bis 33 %. | H |
| Reihe n = 30: Wie viele Labels erzeugt das Vorwärts-Labeling im gestrichenen Graphen? | Verhältnis zum vollen Graphen im Mittel (Bereich über die Zellen): exakte Lücke 0,34 bis 0,52 (Einzelwerte 0,05 bis 0,94); Schranke 2 0,39 bis 0,58; Schranke 1 0,56 bis 0,80; angenommen 0,5 / 1 / 2 / 5 %: 0,11 bis 0,16 / 0,20 bis 0,25 / 0,37 bis 0,42 / 0,71 bis 0,75. | I |
| Reihe n = 30: Wie weit streuen die Einzelinstanzen? | Kleinster Streichanteil bei der exakten Lücke 10,4 % (gruppiert, Breite 100, Zufalls-Seed 1403, Lücke 8,22 % von LB, Labels × 0,94), größter 83,0 % (gruppiert, Breite 40, Zufalls-Seed 1408, Lücke 0,00 %, Labels × 0,06). | J |
| Reihe n = 30: Wie weit liegen die Zellen bei gleicher Schwelle auseinander? | Anteil der Kanten mit Wert höchstens x % von LB (Bereich der vier Zellenmittel): x = 0,5: 21,8 bis 23,8 %; 1: 28,6 bis 30,4 %; 2: 39,7 bis 41,9 %; 3: 49,7 bis 51,4 %; 5: 67,3 bis 70,2 %; 10: 93,1 bis 95,8 %. An allen acht Rasterpunkten (0,5 bis 10 %) schwanken die vier Zellenmittel bei gleicher Schwelle um höchstens 4,0 Prozentpunkte; für Einzelinstanzen gilt das nicht. | K |
| **Reihe n = 50** (nur Breite 100, zufällig 10 und gruppiert 8 Instanzen): Was ändert sich? | Optimum bewiesen in 9 von 10 (zufällig) und nur in 3 von 8 (gruppiert); Aufzählung vollständig in 10 von 10 und 5 von 8. Lücken im Mittel: Schranke 1 4,78 % / 8,88 %, Schranke 2 2,00 % / 3,05 %, exakt 1,35 % / 2,06 %. Gestrichen im Mittel: Schranke 1 27,8 % / 16,8 %, Schranke 2 55,5 % / 39,8 %, exakt 65,2 % (9 Instanzen) / 53,5 % (3 Instanzen); Labels bei der exakten Lücke × 0,33 / × 0,45. 2 550 gerichtete Kanten. | L |
| Stimmen die neu gerechneten Reihen mit der Messung vor dem Bau überein? | 1 386 verglichene Werte (LB, drei obere Schranken, ob exakt, Kanten mit Route, Vorwärtslabels, je Schwelle gestrichene Kanten und Labels), 9 Abweichungen: Zufalls-Seed 1408 (zufällig, n = 50) und 1400 und 1401 (gruppiert, n = 50), alle bei der exakten Stufe ohne bewiesenes Optimum. Reihe n = 30: 1 008 Werte, 0 Abweichungen. | M |
| **Gegenprobe an kleinen Instanzen** (n = 7, 8, 9, 10, Breite 40 und 100, zufällig und gruppiert, je Größe 12 Instanzen, je Instanz k = n und k = 5): Wie oft geht das Optimum verloren? | 384 Fälle (192 elementar, 168 mit Lücke größer null): bei der exakten Lücke in 0 Fällen, bei der halben Lücke in 81 Fällen; keine Route mit reduzierten Kosten höchstens Lücke verliert eine Kante. Die Pfad-reduzierten Kosten lagen in 0 Fällen über dem wahren Wert; bei k = n sind sie gleich, bei k = 5 lagen sie an 150 von 10 134 Kanten mit Route darunter (die Streichung bleibt gültig, wird schwächer). | N |
| Bleiben die kleinsten reduzierten Kosten über alle Endlabels beim Streichen erhalten? | Ja, in 336 von 336 Fällen (n = 30: 48 Instanzen × 7 Schwellen) und 126 von 126 (n = 50: 18 × 7). | O |
| Stehen die Zahlen der Hilfetexte der Szenarien im Kern? | Ja: 13 von 31 Kanten, Optimum 46, 17 Kanten, 50 statt 46, Schwelle 6; die gruppierte Live-Instanz (Zufalls-Seed 5) hat eine Lücke der Schranke 1 über der exakten, die Instanz mit Zufalls-Seed 1 die Lücke 0. | P |
| Welche Regler-Grenzen und Annahmen nennt die README? | Handschwelle 0 bis 6; 5 bis 12 Kunden; Fensterbreite 20, 40, 60, 100; ng-Gedächtnis 2 bis 12; angenommene Lücke 0,5 bis 10 % in Schritten von 0,5; Horizont 300, Bedienzeit 10, Kapazität 70, Nachfrage 5 bis 25; je Runde bis zu 15 neue Spalten; Aufzählung über Kundenmengen bis 14 Kunden; Obergrenze der Aufzählung 300 000 Routen, Zeitgrenze 60 Sekunden je Partitionierung mit HiGHS. | Q, R |

**Zahl → Test.** Die Zahlen der Tabelle stehen in `tests/test_claims.py` (exakt für das Handbeispiel und die Zählungen, aus den gespeicherten Rohwerten in `data/` für die Messreihen, mit den Auswertungsfunktionen der App); Ausnahmen: die Eigenschaft „Kantenwert gleicht dem Minimum über die aufgezählten Routen“ in Zeile C steht außerdem in `tests/test_algorithm.py` und im Orakel-Test, die einmaligen Messungen im Abschnitt „Befunde und Korrekturen“ (Rechenzeit von HiGHS gegen die Aufzählung; rund 60 000 zulässige Routen bei n = 12 und Breite 200; mehrere Sekunden Rechenzeit dort) stehen in keinem Test:
A `test_A_hand_example_master_optimum_and_gap`, B `test_B_hand_example_labels_and_edges_with_a_route`, C `test_C_hand_example_edge_values_by_hand_and_their_distribution`, D `test_D_hand_example_cutting_at_the_thresholds`,
E `test_E_default_live_instance`, F `test_F_series_n30_structure_and_control`, G `test_G_series_n30_gaps_of_the_three_upper_bounds`, H `test_H_series_n30_share_of_removed_edges`, I `test_I_series_n30_label_ratio`,
J `test_J_series_n30_single_instances_with_the_smallest_and_the_largest_share`, K `test_K_series_n30_curve_edges_with_value_up_to_x_percent_of_lb`, L `test_L_series_n50_small_series_with_few_proven_optima`,
M `test_M_comparison_with_the_measurement_before_the_build`, N `test_N_counter_check_counts_of_the_small_instances`, O `test_O_best_end_value_is_kept_when_cutting_in_all_cases`, P `test_P_the_numbers_of_the_app_texts_come_from_the_same_functions`, Q `test_Q_instance_model_and_control_ranges_named_in_the_readme`, R `test_R_limits_of_the_enumeration_and_the_solver`.
Die Messreihen in `data/` hat `tools/baender_erzeugen.py` mit dem Kern dieser Demo gerechnet; `tests/test_baender.py` rechnet Stichproben nach (Schranken auf 1e-6 relativ, gestrichene Kanten und Labels nur in Bändern, weil sie vom Master-Löser abhängen).

## Ehrliche Grenzen

Dieselben Annahmen, Grenzen und bekannten Probleme wie im Expander „⚠️ Annahmen, Grenzen und bekannte Probleme“ der App (ein Test vergleicht beide Fassungen):

**Annahmen**

- Die Instanzen sind eigene, Solomon-artige Instanzen (nicht die Originalinstanzen von Solomon): Quadrat 100 × 100, Depot in der Mitte, Zeit = Entfernung = Kosten (euklidisch, also metrisch), Bedienzeit 10, Horizont 300, Kapazität 70, Nachfrage 5 bis 25, Zeitfenster der Breite 20 bis 100, zufällig verteilt oder in fünf Gruppen. Das Handbeispiel hat sechs Kunden, Manhattan-Abstände, Bedienzeit 2, Kapazität 8, Horizont 40 und ganze Zahlen.
- Der Master ist ein Partitionierungs-Master (jeder Kunde genau einmal). Gerechnet wird mit HiGHS, im Handbeispiel exakt mit Brüchen. Das Pricing ist ein Vorwärts-Labeling mit ng-Gedächtnis (Voreinstellung k = 8; ab k = n elementar). Die Spaltenerzeugung läuft bis zur Konvergenz; ihr Wert ist die untere Schranke LB, ihre Dualpreise sind die der Konvergenz.
- Eine Kante wird gestrichen, wenn ihre Pfad-reduzierten Kosten (die kleinsten reduzierten Kosten einer zulässigen Route über die Kante) größer sind als die Schwelle. Garantiert ist das nur, wenn die Schwelle mindestens UB − LB beträgt, mit einer echten oberen Schranke UB, also dem Wert einer gefundenen ganzzahligen Lösung. „Angenommen x % von LB“ ist keine echte Schranke.
- Die drei oberen Schranken sind: 1 der beste ganzzahlige Wert aus den Spalten der Spaltenerzeugung, 2 dazu die beste Route je Kante, 3 dazu die Aufzählung aller elementaren Routen mit reduzierten Kosten höchstens UB2 − LB. Nur wenn die Aufzählung vollständig und die Partitionierung bewiesen optimal ist, ist Schranke 3 das exakte ganzzahlige Optimum.
- Gezählt werden Kanten und erzeugte Labels; Sekunden zeigt die App nicht.

**Grenzen**

- Die Wirkung ist nur bei den Dualpreisen der Konvergenz gemessen, der Nutzen in späteren Pricing-Aufrufen (nach Verzweigen oder Schnitten) ist nicht gemessen. Bei den Dualpreisen der Konvergenz gibt es keine verbessernde Route mehr; bei geänderten Dualpreisen müssten die Kantenwerte neu berechnet werden (nicht gemessen).
- Die feste Messreihe zu n = 30 hat 4 Zellen (zufällig und gruppiert, Fensterbreite 40 und 100) mit je 12 Instanzen, zusammen 48; die Spannen über die Instanzen sind groß, Mittelwerte gelten nicht für Einzelinstanzen. Die Reihe zu n = 50 (nur Breite 100) hat 10 zufällige und 8 gruppierte Instanzen, davon mit bewiesenem Optimum 9 und 3.
- „Exaktes Optimum“ heißt: ganzzahliges Optimum der Partitionierung über alle elementaren Routen mit reduzierten Kosten höchstens UB2 − LB, nur bei vollständiger Aufzählung und bewiesen optimaler Partitionierung gezählt. Eine echte Verzweigungsrechnung hätte zu dem Zeitpunkt nur eine heuristische obere Schranke; wie viel dort gestrichen würde, ist nicht gemessen.
- Die Lücke ist die zur ng-Schranke bei k = 8 im Wurzelknoten, nicht zur LP-Schranke der elementaren Routen. Die Kosten sind metrisch, der Master ein Partitionierungs-Master.
- Das Verbinden nicht dominierter Vorwärts- und Rückwärtslabels mit disjunkten Gedächtnissen ist eine eigene, einfache Umsetzung und nicht der bidirektionale Algorithmus der Literatur.
- Die Live-Rechnung ist auf 12 Kunden begrenzt, weil sie alle zulässigen Routen aufzählt; größere Fälle stehen nur als feste Messreihen da.

**Bekannte Probleme und Unsicherheiten**

- Die Instanzen entstehen mit dem Zufallsgenerator von Python (`random.Random`), damit sie mit den festen Messreihen übereinstimmen; die Tests rechnen Stichproben der Messreihen nach.
- Die festen Messreihen sind mit dem Kern dieser Demo neu gerechnet (Python 3.14, SciPy 1.18.1, Windows) und mit den Rohdateien der Messung vor dem Bau verglichen: 1 386 Werte verglichen, 9 Abweichungen. Die Zahl gestrichener Kanten und Labels hängt von den Dualpreisen ab; bei mehreren gleich guten Master-Lösungen kann HiGHS auf einem anderen Rechner andere Dualpreise liefern, die Schranken nicht.
- Bei n = 50 hängt es von den Zeitgrenzen ab (60 Sekunden je Partitionierung), ob das Optimum bewiesen wird; auf einem anderen Rechner kann das anders ausgehen.
- Erklärungen mit „weil“ sind Deutungen, soweit nicht ausdrücklich gemessen.
- Die Diagramme haben keine Auswahlfunktion; ein Mausklick auf sie bewirkt nichts.

## Tests

Die Suite hat 267 Tests (`pytest --collect-only -q tests`), alles unter `tests/`:

- **Kern** (`test_algorithm.py`): Erweiterungsregel vorwärts und rückwärts (Last, Fenster, Warten, Grenzen inklusive, Gedächtnis), Dominanzregel je Komponente, Handbeispiel in allen Zahlen gegen Handrechnung (Rechnung in `tests/conftest.py`), Verbinden, Streichen je Schwelle, Master (HiGHS und Brüche), ganzzahlige Partitionierung auf drei Wegen,
  Spaltenerzeugung, Instanzgenerator, Hängetest am Regler-Maximum (n = 12, gruppiert, Breite 100, k = 12; Timeout statt Zeitprüfung).
- **Orakel** (`test_oracle_kantenstreichung_pricing.py`): eigene Tiefensuche über alle zulässigen Routen und eigene Rekursion für das Optimum, nichts aus dem Kern; 60 Instanzen mit n = 6 bis 8, je mit k = n und k = 3 (120 Fälle): Gültigkeit und Gleichheit der Kantenwerte, Dualzulässigkeit gegen alle Routen und gegen ein eigenes LP, Streichen mit der exakten Lücke erhält das Optimum, die Gegenprobe mit der halben Lücke ist trennscharf, bestes Endlabel gleich der kleinsten reduzierten Kosten.
- **Eigenschaften** (`test_eigenschaften_kantenstreichung_pricing.py`): Monotonie der Schwelle, jede Schwelle ab der Lücke erhält das Optimum, Umnummerieren und Skalieren ändern die Kantenwerte nur erwartungsgemäß, ein kleineres Gedächtnis erhöht nie einen Wert, jede Regel wirkt auf mindestens einer Instanz, gleiche Zahlen in zwei Prozessen mit verschiedener Hash-Randomisierung.
- **Randfälle** (`test_edge_cases.py`): ein Kunde, zwei Kunden mit und ohne gemeinsame Route, Last gleich Kapazität, Fenster ohne Spielraum, Horizont inklusive, Kunden am selben Ort, Dualpreise null, Lücke null, sehr große Schwelle, kleinste und größte Live-Einstellung, Obergrenzen.
- **Messreihen und Aussagen** (`test_baender.py`, `test_claims.py`, `test_verdicts.py`, `test_readme.py`): Aufbau und Stichproben der Messreihen, Vergleich mit der Messung vor dem Bau, jede Zahl der README, jedes Verdikt mit Schwellen und Zahlen im Text, README gegen App-Text und Testzahl.
- **Oberfläche** (`test_app.py`, `test_layout.py`, `test_presets.py`, `test_footer.py`, `test_runtime_imports.py`): AppTest für Standard, jedes Beispielszenario (mit den erwarteten Verdikt-Zeilen), Permalink, jeden Regler an Minimum und Maximum, Reihenauswahl, feste Achsen und keine nicht endlichen Zahlen in den Figuren; Schnellstart in der Seitenleiste mit hervorgehobenem Szenario; Footer; jeder Import steht in `requirements.txt`.

## Dateistruktur

| Datei | Zweck |
|---|---|
| `.github/workflows/tests.yml` | CI: Push, Pull Request, wöchentlicher Canary |
| `.gitignore` | venv, Caches, Streamlit-Secrets |
| `.streamlit/config.toml` | Streamlit-Einstellungen (keine Nutzungsstatistik) |
| `app.py` | Streamlit-App: Einleitung, fünf Experimente, Annahmen, Mathematik |
| `data/baender_kanten.json` | Feste Messreihen: je Instanz Schranken, Kanten, Streichen und Labels bei sieben Schwellen (6 Zellen: n = 30 und n = 50), je Zelle Quelle und Vergleich mit der Messung vor dem Bau |
| `data/gegenprobe_zaehlung.json` | Zählung der Gegenprobe an 384 kleinen Fällen (je Fall die Zahlen und eine Zusammenfassung) |
| `ksp_algorithm.py` | Kern: Labeling vorwärts und rückwärts, Verbinden, Streichen, Aufzählung, Prüfer |
| `ksp_baender.py` | Auswertung der festen Messreihen (Mittel, Bereiche, Zählungen, Kurven) |
| `ksp_constants.py` | Regler-Grenzen, feste Annahmen, Obergrenzen, Farben, Beispielszenarien, Vorbehalt |
| `ksp_evaluation.py` | `analyse_instanz`, Handbeispiel, Live-Instanz, Verdikte als reine Funktionen, Zahlenformat |
| `ksp_layout.py` | Fester Kopf (Stylesheet), Tabellen im Telefon-Fenster scrollbar |
| `ksp_master.py` | Master (HiGHS und exakt mit Brüchen), Spaltenerzeugung, ganzzahlige Partitionierung |
| `ksp_presets.py` | Permalink (Begrenzen), Beispielszenarien (Schnellstart in der Seitenleiste), Zufalls-Seed-Button |
| `ksp_scenario.py` | Instanzen (Generator, Handbeispiel) |
| `ksp_texte.py` | Annahmen, Grenzen, Tabelle „Wo die Annahmen enden“, Mathematik |
| `ksp_visualization.py` | Plotly-Abbildungen (Achsen fest, Kategorien mit Typ) |
| `requirements-dev.txt` | Laufzeit plus pytest |
| `requirements.txt` | Laufzeit-Bibliotheken (ungepinnt) |
| `tools/baender_erzeugen.py` | Erzeugt `data/` mit dem Kern der Demo und vergleicht mit den Rohdateien der Messung vor dem Bau |
| `tests/` | Mini-Instanz und unabhängiger Rechenweg, Orakel, Eigenschaften, Randfälle, Messreihen, Aussagen, Verdikte, Oberfläche |

## Bewusst nicht umgesetzt

- **Verzweigen und Schnitte (Branch-and-Price):** Die Demo streicht bei den Dualpreisen der Konvergenz und misst nur dort. Ein Pricing-Aufruf nach einer Verzweigung oder mit geänderten Dualpreisen im gestrichenen Graphen (mit neu berechneten Kantenwerten) ist nicht gemessen.
- **Der bidirektionale Algorithmus der Literatur** (Irnich, Desaulniers, Desrosiers, Hadjar 2010; Titel und Fundstelle in Katalogeinträgen geprüft, Zusammenfassung gelesen, Volltext nicht gelesen): hier ein eigenes, einfacheres Verbinden nicht dominierter Vorwärts- und Rückwärtslabels, ohne Halbweg-Begrenzung.
- **Überdeckungs-Master und nicht metrische Kosten**, **heuristische obere Schranken aus echten Verzweigungsrechnungen**, **mehr als 12 Kunden und Fensterbreite 200 in der Live-Rechnung**.

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

Die CI läuft mit Python 3.12; die festen Messreihen sind mit Python 3.14 gerechnet. Die Streamlit-Cloud-Einstellung der Python-Version ist beim Deploy zu prüfen und hier einzutragen.

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Gebaut mit Streamlit, Plotly, NumPy und SciPy.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zur Reihe: [Ressourcenwege: von der Grenze zur Verfahrenswahl](https://sebastianhanisch.net/konzepte-ressourcenwege.html).
