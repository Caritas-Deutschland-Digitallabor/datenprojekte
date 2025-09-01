# %%
import pandas as pd
import os
import re
import ast
import json
from fuzzywuzzy import process


# %%
class MarkdownCreatorProjects:
    """
    Creates a set of markdown files from a structured CSV data source.

    This class handles the entire process of reading a CSV file, parsing its rows,
    populating markdown templates, and saving the final .md files into a
    structured vault directory. It is designed to create interconnected notes
    for use in knowledge management tools like Obsidian.
    """

    def __init__(
        self,
        type,
        data_file_path,
        name=None,
        column_mapping=None,
        link_fields=None,
        website_data=None,
        website_json_list=None,
        alt_to_main_org_map=None,
    ):
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
            website_json_list (list, optional): The full list of dictionaries from the
                                                organization websites JSON file.
            alt_to_main_org_map (dict, optional): A dictionary mapping alternative organization names to their main name.
        """
        self.type = type
        self.data_file_path = data_file_path
        self.name = name
        self.column_mapping = column_mapping or {}
        self.link_fields = link_fields or []
        self.website_data = website_data or {}
        self.website_json_list = website_json_list
        self.alt_to_main_org_map = alt_to_main_org_map or {}
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
        Replaces problematic characters with spaces and keeps the text readable.
        """
        name_str = str(name)

        # Replace problematic characters with spaces
        problematic_chars = '!?*/\\<>:"|'
        for char in problematic_chars:
            name_str = name_str.replace(char, " ")

        # Clean up multiple consecutive spaces and strip
        while "  " in name_str:
            name_str = name_str.replace("  ", " ")

        return name_str.strip()

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

            ober_to_unter, unmapped_terms = self._process_terms_dict(parsed_dict)
            final_string = self._format_terms_output(ober_to_unter, unmapped_terms)

            if not final_string:
                return content.replace(f"- {placeholder}", "")

            return content.replace(f"- {placeholder}", final_string)

        SINGLE_VALUE_FIELDS = {
            "Projektname",
            "Status",
            "Kurzzusammenfassung",
            "Lizenz",
            "Lizenz-Organisation",
            "Quelle",
            "Webseite-Link",
            "Projekt-Abkürzung",
            "Alternativer Name",
            "title",
            "cluster_name",
            "website",
        }

        if placeholder_name in SINGLE_VALUE_FIELDS:
            value_str = "" if pd.isna(value) else str(value)
            return content.replace(placeholder, value_str)

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
                        list_items = "\n".join(
                            f"- [[Organisation/{self._sanitize_filename(self.alt_to_main_org_map.get(item, item))}]]"
                            for item in parsed_value
                        )
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

    def _process_terms_dict(self, parsed_dict):
        """Separates a dictionary of terms into mapped and unmapped groups."""
        ober_to_unter = {}
        unmapped_terms = []
        for unter, ober in parsed_dict.items():
            ober = str(ober).strip()
            unter = str(unter).strip()
            if not unter:
                continue

            if not ober:  # Unmapped term
                unmapped_terms.append(unter)
            else:  # Mapped term
                if ober not in ober_to_unter:
                    ober_to_unter[ober] = []
                ober_to_unter[ober].append(unter)
        return ober_to_unter, unmapped_terms

    def _format_terms_output(self, ober_to_unter, unmapped_terms):
        """Formats the mapped and unmapped terms into markdown bullet points."""
        output_lines = []

        # Mapped terms with categories
        for ober, unters in sorted(ober_to_unter.items()):
            ober_filename = self._sanitize_filename(ober)
            unter_hashtags = [f"#{u.replace(' ', '-')}" for u in sorted(unters)]
            output_lines.append(f"- [[{ober_filename}]]: {', '.join(unter_hashtags)}")

        # Unmapped terms as individual hashtag bullet points
        if unmapped_terms:
            unmapped_lines = [f"- #{u.replace(' ', '-')}" for u in sorted(unmapped_terms)]
            output_lines.extend(unmapped_lines)

        if not output_lines:
            return ""

        return "\n".join(output_lines)

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

        else:  # type == "Organisation"
            website_names = list(self.website_data.keys())

            # Update website_json_list with new orgs from the CSV
            all_known_orgs = set(website_names)
            for item in self.website_json_list:
                all_known_orgs.update(item.get("alternative_names", []))

            for entity_name in sorted(list(unique_entities)):
                if entity_name in all_known_orgs:
                    continue

                # New entity found, try to match it against existing main organization names
                best_match, score = process.extractOne(entity_name, website_names) if website_names else (None, 0)

                if score > 90:
                    prompt = (
                        f"\nMATCH FOUND (Score: {score})\n"
                        f"  - From CSV:  '{entity_name}'\n"
                        f"  - From JSON: '{best_match}'\n"
                        f"Do these refer to the same organization? (y/n): "
                    )
                    answer = input(prompt).lower().strip()
                    if answer == "y":
                        print(f"--> Accepted. '{entity_name}' will be treated as an alternative for '{best_match}'.")
                        for item in self.website_json_list:
                            if item["organization"] == best_match:
                                item.setdefault("alternative_names", []).append(entity_name)
                                break
                        all_known_orgs.add(entity_name)
                        continue  # Move to the next unique entity

                # If score is not high enough, or if the user rejects the match
                print(f"--> No close match for '{entity_name}' or match rejected. Adding as a new organization.")
                new_entry = {"organization": entity_name, "website": None, "method": "added_from_csv"}
                self.website_json_list.append(new_entry)
                # Update local dicts for the current run
                self.website_data[entity_name] = None
                website_names.append(entity_name)
                all_known_orgs.add(entity_name)

            # Create markdown files for all main organizations that appeared in this CSV
            created_files = []
            alt_to_main_map = {
                alt: item["organization"]
                for item in self.website_json_list
                for alt in item.get("alternative_names", [])
            }

            main_orgs_in_csv = set()
            for entity in unique_entities:
                main_org = alt_to_main_map.get(entity, entity)
                if main_org in self.website_data:
                    main_orgs_in_csv.add(main_org)

            for entity_name in sorted(list(main_orgs_in_csv)):
                filename = self._sanitize_filename(entity_name)
                if not filename:
                    continue

                row_data_dict = {"title": entity_name, "website": self.website_data.get(entity_name)}
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

        content_to_save = self.content
        moc_map = {
            "Projekt": "[[@Alle Projekte]]",
            "Organisation": "[[@Alle Organisationen]]",
            "Art": "[[@Alle Arten]]",
            "Einsatzbereich": "[[@Alle Einsatzbereiche]]",
        }
        if self.type in moc_map:
            backlink = f"\nZurück zu: {moc_map[self.type]}"
            content_to_save += backlink

        try:
            with open(f"{dir_path}/{self.name}.md", "w", encoding="utf-8") as f:
                f.write(content_to_save)
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


