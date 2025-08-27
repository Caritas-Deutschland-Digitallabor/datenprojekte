# %%
import pandas as pd
import os
import re
import ast
import json


# %%
class MarkdownCreatorProjects:
    """
    Creates a set of markdown files from a structured CSV data source.

    This class handles the entire process of reading a CSV file, parsing its rows,
    populating markdown templates, and saving the final .md files into a
    structured vault directory. It is designed to create interconnected notes
    for use in knowledge management tools like Obsidian.
    """

    def __init__(self, type, data_file_path, name=None, column_mapping=None, link_fields=None, website_data=None):
        """
        Initializes the MarkdownCreatorProjects instance.

        Args:
            type (str): The type of markdown file to create (e.g., 'Projekt', 'Organisation').
                        This determines which template to use and which output folder to save to.
            data_file_path (str): The path to the source CSV file.
            name (str, optional): A specific name for a single file creation. Defaults to None.
            column_mapping (dict, optional): A dictionary to map template placeholders to different
                                             CSV column names. Defaults to None.
            link_fields (list, optional): A list of field names that should be formatted
                                          as wiki-links. Defaults to None.
            website_data (dict, optional): A dictionary mapping organization names to their
                                           websites. Defaults to None.
        """
        self.type = type
        self.data_file_path = data_file_path
        self.name = name
        self.column_mapping = column_mapping or {}
        self.link_fields = link_fields or []
        self.website_data = website_data or {}
        self.md_content = self.load_md_file(type)
        self.data_content = self.load_csv_file(data_file_path)
        self.content = self.md_content

    def load_csv_file(self, data_file_path):
        """
        Loads the source data from a CSV file.

        Args:
            data_file_path (str): The path to the CSV file.

        Returns:
            pd.DataFrame: A pandas DataFrame containing the loaded data, or an empty
                          DataFrame if the file is not found.
        """
        if not data_file_path:
            return pd.DataFrame()
        try:
            return pd.read_csv(data_file_path, delimiter=";")
        except FileNotFoundError:
            print(f"Data file not found: {data_file_path}")
            return pd.DataFrame()

    def load_md_file(self, type):
        """
        Loads the appropriate markdown template file based on the given type.

        Args:
            type (str): The type of the template to load (e.g., 'Projekt').

        Returns:
            str: The content of the template file, or an empty string if not found.
        """
        if not self.type:
            return ""
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
        """
        Creates the content for a single markdown file.

        Args:
            name (str): The base name for the output file (without extension).
            row_index (int, optional): The index of the row to use from the DataFrame. Defaults to 0.
            row_data (pd.Series, optional): A specific series of data to use instead of
                                            looking up by row_index. Defaults to None.

        Returns:
            str: The populated markdown content for the file.
        """
        self.name = name

        if row_data is None:
            if self.data_content.empty:
                print("No CSV data available")
                return self.content

            if row_index >= len(self.data_content):
                print(f"Row index {row_index} out of range. Using first row.")
                row_index = 0
            row_data = self.data_content.iloc[row_index]

        self.md_content = self.load_md_file(self.type)
        self.content = self.populate_template(row_data)
        return self.content

    def populate_template(self, row_data):
        """
        Populates the markdown template with data from a pandas Series.

        Args:
            row_data (pd.Series): The data for a single row.

        Returns:
            str: The markdown content with placeholders filled.
        """
        content = self.md_content

        for placeholder, csv_column in self.column_mapping.items():
            if csv_column in row_data:
                value = row_data[csv_column]
                placeholder_formatted = f"{{{{{placeholder}}}}}"
                content = self._replace_placeholder_with_value(content, placeholder_formatted, value)

        for column, value in row_data.items():
            if column in self.column_mapping.values():
                continue

            if column in ["Art", "Einsatzbereich"]:
                continue

            placeholder = f"{{{{{column}}}}}"
            content = self._replace_placeholder_with_value(content, placeholder, value)

            placeholder_lower = f"{{{{{column.lower()}}}}}"
            content = self._replace_placeholder_with_value(content, placeholder_lower, value)

            column_underscore = column.replace(" ", "_")
            placeholder_underscore = f"{{{{{column_underscore}}}}}"
            content = self._replace_placeholder_with_value(content, placeholder_underscore, value)

        if self.type == "Projekt":
            if "Art" in row_data:
                content = self._replace_placeholder_with_value(content, "{{Art}}", row_data["Art"])
            if "Einsatzbereich" in row_data:
                content = self._replace_placeholder_with_value(
                    content, "{{Einsatzbereich}}", row_data["Einsatzbereich"]
                )

        content = re.sub(r"-\s*\{\{.*?\}\}\n?", "", content)
        content = re.sub(r"\{\{.*?\}\}", "", content)

        return content

    def _sanitize_filename(self, name):
        """
        Replaces spaces and slashes with underscores and removes invalid characters.

        Args:
            name (str): The input string to sanitize.

        Returns:
            str: The sanitized string suitable for use as a filename.
        """
        name_str = str(name).replace(" ", "_").replace("/", "_")
        return "".join(c for c in name_str if c.isalnum() or c in "_-")

    def _parse_dict_string(self, value_str):
        """
        Parses a string-represented dictionary using ast.literal_eval for safety.

        Args:
            value_str (str): The string to parse (e.g., "{'key': 'value'}").

        Returns:
            dict: The parsed dictionary, or an empty dictionary if parsing fails.
        """
        if pd.isna(value_str) or not isinstance(value_str, str) or "{" not in value_str:
            return {}
        try:
            return ast.literal_eval(value_str)
        except (ValueError, SyntaxError):
            print(f"Warning: Could not parse dictionary string: {value_str}")
            return {}

    def _parse_value(self, value):
        """
        Parses string representations of lists back into actual lists.

        Args:
            value (str): The input string, typically comma-separated values.

        Returns:
            list: A list of strings, or an empty list if input is empty.
        """
        if pd.isna(value):
            return []

        value_str = str(value).strip()

        if not value_str:
            return []

        return [x.strip() for x in value_str.split(",") if x.strip()]

    def _replace_placeholder_with_value(self, content, placeholder, value):
        """
        Handles replacement of a placeholder with its corresponding value.

        This method contains special formatting logic for different placeholders,
        such as creating backlinks and hashtags for 'Art' and 'Einsatzbereich'.

        Args:
            content (str): The current markdown content.
            placeholder (str): The placeholder to replace (e.g., '{{Projektname}}').
            value (any): The value to insert.

        Returns:
            str: The updated markdown content.
        """
        placeholder_name = placeholder.strip("{}")

        if self.type == "Projekt" and placeholder_name in {"Art", "Einsatzbereich"}:
            parsed_dict = self._parse_dict_string(value)
            if not parsed_dict:
                return content.replace(f"- {placeholder}", "")

            ober_to_unter = {}
            for unter, ober in parsed_dict.items():
                ober = str(ober).strip()
                unter = str(unter).strip()
                if not ober or not unter:
                    continue
                if ober not in ober_to_unter:
                    ober_to_unter[ober] = []
                ober_to_unter[ober].append(unter)

            output_lines = []
            for ober, unters in sorted(ober_to_unter.items()):
                ober_filename = self._sanitize_filename(ober)
                unter_hashtags = [f"#{u.replace(' ', '-')}" for u in sorted(unters)]
                output_lines.append(f"- [[{ober_filename}]]: {', '.join(unter_hashtags)}")

            final_string = "\n".join(output_lines)
            return content.replace(f"- {placeholder}", final_string)

        parsed_value = self._parse_value(value)

        if not parsed_value:
            bullet_placeholder = f"- {placeholder}"
            if bullet_placeholder in content:
                return content.replace(bullet_placeholder, "")
            return content.replace(placeholder, "")

        if isinstance(parsed_value, list):
            bullet_placeholder = f"- {placeholder}"
            if bullet_placeholder in content:
                link = placeholder_name in self.link_fields

                if placeholder_name in {"Art", "Einsatzbereich", "terms"}:
                    list_items = "\n".join(f"- #{item.replace(' ', '-')}" for item in parsed_value)
                elif placeholder_name in {"Organisation"}:
                    if link:
                        list_items = "\n".join(f"- [[{self._sanitize_filename(item)}]]" for item in parsed_value)
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
        """Orchestrates the creation of markdown files based on the instance's type."""
        if self.type == "Projekt":
            self.create_project_files()
        elif self.type in ["Organisation", "Art", "Einsatzbereich"]:
            self.create_entity_files()
        else:
            print(f"Unknown type: {self.type}. Valid types are Projekt, Organisation, Art, Einsatzbereich.")

    def create_project_files(self):
        """Creates one markdown file for each project row in the CSV."""
        if self.data_content.empty:
            print("No CSV data available")
            return

        created_files = []
        title_column = "Projektname"

        for index, row in self.data_content.iterrows():
            if title_column in self.data_content.columns and pd.notna(row[title_column]):
                filename = self._sanitize_filename(row[title_column])
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
        """Creates one markdown file for each unique entity of a given type."""
        if self.data_content.empty:
            print("No CSV data available")
            return

        unique_entities = set()
        if self.type in ["Art", "Einsatzbereich"]:
            column_to_scan = self.type
            if column_to_scan not in self.data_content.columns:
                print(f"Column '{column_to_scan}' not found for type '{self.type}'. Skipping entity file creation.")
                return

            entity_map = {}
            for entity_str in self.data_content[column_to_scan].dropna():
                entities = self._parse_dict_string(entity_str)
                for unterbegriff, oberbegriff in entities.items():
                    if oberbegriff not in entity_map:
                        entity_map[oberbegriff] = set()
                    entity_map[oberbegriff].add(unterbegriff)

            unique_entities = entity_map

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

        if self.type in ["Art", "Einsatzbereich"]:
            for oberbegriff, unterbegriffe in sorted(unique_entities.items()):
                filename = self._sanitize_filename(oberbegriff)
                if not filename:
                    continue

                row_data = pd.Series(
                    {
                        "cluster_name": oberbegriff,
                        "terms": ", ".join(sorted(list(unterbegriffe))),
                    }
                )
                self.create_md_file(name=filename, row_data=row_data)
                self.save_file()
                created_files.append(filename)

        else:
            for entity_name in sorted(list(unique_entities)):
                filename = self._sanitize_filename(entity_name)

                if not filename:
                    continue

                row_data_dict = {"title": entity_name}
                if self.type == "Organisation":
                    website = self.website_data.get(entity_name)
                    if website:
                        row_data_dict["website"] = website

                row_data = pd.Series(row_data_dict)
                self.create_md_file(name=filename, row_data=row_data)
                self.save_file()
                created_files.append(filename)

        print(f"Created {len(created_files)} {self.type} files.")
        return created_files

    def save_file(self):
        """Saves the current markdown content to a file in the Vault directory."""
        if not self.name:
            print("No name specified for file")
            return

        dir_path = f"Vault/{self.type}"
        os.makedirs(dir_path, exist_ok=True)

        try:
            with open(f"{dir_path}/{self.name}.md", "w", encoding="utf-8") as f:
                f.write(self.content)
        except Exception as e:
            print(f"Error saving file: {e}")


