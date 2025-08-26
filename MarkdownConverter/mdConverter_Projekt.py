# %%
import pandas as pd
import os
import ast
import argparse

#%%
class MarkdownCreatorProjects:
    def __init__(self, type, data_file, name=None, column_mapping=None, link_fields=None):
        self.type = type
        self.data_file = data_file
        self.name = name
        self.column_mapping = column_mapping or {}  # Maps placeholder -> CSV column
        self.link_fields = link_fields or []  # List of field names that should be formatted as links
        self.md_content = self.load_md_file(type)
        self.data_content = self.load_csv_file(data_file)
        self.content = self.md_content  # Initialize content with template
    
    def load_csv_file(self, data_file):
        """Load csv data files."""
        try:
            return pd.read_csv(f"data/csv/{data_file}.csv", delimiter=";")
        except FileNotFoundError:
            print("Data is needed")
            return pd.DataFrame()  # Return empty DataFrame instead of string
    
    def load_md_file(self, type):
        """Load markdown template."""
        template_paths = {
            "Projekt": "data/templates/Vorlage_Projekt.md",
            "Art": "data/templates/Vorlage_Art.md",
            "Einsatzbereich": "data/templates/Vorlage_Einsatzbereich.md"
        }
        
        if type not in template_paths:
            print("Type is needed - valid types: Projekt, Art, Einsatzbereich")
            return ""
        
        try:
            with open(template_paths[type], 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Template file not found: {template_paths[type]}")
            return ""
    
    def create_md_file(self, name, row_index=0):
        """Create markdown file with given name using CSV data."""
        self.name = name
        
        if self.data_content.empty:
            print("No CSV data available")
            return self.content
        
        # Get the row data (default to first row)
        if row_index >= len(self.data_content):
            print(f"Row index {row_index} out of range. Using first row.")
            row_index = 0
        
        row_data = self.data_content.iloc[row_index]
        self.content = self.populate_template(row_data)
        return self.content
    
    def populate_template(self, row_data):
        """Populate markdown template with CSV row data."""
        content = self.md_content
        
        # First, handle custom mappings
        for placeholder, csv_column in self.column_mapping.items():
            if csv_column in row_data:
                value = row_data[csv_column]
                placeholder_formatted = f"{{{{{placeholder}}}}}"
                content = self._replace_placeholder_with_value(content, placeholder_formatted, value)
        
        # Then, handle automatic column matching
        for column, value in row_data.items():
            # Skip if this column was already handled by custom mapping
            if column in self.column_mapping.values():
                continue
            
            # Replace placeholders in format {{column_name}}
            placeholder = f"{{{{{column}}}}}"
            content = self._replace_placeholder_with_value(content, placeholder, value)
            
            # Also try lowercase placeholder format
            placeholder_lower = f"{{{{{column.lower()}}}}}"
            content = self._replace_placeholder_with_value(content, placeholder_lower, value)
            
            # Try with spaces replaced by underscores
            column_underscore = column.replace(" ", "_")
            placeholder_underscore = f"{{{{{column_underscore}}}}}"
            content = self._replace_placeholder_with_value(content, placeholder_underscore, value)
        
        return content
    
    def _parse_value(self, value):
        """Parse string representations of lists back into actual lists."""
        if pd.isna(value):
            return ""
        
        value_str = str(value).strip()
        
        # If it's empty or just whitespace, return empty string
        if not value_str:
            return ""
        
        # Split by comma and clean each item
        value_list = [x.strip() for x in value_str.split(",") if x.strip()]
        
        # Return single string if only one item, otherwise return list
        return value_list[0] if len(value_list) == 1 else value_list
    
    def _replace_placeholder_with_value(self, content, placeholder, value):
        """Handle replacement of placeholder with value, including list values."""
        
        # Extract placeholder name without braces for comparison
        placeholder_name = placeholder.replace("{{", "").replace("}}", "")
        
        # Special handling for Organisation - replace separators with commas
        if placeholder_name == "Organisation":
            value_str = str(value)
            value = value_str.replace("/", ",").replace(";", ",")
            # Clean up multiple consecutive commas and whitespace
            while ",," in value:
                value = value.replace(",,", ",")
            value = value.strip(" ,")
        
        # Parse the value to handle string representations of lists
        parsed_value = self._parse_value(value)
        
        # Handle empty values
        if not parsed_value:
            return content.replace(placeholder, "")
        
        # Handle single value fields that should remain as single strings
        if placeholder_name in {"Projektname", "Status"}:
            return content.replace(placeholder, str(parsed_value))
        
        # Handle fields that should join list items with spaces
        if placeholder_name in {"Kurzzusammenfassung"}:
            if isinstance(parsed_value, list):
                joined_text = " ".join(str(item) for item in parsed_value)
            else:
                joined_text = str(parsed_value)
            return content.replace(placeholder, joined_text)
        
        # Handle list values that need special bullet formatting
        if isinstance(parsed_value, list):
            bullet_placeholder = f"- {placeholder}"
            
            if bullet_placeholder in content:
                # Check if this field should be formatted as links
                link = placeholder_name in self.link_fields
                
                # Format based on placeholder type
                if placeholder_name in {"Art", "Einsatzbereich"}:
                    if link:
                        list_items = "\n".join(f"- [[{item}]]" for item in parsed_value)
                    else:
                        list_items = "\n".join(f"- #{item.replace(' ', '-')}" for item in parsed_value)
                elif placeholder_name in {"Organisation"}:
                    if link:
                        list_items = "\n".join(f"- [[{item}]]" for item in parsed_value)
                    else:
                        list_items = "\n".join(f"- {item}" for item in parsed_value)
                elif placeholder_name in {"Quelle", "Webseite-Link"}:
                    list_items = "\n".join(f"- {item}" for item in parsed_value)
                else:
                    # Default bullet format
                    if link:
                        list_items = "\n".join(f"- [[{item}]]" for item in parsed_value)
                    else:
                        list_items = "\n".join(f"- {item}" for item in parsed_value)
                
                return content.replace(bullet_placeholder, list_items)
            else:
                # Not in bullet context, join with commas
                comma_list = ", ".join(str(item) for item in parsed_value)
                return content.replace(placeholder, comma_list)
        
        # Default case: convert to string and replace
        return content.replace(placeholder, str(parsed_value))
    
    def create_multiple_files(self):
        """Create markdown files for all rows in CSV."""
        if self.data_content.empty:
            print("No CSV data available")
            return
        
        created_files = []
        for index, row in self.data_content.iterrows():
            # Use "Projektname" column as filename if it exists
            if "Projektname" in self.data_content.columns and pd.notna(row["Projektname"]):
                filename = str(row["Projektname"]).replace(" ", "_").replace("/", "_")
                # Clean filename - remove special characters but keep underscores and hyphens
                filename = "".join(c for c in filename if c.isalnum() or c in "_-")
            else:
                # Fallback to generic name if Projektname doesn't exist or is empty
                filename = f"projekt_{index}"
            
            # Ensure filename is not empty
            if not filename:
                filename = f"projekt_{index}"
                
            self.create_md_file(filename, index)
            self.save_file()
            created_files.append(filename)
        
        print(f"Created {len(created_files)} files: {created_files}")
        return created_files
    
    def save_file(self):
        """Save current content to file."""
        if not self.name:
            print("No name specified for file")
            return
        
        # Create directory if it doesn't exist
        dir_path = f"data/{self.type}"
        os.makedirs(dir_path, exist_ok=True)
        
        try:
            with open(f"{dir_path}/{self.name}.md", 'w', encoding='utf-8') as f:
                f.write(self.content)
            print(f"Saved {self.name}")
        except Exception as e:
            print(f"Error saving file: {e}")


#%%
creator = MarkdownCreatorProjects("Projekt", "PublicInterestAI_Projekte_enriched", link_fields=["Art"])
creator.create_md_file("test", row_index=37)
creator.save_file()

#%%
def main():
    parser = argparse.ArgumentParser(description="Create markdown files from CSV data using templates")
    parser.add_argument("type", help="Type of template (Projekt, Art, Einsatzbereich)")
    parser.add_argument("datafile", help="CSV data file name (without .csv extension)")
    parser.add_argument("--link-fields", nargs="+", help="Field names that should be formatted as wiki links", default=[])
    
    args = parser.parse_args()
    
    creator = MarkdownCreatorProjects(args.type, args.datafile, link_fields=args.link_fields)
    creator.create_multiple_files()

if __name__ == "__main__":
    main()