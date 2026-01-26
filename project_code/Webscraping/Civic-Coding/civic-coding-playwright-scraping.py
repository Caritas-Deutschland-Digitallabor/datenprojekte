from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import json
import pandas as pd


def scrape_civic_coding_projects():
    """
    Scrape all project links and headlines with 50 results per page
    """
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            page.goto("https://www.civic-coding.de/community-information/projekte")
            print("Loaded initial page")
            
            # Click "50" button
            try:
                page.wait_for_selector("text=50", timeout=10000)
                page.click("text=50")
                print("Selected 50 results per page")
                page.wait_for_load_state('networkidle')
                time.sleep(1)
                
            except Exception as e:
                print(f"Could not find 50 results button: {e}")
            
            # Get total pages
            total_pages = get_total_pages(page)
            print(f"Found {total_pages} pages to scrape")
            
            # Scrape all pages
            all_project_data = []
            
            for page_num in range(1, total_pages + 1):
                print(f"\nScraping page {page_num}/{total_pages}")
                
                html_content = page.content()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extract project data (links + headlines)
                project_data = extract_project_data(soup)
                print(f"Found {len(project_data)} projects on page {page_num}")
                
                all_project_data.extend(project_data)
                
                if page_num < total_pages:
                    if not go_to_next_page(page):
                        break
                    page.wait_for_load_state('networkidle')
                    time.sleep(1)
            
            print(f"\n{'='*50}")
            print(f"Total projects scraped: {len(all_project_data)}")
            return all_project_data
        
        finally:
            browser.close()


def get_total_pages(page):
    """Determine total number of pages from pagination"""
    try:
        html_content = page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        pagination_links = soup.find_all('a', class_='solr-ajaxified')
        
        page_numbers = []
        for link in pagination_links:
            href = link.get('href', '')
            if 'tx_solr%5Bpage%5D=' in href:
                import re
                match = re.search(r'tx_solr%5Bpage%5D=(\d+)', href)
                if match:
                    page_numbers.append(int(match.group(1)))
        
        return max(page_numbers) if page_numbers else 1
    
    except Exception as e:
        print(f"Error determining total pages: {e}")
        return 1


def extract_project_data(soup):
    """Extract project links and headlines - handling multiple classes"""
    project_data_list = []
    
    # Find all div elements with class "projects-list--content"
    project_containers = soup.find_all('div', class_='projects-list--content')
    
    print(f"Found {len(project_containers)} project containers")
    
    for container in project_containers:
        h3_headline = container.find('h3', class_=['projects-headline', 'h5'])
        
        link_element = container.find(
            'div',
            class_='link'
        )
        
        if h3_headline:
            headline_text = h3_headline.text.strip()
        else:
            headline_text = None
            print("Warning: No headline found in container")
        
        if link_element:
            link = link_element.find('a').get('href')

            if not link.startswith("http"):
                full_link = "https://www.civic-coding.de" + link
            else:
                full_link = link

        else:
            full_link = pd.NA
            print("Warning: No link found in container")
        
        project_data_list.append({
                'headline': headline_text,
                'link': full_link
            })
    
    return project_data_list


def go_to_next_page(page):
    """Click the next page button"""
    try:
        next_button = page.locator('li.search-pagination-list-item.next a').first
        
        if next_button.is_visible():
            next_button.click()
            print("Clicked next page button")
            return True
        else:
            print("Next button not visible (probably on last page)")
            return False
            
    except Exception as e:
        print(f"Error clicking next button: {e}")
        return False


# Run the scraper
if __name__ == "__main__":
    all_projects = scrape_civic_coding_projects()
    
    # Convert to DataFrame
    df = pd.DataFrame(all_projects)
    print(df.head())

    # Save to CSV
    df.to_csv('projects.csv', index=False, encoding='utf-8')