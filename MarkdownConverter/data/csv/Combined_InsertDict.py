import pandas as pd
from pathlib import Path


def _process_summary_file(summary_df):
    """Create a term-to-cluster mapping from a summary dataframe."""
    term_to_cluster = {}
    for _, row in summary_df.iterrows():
        cluster_name = row["cluster_name"]
        if pd.notna(row["terms"]):
            terms = [term.strip() for term in str(row["terms"]).split(",")]
            for term in terms:
                if term:
                    term_to_cluster[term] = cluster_name
    return term_to_cluster


def load_term_clustering_results():
    """Load term clustering results from TermSimilarity directory using summary files."""
    term_similarity_dir = Path(__file__).parent.parent.parent / "TermSimilarity"

    try:
        art_summary_file = term_similarity_dir / "term_clustering_art_summary.csv"
        einsatzbereich_summary_file = term_similarity_dir / "term_clustering_einsatzbereich_summary.csv"

        term_to_cluster_art = {}
        if art_summary_file.exists():
            term_art_df = pd.read_csv(art_summary_file, sep=";")
            term_to_cluster_art = _process_summary_file(term_art_df)
            print(f"✅ Loaded {len(term_to_cluster_art)} Art term mappings from summary")
        else:
            print("⚠️  Art clustering summary not found")

        term_to_cluster_einsatzbereich = {}
        if einsatzbereich_summary_file.exists():
            term_einsatzbereich_df = pd.read_csv(einsatzbereich_summary_file, sep=";")
            term_to_cluster_einsatzbereich = _process_summary_file(term_einsatzbereich_df)
            print(f"✅ Loaded {len(term_to_cluster_einsatzbereich)} Einsatzbereich term mappings from summary")
        else:
            print("⚠️  Einsatzbereich clustering summary not found")

        return term_to_cluster_art, term_to_cluster_einsatzbereich

    except Exception as e:
        print(f"❌ Error loading clustering results: {e}")
        return {}, {}


def create_row_dictionary_art(art_column_value, term_to_cluster_art):
    """Create small dictionary for Art column terms"""
    if pd.isna(art_column_value):
        return {}

    terms = [term.strip() for term in str(art_column_value).split(",") if term.strip()]
    row_dict = {}

    for term in terms:
        if term in term_to_cluster_art:
            row_dict[term] = term_to_cluster_art[term]
        else:
            row_dict[term] = ""  # Mark as unmapped

    return row_dict


def create_row_dictionary_einsatzbereich(einsatzbereich_column_value, term_to_cluster_einsatzbereich):
    """Create small dictionary for Einsatzbereich column terms"""
    if pd.isna(einsatzbereich_column_value):
        return {}

    terms = [term.strip() for term in str(einsatzbereich_column_value).split(",") if term.strip()]
    row_dict = {}

    for term in terms:
        if term in term_to_cluster_einsatzbereich:
            row_dict[term] = term_to_cluster_einsatzbereich[term]
        else:
            row_dict[term] = ""  # Mark as unmapped

    return row_dict


def get_all_terms_from_column(series):
    """Extract all unique, non-empty terms from a series with comma-separated strings."""
    all_terms = set()
    for item in series.dropna():
        terms = [term.strip() for term in str(item).split(",") if term.strip()]
        all_terms.update(terms)
    return all_terms


