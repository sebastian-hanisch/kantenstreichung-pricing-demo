"""README gegen App und Tests: gleicher Annahmen-Text, Testzahl = Zahl der gesammelten Tests, jeder in der Zahl-zu-Test-Tabelle genannte Test existiert und jeder Test von `test_claims.py` ist genannt, keine Platzhalter."""

import re
import subprocess
import sys
from pathlib import Path

import pytest

import ksp_constants as C
import ksp_texte as T

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_the_assumptions_text_of_the_app_is_in_the_readme_verbatim():
    assert T.assumptions_markdown() in README


def test_the_test_count_in_the_readme_is_the_number_of_collected_tests():
    p = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", "tests"], cwd=ROOT, capture_output=True, text=True, timeout=300)
    gesammelt = int(re.search(r"(\d+) tests? collected", p.stdout).group(1))
    genannt = int(re.search(r"Die Suite hat (\d+) Tests", README).group(1))
    assert genannt == gesammelt


def test_every_test_named_in_the_number_to_test_table_exists_and_every_claims_test_is_named():
    absatz = README[README.index("**Zahl → Test.**"):README.index("## Ehrliche Grenzen")]
    namen = re.findall(r"`(test_[A-Za-z0-9_]+)`", absatz)
    quelle = (ROOT / "tests" / "test_claims.py").read_text(encoding="utf-8")
    vorhanden = re.findall(r"^def (test_[A-Za-z0-9_]+)\(", quelle, flags=re.M)
    assert len(namen) == len(set(namen)) == len(vorhanden) == 18
    assert set(namen) == set(vorhanden)


def test_no_placeholders_are_left():
    for datei in [ROOT / "README.md", ROOT / "app.py", *ROOT.glob("ksp_*.py")]:
        text = datei.read_text(encoding="utf-8")
        assert "@@" not in text and "TODO" not in text, datei.name


def test_the_table_rows_name_their_test_letters_and_every_letter_is_in_the_mapping():
    tabelle = README[README.index("## Befunde (gemessen"):README.index("**Zahl → Test.**")]
    zeilen = [z for z in tabelle.splitlines() if z.startswith("| ") and not z.startswith("| Frage") and not z.startswith("|---")]
    buchstaben = [re.search(r"\| ([A-R](?:, [A-R])*) \|$", z).group(1) for z in zeilen]
    absatz = README[README.index("**Zahl → Test.**"):README.index("## Ehrliche Grenzen")]
    einzeln = [b for gruppe in buchstaben for b in gruppe.split(", ")]
    assert einzeln == list("ABCDEFGHIJKLMNOPQR") and all(f"{b} `test_{b}_" in absatz for b in einzeln)


def test_the_caveat_stands_in_the_readme_next_to_the_effect_figures():
    assert "nur bei den Dualpreisen der Konvergenz" in README and "ist nicht gemessen" in README
    kern = README[README.index("## Kernfrage"):README.index("## Befunde und Korrekturen")]
    assert "Alle Aussagen über die Wirkung gelten nur bei den Dualpreisen der Konvergenz" in kern
    assert README.count("Dualpreisen der Konvergenz") >= 5


def test_every_demo_linked_as_a_neighbour_has_a_folder_or_is_the_application_or_the_delimitation():
    verlinkt = set(re.findall(r"https://github\.com/sebastian-hanisch/([a-z0-9-]+)\)", README))
    assert {"weg-mit-grenzen-demo", "dominanz-labels-demo", "zeitfenster-labeling-demo", "mehrere-grenzen-demo", "pricing-dualpreise-demo", "crew-pairing-demo", "hub-labeling-demo"} <= verlinkt
    if not any((ROOT.parent / name).is_dir() for name in verlinkt):
        pytest.skip("Die verlinkten Demos liegen nicht als Ordner neben dieser Demo (zum Beispiel in der CI): Ordnerprüfung entfällt")
    for name in verlinkt:
        assert (ROOT.parent / name).is_dir(), name


def test_readme_ends_with_the_portfolio_footer_and_names_the_python_versions():
    assert README.rstrip().endswith("[Ressourcenwege: von der Grenze zur Verfahrenswahl](https://sebastianhanisch.net/konzepte-ressourcenwege.html).")
    assert "Python 3.12" in README and "Python 3.14" in README
