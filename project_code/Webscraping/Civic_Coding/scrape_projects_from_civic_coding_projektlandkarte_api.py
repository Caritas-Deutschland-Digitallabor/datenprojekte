import requests
import pandas as pd
from datetime import date


# # The target URL
# url = 'https://www.civic-coding.de/mapapi/detail'

# number_of_projects = 200
# cms_project_ids = ",".join(str(i) for i in range(0, number_of_projects + 1))


# # Query parameters extracted from the URL
# params = {
#     'cms_ids': cms_project_ids
# }

# # Browser-like headers
# headers = {
#     'Accept': '*/*',
#     'Accept-Language': 'en-US,en;q=0.8',
#     'Cache-Control': 'no-cache',
#     'Connection': 'keep-alive',
#     'Pragma': 'no-cache',
#     'Referer': 'https://www.civic-coding.de/',
#     'Sec-Fetch-Dest': 'empty',
#     'Sec-Fetch-Mode': 'cors',
#     'Sec-Fetch-Site': 'same-origin',
#     'Sec-GPC': '1',
#     'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
#     'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Brave";v="144"',
#     'sec-ch-ua-mobile': '?0',
#     'sec-ch-ua-platform': '"macOS"',
# }

# try:
#     response = requests.get(url, params=params, headers=headers)
    
#     # Check if the request was successful
#     response.raise_for_status()

#     # Convert the JSON response to a DataFrame
#     df = pd.DataFrame(response.json())

#     # Save the DataFrame to a CSV file
#     today = str(date.today())
#     df.to_csv(f"{today}_Civic_Coding-Projekte-via-Map-API.csv", index=False)
#     print("Data saved!")
    
# except requests.exceptions.RequestException as e:
#     print(f"An error occurred: {e}")


comparison_1_data = pd.read_csv("project_code/Webscraping/Civic_Coding/projektlandkarte_vs_community_projects_civic_coding.csv", usecols=["title","content","topic_label","topics", "similar_community_projects","Doppeltes Projekt?"])
comparison_2_data = pd.read_csv("project_code/Webscraping/Civic_Coding/2026-03-27_Civic-Coding-Projekte-via-Map-API_with_top3_matches_from_all_projects.csv", usecols=["title","content","topic_label","topics", "top3_matches"])

print(comparison_1_data)
print(comparison_2_data)

cols_present_in_both = ["title","content","topic_label","topics"]

merged_comparison_df = pd.merge(comparison_1_data, comparison_2_data, how="left", on=cols_present_in_both, suffixes=("_only_Civic_Coding_Community_Projects", "_all_data_without_Civic_Coding_Community_Projects"))

merged_comparison_df.to_csv("project_code/Webscraping/Civic_Coding/2026-03-27_Total_Comparison_Civic-Coding-Projekte-via-Map-API_with_other_projects.csv", index=False)