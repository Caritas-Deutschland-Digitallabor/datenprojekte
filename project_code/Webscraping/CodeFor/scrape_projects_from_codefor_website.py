import requests
import pandas as pd
from datetime import date
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


def get_fully_rendered_soup(url: str) -> BeautifulSoup:
	"""
	Retrieves a fully rendered BeautifulSoup object from a given URL using Selenium.

	Args:
		url (str): The URL to retrieve.

	Returns:
		BeautifulSoup: A fully rendered BeautifulSoup object.
	"""

	options = Options()
	options.add_argument("--headless")
	options.add_argument("--no-sandbox")
	options.add_argument("--disable-dev-shm-usage")

	driver = webdriver.Chrome(
		service=Service(ChromeDriverManager().install()),
		options=options
	)
	driver.get(url)

	# Wait until at least 280 cards are in the DOM (buffer below 288 to be safe)
	WebDriverWait(driver, 20).until(
		lambda d: len(d.find_elements(By.CLASS_NAME, "project-preview-card")) >= 280
	)

	soup = BeautifulSoup(driver.page_source, "html.parser")
	driver.quit()
	return soup

def collect_project_organizations(project_data: BeautifulSoup) -> str:
        """
		Collects project organizations from the scraped website data of an individual project.

		Args:
			project_data (BeautifulSoup): The BeautifulSoup object containing the data of an individual project.

		Returns:
			str: A string containing one or two project organizations.
		"""
        code_for_lab = project_data.find("a", class_="text-danger no-underline lab-link").text

        if code_for_lab:
            project_organizations = code_for_lab+ ", Code for Germany"
        else:
            project_organizations = "Code for Germany"
        
        return project_organizations

def map_project_status(project_status: str) -> str:
	"""
	Maps project status to a human-readable, unified project status string.

	Args:
		project_status (str): The project status string.

	Returns:
		str: The mapped, unified project status string.
	"""

	# Ensure we are working with a string and handle None
	if not project_status:
		return "Unbekannt"
		
	status_in_betrieb = ['abgeschlossen', 'fertig', 'finished', 'done', 'prototyp', "betrieb", "released"]
	status_in_planung = ["laufend", "in progress", "sucht", "in arbeit", "active", "entwicklung"]
	status_eingestellt = ["discontinued", "festgefahren", "dead"]

	# Normalize input
	val = str(project_status).lower().strip()
	words = val.split()

	# 1. Check for exact full-string matches (handles "in progress")
	# 2. Check if any individual word matches a keyword
	if val in status_in_betrieb or any(word in status_in_betrieb for word in words):
		return "In Betrieb"

	if val in status_in_planung or any(word in status_in_planung for word in words):
		return "In Planung"

	if val in status_eingestellt or any(word in status_eingestellt for word in words):
		return "Eingestellt"

	return "Unbekannt"

def collect_project_data_as_dataframe(scraped_data: BeautifulSoup) -> pd.DataFrame:
	"""Collects project data from the scraped website data and returns it as a DataFrame.

	Args:
		scraped_data (BeautifulSoup): The BeautifulSoup object containing the data from the website.

	Returns:
		pd.DataFrame: A DataFrame containing the collected project data.
	"""
	projects_soups = scraped_data.find_all('div', class_="card border-dark h-100 project-preview-card")

	projects_df=pd.DataFrame()

	for project in projects_soups: 
		quelle = project.find('a', class_="text-dark no-underline project-link").get('href')
		title = project.find("h3", class_="title").text
		project_summary = project.find("div", class_="text-dark description").text
		project_organizations = collect_project_organizations(project)
		project_status = project.find("span", class_="text-right status").text


		# Collect data in a DataFrame
		data = {
			"Index": "",
			"Quelle": quelle,
			"Projektname": title,
			"Webseite-Link": quelle,
			"Organisation": project_organizations,
			"Status": map_project_status(project_status),
			"Kurzzusammenfassung": project_summary,
			"Lizenz": "CC-BY 4.0",
			"Lizenz-Organisation": "https://codefor.de"
		}
		df = pd.DataFrame(data, index=[0])
		projects_df = pd.concat([projects_df, df], ignore_index=True)
            
	projects_df["Index"] = projects_df.index

	return projects_df

def scrape_codefor(
		url: str,
		save_to_csv: bool = False
	) -> pd.DataFrame:
	"""
	Scrapes project data from the Code For Germany website and returns it as a DataFrame.

	Args:
		url (str): The URL of the Code For Germany website.
		save_to_csv (bool, optional): Whether to save the data to a CSV file. Default is False.

	Returns:
		pd.DataFrame: A DataFrame containing the scraped project data.
	"""
	
	scraped_codefor_data = get_fully_rendered_soup("https://codefor.de/projekte/alle/")

	codefor_projects = collect_project_data_as_dataframe(scraped_codefor_data)
      	
	if codefor_projects is not None:
		print(f"Successfully retrieved {len(codefor_projects)} projects from the Code For Germany website.")

		if save_to_csv:
			# Optionally, save the DataFrame to a CSV file with today's date
			today = str(date.today())
			codefor_projects.to_csv(f"project_code/Webscraping/CodeFor/{today}_CodeFor-Projekte-via-Scraping.csv", index=False)

	else:
		print("Failed to retrieve projects from the Code For Germany website. The returned data is None.")

	return codefor_projects



if __name__ == "__main__":
	scrape_codefor(
		url="https://codefor.de/projekte/alle/",
		save_to_csv=True
	)