def load_website_data(json_path):
    """
    Loads organization websites from a JSON file into a dictionary.

    Args:
        json_path (str): The path to the JSON file.

    Returns:
        dict: A dictionary mapping organization names to website URLs.
    """
    if not os.path.exists(json_path):
        print(f"Website data file not found: {json_path}")
        return {}
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {item["organization"]: item["website"] for item in data if item.get("website")}


def create_homepage(index_files):
    """
    Creates a homepage (Home.md) for the Obsidian Publish site.

    Args:
        index_files (list): A list of dictionaries, where each dictionary
                            describes a master index file (MOC).
    """
    homepage_content = """# Welcome to the Digital Map of Projects

This site provides an interactive overview of various projects, organizations, and their connections.

---

## How to Explore

To get a full overview of how everything is connected, please use the **Graph View**. You can find the button for it in the top-right corner of the site.

You can also use the navigation panel on the left or browse the master lists below.

## Master Lists
"""
    for file_info in index_files:
        link_text = f"Browse all {file_info['type']}"
        homepage_content += f"- [[{file_info['filename']}|{link_text}]]\n"

    homepage_path = "Vault/Home.md"
    try:
        os.makedirs("Vault", exist_ok=True)
        with open(homepage_path, "w", encoding="utf-8") as f:
            f.write(homepage_content.strip())
        print("\nCreated Home.md for the vault.")
    except Exception as e:
        print(f"Error creating homepage: {e}")


