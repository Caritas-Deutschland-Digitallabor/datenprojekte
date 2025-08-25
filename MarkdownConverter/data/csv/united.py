import pandas as pd
import os
from pathlib import Path

def combine_csv_files():
    csv_dir = Path(__file__).parent
    csv_files = list(csv_dir.glob("*.csv"))
    
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
    
    output_file = csv_dir / "combined_all_projects.csv"
    combined_df.to_csv(output_file, sep=';', index=False)
    
    print(f"\nCombined file created: {output_file}")
    print(f"Total rows: {len(combined_df)}")
    print(f"Total columns: {len(combined_df.columns)}")
    print(f"Columns: {list(combined_df.columns)}")

if __name__ == "__main__":
    combine_csv_files()