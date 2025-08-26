import pandas as pd
import os
from pathlib import Path

def load_term_clustering_results():
    """Load term clustering results from TermSimilarity directory"""
    term_similarity_dir = Path(__file__).parent.parent.parent / "TermSimilarity"
    
    try:
        art_results_file = term_similarity_dir / "term_clustering_art_results.csv"
        einsatzbereich_results_file = term_similarity_dir / "term_clustering_einsatzbereich_results.csv"
        
        if art_results_file.exists():
            term_art_df = pd.read_csv(art_results_file, sep=";")
            term_to_cluster_art = dict(zip(term_art_df["term"], term_art_df["cluster_name"]))
            print(f"✅ Loaded {len(term_to_cluster_art)} Art term mappings")
        else:
            term_to_cluster_art = {}
            print("⚠️  Art clustering results not found")
        
        if einsatzbereich_results_file.exists():
            term_einsatzbereich_df = pd.read_csv(einsatzbereich_results_file, sep=";")
            term_to_cluster_einsatzbereich = dict(zip(term_einsatzbereich_df["term"], term_einsatzbereich_df["cluster_name"]))
            print(f"✅ Loaded {len(term_to_cluster_einsatzbereich)} Einsatzbereich term mappings")
        else:
            term_to_cluster_einsatzbereich = {}
            print("⚠️  Einsatzbereich clustering results not found")
            
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
            # Keep original term if not found in clustering
            row_dict[term] = term
    
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
            # Keep original term if not found in clustering
            row_dict[term] = term
    
    return row_dict

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
            df = pd.read_csv(csv_file, delimiter=';')
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
    combined_df.to_csv(output_file, sep=';', index=False)
    
    print(f"\n✅ Combined file created: {output_file}")
    print(f"📊 Total rows: {len(combined_df)}")
    print(f"📊 Total columns: {len(combined_df.columns)}")
    print(f"📋 Columns: {list(combined_df.columns)}")
    
    # Load term clustering results and create enhanced version
    print(f"\n{'='*60}")
    print("🔄 APPLYING TERM CLUSTERING DICTIONARIES")
    print(f"{'='*60}")
    
    term_to_cluster_art, term_to_cluster_einsatzbereich = load_term_clustering_results()
    
    if term_to_cluster_art or term_to_cluster_einsatzbereich:
        # Create a copy for term dictionary version
        enhanced_df = combined_df.copy()
        
        # Replace Art column with dictionaries if clustering results available
        if term_to_cluster_art and 'Art' in enhanced_df.columns:
            enhanced_df["Art"] = enhanced_df["Art"].apply(
                lambda x: create_row_dictionary_art(x, term_to_cluster_art)
            )
            print("✅ Art column replaced with term-to-cluster dictionaries")
        
        # Replace Einsatzbereich column with dictionaries if clustering results available
        if term_to_cluster_einsatzbereich and 'Einsatzbereich' in enhanced_df.columns:
            enhanced_df["Einsatzbereich"] = enhanced_df["Einsatzbereich"].apply(
                lambda x: create_row_dictionary_einsatzbereich(x, term_to_cluster_einsatzbereich)
            )
            print("✅ Einsatzbereich column replaced with term-to-cluster dictionaries")
        
        # Save enhanced file with term dictionaries
        enhanced_output_file = csv_dir / "combined_projects_with_term_dictionaries.csv"
        enhanced_df.to_csv(enhanced_output_file, sep=';', index=False)
        
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