def create_index_files(csv_file_path, sanitize_func):
    """
    Creates master list files (MOCs) for each entity type.

    These files act as central hubs, providing a complete, linked list
    for all projects, organisations, etc.

    Args:
        csv_file_path (str): The path to the main CSV data file.
        sanitize_func (function): The function to use for sanitizing filenames/links.

    Returns:
        list: A list of dictionaries describing the created index files.
    """
    if not os.path.exists(csv_file_path):
        print("Index file creation skipped: CSV not found.")
        return []

    print("Creating index files (MOCs)...")
    df = pd.read_csv(csv_file_path, delimiter=";")
    index_files_info = []

    def _parse_dict(val):
        if pd.isna(val) or not isinstance(val, str) or "{" not in val:
            return {}
        try:
            return ast.literal_eval(val)
        except (ValueError, SyntaxError):
            return {}

    projects = sorted(df["Projektname"].dropna().unique())
    content = "# All Projects\n\n" + "\n".join(f"- [[{sanitize_func(p)}]]" for p in projects)
    with open("Vault/_Projekte.md", "w", encoding="utf-8") as f:
        f.write(content)
    index_files_info.append({"type": "Projects", "filename": "_Projekte"})

    orgs = set()
    df["Organisation"].dropna().apply(lambda x: [orgs.add(o.strip()) for o in str(x).split(",")])
    content = "# All Organisations\n\n" + "\n".join(f"- [[{sanitize_func(o)}]]" for o in sorted(list(orgs)))
    with open("Vault/_Organisationen.md", "w", encoding="utf-8") as f:
        f.write(content)
    index_files_info.append({"type": "Organisations", "filename": "_Organisationen"})

    arten = set()
    df["Art"].dropna().apply(lambda x: [arten.add(v) for v in _parse_dict(x).values()])
    content = "# All Arten\n\n" + "\n".join(f"- [[{sanitize_func(a)}]]" for a in sorted(list(arten)))
    with open("Vault/_Arten.md", "w", encoding="utf-8") as f:
        f.write(content)
    index_files_info.append({"type": "Arten", "filename": "_Arten"})

    einsatz = set()
    df["Einsatzbereich"].dropna().apply(lambda x: [einsatz.add(v) for v in _parse_dict(x).values()])
    content = "# All Einsatzbereiche\n\n" + "\n".join(f"- [[{sanitize_func(e)}]]" for e in sorted(list(einsatz)))
    with open("Vault/_Einsatzbereiche.md", "w", encoding="utf-8") as f:
        f.write(content)
    index_files_info.append({"type": "Einsatzbereiche", "filename": "_Einsatzbereiche"})

    print("Finished creating index files.")
    return index_files_info


