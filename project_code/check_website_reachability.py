import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

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
            "reachable": response.status_code < 400,
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
    """
    Check reachability of all URLs in a DataFrame column.

    Args:
        df:          DataFrame containing the URLs.
        url_column:  Name of the column with website URLs.
        timeout:     Seconds before a request times out.
        max_workers: Number of parallel threads.

    Returns:
        Original DataFrame with added columns:
        reachable, status_code, final_url, error
    """
    urls = df[url_column].tolist()
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_url, url, timeout): url for url in urls}
        for future in as_completed(futures):
            result = future.result()
            results[result["url"]] = result

    # Normalize URLs the same way check_url does before merging
    def normalize(u):
        return u if u.startswith(("http://", "https://")) else "https://" + u

    result_df = pd.DataFrame([
        results[normalize(url)] for url in urls
    ])

    df.assign(
        reachable=result_df["reachable"].values,
        status_code=result_df["status_code"].values,
        final_url=result_df["final_url"].values,
        error=result_df["error"].values,
    )

    df = preprocess_final_dataframe(df)

    return df

df = pd.read_csv("Webscraping/Erfolgsgeschichten/Liste der Projekte Datenerfolgsgeschichten.csv", sep=";")
result = check_websites(df, url_column="Webseite-Link", timeout=5, max_workers=20)
result.to_csv("check_website_reachability.csv", index=False)