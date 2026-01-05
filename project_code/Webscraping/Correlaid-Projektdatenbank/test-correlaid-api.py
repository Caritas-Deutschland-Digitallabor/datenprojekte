import pandas as pd
import requests
import json

# Configuration
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

def fetch_project_overview():
    try:
        # Directus GraphQL is usually a POST request to the /graphql endpoint
        response = requests.post(
            BASE_URL,
            json={'query': query},
            timeout=10
        )
        
        # Check for HTTP errors
        response.raise_for_status()
        
        data = response.json()
        
        if 'errors' in data:
            print("GraphQL Errors:", data['errors'])
            return None
            
        return data['data']['Projects']

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

# Execute
projects = fetch_project_overview()

if projects:
    print(f"Successfully retrieved {len(projects)} projects.")
    
    df = pd.json_normalize(projects)
    print(df)
    print(df.iloc[0])