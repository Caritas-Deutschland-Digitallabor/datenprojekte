#!/usr/bin/env python3
"""
Simple Organization Link Finder
Finds organization websites from CSV data using Brave Search API and scoring analysis
"""

import csv
import requests
import time
import re
import json
import os
from typing import Dict, Optional, List
from urllib.parse import quote, unquote, urlparse
import random
from datetime import date
import pandas as pd


class OrganizationLinkFinder:
    def __init__(self, csv_file_path: str):
        self.csv_file_path = csv_file_path
        self.organizations = []
        self.results = []
        self.session = requests.Session()
        
        # Fetch API Key from environment
        self.brave_api_key = os.getenv("BRAVE_API_KEY")

        # Session headers
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

        if not self.brave_api_key:
            print("⚠ Warning: BRAVE_API_KEY not found in environment variables.")
        else:
            print("✓ Brave Search API integration ready")
        print("✓ String-based scoring enabled")

    def load_csv_data(self) -> None:
        """Load organization names from CSV file"""
        try:
            with open(self.csv_file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file, delimiter=";")
                for row in reader:
                    org_field = row.get("Organisation", "").strip()

                    if org_field:
                        # Split only by comma (as previously preprocessing happended to ensure multiple organizations are separated by a comma)
                        org_names = re.split(r",", org_field)
                        org_names = [name.strip() for name in org_names if name.strip()]

                        for org_name in org_names:
                            if org_name and org_name.lower() not in [
                                org["name"].lower() for org in self.organizations
                            ]:
                                self.organizations.append({"name": org_name})
        except Exception as e:
            print(f"Error reading CSV file: {e}")

    def search_brave(self, org_name: str, retry_count: int = 0) -> List[Dict]:
        """Search using Brave Search API and return list of URLs with descriptions"""
        if not self.brave_api_key:
            return []

        try:
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": self.brave_api_key
            }
            params = {
                "q": f"{org_name} offizelle Website",
                "count": 5,  # Retrieve top 5 for scoring
                "country": "DE",
                "search_lang": "de"

            }

            # Brave Free Tier limit: 1 request per second
            time.sleep(1.1)

            response = self.session.get(url, headers=headers, params=params, timeout=15)
            
            # Handle rate limiting (429) specifically
            if response.status_code == 429 and retry_count < 2:
                print(f"    Rate limit hit. Waiting for retry {retry_count + 1}...")
                time.sleep(2)
                return self.search_brave(org_name, retry_count + 1)
            
            response.raise_for_status()
            data = response.json()
            
            raw_results = data.get("web", {}).get("results", [])
            results = []

            for r in raw_results:
                actual_url = r.get("url", "")
                title = r.get("title", "")
                description = r.get("description", "")

                if not actual_url.startswith("http"):
                    continue

                # Skip unwanted sites (maintain existing logic)
                if any(skip in actual_url.lower() for skip in ["wikipedia", "facebook", "twitter", "linkedin", "youtube", "instagram", "reddit"]):
                    continue

                results.append({
                    "url": actual_url,
                    "title": title,
                    "description": description
                })

            print(f"    Found {len(results)} results from Brave Search")
            return results

        except Exception as e:
            print(f"    Brave Search error: {e}")
            return []

    def search_engines(self, org_name: str) -> List[Dict]:
        """Search using Brave and return results with descriptions"""
        print("    Searching Brave Search API...")
        brave_results = self.search_brave(org_name)
        
        if brave_results:
            return brave_results

        # If Brave fails, try fallback domain guessing
        print("    Brave search failed/no results, trying domain guessing...")
        fallback_urls = self.fallback_search(org_name)

        # Convert simple URLs to result format
        results = []
        for url in fallback_urls:
            results.append({
                "url": url,
                "title": f"Potential official site for {org_name}",
                "description": f"Domain appears to be related to {org_name}",
            })
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
        search_results = self.search_engines(org_name)
        if not search_results:
            return result

        # Analyze results with scoring
        print("    Analyzing search results with scoring algorithm...")
        best_url = self.analyze_results_with_scoring(org_name, search_results)
        if best_url:
            result.update({"website": best_url, "method": "scoring_analysis"})
        else:
            result.update({"website": search_results[0].get("url"), "method": "search_first_result"})
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
    # Adjust path if script is run from a subfolder
    csv_path = f"project_code/MarkdownConverter/data/csv/{today}_combined_all_projects.csv"
    
    print("Loading organizations from CSV...")
    finder = OrganizationLinkFinder(csv_path)
    finder.load_csv_data()

    if not finder.organizations:
        print("No organizations found!")
        return

    # Process all organizations
    finder.process_all_organizations()

    # Save and show results
    finder.save_results(output_file=f"project_code/MarkdownConverter/OrganizationLinkFinder/{today}_organization_websites.json")
    finder.print_summary()


if __name__ == "__main__":
    find_correct_organization_links()
