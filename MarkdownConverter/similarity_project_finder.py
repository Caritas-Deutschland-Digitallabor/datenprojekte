# %%
import pandas as pd
from fuzzywuzzy import fuzz

csv_file = "data/csv/combined_projects_with_term_dictionaries.csv"
df = pd.read_csv(csv_file, delimiter=";")


def get_similar_project_groups(df, column_name, threshold=85):
    """
    Finds groups of similar project names.
    """
    names = df[column_name].dropna().unique().tolist()

    groups = []
    processed_indices = set()

    for i, name1 in enumerate(names):
        if i in processed_indices:
            continue

        current_group = {name1}
        processed_indices.add(i)

        for j, name2 in enumerate(names[i + 1 :], start=i + 1):
            if j in processed_indices:
                continue

            if fuzz.token_sort_ratio(name1, name2) >= threshold:
                current_group.add(name2)
                processed_indices.add(j)

        if len(current_group) > 1:
            groups.append(list(current_group))

    return groups


similar_groups = get_similar_project_groups(df, "Projektname")

if similar_groups:
    print("\nFound groups of similar projects:")
    for i, group in enumerate(similar_groups):
        print(f"\n--- Group {i+1} ---")
        group_df = df[df["Projektname"].isin(group)]
        print(group_df[["Projektname", "Quelle"]])  # Showing name and source for context
else:
    print("\nNo similar project groups found with the current threshold.")

all_similar_names = [name for group in similar_groups for name in group]
similar_projects_df = df[df["Projektname"].isin(all_similar_names)]

if not similar_projects_df.empty:
    print("\n--- DataFrame containing all similar projects ---")
    print(similar_projects_df)

# %%
similar_projects_df
