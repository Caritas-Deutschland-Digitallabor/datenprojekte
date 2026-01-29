# %%
import pandas as pd
import json
import os
import re
import time
from typing import Dict, List
from datetime import date

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field, ConfigDict


# %%
from dotenv import load_dotenv

load_dotenv()

# --- Global State to remember the working LLM model across function triggers ---
PRIORITIZED_MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "meta-llama/llama-4-scout-17b-16e-instruct"
]
CURRENT_MODEL_INDEX = 0

def scrape(url: str, use_selenium: bool = False) -> Dict[str, str]:
    """
    Scrape a URL with optional Selenium support for JavaScript-rendered content.

    Args:
        url: The URL to scrape
        use_selenium: If True, use Selenium WebDriver for JavaScript support
    """
    if use_selenium:
        return scrape_with_selenium(url)
    else:
        # Use faster requests method for static content
        return scrape_with_requests(url)


def convert_soup_to_enriched_text(soup: BeautifulSoup) -> str:
    """
    Converts a BeautifulSoup object to a string, preserving links and images
    in a markdown-like format, e.g., 'text (link)' or '[Image: alt](src)'.
    """
    # Process images first, so if they are inside a link, their text representation is available
    for img in soup.find_all("img", src=True):
        src = img.get("src", "")
        alt = img.get("alt", "").strip()
        # Create a markdown-like string for the image
        img.replace_with(f" [Image: {alt}]({src}) ")

    # Process links
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        # If the link has text (which could now include the image string), format it
        if text:
            a.replace_with(f" {text} ({href}) ")
        else:
            # If link has no text content (e.g., it was just a wrapper), remove the tag
            a.unwrap()

    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text)


def scrape_with_requests(url: str) -> Dict[str, str]:
    """Original scraping method using requests + BeautifulSoup"""
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        r.raise_for_status()
    except Exception:
        return {"final_url": url, "title": "", "meta": "", "text": "", "html": ""}

    final_url = str(r.url)
    html = r.text
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "template", "iframe", "svg", "canvas"]):
        t.decompose()

    title = soup.title.get_text(strip=True) if soup.title else ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    meta = meta_tag.get("content", "").strip() if meta_tag else ""
    if not meta:
        og = soup.find("meta", attrs={"property": "og:description"})
        meta = og.get("content", "").strip() if og else ""

    text = convert_soup_to_enriched_text(soup)
    text = text[:10000]
    return {"final_url": final_url, "title": title, "meta": meta, "text": text, "html": html}


def scrape_with_selenium(url: str) -> Dict[str, str]:
    """Simple Selenium scraping - same output as requests method"""
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)

        # Wait for page to load
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)  # Brief wait for dynamic content

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        # Clean up - same as requests method
        for t in soup(["script", "style", "noscript", "template", "iframe", "svg", "canvas"]):
            t.decompose()

        title = soup.title.get_text(strip=True) if soup.title else ""

        meta_tag = soup.find("meta", attrs={"name": "description"})
        meta = meta_tag.get("content", "").strip() if meta_tag else ""
        if not meta:
            og = soup.find("meta", attrs={"property": "og:description"})
            meta = og.get("content", "").strip() if og else ""

        text = convert_soup_to_enriched_text(soup)
        text = text[:10000]

        return {"final_url": driver.current_url, "title": title, "meta": meta, "text": text, "html": html}

    except Exception as e:
        print(f"Selenium failed: {e}")
        return {"final_url": url, "title": "", "meta": "", "text": "", "html": ""}
    finally:
        if driver:
            driver.quit()