def combine_csv_files():
    csv_dir = Path(__file__).parent
    csv_files = list(csv_dir.glob("*.csv"))

    # Exclude the output files from input
    exclude_files = {"combined_all_projects.csv", "combined_projects_with_term_dictionaries.csv"}
    csv_files = [f for f in csv_files if f.name not in exclude_files]

    if not csv_files:
        print("No CSV files found in the directory.")
        return

    all_dataframes = []

    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, delimiter=";")
            print(f"Loaded {csv_file.name}: {len(df)} rows, {len(df.columns)} columns")
            all_dataframes.append(df)
        except Exception as e:
            print(f"Error reading {csv_file.name}: {e}")

    if not all_dataframes:
        print("No CSV files could be loaded.")
        return

    combined_df = pd.concat(all_dataframes, ignore_index=True, sort=False)

    # Save basic combined file
    output_file = csv_dir / "combined_all_projects.csv"
    combined_df.to_csv(output_file, sep=";", index=False)

    print(f"\n✅ Combined file created: {output_file}")
    print(f"📊 Total rows: {len(combined_df)}")
    print(f"📊 Total columns: {len(combined_df.columns)}")
    print(f"📋 Columns: {list(combined_df.columns)}")

    # Load term clustering results and create enhanced version
    print(f"\n{'='*60}")
    print("🔄 APPLYING TERM CLUSTERING DICTIONARIES")
    print(f"{'='*60}")

    term_to_cluster_art, term_to_cluster_einsatzbereich = load_term_clustering_results()

    # Find and print unmapped terms
    if "Art" in combined_df.columns and term_to_cluster_art:
        all_art_terms = get_all_terms_from_column(combined_df["Art"])
        unmapped_art_terms = all_art_terms - set(term_to_cluster_art.keys())
        if unmapped_art_terms:
            print("\n⚠️  The following 'Art' terms have no category and need to be added to the summary file:")
            for term in sorted(list(unmapped_art_terms)):
                print(f"  -{term}-")

    if "Einsatzbereich" in combined_df.columns and term_to_cluster_einsatzbereich:
        all_einsatzbereich_terms = get_all_terms_from_column(combined_df["Einsatzbereich"])
        unmapped_einsatzbereich_terms = all_einsatzbereich_terms - set(term_to_cluster_einsatzbereich.keys())
        if unmapped_einsatzbereich_terms:
            print(
                "\n⚠️  The following 'Einsatzbereich' terms have no category and need to be added to the summary file:"
            )
            for term in sorted(list(unmapped_einsatzbereich_terms)):
                print(f"  -{term}-")

    if term_to_cluster_art or term_to_cluster_einsatzbereich:
        # Create a copy for term dictionary version
        enhanced_df = combined_df.copy()

        # Replace Art column with dictionaries if clustering results available
        if term_to_cluster_art and "Art" in enhanced_df.columns:
            enhanced_df["Art"] = enhanced_df["Art"].apply(lambda x: create_row_dictionary_art(x, term_to_cluster_art))
            print("✅ Art column replaced with term-to-cluster dictionaries")

        # Replace Einsatzbereich column with dictionaries if clustering results available
        if term_to_cluster_einsatzbereich and "Einsatzbereich" in enhanced_df.columns:
            enhanced_df["Einsatzbereich"] = enhanced_df["Einsatzbereich"].apply(
                lambda x: create_row_dictionary_einsatzbereich(x, term_to_cluster_einsatzbereich)
            )
            print("✅ Einsatzbereich column replaced with term-to-cluster dictionaries")

        # Save enhanced file with term dictionaries
        enhanced_output_file = csv_dir / "combined_projects_with_term_dictionaries.csv"
        enhanced_df.to_csv(enhanced_output_file, sep=";", index=False)

        print(f"\n✅ Enhanced file created: {enhanced_output_file}")
        print(f"📊 Art dictionary mappings: {len(term_to_cluster_art)}")
        print(f"📊 Einsatzbereich dictionary mappings: {len(term_to_cluster_einsatzbereich)}")

        # Show sample mappings
        if term_to_cluster_art:
            print("\n🔍 Sample Art term-to-cluster mappings:")
            for i, (term, cluster) in enumerate(list(term_to_cluster_art.items())[:3]):
                print(f"  '{term}' → '{cluster}'")

        if term_to_cluster_einsatzbereich:
            print("\n🔍 Sample Einsatzbereich term-to-cluster mappings:")
            for i, (term, cluster) in enumerate(list(term_to_cluster_einsatzbereich.items())[:3]):
                print(f"  '{term}' → '{cluster}'")

    else:
        print("⚠️  No clustering results found. Only basic combined file created.")


if __name__ == "__main__":
    combine_csv_files()
