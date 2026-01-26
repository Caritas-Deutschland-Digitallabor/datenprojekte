#!/usr/bin/env python3
"""
Simple Organization Link Finder
Finds organization websites from CSV data using DuckDuckGo search and scoring analysis
"""

import csv
import requests
import time
import re
import json
from typing import Dict, Optional, List
from urllib.parse import quote, unquote, urlparse
from bs4 import BeautifulSoup
import random
from datetime import date
import pandas as pd


class OrganizationLinkFinder:
    def __init__(self, csv_file_path: str):
        self.csv_file_path = csv_file_path
        self.organizations = []
        self.results = []
        self.session = requests.Session()

        # Set up session headers to appear more like a browser
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )

        print("✓ DuckDuckGo search available")
        print("✓ String-based scoring enabled")

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

    def normalize_string(self, text: str) -> str:
        """Normalize string for comparison by removing special chars and converting to lowercase"""
        # Remove common suffixes and legal forms
        text = re.sub(r'\b(gmbh|inc|ltd|llc|ag|e\.v\.|ev|ggmbh|co|corp|corporation)\b', '', text, flags=re.IGNORECASE)
        # Remove special characters and convert to lowercase
        text = re.sub(r'[^a-z0-9\s]', ' ', text.lower())
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text

    def get_organization_tokens(self, org_name: str) -> List[str]:
        """Extract meaningful tokens from organization name"""
        normalized = self.normalize_string(org_name)
        tokens = normalized.split()
        # Filter out very short tokens (likely not meaningful)
        tokens = [t for t in tokens if len(t) > 2]
        return tokens

    def score_result(self, org_name: str, result: Dict, position: int) -> float:
        """Score a search result based on string matching with organization name"""
        score = 0.0
        
        url = result.get("url", "").lower()
        title = result.get("title", "").lower()
        description = result.get("description", "").lower()
        
        # Get organization tokens
        org_tokens = self.get_organization_tokens(org_name)
        org_normalized = self.normalize_string(org_name)
        
        # Extract domain from URL
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        domain = re.sub(r'^www\.', '', domain)  # Remove www prefix
        domain_normalized = self.normalize_string(domain)
        
        # 1. Full organization name match in domain (highest priority)
        if org_normalized in domain_normalized:
            score += 50
        
        # 2. Token matching in domain
        domain_token_matches = sum(1 for token in org_tokens if token in domain_normalized)
        score += domain_token_matches * 15
        
        # 3. Acronym matching in domain
        if len(org_tokens) >= 2:
            acronym = ''.join([token[0] for token in org_tokens])
            if len(acronym) >= 2 and acronym in domain_normalized:
                score += 25
        
        # 4. Token matching in title
        title_normalized = self.normalize_string(title)
        title_token_matches = sum(1 for token in org_tokens if token in title_normalized)
        score += title_token_matches * 8
        
        # 5. Full organization name in title
        if org_normalized in title_normalized:
            score += 20
        
        # 6. Token matching in description
        description_normalized = self.normalize_string(description)
        desc_token_matches = sum(1 for token in org_tokens if token in description_normalized)
        score += desc_token_matches * 4
        
        # 7. Full organization name in description
        if org_normalized in description_normalized:
            score += 10
        
        # 8. Official domain TLDs bonus
        if domain.endswith('.org'):
            score += 12
        elif domain.endswith('.gov') or domain.endswith('.edu'):
            score += 15
        elif domain.endswith('.de') or domain.endswith('.nrw') or domain.endswith('.eu'):
            score += 8
        
        # 9. Official keywords in title/description
        official_keywords = ['official', 'home', 'homepage', 'hauptseite', 'startseite', 'offiziell', 'offizielle']
        if any(keyword in title_normalized for keyword in official_keywords):
            score += 10
        if any(keyword in description_normalized for keyword in official_keywords):
            score += 5
        
        # 10. Position bonus (earlier results are often better)
        position_bonus = max(0, 10 - position) * 2
        score += position_bonus
        
        # 11. Penalties for unwanted indicators
        penalty_keywords = ['news', 'blog', 'forum', 'jobs', 'karriere', 'press', 'presse', 'wiki']
        for keyword in penalty_keywords:
            if keyword in url or keyword in title_normalized:
                score -= 10
        
        return max(0, score)

    def analyze_results_with_scoring(
        self, org_name: str, results: List[Dict]
    ) -> Optional[str]:
        """Analyze search results using string-based scoring and pick the best URL"""
        if not results:
            return None

        # Score all results
        scored_results = []
        for i, result in enumerate(results):
            score = self.score_result(org_name, result, i)
            scored_results.append({
                'url': result.get('url'),
                'title': result.get('title'),
                'score': score
            })
        
        # Sort by score (highest first)
        scored_results.sort(key=lambda x: x['score'], reverse=True)
        
        # Print top 3 results for debugging
        print(f"    Top 3 scored results:")
        for i, sr in enumerate(scored_results[:3], 1):
            print(f"      {i}. Score: {sr['score']:.1f} - {sr['url']}")
        
        # Return the URL with the highest score if it meets minimum threshold
        if scored_results[0]['score'] >= 15:  # Minimum threshold
            return scored_results[0]['url']
        
        return None

    def find_organization_website(self, org_name: str) -> Dict:
        """Find website for a single organization"""
        result = {"organization": org_name, "website": None, "method": "not_found"}

        # Search using multiple engines
        search_results = self.search_engines(org_name)
        if not search_results:
            return result

        # Analyze results with scoring
        print("    Analyzing search results with scoring algorithm...")
        best_url = self.analyze_results_with_scoring(org_name, search_results)
        if best_url:
            result["website"] = best_url
            result["method"] = "scoring_analysis"
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

    def save_results(self, output_file: str):
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
        scoring_found = len([r for r in self.results if r["method"] == "scoring_analysis"])
        search_found = len(
            [r for r in self.results if r["method"] == "search_first_result"]
        )

        print("\nSUMMARY:")
        print(f"Total organizations: {total}")
        print(f"Websites found: {found}")
        print(f"Scoring analysis: {scoring_found}")
        print(f"Search first result: {search_found}")
        print(
            f"Success rate: {(found/total*100):.1f}%"
            if total > 0
            else "Success rate: 0.0%"
        )


def find_correct_organization_links():
    today = str(date.today())
    combined_projects_csv = f"project_code/MarkdownConverter/data/csv/{today}_combined_all_projects.csv"
    
    finder = OrganizationLinkFinder(combined_projects_csv)

    print("Loading organizations from CSV...")
    finder.load_csv_data()

    if not finder.organizations:
        print("No organizations found!")
        return

    # Process all organizations
    finder.process_all_organizations()

    # Save and show results
    finder.save_results(output_file=f"MarkdownConverter/OrganizationLinkFinder/{today}_organization_websites.json")
    finder.print_summary()


if __name__ == "__main__":
    find_correct_organization_links()
