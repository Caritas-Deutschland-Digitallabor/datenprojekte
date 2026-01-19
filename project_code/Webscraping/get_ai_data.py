# %%
import pandas as pd
import json
import os
import re
import time
from typing import Dict, List

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


def call_llm(model: str, payload: Dict[str, str]) -> Dict[str, str]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Warning: GROQ_API_KEY not found in environment variables")
        return {}
    
    # Future-proof abstraction - easily swap providers by changing this class
    llm = ChatGroq(
        model=model,
        api_key=api_key,
        temperature=0.0,
    )

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

    # Use with_structured_output for type-safe parsing
    structured_llm = llm.with_structured_output(ProjectExtraction)

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

    # Retry logic (3 attempts)
    for attempt in range(3):
        try:
            # Invoke LLM with structured output
            response: ProjectExtraction = structured_llm.invoke(messages)
            
            # Convert Pydantic model to dictionary
            data = response.model_dump(by_alias=True)
            
            # Convert any list values to comma-separated strings (if needed)
            for key, value in data.items():
                if isinstance(value, list):
                    data[key] = ", ".join(str(v) for v in value)
            
            return data
            
        except Exception as e:
            print(f"  -> AI call failed (attempt {attempt + 1}/3): {e}")
            if attempt < 2:  # Don't wait after the last attempt
                print("  -> Waiting 10 seconds before retry...")
                time.sleep(10)
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

def enrich_csv_with_ai(csv_path: str, use_selenium: bool = False, seperator: str = ",") -> str:
    """
    Enrich a CSV file with AI-extracted data from URLs.

    Args:
        csv_path: Path to the input CSV file
        use_selenium: Whether to use Selenium for scraping (default: False)
        model: AI model to use (default: DEFAULT_MODEL)

    Returns:
        Path to the enriched output CSV file
    """
    # Read CSV
    df = pd.read_csv(csv_path, sep=seperator, encoding="utf-8-sig", index_col=0)

    # Ensure required columns exist
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    total = len(df)
    print(f"Processing {total} rows...")

    # Process each row
    for i, row in df.iterrows():
        url = ""
        if "Quelle" in df.columns and pd.notna(row["Quelle"]):
            url = str(row["Quelle"]).strip()

        if not url:
            print(f"Row {i+1}: No URL found, skipping.")
            continue

        # Ensure URL has a scheme
        if not re.match(r"^https?://", url):
            print(f"  -> URL '{url}' is missing a scheme, prepending 'https://'")
            url = "https://" + url

        print(f"[{list(df.index).index(i)+1}/{total}] {url}")
        page = scrape(url, use_selenium=use_selenium)

        payload = {
            "hinweis": "Gib NUR JSON zurück.",
            "quelle": url,
            "final_url": page["final_url"],
            "titel": page["title"],
            "meta": page["meta"],
            "text": page["text"],
        }

        ai = call_llm(model="llama-3.3-70b-versatile", payload=payload)
        print(f"AI result: {ai}")

        # Merge required columns
        for col in REQUIRED_COLUMNS:
            val = (ai or {}).get(col, "")
            if val:
                df.loc[i, col] = val

        # Ensure fallbacks
        if not str(df.loc[i, "Quelle"]).strip():
            df.loc[i, "Quelle"] = url

    # Save enriched CSV
    output_path = os.path.splitext(csv_path)[0] + "_enriched.csv"
    df.to_csv(output_path, sep=";", index=False, encoding="utf-8")
    print(f"Fertig: {output_path}")
    return output_path


# %% Example usage
# csv_path = r"C:\Users\flori\Documents\git\datenprojekte\Webscraping\CodeFor_Projekte_copy.csv"
# enrich_csv_with_ai(csv_path, use_selenium=True, seperator=",")

# # %% Citylab-Berlin
# csv_path = r"C:\Users\flori\Documents\git\datenprojekte\Webscraping\Citylab-Berlin\Citylab-Berlin_Projekte.csv"
# enrich_csv_with_ai(csv_path, use_selenium=True, seperator=",")

# # %% Civic-Coding
# csv_path = r"C:\Users\flori\Documents\git\datenprojekte\Webscraping\Civic-Coding\CivicCoding_Projekte.csv"
# enrich_csv_with_ai(csv_path, use_selenium=True, seperator=",")

# # %% CodeFor
# csv_path = r"C:\Users\flori\Documents\git\datenprojekte\Webscraping\CodeFor\CodeFor_Projekte.csv"
# enrich_csv_with_ai(csv_path, use_selenium=True, seperator=",")

# # %% Correlaid-Projektdatenbank
csv_path = "Correlaid-Projektdatenbank/2026-01-19_Correlaid-Projekte-via-API.csv"
enrich_csv_with_ai(csv_path, use_selenium=True, seperator=",")

# # %% PublicinterestAI
# csv_path = r"C:\Users\flori\Documents\git\datenprojekte\Webscraping\PublicInterestAI\PublicInterestAI_Projekte.csv"
# enrich_csv_with_ai(csv_path, use_selenium=True, seperator=",")

# %% Erfolgsgeschichten
# csv_path = r"C:\Users\flori\Documents\git\datenprojekte\Webscraping\Erfolgsgeschichten\Liste der Projekte Datenerfolgsgeschichten (1).csv"
# enrich_csv_with_ai(csv_path, use_selenium=True, seperator=";")

# %%
