import pandas as pd
import requests
import json
from datetime import date

def fetch_project_overview_from_correlaid_api() -> list:
	"""
	Fetches project data from the Correlaid API and returns it as a list of dictionaries.

	Returns:
		list: A list of dictionaries containing project data.
	"""
    
	# Configuration Directus API
	BASE_URL = "https://cms.correlaid.org/graphql"

	# Your GraphQL Query
	query = """
	query ProjectOverview($language: String = "de", $status: [String] = ["published_anon", "published"]) {
		Projects(limit: -1, filter: { status: { _in: $status }  } ) {
			status
			project_id
			project_status
			is_internal
			end_date_predicted
			end_date
			project_types
			data_types
			Podcast {
				language
				soundcloud_link
				title
			}
			Blog_Posts {
				Blog_Posts_id(filter: { status: { _in: $status } }) {
					id
					translations {
						languages_code {
							code
						}
						title
						slug
					}
				}
			}
			Projects_Outputs(filter: { is_public: { _eq: true } }) {
				url
				output_type
			}
			Organizations {
				Organizations_id {
					sector
					translations(filter: { languages_code: { code: { _eq: $language } } }) {
						languages_code {
							code
						}
						name
					}
				}
			}
			translations(filter: { languages_code: { code: { _eq: $language } } }) {
				title
				teaser
			}
			Local_Chapters {
				Local_Chapters_id (filter: { status: { _in: $status } }){
					short_id
					translations(filter: { languages_code: { code: { _eq: $language } } }) {
						city
					}
				}
			}
		}
	}
	"""
	
	try:
		response = requests.post(
            BASE_URL,
            json={'query': query},
            timeout=10
        )
        
        # Check for HTTP errors
		response.raise_for_status()
		data = response.json()

		# Check for GraphQL errors
		if 'errors' in data:
			print("The following errors occurred in the GraphQL response:", data['errors'])
			return None
		
		return data['data']['Projects']
	
	# Handle exceptions
	except requests.exceptions.RequestException as e:
		print(f"An error occurred: {e}")
		return None

def convert_project_status(status: str) -> str:
	"""
	Converts the returned Correlaid project status string to a project status string expected for the Obsidian project.

	Args:
		status (str): The project status string from the Correlaid API.

	Returns:
		str: The desired project status string.
	"""

	if status == "finished":
		return "In Betrieb"
	elif status == "project_work":
		return "In Planung"
	else:   
		return status
	
def collect_organisation_names(orga_information: list) -> str:
	"""
	Collects the names of the organizations involved in a project.

	Args:
		orga_information (list): A list of dictionaries containing the organization information.

	Returns:
		str: A string containing only the names of the organizations, separated by commas.
	"""
    
	organisation_names = [orga["Organizations_id"]["translations"][0]["name"] for orga in orga_information]
    
	# Add CorrelAid e.V. if not already in the list (as all projects are part of CorrelAid e.V.)
	if "CorrelAid e.V." not in organisation_names:
		organisation_names.append("CorrelAid e.V.")

	# Convert list organisation_names to string without the square brackets
	organisation_names = ", ".join(organisation_names)

	return organisation_names

def collect_project_result_websites(project_outputs: list) -> str:
	"""
	Collects the URLs of the project outputs.

	Args:
		project_outputs (list): A list of dictionaries containing the project output information.

	Returns:
		str: A string containing only the URLs of the project outputs, separated by commas.
	"""

	project_result_websites = [output["url"] for output in project_outputs]

	# Convert list to string without the square brackets
	project_result_websites = ", ".join(project_result_websites)

	return project_result_websites

def preprocess_json_to_expected_df(
		projects_json_data: list,
		expected_column_names: list = ["Index", "Quelle", "Projektname", "Art", "Einsatzbereich", "Webseite-Link", "Organisation", "Status", "Kurzzusammenfassung", "Projekt-Abkürzung", "Lizenz", "Lizenz-Organisation"] ) -> pd.DataFrame:
	"""
	Preprocesses the JSON project data from the Correlaid API to a DataFrame with the expected column names for further processing with other scraped information.

	Args:
		projects_json_data (list): A list of dictionaries containing the project data.

	Returns:
		pd.DataFrame: A DataFrame with the expected column names for further processing with other scraped information.
	"""

	# Convert the list of dictionaries to a DataFrame
	projects_df = pd.json_normalize(projects_json_data)

	# Add new, expected columns to the DataFrame
	projects_df["Index"] = projects_df.index
	projects_df["Quelle"] = projects_df["project_id"].apply(lambda x: f"https://correlaid.org/daten-nutzen/projektdatenbank/{x}")
	projects_df["Projektname"] = projects_df["translations"].apply(lambda x: x[0]["title"])
	projects_df["Art"] = projects_df["project_types"]
	projects_df["Einsatzbereich"] = projects_df["data_types"]
	projects_df["Webseite-Link"] = projects_df["Projects_Outputs"].apply(lambda x: collect_project_result_websites(x))
	projects_df["Organisation"] = projects_df["Organizations"].apply(lambda x: collect_organisation_names(x))
	projects_df["Status"] = projects_df["project_status"].apply(lambda x: convert_project_status(x))
	projects_df["Kurzzusammenfassung"] = projects_df["translations"].apply(lambda x: x[0]["teaser"])
	projects_df["Projekt-Abkürzung"] = pd.NA
	projects_df["Lizenz"] = "CC-BY 4.0" # we assume all projects are CC-BY 4.0
	projects_df["Lizenz-Organisation"] = "https://correlaid.org/" # mentioning here the homepage of Correlaid

	# Drop all unneeded columns
	projects_df = projects_df[expected_column_names]

	return projects_df

if __name__ == "__main__":
	correlaid_projects = fetch_project_overview_from_correlaid_api()

	if correlaid_projects is not None:
		print(f"Successfully retrieved {len(correlaid_projects)} projects from the Correlaid API.")

		projects_df = preprocess_json_to_expected_df(correlaid_projects)
	
		# Optionally, save the DataFrame to a CSV file with today's date
		# today = str(date.today())
		# projects_df.to_csv(f"{today}_Correlaid-Projekte-via-API.csv", index=False)

	else:
		print("Failed to retrieve projects from the Correlaid API. The returned data is None, even though the API request was successful.")