def call_llm(payload: Dict[str, str]) -> Dict[str, str]:
    global CURRENT_MODEL_INDEX
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Warning: GROQ_API_KEY not found in environment variables")
        return {}

    class ProjectExtraction(BaseModel):
        """Structured extraction of project information from website data."""
    
        projekt_abkuerzung: str = Field(
            default="",
            alias="Projekt-Abkürzung",
            description="Falls verfügbar eine Projekt-Abkürzung einfügen, sonst leer lassen."
        )
    
        Art: str = Field(
            description=(
                "Liste die Arten des Projekts, komma-separiert. Hier ist eine Liste an Vorschlägen, an denen du dich orientieren kannst. "
                "Es gibt meist mehrere Arten je Projekt. Beispiele: Analyse von Sensordaten und ML, "
                "Automatisierte Datenübermittlung, Bericht, Crowd-Sourced Daten, Dashboard, Datenanalyse, "
                "Datenerhebung, Datenanwendung für Öffentlichkeit, Datenstandards, Datensatz und Visualisierung, "
                "Digitale Plattform, Dokumentations- und Netzwerktool, Entscheidungsassistent, Festival und Studie, "
                "Generative KI, Interaktive App, Interaktive Karte, Interaktiver Fragebogen, Interne Datenanwendung, "
                "KI Anwendung, Karte, Knowledge Graph, Large Language Model (LLM), Matching, Monitoring, "
                "Offene Daten, Output Monitoring, Plattform für Wahlentscheidungen, Prozessautomatisierung, "
                "Reporting, Skalierung der Wirkungsmessung, Sprach-Editor, Umfrage, Übersetzungsassistent, "
                "Vernetzungsassistent, Verzeichnis / Karte, Visualisierung mit Karten, "
                "Zugänglichkeit Offene Daten des Statistischen Bundesamts."
            )
        )
    
        Einsatzbereich: str = Field(
            description=(
                "Liste komma-separiert die Einsatzbereiche des Projekts. Hier ist eine Liste an Vorschlägen, an denen du dich orientieren kannst. "
                "Es gibt meist mehrere Einsatzbereiche je Projekt. Beispiele: Afrika, Antidiskriminierung, "
                "Antirassismus, Arbeit mit Kindern, Armut, Barrierefreiheit, Beratung, Chancengleichheit, "
                "Demokratie, Demenz, Datenschutz, Energie, Ethik, Evaluation, Frauen, Fundraising, Geflüchtete, "
                "Genderneutrale Sprache, Gleichberechtigung, Gleichstellung, Gesundheit, Humanitäre Hilfe, "
                "Indien, Inklusion, Integration, International, Jugendarbeit, Jugendbeteiligung, Jugendhilfe, "
                "Kamerun, Katastrophenschutz, Kältehilfe, Kinderschutz, Kinder- und Jugendhilfe, KI, Kongo, "
                "Kroatien, Landwirtschaft, Meeresschutz, Mentale Gesundheit, Mentoring, Menschen mit Behinderung, "
                "Menschenrechte, Migration, Migrationsberatung, Nachhaltigkeit, Offene Daten, Partizipation, "
                "Patenschaft, Pflege, Pflegende Angehörige, Queere Sichtbarkeit, Rettungsdienst, Senioren, "
                "Soziale Arbeit, Sport, Stadt, Stadtplanung, Teilhabe, Telemedizin, Transparenz, Türkei, "
                "Umwelt, Umweltschutz, Vernetzung, Verwaltung, Wirkungsmessung, Wohlfahrt, Wohnen, "
                "Wohnungslosenhilfe, Wissensmanagement."
            )
        )
    
        model_config = ConfigDict(populate_by_name=True)

    # Simplified instruction - Pydantic model handles field descriptions
    instruction = (
        "Extrahiere die folgenden Felder aus der Website basierend auf den bereitgestellten "
        "Feldanweisungen. Unbekanntes stets als leere Zeichenkette. Schreibe auf Deutsch."
    )

    # Prepare messages
    messages = [
        SystemMessage(content=instruction),
        HumanMessage(content="Website data: " + json.dumps(payload, ensure_ascii=False))
    ]

    # Retry logic (4 attempts)
    for attempt in range(4):
        # Determine which model to use based on current index and attempt number
        # Using modulo ensures we wrap around if we exceed the list length
        model_to_use_idx = (CURRENT_MODEL_INDEX + attempt) % len(PRIORITIZED_MODELS)
        selected_model = PRIORITIZED_MODELS[model_to_use_idx]

        try:
            print(f"  -> Attempt {attempt + 1}: Using model {selected_model}")
            
            llm = ChatGroq(model=selected_model, api_key=api_key, temperature=0.0)
            structured_llm = llm.with_structured_output(ProjectExtraction)
            
            response: ProjectExtraction = structured_llm.invoke(messages)
            
            # SUCCESS: Update the global index so the NEXT call starts with this model
            CURRENT_MODEL_INDEX = model_to_use_idx
            
            data = response.model_dump(by_alias=True)
            for key, value in data.items():
                if isinstance(value, list):
                    data[key] = ", ".join(str(v) for v in value)
            return data
            
        except Exception as e:
            print(f"  -> {selected_model} failed: {e}")
            if attempt < 3:
                print("  -> Switching to next available model and retrying...")
                time.sleep(2)
    return {}


# %%
# ,Quelle,Projektname,Art,Einsatzbereich,Webseite-Link,Organisation,Status,Kurzzusammenfassung

