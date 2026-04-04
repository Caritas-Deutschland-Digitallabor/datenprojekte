import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

def access_page_with_retry(page: object, url: str):
    for attempt in range(3):
        try:
            page.goto(url, timeout=60000)
            break
        except Exception as e:
            if attempt == 2:
                raise
            print(f"Attempt {attempt + 1} failed, retrying in 10s...")
            time.sleep(10)

    return page

def scrape_html_website(url: str) -> BeautifulSoup:
	"""Scrapes data from an HTML website and returns it as a BeautifulSoup object. To avoid being blocked by the website, the user agent is specified to look like a standard Windows user on Chrome.

	Args:
		url (str): The URL of the website.

	Returns:
		BeautifulSoup: A BeautifulSoup object containing the data from the website.
	"""
     
	headers = {
		"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
		"Accept-Language": "en-US,en;q=0.9",
		"Referer": "https://www.google.com/" # Tells the site you "came from" Google
	}

	try:
		response = requests.get(url, headers=headers)
		response.raise_for_status() # Check if the request was successful
		soup = BeautifulSoup(response.text, "html.parser")
		return soup
	
	except requests.exceptions.ConnectionError as e:
		print(f"The is blocking the scraping processs. Here is the error: {e}")