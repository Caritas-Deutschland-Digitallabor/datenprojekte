"""Build the published data.csv from the manually maintained Obsidian vault.

The vault project files (``Vault/Projekt/*.md``) are the source of truth: they
are what people manually correct after the LLM-based enrichment. Publishing
therefore reads those files directly instead of the intermediate combined CSV,
so manual corrections end up in ``data.csv``.
"""

import re
from pathlib import Path

import pandas as pd

VAULT_PROJEKT_DIR = "Vault/Projekt"


# Maps the various raw status spellings to a fixed set of canonical values.
STATUS_MAP = {
    "in betrieb": "In Betrieb",
    "laufend": "In Betrieb",
    "in planung": "In Planung",
    "in weiterentwicklung": "In Weiterentwicklung",
    "im testbetrieb": "Im Testbetrieb",
    "in testbetrieb": "Im Testbetrieb",
    "prototyp": "Prototyp",
    "eingestellt": "Eingestellt",
    "abgeschlossen": "Abgeschlossen",
    "abgeschlossen/ eingestellt": "Eingestellt",
    "abgeschlossen/eingestellt": "Eingestellt",
    "unbekannt": "Unbekannt",
    "unclear": "Unbekannt",
}


def normalize_status(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "Unbekannt"
    key = str(value).strip().lower()
    key = key.removeprefix("online - ").strip()  # drop redundant "online - " prefix
    return STATUS_MAP.get(key, "Unbekannt")


def _split_sections(body):
    """Split a markdown body into a {section title: [lines]} mapping."""
    sections = {}
    current = None
    for line in body.splitlines():
        heading = re.match(r"^##\s+(.*)$", line)
        if heading:
            current = heading.group(1).strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return sections


def _bullet_values(lines):
    """Return the text of every non-empty ``- ...`` bullet in a section."""
    values = []
    for line in lines:
        m = re.match(r"^-\s*(.*)$", line)
        if m and m.group(1).strip():
            values.append(m.group(1).strip())
    return values


def _linked_categories(lines):
    """Extract the ``[[Kategorie]]`` targets from term bullets.

    Lines look like ``- [[Datenanalyse]]: #Statistik``. Only the mapped
    categories (``[[...]]``) are kept; unmapped ``- #Hashtag`` bullets are
    intentionally dropped, matching the previous published schema.
    """
    categories = []
    for line in lines:
        for match in re.findall(r"\[\[([^\]]+)\]\]", line):
            category = match.strip()
            if category and category not in categories:
                categories.append(category)
    return categories


def parse_project_file(path):
    """Parse a single vault project file into a record dict, or None if it is
    not a project file."""
    text = Path(path).read_text(encoding="utf-8")

    if not re.search(r"^type:\s*Projekt\s*$", text, flags=re.MULTILINE):
        return None

    title_match = re.search(r"^title:\s*(.*)$", text, flags=re.MULTILINE)
    status_match = re.search(r"^status:\s*(.*)$", text, flags=re.MULTILINE)

    sections = _split_sections(text)

    kurz = " ".join(
        l.strip() for l in sections.get("Kurzbeschreibung", []) if l.strip()
    )

    organisationen = [
        org.replace("[[Organisation/", "").replace("[[", "").replace("]]", "").strip()
        for org in _bullet_values(sections.get("Organisation(en)", []))
    ]

    links = _bullet_values(sections.get("Projekt-Links", []))
    quelle_bullets = _bullet_values(sections.get("Quelle", []))
    # The Quelle section also contains the free-text "Lizenz: ..." line, which is
    # not a bullet, so quelle_bullets only holds the actual source URL(s).

    lizenz, lizenz_organisation = "", ""
    lizenz_match = re.search(r'Lizenz:\s*"([^"]*)"\s*mit Dank an\s*(\S+)', text)
    if lizenz_match:
        lizenz = lizenz_match.group(1).strip()
        lizenz_organisation = lizenz_match.group(2).strip()

    return {
        "projektname": title_match.group(1).strip() if title_match else "",
        "kurzzusammenfassung": kurz,
        "art": _linked_categories(sections.get("Arten", [])),
        "einsatzbereich": _linked_categories(sections.get("Einsatzbereiche", [])),
        "status": normalize_status(status_match.group(1) if status_match else None),
        "organisation": ", ".join(organisationen),
        "webseite_link": ", ".join(links),
        "quelle": ", ".join(quelle_bullets),
        "lizenz": lizenz,
        "lizenz_organisation": lizenz_organisation,
    }


COLUMN_ORDER = [
    "projektname",
    "kurzzusammenfassung",
    "art",
    "einsatzbereich",
    "status",
    "organisation",
    "webseite_link",
    "quelle",
    "lizenz",
    "lizenz_organisation",
]


def publish_data(vault_projekt_dir: str = VAULT_PROJEKT_DIR, output_csv: str = "data.csv"):
    records = []
    for path in sorted(Path(vault_projekt_dir).glob("*.md")):
        record = parse_project_file(path)
        if record is not None:
            records.append(record)

    df = pd.DataFrame(records, columns=COLUMN_ORDER)
    df.to_csv(output_csv, sep=";", index=False)
    print(f"Published {len(df)} projects to {output_csv}")
    return df


if __name__ == "__main__":
    publish_data()
