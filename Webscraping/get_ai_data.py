# %%
import pandas as pd
import json
import os
import re
import time
from typing import Dict, List

import requests
from bs4 import BeautifulSoup
from google import genai


# %%
from dotenv import load_dotenv

load_dotenv()


def scrape(url: str) -> Dict[str, str]:
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        r.raise_for_status()
    except Exception:
        return {"final_url": url, "title": "", "meta": "", "text": ""}

    final_url = str(r.url)
    soup = BeautifulSoup(r.text, "html.parser")
    for t in soup(["script", "style", "noscript", "template", "iframe", "svg", "canvas"]):
        t.decompose()

    title = soup.title.get_text(strip=True) if soup.title else ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    meta = meta_tag.get("content", "").strip() if meta_tag else ""
    if not meta:
        og = soup.find("meta", attrs={"property": "og:description"})
        meta = og.get("content", "").strip() if og else ""

    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)[:10000]
    return {"final_url": final_url, "title": title, "meta": meta, "text": text}


def call_gemini(model: str, payload: Dict[str, str]) -> Dict[str, str]:
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {}

    client = genai.Client(api_key=api_key)

    instruction = (
        "Extrahiere die folgenden Felder aus der Website. Antworte NUR als JSON-Objekt "
        "mit genau diesen Schlüsseln: " + ", ".join(REQUIRED_COLUMNS) + ". "
        "Projektname: Der offizielle Name des Projekts von der Website. Es muss immer ein Projektname sein, keine URL!"
        "Art: Hier ist eine Liste an vorschlägen, an an denen du dich orientieren kannst. Es gibt meist mehrere Arten je Projekt. Beispiele: Analyse von Sensordaten und ML, Automatisierte Datenübermittlung, Bericht, Crowd-Sourced Daten, Dashboard, Datenanalyse, Datenerhebung, Datenanwendung für Öffentlichkeit, Datenstandards, Datensatz und Visualisierung, Digitale Plattform, Dokumentations- und Netzwerktool, Entscheidungsassistent, Festival und Studie, Generative KI, Interaktive App, Interaktive Karte, Interaktiver Fragebogen, Interne Datenanwendung, KI Anwendung, Karte, Knowledge Graph, Large Language Model (LLM), Matching, Monitoring, Offene Daten, Output Monitoring, Plattform für Wahlentscheidungen, Prozessautomatisierung, Reporting, Skalierung der Wirkungsmessung, Sprach-Editor, Umfrage, Übersetzungsassistent, Vernetzungsassistent, Verzeichnis / Karte, Visualisierung mit Karten, Zugänglichkeit Offene Daten des Statistischen Bundesamts."
        "Einsatzbereich: Hier ist eine Liste an vorschlägen, an an denen du dich orientieren kannst. Es gibt meist mehrere Einsatzbereiche je Projekt. Beispiele: : Afrika, Antidiskriminierung, Antirassismus, Arbeit mit Kindern, Armut, Barrierefreiheit, Beratung, Chancengleichheit, Demokratie, Demenz, Datenschutz, Energie, Ethik, Evaluation, Frauen, Fundraising, Geflüchtete, Genderneutrale Sprache, Gleichberechtigung, Gleichstellung, Gesundheit, Humanitäre Hilfe, Indien, Inklusion, Integration, International, Jugendarbeit, Jugendbeteiligung, Jugendhilfe, Kamerun, Katastrophenschutz, Kältehilfe, Kinderschutz, Kinder- und Jugendhilfe, KI, Kongo, Kroatien, Landwirtschaft, Meeresschutz, Mentale Gesundheit, Mentoring, Menschen mit Behinderung, Menschenrechte, Migration, Migrationsberatung, Nachhaltigkeit, Offene Daten, Partizipation, Patenschaft, Pflege, Pflegende Angehörige, Queere Sichtbarkeit, Rettungsdienst, Senioren, Soziale Arbeit, Sport, Stadt, Stadtplanung, Teilhabe, Telemedizin, Transparenz, Türkei, Umwelt, Umweltschutz, Vernetzung, Verwaltung, Wirkungsmessung, Wohlfahrt, Wohnen, Wohnungslosenhilfe, Wissensmanagement. "
        "Status: Wähle EXAKT eine Option aus: In Planung, Im Testbetrieb, In Weiterentwicklung, In Betrieb, Eingestellt, Unbekannt."
        "Kurzzusammenfassung: 1-2 Sätze, was das Projekt ist/macht. "
        "Webseite-Link: Falls verfügbar einfügen, sonst leer lassen. "
        "Unbekanntes stets als leere Zeichenkette. Schreibe auf Deutsch."
    )
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model,
                contents=instruction + "\n\nWebsite data: " + json.dumps(payload, ensure_ascii=False),
                config={"response_mime_type": "application/json"},
            )
            content = (response.text or "{}") if hasattr(response, "text") else "{}"
            data = json.loads(content)
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, list):
                        data[key] = ", ".join(str(v) for v in value)
                return data
            return {}
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
    "Art",
    "Einsatzbereich",
    "Webseite-Link",
    "Organisation",
    "Status",
    "Kurzzusammenfassung",
]

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")


# %% Parameters
input_csv = r"C:\Users\flori\Documents\git\datenprojekte\Webscraping\PublicInterestAI\PublicInterestAI_Projekte.csv"
output_csv = None  # or set a path; None -> auto _enriched.csv next to input
model = DEFAULT_MODEL

# %%


df = pd.read_csv(input_csv, sep=",", encoding="utf-8-sig", index_col=0)
for col in REQUIRED_COLUMNS:
    if col not in df.columns:
        df[col] = ""

total = len(df)
df
# %%

for i in range(total):
    url = ""
    if "Quelle" in df.columns and pd.notna(df.at[i, "Quelle"]):
        url = str(df.at[i, "Quelle"]).strip()
    else:
        print("No URL found")
        continue

    print(f"[{i+1}/{total}] {url}")
    page = scrape(url)
    print(page)

    payload = {
        "hinweis": "Gib NUR JSON zurück.",
        "quelle": url,
        "final_url": page["final_url"],
        "titel": page["title"],
        "meta": page["meta"],
        "text": page["text"],
    }

    ai = call_gemini(model, payload)
    print(ai)

    # Merge required columns
    for col in REQUIRED_COLUMNS:
        val = (ai or {}).get(col, "")
        if val:
            df.at[i, col] = val

    # Ensure fallbacks
    if not str(df.at[i, "Quelle"]).strip():
        df.at[i, "Quelle"] = url

out_path = output_csv or os.path.splitext(input_csv)[0] + "_enriched.csv"
df.to_csv(out_path, sep=";", index=False, encoding="utf-8")
print(f"Fertig: {out_path}")

# %%
