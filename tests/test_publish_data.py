import tempfile
from pathlib import Path

from misc.publish_data import (
    COLUMN_ORDER,
    normalize_status,
    parse_project_file,
    publish_data,
)

# A project file mirroring the real Vault/Projekt/*.md format, including the
# edge cases the parser must handle: an unmapped "- #Hashtag" art bullet, two
# organisations, and the free-text license line inside the Quelle section.
SAMPLE_MD = """---
title: Beispiel Projekt
type: Projekt
status: Laufend
aliases:
  ---

# Beispiel Projekt

## Kurzbeschreibung
Ein Beispielprojekt zur Demonstration.

## Organisation(en)
- [[Organisation/OK Lab Berlin]]
- [[Organisation/Code for Germany]]

## Projekt-Links
- https://example.org/projekt

## Einsatzbereiche
- [[Inklusion & Teilhabe]]: #Barrierefreiheit
- [[Stadtentwicklung]]: #Verkehr

## Arten
- [[Datenanalyse]]: #Statistik
- [[Webanwendungen]]: #Web-App
- #KI-Anwendung

## Quelle
- https://source.example.org/projekt
Lizenz: "CC-BY 4.0" mit Dank an https://example.org

Zurück zu: [[@Alle Projekte]]
"""


def _parse_sample(text):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "sample.md"
        path.write_text(text, encoding="utf-8")
        return parse_project_file(path)


def test_normalize_status():
    assert normalize_status("Laufend") == "In Betrieb"
    assert normalize_status("laufend") == "In Betrieb"
    assert normalize_status("online - im Testbetrieb") == "Im Testbetrieb"
    assert normalize_status("Abgeschlossen") == "Abgeschlossen"
    assert normalize_status("Prototyp") == "Prototyp"
    assert normalize_status("unclear") == "Unbekannt"
    assert normalize_status(None) == "Unbekannt"
    assert normalize_status("etwas ganz anderes") == "Unbekannt"


def test_parse_project_file_fields():
    record = _parse_sample(SAMPLE_MD)

    assert record["projektname"] == "Beispiel Projekt"
    assert record["kurzzusammenfassung"] == "Ein Beispielprojekt zur Demonstration."
    assert record["status"] == "In Betrieb"  # normalized from "Laufend"
    assert record["organisation"] == "OK Lab Berlin, Code for Germany"
    assert record["webseite_link"] == "https://example.org/projekt"
    assert record["quelle"] == "https://source.example.org/projekt"
    assert record["lizenz"] == "CC-BY 4.0"
    assert record["lizenz_organisation"] == "https://example.org"


def test_parse_only_mapped_categories():
    record = _parse_sample(SAMPLE_MD)

    # [[Kategorie]] targets are kept, the unmapped "- #KI-Anwendung" is dropped.
    assert record["art"] == ["Datenanalyse", "Webanwendungen"]
    assert record["einsatzbereich"] == ["Inklusion & Teilhabe", "Stadtentwicklung"]


def test_non_project_file_returns_none():
    record = _parse_sample(SAMPLE_MD.replace("type: Projekt", "type: Organisation"))
    assert record is None


def test_publish_data_smoke():
    """Runs the real vault through publish_data and checks the schema."""
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "data.csv"
        df = publish_data(output_csv=str(out))

    assert list(df.columns) == COLUMN_ORDER
    assert len(df) > 0
    assert (df["projektname"].str.strip() != "").all()
    assert set(df["status"].unique()).issubset(
        {
            "In Betrieb",
            "In Planung",
            "Im Testbetrieb",
            "Prototyp",
            "In Weiterentwicklung",
            "Abgeschlossen",
            "Eingestellt",
            "Unbekannt",
        }
    )


if __name__ == "__main__":
    test_normalize_status()
    test_parse_project_file_fields()
    test_parse_only_mapped_categories()
    test_non_project_file_returns_none()
    test_publish_data_smoke()
    print("All tests passed!")
