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
            print("Type is needed - valid types: Projekt, Art, Einsatzbereich, Organisation")
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

            # Skip Art and Einsatzbereich, as they are handled explicitly below
            if column in ["Art", "Einsatzbereich"]:
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

        # Explicitly process Art and Einsatzbereich to ensure they are always handled correctly
        # for project files.
        if self.type == "Projekt":
            if "Art" in row_data:
                content = self._replace_placeholder_with_value(content, "{{Art}}", row_data["Art"])
            if "Einsatzbereich" in row_data:
                content = self._replace_placeholder_with_value(
                    content, "{{Einsatzbereich}}", row_data["Einsatzbereich"]
                )

        # Clean up any remaining placeholders that were not filled
        content = re.sub(r"-\s*\{\{.*?\}\}\n?", "", content)
        content = re.sub(r"\{\{.*?\}\}", "", content)

        return content

    def _parse_dict_string(self, value_str):
        """Parse a string like '{key:val, key2:val2}' into a dictionary."""
        if pd.isna(value_str) or not isinstance(value_str, str) or "{" not in value_str:
            return {}
        # Remove braces and split into pairs
        pairs = value_str.strip("{}").split(",")
        result_dict = {}
        for pair in pairs:
            if ":" in pair:
                key, val = pair.split(":", 1)
                result_dict[key.strip()] = val.strip()
        return result_dict

    def _parse_value(self, value):
        """Parse string representations of lists back into actual lists."""
        if pd.isna(value):
            return []

        value_str = str(value).strip()

        # If it's empty or just whitespace, return empty list
        if not value_str:
            return []

        # Split by comma and clean each item, always return a list
        return [x.strip() for x in value_str.split(",") if x.strip()]

    def _replace_placeholder_with_value(self, content, placeholder, value):
        """Handle replacement of placeholder with value, including list values."""
        placeholder_name = placeholder.strip("{}")

        # For project files, parse Art/Einsatzbereich to get Unterbegriffe (keys)
        if self.type == "Projekt" and placeholder_name in {"Art", "Einsatzbereich"}:
            parsed_dict = self._parse_dict_string(value)
            parsed_value = list(parsed_dict.keys())
        else:
            parsed_value = self._parse_value(value)

        if not parsed_value:
            # Even if empty, we want to replace the placeholder to avoid leftover {{...}}
            bullet_placeholder = f"- {placeholder}"
            if bullet_placeholder in content:
                return content.replace(bullet_placeholder, "")
            return content.replace(placeholder, "")

        if isinstance(parsed_value, list):
            bullet_placeholder = f"- {placeholder}"
            if bullet_placeholder in content:
                link = placeholder_name in self.link_fields

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
                else:
                    if link:
                        list_items = "\n".join(f"- [[{item}]]" for item in parsed_value)
                    else:
                        list_items = "\n".join(f"- {item}" for item in parsed_value)
                return content.replace(bullet_placeholder, list_items)
            else:
                return content.replace(placeholder, ", ".join(map(str, parsed_value)))

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

        unique_entities = set()
        # For Art/Einsatzbereich, we create files for Oberbegriffe (values in the dict)
        if self.type in ["Art", "Einsatzbereich"]:
            column_to_scan = self.type
            if column_to_scan not in self.data_content.columns:
                print(f"Column '{column_to_scan}' not found for type '{self.type}'. Skipping entity file creation.")
                return

            for entity_str in self.data_content[column_to_scan].dropna():
                entities = self._parse_dict_string(entity_str)
                for oberbegriff in entities.values():
                    unique_entities.add(oberbegriff)
        # For Organisation, we split by comma
        elif self.type == "Organisation":
            column_to_scan = self.type
            if column_to_scan not in self.data_content.columns:
                print(f"Column '{column_to_scan}' not found for type '{self.type}'. Skipping entity file creation.")
                return

            for entity_str in self.data_content[column_to_scan].dropna():
                entity_list = [e.strip() for e in str(entity_str).split(",") if e.strip()]
                for entity in entity_list:
                    unique_entities.add(entity)

        created_files = []
        for entity_name in sorted(list(unique_entities)):
            filename = str(entity_name).replace(" ", "_").replace("/", "_")
            filename = "".join(c for c in filename if c.isalnum() or c in "_-")

            if not filename:
                continue

            # Use 'title' for placeholders in Art/Einsatzbereich/Organisation templates
            row_data = pd.Series({"title": entity_name})
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

        dir_path = f"Vault/{self.type}"
        os.makedirs(dir_path, exist_ok=True)

        try:
            with open(f"{dir_path}/{self.name}.md", "w", encoding="utf-8") as f:
                f.write(self.content)
            # print(f"Saved {self.name}")
        except Exception as e:
            print(f"Error saving file: {e}")


# %%
def main(type, data_file_path, link_fields=None):
    """
    Creates markdown files from a given CSV file.
    """
    if not os.path.exists(data_file_path):
        print(f"Error: The path '{data_file_path}' does not exist.")
        return

    print(f"\n----- Processing type: {type} -----")
    creator = MarkdownCreatorProjects(type=type, data_file_path=data_file_path, link_fields=link_fields)
    creator.create_multiple_files()


if __name__ == "__main__":
    csv_file = "data/csv/combined_all_projects.csv"

    # 1. Create Project files with links to other entities
    main(
        type="Projekt",
        data_file_path=csv_file,
        link_fields=["Organisation"],
    )

    # 2. Create individual files for Organisations, Arten, and Einsatzbereiche
    main(type="Organisation", data_file_path=csv_file)
    main(type="Art", data_file_path=csv_file)
    main(type="Einsatzbereich", data_file_path=csv_file)

# %%
