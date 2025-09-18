#!/usr/bin/env python3
"""
Simple Organization Link Finder
Finds organization websites from CSV data using DuckDuckGo search and LLM analysis
"""

import csv
import requests
import time
import re
import json
from typing import Dict, Optional, List
from urllib.parse import quote, unquote
from bs4 import BeautifulSoup
import random

try:
    import ollama

    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


class OrganizationLinkFinder:
    def __init__(self, csv_file_path: str):
        self.csv_file_path = csv_file_path
        self.organizations = []
        self.results = []
        self.ollama_working = False
        self.session = requests.Session()

        # Set up session headers to appear more like a browser
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )

        print("✓ DuckDuckGo search available")

        if OLLAMA_AVAILABLE:
            self.ollama_working = self.test_ollama_connection()
            if self.ollama_working:
                print("✓ Ollama connected and working")
            else:
                print("✗ Ollama installed but not working - start with: ollama serve")
        else:
            print("✗ Ollama not available - install with: pip install ollama")

    def test_ollama_connection(self) -> bool:
        """Test if Ollama is actually working"""
        try:
            # Try a simple chat to test connection
            ollama.chat(
                model="llama3.2",
                messages=[{"role": "user", "content": "hi"}],
                options={"timeout": 10},
            )
            return True
        except Exception as e:
            print(f"    Ollama test failed: {e}")
            return False

    def load_csv_data(self) -> None:
        """Load organization names from CSV file"""
        try:
            with open(self.csv_file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file, delimiter=";")
                for row in reader:
                    org_field = row.get("Organisation", "").strip()

                    if org_field:
                        # Split by multiple separators: comma, semicolon, and forward slash
                        org_names = re.split(r"[,;/]", org_field)
                        org_names = [name.strip() for name in org_names if name.strip()]

                        for org_name in org_names:
                            if org_name and org_name not in [
                                org["name"] for org in self.organizations
                            ]:
                                self.organizations.append({"name": org_name})
        except Exception as e:
            print(f"Error reading CSV file: {e}")

    def search_duckduckgo_html(self, org_name: str, retry_count: int = 0) -> List[Dict]:
        """Search using DuckDuckGo HTML and return list of URLs with descriptions"""
        try:
            search_query = f"{org_name} official website"
            encoded_query = quote(search_query)

            # DuckDuckGo HTML search URL
            search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

            # Add random delay to avoid detection
            time.sleep(random.uniform(2, 4))

            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()

            # Handle encoding properly
            response.encoding = response.apparent_encoding or "utf-8"

            soup = BeautifulSoup(response.text, "html.parser")
            results = []

            # Look for result links in DuckDuckGo HTML
            result_links = soup.find_all("a", class_="result__a")

            for link in result_links:
                href = link.get("href", "")
                title = link.get_text(strip=True)

                if href and title:
                    # Extract actual URL from DuckDuckGo redirect
                    actual_url = href
                    if "uddg=" in href:
                        try:
                            # Extract URL from DuckDuckGo redirect format
                            actual_url = href.split("uddg=")[1].split("&")[0]
                            actual_url = unquote(actual_url)
                        except Exception:
                            continue

                    if not actual_url.startswith("http"):
                        continue

                    # Skip unwanted sites
                    if any(
                        skip in actual_url.lower()
                        for skip in [
                            "wikipedia",
                            "facebook",
                            "twitter",
                            "linkedin",
                            "youtube",
                            "instagram",
                            "reddit",
                        ]
                    ):
                        continue

                    # Find description in parent elements
                    description = ""
                    parent = link.find_parent("div", class_="result")
                    if parent:
                        desc_elem = parent.find("a", class_="result__snippet")
                        if desc_elem:
                            description = desc_elem.get_text(strip=True)

                    results.append(
                        {"url": actual_url, "title": title, "description": description}
                    )

                    if len(results) >= 10:  # Limit to 10 results
                        break

            print(f"    Found {len(results)} results from DuckDuckGo")
            return results

        except requests.exceptions.RequestException as e:
            if retry_count < 2:
                wait_time = random.uniform(5, 15) * (retry_count + 1)
                print(
                    f"    Request error, waiting {wait_time:.1f} seconds before retry {retry_count + 1}/2..."
                )
                time.sleep(wait_time)
                return self.search_duckduckgo_html(org_name, retry_count + 1)
            else:
                print(f"    DuckDuckGo search error: {e}")
                return []
        except Exception as e:
            print(f"    DuckDuckGo search error: {e}")
            return []

    def search_engines(self, org_name: str) -> List[Dict]:
        """Search using multiple engines and return results with descriptions"""
        results = []

        # Try DuckDuckGo HTML first (most reliable)
        print("    Searching DuckDuckGo...")
        ddg_results = self.search_duckduckgo_html(org_name)
        if ddg_results:
            results.extend(ddg_results)
            return results

        # If DuckDuckGo fails, try fallback domain guessing
        print("    DuckDuckGo failed, trying domain guessing...")
        fallback_urls = self.fallback_search(org_name)

        # Convert simple URLs to result format
        for url in fallback_urls:
            results.append(
                {
                    "url": url,
                    "title": f"Potential official site for {org_name}",
                    "description": f"Domain appears to be related to {org_name}",
                }
            )

        return results

    def fallback_search(self, org_name: str) -> List[str]:
        """Fallback search method using direct domain guessing"""
        urls = []

        # Try common domain patterns
        org_clean = re.sub(r"[^a-zA-Z0-9\s]", "", org_name.lower())
        org_words = org_clean.split()

        # Generate potential domain names
        potential_domains = []

        if len(org_words) >= 2:
            # Try acronym
            acronym = "".join([word[0] for word in org_words if len(word) > 2])
            if len(acronym) >= 2:
                potential_domains.extend(
                    [f"{acronym}.org", f"{acronym}.com", f"{acronym}.gov"]
                )

        # Try full name variations
        full_name = "".join(org_words)
        if len(full_name) > 3:
            potential_domains.extend(
                [f"{full_name}.org", f"{full_name}.com", f"{full_name}.gov"]
            )

        # Try hyphenated version
        if len(org_words) > 1:
            hyphenated = "-".join(org_words)
            potential_domains.extend(
                [f"{hyphenated}.org", f"{hyphenated}.com", f"{hyphenated}.gov"]
            )

        # Test these domains
        for domain in potential_domains[:5]:  # Limit to 5 attempts
            try:
                test_url = f"https://{domain}"
                response = self.session.head(test_url, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    urls.append(test_url)
                    print(f"    Found potential domain: {test_url}")
                    if len(urls) >= 3:
                        break
            except Exception:
                continue

        return urls

    def analyze_results_with_llm(
        self, org_name: str, results: List[Dict]
    ) -> Optional[str]:
        """Use LLM to analyze search results and pick the best URL"""
        if not self.ollama_working or not results:
            return None

        try:
            # Format results for LLM analysis
            result_list = []
            for i, result in enumerate(results, 1):
                title = result.get("title", "No title")
                url = result.get("url", "")
                description = result.get("description", "No description")

                result_list.append(
                    f"""Result {i}:
URL: {url}
Title: {title}
Description: {description}
"""
                )

            formatted_results = "\n".join(result_list)

            prompt = f"""I'm looking for the official website of the organization: "{org_name}"

Here are the search results with titles and descriptions:

{formatted_results}

Please analyze these results and return ONLY the URL that is most likely to be the official website for "{org_name}". 

Look for:
- URLs that contain the organization name or acronym in the domain
- Official domains (.org, .com, .edu, .gov, .de, .nrw, etc.)
- Titles and descriptions that indicate this is the main/official site
- Avoid Wikipedia, news articles, social media, job sites, directories

Consider the title and description context to make the best choice. Reply with just the URL (starting with http:// or https://) or "none" if no suitable official website is found."""

            response = ollama.chat(
                model="llama3.2",
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1, "timeout": 45},
            )

            answer = response["message"]["content"].strip()

            # Extract URL from response
            if answer.lower() == "none":
                return None

            # Look for URL in the response
            url_pattern = r'https?://[^\s<>"\'\(\)]+[^\s<>"\'\(\)\.]'
            found_urls = re.findall(url_pattern, answer)

            if found_urls:
                # Verify the URL is from our results
                found_url = found_urls[0]
                for result in results:
                    if result.get("url") == found_url:
                        return found_url

                # If exact match not found, try partial match
                for result in results:
                    if (
                        found_url in result.get("url", "")
                        or result.get("url", "") in found_url
                    ):
                        return result.get("url")

            return None

        except Exception as e:
            print(f"    LLM error: {e}")
            return None

    def find_organization_website(self, org_name: str) -> Dict:
        """Find website for a single organization"""
        result = {"organization": org_name, "website": None, "method": "not_found"}

        # Search using multiple engines
        search_results = self.search_engines(org_name)
        if not search_results:
            return result

        # Try LLM analysis of search results
        if self.ollama_working:
            print("    Analyzing search results with LLM...")
            llm_choice = self.analyze_results_with_llm(org_name, search_results)
            if llm_choice:
                result["website"] = llm_choice
                result["method"] = "llm_analysis"
                return result

        # Fallback: return first URL from search results
        if search_results:
            result["website"] = search_results[0].get("url")
            result["method"] = "search_first_result"

        return result

    def process_all_organizations(self):
        """Process all organizations and find their websites"""
        print(f"Processing {len(self.organizations)} organizations...")

        for i, org in enumerate(self.organizations, 1):
            print(f"({i}/{len(self.organizations)}) Searching: {org['name']}")

            result = self.find_organization_website(org["name"])
            self.results.append(result)

            if result["website"]:
                print(f"    ✓ Found: {result['website']} ({result['method']})")
            else:
                print("    ✗ Not found")

            # Random delay between searches to avoid rate limiting
            delay = random.uniform(8, 15)
            time.sleep(delay)

    def save_results(self, output_file: str = "organization_websites.json"):
        """Save results to JSON file"""
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            print(f"\nResults saved to {output_file}")
        except Exception as e:
            print(f"Error saving results: {e}")

    def print_summary(self):
        """Print summary statistics"""
        total = len(self.results)
        found = len([r for r in self.results if r["website"]])
        llm_found = len([r for r in self.results if r["method"] == "llm_analysis"])
        search_found = len(
            [r for r in self.results if r["method"] == "search_first_result"]
        )

        print("\nSUMMARY:")
        print(f"Total organizations: {total}")
        print(f"Websites found: {found}")
        print(f"LLM analyzed: {llm_found}")
        print(f"Search first result: {search_found}")
        print(
            f"Success rate: {(found/total*100):.1f}%"
            if total > 0
            else "Success rate: 0.0%"
        )


def main():
    csv_path = "/Users/ramius/Desktop/CodeVault/Caritas Datenprojekt/datenprojekte_git/MarkdownConverter/data/csv/combined_all_projects.csv"
    finder = OrganizationLinkFinder(csv_path)

    print("Loading organizations from CSV...")
    finder.load_csv_data()

    if not finder.organizations:
        print("No organizations found!")
        return

    # Process all organizations
    finder.process_all_organizations()

    # Save and show results
    finder.save_results()
    finder.print_summary()


if __name__ == "__main__":
    main()
