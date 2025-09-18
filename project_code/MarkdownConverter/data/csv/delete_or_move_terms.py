# %% read csv and delete terms from a column called Einsatzbereich

import pandas as pd

df = pd.read_csv("Correlaid_Projekte_enriched.csv", sep=";")

# %%

# löschen falls es in einsatzbereich vorkommt: KI, Sprache, Digitalisierung, Legal Tech, Technologie
terms_to_delete = ["KI", "Sprache", "Digitalisierung", "Legal Tech", "Technologie"]
for term in terms_to_delete:
    # Using .str.replace handles non-string (NaN) values gracefully and is more efficient.
    df["Einsatzbereich"] = df["Einsatzbereich"].str.replace(term, "", regex=False)

# %%

# Datenanalyse, Datenschutz, Offene Daten, Open Data (falls vorhanden muss es verschoben werden von eionsatzbereich nach Art -> Verschieben nach Art)

terms_to_move = ["Datenanalyse", "Datenschutz", "Offene Daten", "Open Data"]
for term in terms_to_move:
    mask = df["Einsatzbereich"].str.contains(term, na=False)

    # Add to 'Art'
    df.loc[mask, "Art"] = df.loc[mask, "Art"].fillna("").apply(lambda x: (x + ", " + term).strip(", "))

    # Remove from 'Einsatzbereich'
    df.loc[mask, "Einsatzbereich"] = df.loc[mask, "Einsatzbereich"].str.replace(term, "")

# Clean up 'Einsatzbereich' column from empty strings and dangling commas
df["Einsatzbereich"] = df["Einsatzbereich"].apply(
    lambda x: ", ".join([part.strip() for part in x.split(",") if part.strip()]) if isinstance(x, str) else x
)

# %%

df.to_csv("Correlaid_Projekte_enriched.csv", sep=";", index=False)

# %%
