"""
fuzzy_self_match.py
────────────────────
For a given column in a DataFrame, find all pairs of rows with
similar values (fuzzy score ≥ SCORE_CUTOFF).

Dependencies:
    pip install pandas rapidfuzz
"""

import pandas as pd
import numpy as np
from rapidfuzz import process, fuzz
from rapidfuzz.process import cdist


# ─────────────────────────────────────────────
# CONFIGURATION  ← edit these
# ─────────────────────────────────────────────
COLUMN        = "Projektname"   # column to check for duplicates
SCORE_CUTOFF  = 90              # minimum similarity score (0–100)
SCORER        = fuzz.WRatio     # scoring algorithm
TOP_N         = 3               # max candidates to list per row
# ─────────────────────────────────────────────


def find_similar_within_column(
    df: pd.DataFrame,
    column: str,
    score_cutoff: float = SCORE_CUTOFF,
    scorer=SCORER,
    top_n: int = TOP_N,
) -> pd.DataFrame:
    """
    For each row in `df[column]`, find other rows with a fuzzy
    similarity score >= score_cutoff.

    Returns a DataFrame with one row per SOURCE value, listing all
    similar matches found elsewhere in the same column.
    """
    values = df[column].fillna("").astype(str).tolist()

    # ── Build full NxN similarity matrix in one efficient call ──
    print(f"Computing {len(values)}×{len(values)} similarity matrix …")
    matrix = cdist(
        values,
        values,
        scorer=scorer,
        score_cutoff=score_cutoff,  # zeros out scores below threshold
        workers=-1,                 # use all CPU cores
    )

    # ── Zero out the diagonal (a string is always 100% similar to itself) ──
    np.fill_diagonal(matrix, 0)

    # ── Build result records ─────────────────────────────────────
    records = []
    for i, query in enumerate(values):
        # Indices of rows that scored above the cutoff
        match_indices = np.where(matrix[i] > 0)[0]

        if len(match_indices) == 0:
            continue  # no near-duplicates found → skip row

        # Sort by score descending, take top_n
        top_indices = match_indices[np.argsort(matrix[i][match_indices])[::-1]][:top_n]

        candidates = [
            {"value": values[j], "score": round(matrix[i][j], 1), "row_index": int(j)}
            for j in top_indices
        ]

        records.append(
            {
                "row_index":        i,
                "source_value":     query,
                "n_similar":        len(match_indices),
                "best_match":       candidates[0]["value"],
                "best_score":       candidates[0]["score"],
                # Human-readable summary of top candidates
                "top_candidates":   " | ".join(
                    f"{c['row_index']}: '{c['value']}' ({c['score']})"
                    for c in candidates
                ),
                # Machine-readable: list of (row_index, value, score) tuples
                "matches_detail":   [(c["row_index"], c["value"], c["score"]) for c in candidates],
            }
        )

    result = pd.DataFrame(records)
    if not result.empty:
        result = result.sort_values("best_score", ascending=False).reset_index(drop=True)

    print(f"✓ Found {len(result)} rows with at least one similar value (cutoff={score_cutoff})")
    return result


def deduplicate_pairs(similar_df: pd.DataFrame) -> pd.DataFrame:
    """
    Optional: collapse the result into unique PAIRS (A↔B appears once, not twice).
    Useful for reviewing duplicates without seeing mirror entries.
    """
    seen = set()
    deduped = []
    for _, row in similar_df.iterrows():
        for row_idx, value, score in row["matches_detail"]:
            pair = tuple(sorted([row["row_index"], row_idx]))
            if pair not in seen:
                seen.add(pair)
                deduped.append(
                    {
                        "index_a":  row["row_index"],
                        "value_a":  row["source_value"],
                        "index_b":  row_idx,
                        "value_b":  value,
                        "score":    score,
                    }
                )
    return pd.DataFrame(deduped).sort_values("score", ascending=False).reset_index(drop=True)