def load_website_json(json_path):
    """
    Loads the full JSON data for organization websites.

    Args:
        json_path (str): The path to the JSON file.

    Returns:
        list: A list of dictionaries from the JSON file.
    """
    if not os.path.exists(json_path):
        print(f"Website data file not found: {json_path}")
        return []
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_website_json(json_path, data):
    """
    Saves the organization website data back to the JSON file.

    Args:
        json_path (str): The path to the JSON file to save.
        data (list): The list of dictionaries to save.
    """
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nUpdated and saved website data to {json_path}")


def create_index_files():
    """Creates empty master list files (MOCs) to act as hubs for backlinks."""
    print("Creating empty index files (MOCs)...")

    moc_content = {
        "Projekt/@Alle Projekte.md": "# Nutze die Links, um auf die jeweiligen Seiten zu gelangen.",
        "Organisation/@Alle Organisationen.md": "# Nutze die Links, um auf die jeweiligen Seiten zu gelangen.",
        "Art/@Alle Arten.md": "# Nutze die Links, um auf die jeweiligen Seiten zu gelangen.",
        "Einsatzbereich/@Alle Einsatzbereiche.md": "# Nutze die Links, um auf die jeweiligen Seiten zu gelangen.",
    }

    for filename, content in moc_content.items():
        dir_path = os.path.dirname(f"Vault/{filename}")
        os.makedirs(dir_path, exist_ok=True)
        with open(f"Vault/{filename}", "w", encoding="utf-8") as f:
            f.write(content)

    print("Finished creating index files.")


# %%
def main(type, data_file_path, link_fields=None, website_data=None, website_json_list=None, alt_to_main_org_map=None):
    """
    Runs the markdown creation process for a specific entity type.

    Args:
        type (str): The type of entity to process (e.g., 'Projekt').
        data_file_path (str): The path to the source CSV file.
        link_fields (list, optional): A list of fields to format as links. Defaults to None.
        website_data (dict, optional): A dictionary of organization websites. Defaults to None.
        website_json_list (list, optional): The full list of dictionaries from the JSON file.
        alt_to_main_org_map (dict, optional): A mapping of alternative to main organization names.
    """
    if not os.path.exists(data_file_path):
        print(f"Error: The path '{data_file_path}' does not exist.")
        return

    print(f"\n----- Processing type: {type} -----")
    creator = MarkdownCreatorProjects(
        type=type,
        data_file_path=data_file_path,
        link_fields=link_fields,
        website_data=website_data,
        website_json_list=website_json_list,
        alt_to_main_org_map=alt_to_main_org_map,
    )
    creator.create_multiple_files()


if __name__ == "__main__":
    csv_file = "data/csv/combined_projects_with_term_dictionaries.csv"
    websites_file = "OrganizationLinkFinder/organization_websites.json"

    website_json_list = load_website_json(websites_file)
    website_data = {item["organization"]: item["website"] for item in website_json_list if item.get("website")}

    main(type="Organisation", data_file_path=csv_file, website_data=website_data, website_json_list=website_json_list)

    alt_to_main_org_map = {}
    for item in website_json_list:
        if "alternative_names" in item:
            for alt_name in item["alternative_names"]:
                alt_to_main_org_map[alt_name] = item["organization"]

    main(
        type="Projekt",
        data_file_path=csv_file,
        link_fields=["Organisation"],
        alt_to_main_org_map=alt_to_main_org_map,
    )

    main(type="Art", data_file_path=csv_file)
    main(type="Einsatzbereich", data_file_path=csv_file)

    create_index_files()

    save_website_json(websites_file, website_json_list)

# %%
