import re
import requests
import pandas as pd
from datetime import date

def extract_project_website(value: str) -> str | None:
    """
    Extracts the website URL from a JSON string.

    Args:
        value (str): The JSON string to extract the website URL from.

    Returns:
        str | None: The extracted website URL, or None if not found.
    """
    try:
        match = re.search(r"'src': '([^']+)'", str(value))
        return match.group(1) if match else None
    except Exception:
        return None

def preprocess_api_response_to_projects_dataframe(raw_json_data: dict) -> pd.DataFrame:
    """
    Preprocesses raw JSON data form the Civic Coding Map API and converts it to a DataFrame in the expected format.

    Args:
        raw_json_data (dict): The raw JSON data to preprocess.

    Returns:
        dict: The preprocessed projects data.
    """
	
    # Convert the JSON response to a DataFrame
    df = pd.DataFrame(raw_json_data)
		
    # Preprocess the DataFrame
    df.insert(0, "Index", range(len(df)))
    df.rename(columns={
        "title": "Projektname",
    }, inplace=True)
    df["Kurzzusammenfassung"] = df["content"].apply(lambda x: str(x).strip("[']"))
    df['Quelle'] = df['links'].apply(extract_project_website)
    df["Webseite-Link"] = df["Quelle"]
    df["Organisation"] = "Civic Coding"
    df["Status"] = "Unbekannt"
    df["Lizenz"] = "CC-BY-NC-ND 4.0"
    df["Lizenz-Organisation"] = "https://www.civic-coding.de"

    # Select relevant columns
    final_df = df[["Index", "Quelle", "Projektname", "Webseite-Link", "Organisation", "Status", "Kurzzusammenfassung", "Lizenz", "Lizenz-Organisation"]]

    return final_df

def fetch_projektlandkarte_projects_via_map_api(number_of_projects: int = 200) -> pd.DataFrame:
    """
    Fetches all Projektlandkarte projects from Civic Coding using the Civic Coding Map API.

    Returns:
        pd.DataFrame: A pandas DataFrame containing the fetched data.
    """
	
    # The target URL
    url = 'https://www.civic-coding.de/mapapi/detail'

    # Query parameters extracted from the URL
    cms_project_ids = ",".join(str(i) for i in range(0, number_of_projects + 1))
    params = {
        'cms_ids': cms_project_ids
    }

    # Browser-like headers
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Referer': 'https://www.civic-coding.de/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-GPC': '1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Brave";v="144"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        
        # Check if the request was successful
        response.raise_for_status()

        # Process the response
        final_df = preprocess_api_response_to_projects_dataframe(response.json())

        return final_df
        
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None
    
def source_civic_coding_projektlandkarte_projects(
		save_to_csv: bool = False
	) -> pd.DataFrame:
	"""
	Fetches project data from the Civic Coding Projektlandkarte via the Civic Coding Map API and returns the community projects as a DataFrame.

	Args:
		save_to_csv (bool, optional): Whether to save the data to a CSV file. Default is False.

	Returns:
		pd.DataFrame: A DataFrame containing the fetched project data.
	"""
	
	civic_coding_projektlandkarte_projects = fetch_projektlandkarte_projects_via_map_api()
      	
	if civic_coding_projektlandkarte_projects is not None:
		print(f"Successfully retrieved {len(civic_coding_projektlandkarte_projects)} projects from the Civic Coding Map API.")

		if save_to_csv:
			# Optionally, save the DataFrame to a CSV file with today's date
			today = str(date.today())
			civic_coding_projektlandkarte_projects.to_csv(f"project_code/Webscraping/Civic_Coding/{today}_Civic-Coding-Projektlandkarte-Projekte-via-Map-API.csv", index=False)

	else:
		print("Failed to retrieve projects from the Civic Coding Map API. The returned data is None.")

	return civic_coding_projektlandkarte_projects


if __name__ == "__main__":
	source_civic_coding_projektlandkarte_projects(
		save_to_csv=True
	)