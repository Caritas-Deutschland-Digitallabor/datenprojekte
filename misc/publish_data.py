import pandas as pd
import ast


def dict_to_cluster_list(dict_str):
    if pd.isna(dict_str):
        return []
    try:
        d = ast.literal_eval(dict_str)
        return list(set(v for v in d.values() if v))  # unique non-empty values only
    except (ValueError, SyntaxError):
        return []


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
    if pd.isna(value):
        return "Unbekannt"
    key = str(value).strip().lower()
    key = key.removeprefix("online - ").strip()  # drop redundant "online - " prefix
    return STATUS_MAP.get(key, "Unbekannt")


def publish_data(input_csv: str, output_csv: str = "data.csv"):
    df = pd.read_csv(input_csv, sep=";")

    df["Art"] = df["Art"].apply(dict_to_cluster_list)
    df["Einsatzbereich"] = df["Einsatzbereich"].apply(dict_to_cluster_list)
    df["Status"] = df["Status"].apply(normalize_status)

    df.columns = [col.lower().replace("-", "_").replace(" ", "_") for col in df.columns]

    # Drop the LLM-generated abbreviation: almost always empty, not a stable identifier.
    df = df.drop(columns=["projekt_abkürzung"], errors="ignore")

    # Preferred column order; any remaining columns are appended at the end.
    column_order = [
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
    ordered = [c for c in column_order if c in df.columns]
    ordered += [c for c in df.columns if c not in ordered]
    df = df[ordered]

    df.to_csv(output_csv, sep=";", index=False)
    print(f"Published {len(df)} projects to {output_csv}")


if __name__ == "__main__":
    publish_data("project_code/MarkdownConverter/data/csv/2026-01-30_combined_projects_with_term_dictionaries.csv")
