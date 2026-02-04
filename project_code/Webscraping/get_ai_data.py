# %%
import pandas as pd
import json
import os
import re
import time
from typing import Dict, List, Annotated, Union
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
from pydantic import BaseModel, Field, ConfigDict, BeforeValidator, field_validator
from enum import Enum


# %%
from dotenv import load_dotenv

load_dotenv()

# --- Global State to remember the working LLM model across function triggers ---
GROQ_MODELS = [
    "openai/gpt-oss-safeguard-20b",
    "qwen/qwen3-32b",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "openai/gpt-oss-120b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",


    # "allam-2-7b", # NO - tool calling not supported
    # "canopylabs/orpheus-arabic-saudi", # Maybe? - requires terms acceptenance, see error message
    # "canopylabs/orpheus-v1-english", # Maybe? - requires terms acceptenance, see error message
    # "groq/compound", # NO - tool calling not supported
    # "groq/compound-mini", # NO - tool calling not supported
    # "llama-3.1-8b-instant", # MAYBE - output is often very large and does not adhere well to prompt instructions and has often errors to tool_use_failed
    # "meta-llama/llama-guard-4-12b", # NO - tool calling not supported
    # "meta-llama/llama-prompt-guard-2-22m", # NO - tool calling not supported
    # "meta-llama/llama-prompt-guard-2-86m", # NO - tool calling not supported
    # "moonshotai/kimi-k2-instruct", # NO, fails sometimes/always?
    # "moonshotai/kimi-k2-instruct-0905", # NO, fails sometimes/always?
    # "whisper-large-v3", # No, does not support chat completions
    # "whisper-large-v3-turbo" # No, does not support chat completions
]

CURRENT_MODEL_INDEX = 0

ALLOWED_PROJEKT_ARTEN = pd.read_csv("project_code/MarkdownConverter/TermSimilarity/term_clustering_art_results.csv", sep=";").term.unique().tolist()
ALLOWED_PROJEKT_EINSATZBEREICHE = pd.read_csv("project_code/MarkdownConverter/TermSimilarity/term_clustering_einsatzbereich_results.csv", sep=";").term.unique().tolist()

def ensure_list(v: Union[str, List[str]]) -> List[str]:
    """If the LLM sends a string 'A, B', convert it to ['A', 'B'] before validation."""
    if isinstance(v, str):
        # Split by comma and strip whitespace
        return [item.strip() for item in v.split(",") if item.strip()]
    return v

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


def convert_soup_to_enriched_text(soup: BeautifulSoup, max_text_length: int = 8000) -> str:
    """
    Refined extraction: removes headers/footers, preserves image alt-text,
    and strips all URLs while keeping only the link text.
    """
    # 1. REMOVE NOISE: Strip non-content areas aggressively
    for noise in soup(["header", "footer", "nav", "aside", "form", "script", "style", "noscript", "svg"]):
        noise.decompose()

    # 2. TARGET CONTENT: Focus on the main part of the page
    main_content = soup.find("main") or soup.find("article") or soup.find(id=re.compile(r'content|main|body', re.I))
    search_area = main_content if main_content else soup

    # 3. IMAGES: Keep alt-text if descriptive, otherwise remove
    for img in search_area.find_all("img"):
        alt = img.get("alt", "").strip()
        if len(alt) > 5:
            img.replace_with(f" [Bild: {alt}] ")
        else:
            img.decompose()

    # 4. LINKS: Strip the href entirely, keep only the visible text
    for a in search_area.find_all("a"):
        link_text = a.get_text(strip=True)
        if link_text:
            # Replace the whole <a> tag with just its inner text
            a.replace_with(f" {link_text} ")
        else:
            a.decompose()

    # 5. CLEANUP: Extract text and normalize whitespace
    text = search_area.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    capped_text = text[:max_text_length]
    
    return capped_text


def scrape_with_requests(url: str) -> Dict[str, str]:
    """Original scraping method using requests + BeautifulSoup"""
    try:
        r = requests.get(url, timeout=200, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        r.raise_for_status()
    except Exception:
        return {"final_url": url, "title": "", "meta": "", "text": "", "html": ""}

    final_url = str(r.url)
    html = r.text
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "template", "iframe", "svg", "canvas"]):
        t.decompose()

    title = soup.title.string if soup.title else ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    meta = meta_tag.get("content", "").strip() if meta_tag else ""
    if not meta:
        og = soup.find("meta", attrs={"property": "og:description"})
        meta = og.get("content", "").strip() if og else ""

    text = convert_soup_to_enriched_text(soup)

    return {"final_url": final_url, "title": title, "meta": meta, "text": text, "html": soup.prettify()}


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
            description=(
            "NUR das offizielle Akronym oder den kurzen Marketing-Namen extrahieren. "
            "Falls KEIN expliziter Kurzname im Text steht, MUSS dieses Feld ein leerer String sein."
        )
        )
    
        Art: Annotated[List[str], BeforeValidator(ensure_list)] = Field(
            default=[],
            description=f"WICHTIG: Gib eine JSON-Liste von Strings zurück (KEIN kommagetrennter String). Wähle bis zu 7 passende Kategorien aus dieser Liste: {', '.join(ALLOWED_PROJEKT_ARTEN)}"
        )
    
        Einsatzbereich: Annotated[List[str], BeforeValidator(ensure_list)] = Field(
            default=[],
            description=f"WICHTIG: Gib eine JSON-Liste von Strings zurück (KEIN kommagetrennter String). Wähle bis zu 7 passende Einsatzbereiche aus dieser Liste: {', '.join(ALLOWED_PROJEKT_EINSATZBEREICHE)}"
        )
    
        model_config = ConfigDict(populate_by_name=True)

    # Simplified instruction - Pydantic model handles field descriptions
    system_prompt = (
        "Du bist ein Extraktions-Experte. Analysiere HTML-Projektwebsites. "
        "WICHTIG: Für 'Projekt-Abkürzung' extrahiere nur dann einen Wert, wenn ein spezifischer Kurzname oder ein Akronym existiert. "
        "Wenn das Projekt nur mit seinem vollen Namen bezeichnet wird, lass das Feld leer. "
        "WICHTIG: Nutze für 'Art' und 'Einsatzbereich' EXAKT die Begriffe aus der Liste in der Feldbeschreibung. Erfinde keine neuen Kategorien."
    )

    # Prepare messages
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Website data: " + json.dumps(payload, ensure_ascii=False))
    ]

    # Retry logic (4 attempts)
    for attempt in range(10):
        # Determine which model to use based on current index and attempt number
        # Using modulo ensures we wrap around if we exceed the list length
        model_to_use_idx = (CURRENT_MODEL_INDEX + attempt) % len(GROQ_MODELS)
        selected_model = GROQ_MODELS[model_to_use_idx]

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

        if page["html"]:
            print(f"  -> Length of scraped HTML website: {len(page['html'])} chars")
        else:
            print("  -> No HTML was scraped due to slow website response.")

        payload = {
            "url": page["final_url"],
            "title": page["title"],
            "description": page["meta"],
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
    output_path = f"project_code/Webscraping/{type_of_data}/{today}_{type_of_data}-Projekte-via-Scraping_enriched.csv"
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