# %%
def main(type, data_file_path, link_fields=None, website_data=None):
    """
    Runs the markdown creation process for a specific entity type.

    Args:
        type (str): The type of entity to process (e.g., 'Projekt').
        data_file_path (str): The path to the source CSV file.
        link_fields (list, optional): A list of fields to format as links. Defaults to None.
        website_data (dict, optional): A dictionary of organization websites. Defaults to None.
    """
    if not os.path.exists(data_file_path):
        print(f"Error: The path '{data_file_path}' does not exist.")
        return

    print(f"\n----- Processing type: {type} -----")
    creator = MarkdownCreatorProjects(
        type=type, data_file_path=data_file_path, link_fields=link_fields, website_data=website_data
    )
    creator.create_multiple_files()


if __name__ == "__main__":
    csv_file = "data/csv/combined_projects_with_term_dictionaries.csv"
    websites_file = "OrganizationLinkFinder/organization_websites.json"

    website_data = load_website_data(websites_file)

    main(
        type="Projekt",
        data_file_path=csv_file,
        link_fields=["Organisation"],
    )

    main(type="Organisation", data_file_path=csv_file, website_data=website_data)
    main(type="Art", data_file_path=csv_file)
    main(type="Einsatzbereich", data_file_path=csv_file)

    temp_creator = MarkdownCreatorProjects(type=None, data_file_path=None)
    index_files = create_index_files(csv_file, temp_creator._sanitize_filename)

    create_homepage(index_files)

# %%
