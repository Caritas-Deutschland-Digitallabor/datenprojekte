import re
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

def extract_urls(text: str) -> list[str]:
    """Extract individual URLs from a string that may contain multiple URLs."""
    if pd.isna(text):
        return []
    # Split on common delimiters: comma, semicolon, whitespace, newlines
    parts = re.split(r"[,;\s\n]+", str(text).strip())
    # Filter out empty strings
    return [p.strip() for p in parts if p.strip()]

def check_url(url: str, timeout: int = 5) -> dict:
    """Check if a single URL is reachable and return its status."""
    # Ensure the URL has a scheme
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True,
                                 headers={"User-Agent": "Mozilla/5.0"})
        return {
            "url": url,
            "reachable": response.status_code < 400 or response.status_code == 403,
            "status_code": response.status_code,
            "final_url": response.url,  # captures redirects
            "error": None,
        }
    except requests.exceptions.SSLError:
        # Retry without SSL verification as fallback
        try:
            response = requests.head(url, timeout=timeout, allow_redirects=True,
                                     verify=False, headers={"User-Agent": "Mozilla/5.0"})
            return {
                "url": url,
                "reachable": response.status_code < 400,
                "status_code": response.status_code,
                "final_url": response.url,
                "error": "SSL warning (unverified)",
            }
        except Exception as e:
            return {"url": url, "reachable": False, "status_code": None,
                    "final_url": None, "error": str(e)}
    except requests.exceptions.ConnectionError:
        return {"url": url, "reachable": False, "status_code": None,
                "final_url": None, "error": "Connection error"}
    except requests.exceptions.Timeout:
        return {"url": url, "reachable": False, "status_code": None,
                "final_url": None, "error": "Timeout"}
    except Exception as e:
        return {"url": url, "reachable": False, "status_code": None,
                "final_url": None, "error": str(e)}

def preprocess_final_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df["Website_has_changed"] = df["final_url"] != df["Webseite-Link"] 
    return df

def check_websites(df: pd.DataFrame, url_column: str,
                   timeout: int = 5, max_workers: int = 20) -> pd.DataFrame:
    
    # Explode multi-URL cells into individual rows
    df = df.copy()
    df["_url_list"] = df[url_column].apply(extract_urls)
    df_exploded = df.explode("_url_list").rename(columns={"_url_list": "_single_url"})
    df_exploded = df_exploded.dropna(subset=["_single_url"])

    # Deduplicate — only check each unique URL once
    unique_urls = df_exploded["_single_url"].unique().tolist()

    # Check all unique URLs in parallel
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_url, url, timeout): url for url in unique_urls}
        for future in as_completed(futures):
            result = future.result()
            results[result["url"]] = result

    def normalize(u):
        return u if u.startswith(("http://", "https://")) else "https://" + u

    # Map results back onto the exploded rows
    df_exploded["reachable"]   = df_exploded["_single_url"].apply(lambda u: results[normalize(u)]["reachable"])
    df_exploded["status_code"] = df_exploded["_single_url"].apply(lambda u: results[normalize(u)]["status_code"])
    df_exploded["final_url"]   = df_exploded["_single_url"].apply(lambda u: results[normalize(u)]["final_url"])
    df_exploded["error"]       = df_exploded["_single_url"].apply(lambda u: results[normalize(u)]["error"])

    df_exploded.drop(columns=["_url_list"], errors="ignore").reset_index(drop=True)

    final_df = preprocess_final_dataframe(df_exploded)

    return final_df

df = pd.read_csv("Webscraping/Erfolgsgeschichten/Liste der Projekte Datenerfolgsgeschichten.csv", sep=";")
result = check_websites(df, url_column="Webseite-Link", timeout=5, max_workers=20)
result.to_csv("check_website_reachability.csv", index=False)