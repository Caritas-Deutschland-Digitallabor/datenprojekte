import pandas as pd
import numpy as np

from rapidfuzz import fuzz
from rapidfuzz.process import cdist
from collections import defaultdict


def source_all_projects_for_deduplication(
    list_of_projects_dataframes: list[pd.DataFrame],
    dataframe_lookup: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Concatenates projects data for deduplication purpose.

    Args:
        

    Returns:
        pd.DataFrame: Sourced & merged limited information fromm all projects data
    """
    cols_to_read_from_scraped_data = ["Index", "Projektname"]

    for dataframe in list_of_projects_dataframes:
        # Check if dataframe has column data_source
        if "data_source" not in dataframe.columns:
            # Add column data_source
            dataframe["data_source"] = next(k for k, v in dataframe_lookup.items() if v.equals(dataframe))

    all_projects_to_be_deduplicated = pd.concat(list_of_projects_dataframes, ignore_index=True)

    return all_projects_to_be_deduplicated

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

def deduplicate_projects(projects_df: pd.DataFrame) -> dict[str, list]:
    """
    Runs the deduplication process on a DataFrame of projects.

    Args:
        projects_df (pd.DataFrame): DataFrame with columns ["Index", "Projektname", "data_source"].

    Returns:
        dict[str, list]: {data_source: [list of original Index values that were removed]}
    """
    duplicates_dict = find_and_remove_duplicates(projects_df, threshold=90)

    # Print number of duplicates in total
    print(f"\nTotal number of duplicates: {sum(len(duplicates) for duplicates in duplicates_dict.values())}")

    return duplicates_dict   

def remove_duplicated_rows(dataframe_lookup_dict: dict[str, pd.DataFrame], source_name: str, duplicate_indices: list[int]):
    """
    Removes duplicate rows from a DataFrame in-place.

    Args:
        dataframe_lookup_dict (dict[str, pd.DataFrame]): Dictionary mapping source names to DataFrames.
        source_name (str): Name of the DataFrame to remove duplicates from.
        duplicate_indices (list[int]): List of row indices to remove.
    """
    df = dataframe_lookup_dict[source_name]
    df.drop(index=df[df["Index"].isin(duplicate_indices)].index, inplace=True)
    df["Index"] = range(len(df))  # reassign sequential IDs back to the "Index" column
    print(f"✓ Dropped {len(duplicate_indices)} rows from '{source_name}'")