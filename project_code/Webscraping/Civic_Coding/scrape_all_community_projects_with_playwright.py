from playwright.sync_api import sync_playwright
import pandas as pd

def scrape_with_playwright(username, password):
    with sync_playwright() as p:
        # 1. Launch Browser
        browser = p.chromium.launch(headless=False) # Set to False to watch it happen
        context = browser.new_context()
        page = context.new_page()

        # 2. Go to Login Page
        print("Navigating to login...")
        page.goto("https://www.civic-coding.de/anmelden")

        # 3. Fill in credentials (using the actual selectors from the site)

        # Wait for the password field to appear on the screen
        page.wait_for_selector('#user')

        # Clear any existing text and type the password
        page.fill('#user', username)

        # Wait for the password field to appear on the screen
        page.wait_for_selector('#pass')

        # Clear any existing text and type the password
        page.fill('#pass', password)

        # 4. Press Enter to submit (often more reliable than clicking a button)
        page.keyboard.press("Enter")

        # 4. Wait for navigation to complete
        page.wait_for_load_state("networkidle")

        # 5. Check if we are logged in (look for the "Abmelden" text)
        if "bist aber nicht eingeloggt" in page.content():
            print("❌ Login Failed. Check credentials or selectors.")
            browser.close()
            return None
        else:
            print("✅ Login Successful!")


        # 6. Scrape the Projects
        all_data = []
        for page_num in range(1, 5): # Example: first 5 pages
            url = f"https://www.civic-coding.de/community/projekte?tx_solr%5Bpage%5D={page_num}"
            print(f"Scraping {url}...")
            page.goto(url)
            page.wait_for_selector(".projects-list--content")

            # Extract data using Javascript logic inside the browser
            projects = page.query_selector_all(".projects-list--content")
            for project in projects:
                title = project.query_selector(".projects-headline").inner_text()
                summary = project.query_selector(".projects-text").inner_text()
                
                all_data.append({
                    "Projektname": title.strip(),
                    "Kurzzusammenfassung": summary.strip(),
                    "Quelle": page.url
                })

        browser.close()
        return pd.DataFrame(all_data)

# Usage
df = scrape_with_playwright("juosth@gmail.com", "hvb.yru.cyf4whe5MWV")
print(df.head())