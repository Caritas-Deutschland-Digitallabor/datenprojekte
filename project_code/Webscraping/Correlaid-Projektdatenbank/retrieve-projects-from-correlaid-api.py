import pandas as pd
import requests
import json

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
	query ProjectOverview($language: String = "de-DE", $status: [String] = ["published"]) {
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

if __name__ == "__main__":
	correlaid_projects = fetch_project_overview_from_correlaid_api()

	if correlaid_projects is not None:
		print(f"Successfully retrieved {len(correlaid_projects)} projects from the Correlaid API.")

		# TODO: Put here the code for further data processing from the Jupyter notebook.

	else:
		print("Failed to retrieve projects from the Correlaid API. The returned data is None, even though the API request was successful.")