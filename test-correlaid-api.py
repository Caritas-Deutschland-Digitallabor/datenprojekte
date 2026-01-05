import requests
import json

# Configuration
BASE_URL = "https://cms.correlaid.org/graphql"

# Your GraphQL Query
query = """
query ProjectOverview {
    Projects(limit: -1) {
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
            Blog_Posts_id {
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
        Projects_Outputs {
            url
            output_type
            is_public
        }
        Organizations {
            Organizations_id {
                sector
                translations {
                    languages_code {
                        code
                    }
                    name
                }
            }
        }
        translations {
            title
            teaser
            languages_code {
                code
            }
        }
        Local_Chapters {
            Local_Chapters_id {
                short_id
                translations {
                    city
                    languages_code {
                        code
                    }
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
    # Example: print the title of the first project
    print(json.dumps(projects[0], indent=2))