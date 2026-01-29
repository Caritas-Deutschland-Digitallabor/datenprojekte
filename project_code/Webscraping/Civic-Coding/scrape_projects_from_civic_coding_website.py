import requests
import pandas as pd
from datetime import date
from bs4 import BeautifulSoup
from project_code.Webscraping.utils import scrape_html_website


def clean_string(raw_string: str) -> str:
    """
    Clean a string by removing leading and trailing whitespace and single quotes.

    Args:
        raw_string (str): The string to be cleaned.

    Returns:
        str: The cleaned string.
    """

    clean_string = " ".join(raw_string.split()).strip("'")
    return clean_string

def get_correct_project_url(project_soup: BeautifulSoup) -> str:
	"""
	Get the correct project URL from a BeautifulSoup object.

	Args:
		project_soup (BeautifulSoup): The BeautifulSoup object containing the project data.

	Returns:
		str: The correct project URL.
	"""
	if project_soup.find('a', class_="position-absolute top-0 bottom-0 start-0 end-0 z-1 projectidea-link"):
		project_url_final_part = project_soup.find('a', class_="position-absolute top-0 bottom-0 start-0 end-0 z-1 projectidea-link").get('href')
		project_url = "https://www.civic-coding.de" + project_url_final_part

	else:
		project_url = project_soup.find('div', class_="link").find('a').get('href')

	return project_url

def collect_project_data_as_dataframe() -> pd.DataFrame:
	"""Collects project data from the Civic Coding website data and returns it as a DataFrame.

	Returns:
		pd.DataFrame: A DataFrame containing the collected project data.
	"""
	projects_df=pd.DataFrame()

	max_pages_to_scrape = 50 # increase this number in case you want to scrape more project pages
	
	for page_number in range(1,max_pages_to_scrape):
		url = f"https://www.civic-coding.de/community-information/projekte?tx_solr%5Bpage%5D={page_number}"
		print("Scraping content from: " + url)

		scraped_civic_coding_data = scrape_html_website(url)

		projects_soups = scraped_civic_coding_data.find_all('div', class_='projects-list--content')

		if not projects_soups:
			break # Break the loop if no projects are found (this means all project pages have already been scraped)

		for project in projects_soups: 
			title = project.find("h3", class_="projects-headline h5").text
			project_summary = project.find("div", class_="projects-text mb-5").text

			# Collect data in a DataFrame
			data = {
				"Index": "",
				"Quelle": get_correct_project_url(project),
				"Projektname": clean_string(title),
				"Webseite-Link": get_correct_project_url(project),
				"Organisation": "Civic Coding",
				"Status": "Unbekannt",
				"Kurzzusammenfassung": clean_string(project_summary),
				"Lizenz": "CC-BY-NC-ND 4.0",
				"Lizenz-Organisation": "https://www.civic-coding.de"
			}
			df = pd.DataFrame(data, index=[0])
			projects_df = pd.concat([projects_df, df], ignore_index=True)
			
		projects_df["Index"] = projects_df.index

	return projects_df

def scrape_civic_coding(
		save_to_csv: bool = False
	) -> pd.DataFrame:
	"""
	Scrapes project data from the Civic Coding website and returns it as a DataFrame.

	Args:
		save_to_csv (bool, optional): Whether to save the data to a CSV file. Default is False.

	Returns:
		pd.DataFrame: A DataFrame containing the scraped project data.
	"""
	
	civic_coding_projects = collect_project_data_as_dataframe()
      	
	if civic_coding_projects is not None:
		print(f"Successfully retrieved {len(civic_coding_projects)} projects from the Civic Coding website.")

		if save_to_csv:
			# Optionally, save the DataFrame to a CSV file with today's date
			today = str(date.today())
			civic_coding_projects.to_csv(f"project_code/Webscraping/Civic_Coding/{today}_Civic-Coding-Projekte-via-Scraping.csv", index=False)

	else:
		print("Failed to retrieve projects from the Civic Coding website. The returned data is None.")

	return civic_coding_projects



if __name__ == "__main__":
	scrape_civic_coding(
		save_to_csv=True
	)