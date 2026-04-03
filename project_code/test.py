import pandas as pd
from collections import defaultdict
from rapidfuzz import fuzz
import numpy as np
from rapidfuzz.process import cdist


# Read in data
cols_to_read_from_scraped_data = ["Index", "Projektname"]

citylab = pd.read_csv(
    "Webscraping/Citylab_Berlin/2026-01-22_CityLAB-Berlin-Projekte-via-Scraping.csv",
    usecols=cols_to_read_from_scraped_data,
).assign(data_source="CityLAB Berlin")
code_for = pd.read_csv(
    "Webscraping/CodeFor/2026-01-28_CodeFor-Projekte-via-Scraping.csv",
    usecols=cols_to_read_from_scraped_data,
).assign(data_source="CodeFor Germany")
civic_coding_community = pd.read_csv("Webscraping/Civic_Coding/2026-03-25_Civic-Coding-Community-Projekte-via-Scraping.csv",
                                     usecols=cols_to_read_from_scraped_data).assign(data_source="Civic Coding Community")
civic_coding_projektlandkarte = pd.read_csv("Webscraping/Civic_Coding/2026-04-02_Civic-Coding-Projektlandkarte-Projekte-via-Map-API.csv",
                                            usecols=cols_to_read_from_scraped_data).assign(data_source="Civic Coding Projektlandkarte")
correlaid = pd.read_csv("Webscraping/Correlaid-Projektdatenbank/2026-01-19_Correlaid-Projekte-via-API_enriched.csv", sep=";",
                        usecols=["Projektname"]).assign(data_source="Correlaid").reset_index(names='Index')
public_interest_ai = pd.read_csv("Webscraping/PublicInterestAI/PublicInterestAI_Projekte_enriched.csv", sep=";",
                                 usecols=["Projektname"]).assign(data_source="PublicInterestAI").reset_index(names='Index')
erfolgsgeschichten = pd.read_csv("Webscraping/Erfolgsgeschichten/Liste der Projekte Datenerfolgsgeschichten.csv", sep=";",
                                  usecols=["Projektname"]).assign(data_source="Datenerfolgsgeschichten").reset_index(names='Index')


merged_df = pd.concat([citylab, code_for, civic_coding_community, civic_coding_projektlandkarte, correlaid, public_interest_ai, erfolgsgeschichten], ignore_index=True)
print(merged_df)



def find_and_remove_duplicates(df: pd.DataFrame, threshold: int = 90) -> dict[str, list]:
    """
    Uses a vectorised NxN similarity matrix (cdist + WRatio) to find duplicates,
    then applies the same forward-only greedy deduplication as before.

    Args:
        df:         Merged dataframe with columns ["Index", "Projektname", "data_source"].
        threshold:  Minimum similarity score (0–100) to flag as duplicate. Default: 90.

    Returns:
        duplicates: {data_source: [list of original Index values that were removed]}
    """
    values = df["Projektname"].fillna("").astype(str).tolist()

    # ── Step 1: build the full NxN similarity matrix in one vectorised call ──
    print(f"Computing {len(values)}×{len(values)} similarity matrix …")
    matrix = cdist(
        values,
        values,
        scorer=fuzz.WRatio,     # ← more recall than token_sort_ratio
        score_cutoff=threshold,  # entries below threshold become 0 → sparse-ish
        workers=-1,              # use all CPU cores
    )
    np.fill_diagonal(matrix, 0)  # a string is always 100% similar to itself → ignore

    # ── Step 2: forward-only greedy deduplication (same logic as before) ──
    duplicates: dict[str, list] = defaultdict(list)
    active = np.ones(len(df), dtype=bool)  # True = row still alive

    positional_index = list(range(len(df)))  # maps position → df.index label

    for pos_i in positional_index:
        if not active[pos_i]:
            continue

        # Only look at positions AFTER pos_i that are still active
        forward_positions = [j for j in range(pos_i + 1, len(df)) if active[j]]

        for pos_j in forward_positions:
            if matrix[pos_i, pos_j] > 0:   # > 0 means it already passed score_cutoff
                source = df.iloc[pos_j]["data_source"]
                original_id = df.iloc[pos_j]["Index"]
                duplicates[source].append(original_id)
                active[pos_j] = False

    # ── Step 3: drop all flagged rows in one go ──
    rows_to_drop = df.index[~active]
    df.drop(index=rows_to_drop, inplace=True)
    df.reset_index(drop=True, inplace=True)

    print(f"✓ Removed {(~active).sum()} duplicate rows across {len(duplicates)} sources")
    return dict(duplicates)


# ── Run ────────────────────────────────────────────────────────────────────────
duplicates_dict = find_and_remove_duplicates(merged_df, threshold=90)
print(f"\nRemaining rows in merged_df: {len(merged_df)}")

# Print number of duplicates in total
print(f"\nTotal number of duplicates: {sum(len(duplicates) for duplicates in duplicates_dict.values())}")   


# Map the string name → the actual DataFrame object
dataframe_lookup = {
    "CityLAB Berlin": citylab,
    "CodeFor Germany": code_for,
    "Civic Coding Community": civic_coding_community,
    "Civic Coding Projektlandkarte": civic_coding_projektlandkarte,
    "Correlaid": correlaid,
    "Datenerfolgsgeschichten": erfolgsgeschichten,
    "PublicInterestAI": public_interest_ai
}

# Iterate over the duplicates dict and drop rows in-place
for source_name, duplicate_indices in duplicates_dict.items():
    df = dataframe_lookup[source_name]
    df.drop(index=df[df["Index"].isin(duplicate_indices)].index, inplace=True)
    df["Index"] = range(len(df))  # reassign sequential IDs back to the "Index" column
    print(f"✓ Dropped {len(duplicate_indices)} rows from '{source_name}'")
    df.to_csv(f"test_unduplicated_data/{source_name}.csv", index=False)