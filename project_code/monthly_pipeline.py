import pandas as pd
from Webscraping.Citylab_Berlin.scrape_projects_from_citylab_website import scrape_citylab_berlin
from Webscraping.get_ai_data import enrich_projects_data_with_ai
from MarkdownConverter.data.csv.Combined_InsertDict import combine_projects_data
from MarkdownConverter.OrganizationLinkFinder.organization_link_finder import find_correct_organization_links
from MarkdownConverter.mdConverter_Projekt import create_obsidian_vault
from datetime import date

# # Scrape CityLAB Berlin Projects
# citylab_berlin_projects = scrape_citylab_berlin(
# 		url="https://citylab-berlin.org/de/projects/",
# 		save_to_csv=True
# 	)

# # # Actually, with the further project setup it is better to write out the data as CSV file instead
# citylab_berlin_projects_enriched = enrich_projects_data_with_ai(
#     citylab_berlin_projects,
#     type_of_data="Citylab_Berlin"
#     )

# TODO: CodeFor Scraping
# TODO: Civic Coding Scraping


combine_projects_data(
    individual_projects_data_files=[
        "project_code/Webscraping/Citylab_Berlin/test-projekte.csv",
        # "project_code/Webscraping/PublicInterestAI/PublicInterestAI_Projekte_enriched.csv",
        # "project_code/Webscraping/Erfolgsgeschichten/Liste der Projekte Datenerfolgsgeschichten.csv",
        # citylab_berlin_projects_enriched,
        # TODO: Path to scraped CodeFor data
        # TODO: Path to scraped Civic Coding data
    ]  
)

find_correct_organization_links()

today = str(date.today())

create_obsidian_vault(
    joint_projects_file_path=f"project_code/MarkdownConverter/data/csv/{today}_combined_projects_with_term_dictionaries.csv",
    organization_urls_file_path=f"project_code/MarkdownConverter/OrganizationLinkFinder/{today}_organization_websites.json",
)