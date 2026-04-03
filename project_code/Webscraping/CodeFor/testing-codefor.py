from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
from scrape_projects_from_codefor_website import collect_project_data_as_dataframe

def get_fully_rendered_soup(url: str) -> BeautifulSoup:
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


# Use it as a drop-in replacement for your existing requests-based scraping
scraped_data = get_fully_rendered_soup("https://codefor.de/projekte/alle/")
df = collect_project_data_as_dataframe(scraped_data)
print(df)