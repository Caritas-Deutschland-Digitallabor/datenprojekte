import requests
import pandas as pd
from datetime import date
from bs4 import BeautifulSoup

def scrape_citylab_projects_website(url: str) -> BeautifulSoup:
	"""Scrapes data from the CityLAB Berlin project website and returns it as a BeautifulSoup object.

	Args:
		url (str): The URL of the website.

	Returns:
		BeautifulSoup: A BeautifulSoup object containing the data from the website.
	"""
	response = requests.get(url)
	soup = BeautifulSoup(response.text, 'html.parser')

	return soup

def assign_project_status(chunk: int) -> str:
    """Assigns a project status based on the chunk number, as the first chunk on the website shows running projects, the second chunk shows completed projects.

	Args:
		chunk (int): The chunk number.

	Returns:
		str: A uniform project status.
	"""
    if chunk == 0:
        return "In Planung"
    else:
        return "In Betrieb"

def collect_project_categories(project_data: BeautifulSoup) -> str:
	"""Collects project categories from the scraped website data of an individual project.

	Args:
		project_data (BeautifulSoup): The BeautifulSoup object containing the data of an individual project.

	Returns:
		str: A string containing the project categories, separated by commas.
	"""
	category_texts = []
	categories = project_data.find('div', class_="wpgb-block-2").find_all("a")
	for category in categories:
		category_text = category.text
		category_texts.append(category_text)

	list_as_string = ', '.join(category_texts)

	return list_as_string

def collect_project_data_as_dataframe(scraped_data: BeautifulSoup) -> pd.DataFrame:
	"""Collects project data from the scraped website data and returns it as a DataFrame.

	Args:
		scraped_data (BeautifulSoup): The BeautifulSoup object containing the data from the website.

	Returns:
		pd.DataFrame: A DataFrame containing the collected project data.
	"""
	project_chunks = scraped_data.find_all('div', class_='wpgb-masonry')
	projects_df=pd.DataFrame()

	for chunk in range(len(project_chunks)):
		for project in project_chunks[chunk].find_all('article'): 
			quelle = project.find('a', class_="wpgb-card-layer-link").get('href')
			title = project.find("h3", class_="wpgb-block-3 wpgb-idle-scheme-1").text
			project_summary = project.find(class_="wpgb-block-6 wpgb-idle-scheme-2").text

			project_categories = collect_project_categories(project)

			# Collect data in a DataFrame
			data = {
				"Index": "",
				"Quelle": quelle,
				"Projektname": title,
				"Einsatzbereich": f"{project_categories}",
				"Webseite-Link": quelle,
				"Organisation": "CityLAB Berlin",
				"Status": assign_project_status(chunk),
				"Kurzzusammenfassung": project_summary,
				"Lizenz": "CC BY-NC-SA",
				"Lizenz-Organisation": "https://citylab-berlin.org"
			}
			df = pd.DataFrame(data, index=[0])
			projects_df = pd.concat([projects_df, df], ignore_index=True)

	projects_df["Index"] = projects_df.index

	return projects_df

def scrape_citylab_berlin(
		url: str,
		save_to_csv: bool = False
	) -> pd.DataFrame:
	scraped_citylab_berlin_data = scrape_citylab_projects_website(url)

	citylab_berlin_projects = collect_project_data_as_dataframe(scraped_citylab_berlin_data)
	
	if citylab_berlin_projects is not None:
		print(f"Successfully retrieved {len(citylab_berlin_projects)} projects from the CityLAB Berlin website.")

		if save_to_csv:
			# Optionally, save the DataFrame to a CSV file with today's date
			today = str(date.today())
			citylab_berlin_projects.to_csv(f"project_code/Webscraping/Citylab_Berlin/{today}_CityLAB-Berlin-Projekte-via-Scraping.csv", index=False)

	else:
		print("Failed to retrieve projects from the CityLAB Berlin website. The returned data is None.")

	return citylab_berlin_projects



if __name__ == "__main__":
	scrape_citylab_berlin(
		url="https://citylab-berlin.org/de/projects/",
		save_to_csv=False
	)