REQUIRED_COLUMNS: List[str] = [
    "Quelle",
    "Projektname",
    "Projekt-Abkürzung",
    "Art",
    "Einsatzbereich",
    "Webseite-Link",
    "Organisation",
    "Status",
    "Kurzzusammenfassung",
]

def enrich_projects_data_with_ai(
        projects_data: pd.DataFrame,
        use_selenium: bool = False,
        seperator: str = ",",
        type_of_data: str = "projects"
) -> pd.DataFrame:
    """
    Enrich previously scraped projects data file with AI-extracted data from URLs.

    Args:
        projects_data: A Pandas DataFrame containing the projects data
        use_selenium: Whether to use Selenium for scraping (default: False)
        model: AI model to use (default: DEFAULT_MODEL)

    Returns:
        A Pandas DataFrame containing the enriched projects data
    """

    # Ensure required columns exist
    for col in REQUIRED_COLUMNS:
        if col not in projects_data.columns:
            projects_data[col] = ""

    total = len(projects_data)
    print(f"Processing {total} rows...")

    # Process each row
    for i, row in projects_data.iterrows():
        url = ""
        if "Quelle" in projects_data.columns and pd.notna(row["Quelle"]):
            url = str(row["Quelle"]).strip()

        if not url:
            print(f"Row {i+1}: No URL found, skipping.")
            continue

        # Ensure URL has a scheme
        if not re.match(r"^https?://", url):
            print(f"  -> URL '{url}' is missing a scheme, prepending 'https://'")
            url = "https://" + url

        print(f"[{list(projects_data.index).index(i)+1}/{total}] {url}")
        page = scrape(url, use_selenium=use_selenium)

        payload = {
            "hinweis": "Gib NUR JSON zurück.",
            "quelle": url,
            "final_url": page["final_url"],
            "titel": page["title"],
            "meta": page["meta"],
            "text": page["text"],
        }

        ai = call_llm(payload=payload)
        print(f"AI result: {ai}")

        # Merge required columns
        for col in REQUIRED_COLUMNS:
            val = (ai or {}).get(col, "")
            if val:
                projects_data.loc[i, col] = val

        # Ensure fallbacks
        if not str(projects_data.loc[i, "Quelle"]).strip():
            projects_data.loc[i, "Quelle"] = url

    # Save enriched CSV
    today = str(date.today())
    output_path = f"project_code/Webscraping/{type_of_data}/{today}_CityLAB-Berlin-Projekte-via-Scraping_enriched.csv"
    projects_data.to_csv(output_path, sep=";", index=False, encoding="utf-8")
    print(f"Fertig: {output_path}")
    return output_path


# %% Example usage
# csv_path = r"C:\Users\flori\Documents\git\datenprojekte\Webscraping\CodeFor_Projekte_copy.csv"
# enrich_csv_with_ai(csv_path, use_selenium=True, seperator=",")

# # # %% Citylab-Berlin
# csv_path = "Citylab-Berlin/2026-01-22_CityLAB-Berlin-Projekte-via-Scraping.csv"
# enrich_csv_with_ai(csv_path, use_selenium=True, seperator=",")

# # %% Civic-Coding
# csv_path = r"C:\Users\flori\Documents\git\datenprojekte\Webscraping\Civic-Coding\CivicCoding_Projekte.csv"
# enrich_csv_with_ai(csv_path, use_selenium=True, seperator=",")

# # %% CodeFor
# csv_path = r"C:\Users\flori\Documents\git\datenprojekte\Webscraping\CodeFor\CodeFor_Projekte.csv"
# enrich_csv_with_ai(csv_path, use_selenium=True, seperator=",")

# # %% Correlaid-Projektdatenbank
# csv_path = "Correlaid-Projektdatenbank/2026-01-19_Correlaid-Projekte-via-API.csv"
# enrich_csv_with_ai(csv_path, use_selenium=True, seperator=",")

# # %% PublicinterestAI
# csv_path = r"C:\Users\flori\Documents\git\datenprojekte\Webscraping\PublicInterestAI\PublicInterestAI_Projekte.csv"
# enrich_csv_with_ai(csv_path, use_selenium=True, seperator=",")

# %% Erfolgsgeschichten
# csv_path = r"C:\Users\flori\Documents\git\datenprojekte\Webscraping\Erfolgsgeschichten\Liste der Projekte Datenerfolgsgeschichten (1).csv"
# enrich_csv_with_ai(csv_path, use_selenium=True, seperator=";")

# %%
