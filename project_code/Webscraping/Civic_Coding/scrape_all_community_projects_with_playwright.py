import os
import pandas as pd
from datetime import date
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from misc.scraping_utils import access_page_with_retry


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

def get_community_projects_with_playwright(username: str, password: str) -> pd.DataFrame:
    """
    Scrape all community projects from Civic Coding using Playwright.

    Args:
        username (str): The username for logging in.
        password (str): The password for logging in.

    Returns:
        pd.DataFrame: A pandas DataFrame containing the scraped data.
    """
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True) # Set headless=True for headless mode
        context = browser.new_context()
        page = context.new_page()

        # 1. Login Logic
        print("Logging in...")
        page = access_page_with_retry(page=page, url="https://www.civic-coding.de/anmelden")
        page.locator('#user').fill(username) 
        page.locator('#pass').fill(password)
        page.keyboard.press("Enter")
        
        # Wait for the login to process
        page.wait_for_load_state("networkidle")

        all_projects = []

        # 2. Scrape Loop
        for page_num in range(1, 100):
            url = f"https://www.civic-coding.de/community/projekte?tx_solr%5Bpage%5D={page_num}"
            print(f"Scraping Page {page_num} from Civic Coding Community Projects...")
            
            page.goto(url)

            # 3. HAND OVER TO BEAUTIFULSOUP
            # Get the full HTML from the browser
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            project_soups = soup.find_all('div', class_='projects-list--content')
            
            if not project_soups:
                break # Break the loop if no projects are found (this means all project pages have already been scraped)

            for project in project_soups:
                title = project.find("h3", class_="projects-headline h5").text
                summary = project.find("div", class_="projects-text mb-5").text

                all_projects.append({
                    "Index": "",
                    "Quelle": get_correct_project_url(project),
                    "Projektname": clean_string(title),
                    "Webseite-Link": get_correct_project_url(project),
                    "Organisation": "Civic Coding",
                    "Status": "Unbekannt",
                    "Kurzzusammenfassung": clean_string(summary),
                    "Lizenz": "CC-BY-NC-ND 4.0",
                    "Lizenz-Organisation": "https://www.civic-coding.de"
                })

        browser.close()

        projects_df = pd.DataFrame(all_projects)
        projects_df['Index'] = projects_df.index
        
        return projects_df
    
def scrape_civic_coding_community_projects(
		save_to_csv: bool = False
	) -> pd.DataFrame:
	"""
	Scrapes community project data from the Civic Coding website after logging in as Community member and returns the community projects as a DataFrame.

	Args:
		save_to_csv (bool, optional): Whether to save the data to a CSV file. Default is False.

	Returns:
		pd.DataFrame: A DataFrame containing the scraped project data.
	"""
	
	civic_coding_projects = get_community_projects_with_playwright(
        username=os.getenv("CIVIC_CODING_USERNAME"),
        password=os.getenv("CIVIC_CODING_PASSWORD")
	)
      	
	if civic_coding_projects is not None:
		print(f"Successfully retrieved {len(civic_coding_projects)} projects from the Civic Coding Community website.")

		if save_to_csv:
			# Optionally, save the DataFrame to a CSV file with today's date
			today = str(date.today())
			civic_coding_projects.to_csv(f"project_code/Webscraping/Civic_Coding/{today}_Civic-Coding-Community-Projekte-via-Scraping.csv", index=False)

	else:
		print("Failed to retrieve projects from the Civic Coding website. The returned data is None.")

	return civic_coding_projects



if __name__ == "__main__":
	scrape_civic_coding_community_projects(
		save_to_csv=True
	)