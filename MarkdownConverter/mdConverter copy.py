# %%
import pandas as pd
import os
import re


# %%
class MarkdownCreatorProjects:
    def __init__(self, type, data_file_path, name=None, column_mapping=None, link_fields=None):
        self.type = type
        self.data_file_path = data_file_path
        self.name = name
        self.column_mapping = column_mapping or {}  # Maps placeholder -> CSV column
        self.link_fields = link_fields or []  # List of field names that should be formatted as links
        self.md_content = self.load_md_file(type)
        self.data_content = self.load_csv_file(data_file_path)
        self.content = self.md_content  # Initialize content with template

    def load_csv_file(self, data_file_path):
        """Load csv data files."""
        if not data_file_path:
            return pd.DataFrame()
        try:
            return pd.read_csv(data_file_path, delimiter=";")
        except FileNotFoundError:
            print(f"Data file not found: {data_file_path}")
            return pd.DataFrame()  # Return empty DataFrame instead of string

    def load_md_file(self, type):
        """Load markdown template."""
        template_paths = {
            "Projekt": "data/templates/Vorlage_Projekt.md",
            "Art": "data/templates/Vorlage_Art.md",
            "Einsatzbereich": "data/templates/Vorlage_Einsatzbereich.md",
            "Organisation": "data/templates/Vorlage_Organisation.md",
        }

        if type not in template_paths:
            print("Type is needed - valid types: Projekt, Art, Einsatzbereich")
            return ""

        try:
            with open(template_paths[type], "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            print(f"Template file not found: {template_paths[type]}")
            return ""

    def create_md_file(self, name, row_index=0, row_data=None):
        """Create markdown file with given name using CSV data."""
        self.name = name

        if row_data is None:
            if self.data_content.empty:
                print("No CSV data available")
                return self.content

            # Get the row data (default to first row)
            if row_index >= len(self.data_content):
                print(f"Row index {row_index} out of range. Using first row.")
                row_index = 0
            row_data = self.data_content.iloc[row_index]

        # Reset content to original template before populating
        self.md_content = self.load_md_file(self.type)
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

        # Clean up any remaining placeholders that were not filled
        content = re.sub(r"\{\{.*?\}\}", "", content)

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
        """Create markdown files based on the type."""
        if self.type == "Projekt":
            self.create_project_files()
        elif self.type in ["Organisation", "Art", "Einsatzbereich"]:
            self.create_entity_files()
        else:
            print(f"Unknown type: {self.type}. Valid types are Projekt, Organisation, Art, Einsatzbereich.")

    def create_project_files(self):
        """Create markdown files for all rows in CSV (one per project)."""
        if self.data_content.empty:
            print("No CSV data available")
            return

        created_files = []
        title_column = "Projektname"

        for index, row in self.data_content.iterrows():
            if title_column in self.data_content.columns and pd.notna(row[title_column]):
                filename = str(row[title_column]).replace(" ", "_").replace("/", "_")
                filename = "".join(c for c in filename if c.isalnum() or c in "_-")
            else:
                filename = f"projekt_{index}"

            if not filename:
                filename = f"projekt_{index}"

            self.create_md_file(filename, row_index=index)
            self.save_file()
            created_files.append(filename)

        print(f"Created {len(created_files)} project files.")
        return created_files

    def create_entity_files(self):
        """Create one markdown file for each unique entity of a given type."""
        if self.data_content.empty:
            print("No CSV data available")
            return

        entity_column_base = self.type

        # Find all columns that could contain entity names by checking for variations
        cols_to_scan = []
        for col in self.data_content.columns:
            if col.lower().startswith(entity_column_base.lower()):
                cols_to_scan.append(col)

        if not cols_to_scan:
            print(
                f"No columns found for type '{self.type}'. Searched for columns starting with '{entity_column_base}'."
            )
            return

        print(f"Found entity columns: {cols_to_scan}")

        unique_entities = set()
        for _, row in self.data_content.iterrows():
            for col in cols_to_scan:
                entity_value = row.get(col)
                if pd.isna(entity_value):
                    continue

                entity_list_str = str(entity_value).replace("/", ",").replace(";", ",")
                entity_list = [item.strip() for item in entity_list_str.split(",") if item.strip()]

                for item in entity_list:
                    unique_entities.add(item)

        created_files = []
        for entity_name in sorted(list(unique_entities)):
            filename = str(entity_name).replace(" ", "_").replace("/", "_")
            filename = "".join(c for c in filename if c.isalnum() or c in "_-")

            if not filename:
                continue

            row_data = pd.Series({entity_column_base: entity_name})
            self.create_md_file(name=filename, row_data=row_data)
            self.save_file()
            created_files.append(filename)

        print(f"Created {len(created_files)} {self.type} files.")
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
            with open(f"{dir_path}/{self.name}.md", "w", encoding="utf-8") as f:
                f.write(self.content)
            print(f"Saved {self.name}")
        except Exception as e:
            print(f"Error saving file: {e}")


# %%
# creator = MarkdownCreatorProjects("Projekt", "data/csv/PublicInterestAI_Projekte_enriched.csv", link_fields=["Art"])
# creator.create_md_file("test", row_index=37)
# creator.save_file()


# %%
def main(type, input_path, link_fields=None):
    """
    Creates markdown files from a single CSV file or all CSV files in a directory.
    """
    if not os.path.exists(input_path):
        print(f"Error: The path '{input_path}' does not exist.")
        return

    def process_csv(file_path):
        print(f"Processing {file_path}...")
        creator = MarkdownCreatorProjects(type=type, data_file_path=file_path, link_fields=link_fields)
        creator.create_multiple_files()

    if os.path.isfile(input_path):
        if input_path.lower().endswith(".csv"):
            process_csv(input_path)
        else:
            print(f"Error: Provided file '{input_path}' is not a .csv file.")

    elif os.path.isdir(input_path):
        print(f"\n----- Processing type: {type} -----")
        print(f"Scanning for CSV files in '{input_path}'...")
        csv_files_found = False
        all_data = []
        for filename in os.listdir(input_path):
            if filename.lower().endswith(".csv"):
                csv_files_found = True
                file_path = os.path.join(input_path, filename)
                try:
                    df = pd.read_csv(file_path, delimiter=";")
                    all_data.append(df)
                except Exception as e:
                    print(f"Could not read {file_path}: {e}")

        if all_data:
            full_df = pd.concat(all_data, ignore_index=True)
            print(f"Found {len(full_df)} total rows. Creating markdown files...")
            creator = MarkdownCreatorProjects(type=type, data_file_path=None, link_fields=link_fields)
            creator.data_content = full_df
            creator.create_multiple_files()

        if not csv_files_found:
            print(f"No CSV files found in directory '{input_path}'.")

    else:
        print(f"Error: The path '{input_path}' is not a valid file or directory.")


if __name__ == "__main__":
    # 1. Create Project files with links to other entities
    main(
        type="Projekt",
        input_path="data/csv",
        link_fields=["Organisation", "Art", "Einsatzbereich"],
    )

    # 2. Create individual files for Organisations, Arten, and Einsatzbereiche
    main(type="Organisation", input_path="data/csv")


# %%
