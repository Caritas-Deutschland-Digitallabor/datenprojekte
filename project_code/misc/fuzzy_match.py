"""
fuzzy_match.py
──────────────
Compare a column from two CSV files using fuzzy string matching.
Produces a result CSV with:
  - The value from dataset 1
  - The value from dataset 2 (best match)
  - Top-3 candidate matches with scores (descending)

Dependencies:
    pip install pandas rapidfuzz
"""

import ast
import pandas as pd
from rapidfuzz import process, fuzz
from pathlib import Path


# ─────────────────────────────────────────────
# CONFIGURATION  ← edit these
# ─────────────────────────────────────────────
CSV_1         = "Webscraping/Civic_Coding/2026-03-25_Civic-Coding-Projekte-via-Map-API.csv"
CSV_2         = "Webscraping/Civic_Coding/2026-03-25_Civic-Coding-Community-Projekte-via-Scraping.csv"

COL_1         = "title"   # column name in CSV_1
COL_2         = "Projektname"   # column name in CSV_2 (same feature)

SCORE_CUTOFF  = 0                # minimum score to keep (0 = keep all)
TOP_N         = 3                # how many candidates to list per row
SCORER        = fuzz.WRatio      # scoring algorithm (WRatio works well for short strings)

OUTPUT_FILE   = "fuzzy_match_results.csv"
# ─────────────────────────────────────────────


def top_n_matches(
    query: str,
    choices: list[str],
    n: int = TOP_N,
    scorer=SCORER,
    score_cutoff: float = SCORE_CUTOFF,
) -> list[tuple[str, float]]:
    """Return the top-n (match, score) tuples, sorted descending by score."""
    results = process.extract(
        query,
        choices,
        scorer=scorer,
        limit=n,
        score_cutoff=score_cutoff,
    )
    # process.extract returns (match, score, index) – keep only (match, score)
    return [(match, round(score, 1)) for match, score, *_ in results]


def format_top3(matches: list[tuple[str, float]]) -> str:
    """Serialise the top-3 list into a readable string for the CSV cell."""
    lines = [f"{i+1}. '{m}' ({s})" for i, (m, s) in enumerate(matches)]
    return " | ".join(lines)


def run_matching(
    csv1: str,
    csv2: str,
    col1: str,
    col2: str,
    output: str,
) -> pd.DataFrame:
    # ── Load data ─────────────────────────────
    print(f"Loading '{csv1}' …")
    df1 = pd.read_csv(csv1)
    print(f"  {len(df1):,} rows, columns: {list(df1.columns)}")

    print(f"Loading '{csv2}' …")
    df2 = pd.read_csv(csv2)
    print(f"  {len(df2):,} rows, columns: {list(df2.columns)}")

    if col1 not in df1.columns:
        raise ValueError(f"Column '{col1}' not found in {csv1}. Available: {list(df1.columns)}")
    if col2 not in df2.columns:
        raise ValueError(f"Column '{col2}' not found in {csv2}. Available: {list(df2.columns)}")

    choices = df2[col2].dropna().astype(str).tolist()

    # ── Fuzzy matching ────────────────────────
    print(f"\nMatching '{col1}' → '{col2}' (top {TOP_N}, scorer={SCORER.__name__}) …")

    records = []
    for i, query in enumerate(df1[col1].astype(str), 1):
        matches = top_n_matches(query, choices)

        best_match, best_score = matches[0] if matches else ("", 0.0)
        top3_str              = format_top3(matches)

        records.append(
            {
                f"source_{col1}":   query,
                f"best_match_{col2}": best_match,
                "best_score":       best_score,
                "top3_candidates":  top3_str,
            }
        )

        if i % 100 == 0 or i == len(df1):
            print(f"  {i}/{len(df1)} processed …")

    result = pd.DataFrame(records)

    # ── Sort & save ───────────────────────────
    result = result.sort_values("best_score", ascending=False).reset_index(drop=True)
    result.to_csv(output, index=False, encoding="utf-8-sig")

    print(f"\n✓ Results saved → '{output}'  ({len(result):,} rows)")
    print(f"\nScore distribution:\n{result['best_score'].describe().round(1).to_string()}")
    print(f"\nSample (top 5):\n{result.head().to_string(index=False)}")

    return result


# ─────────────────────────────────────────────
# Optional: parse the top3 column back to a list
# (useful when loading the result CSV programmatically)
# ─────────────────────────────────────────────
def parse_top3_column(series: pd.Series) -> pd.Series:
    """Convert the top3_candidates string column back to a list of (match, score) tuples."""
    def _parse(cell: str):
        entries = cell.split(" | ")
        out = []
        for entry in entries:
            # e.g. "1. 'Some Name' (92.5)"
            try:
                name  = entry.split("'")[1]
                score = float(entry.rsplit("(", 1)[-1].rstrip(")"))
                out.append((name, score))
            except Exception:
                pass
        return out
    return series.apply(_parse)


# ─────────────────────────────────────────────
if __name__ == "__main__":
    result_df = run_matching(
        csv1   = CSV_1,
        csv2   = CSV_2,
        col1   = COL_1,
        col2   = COL_2,
        output = OUTPUT_FILE,
    )