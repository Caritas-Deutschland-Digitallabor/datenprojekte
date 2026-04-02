import pandas as pd
from Webscraping.Citylab_Berlin.scrape_projects_from_citylab_website import scrape_citylab_berlin
from Webscraping.CodeFor.scrape_projects_from_codefor_website import scrape_codefor
from Webscraping.Civic_Coding.scrape_all_community_projects_with_playwright import scrape_civic_coding
from Webscraping.get_ai_data import enrich_projects_data_with_ai
from MarkdownConverter.data.csv.Combined_InsertDict import combine_projects_data
from MarkdownConverter.OrganizationLinkFinder.organization_link_finder import find_correct_organization_links
from MarkdownConverter.mdConverter_Projekt import create_obsidian_vault
from datetime import date
from misc.check_website_reachability import check_websites

# # Scrape CityLAB Berlin Projects
# citylab_berlin_projects = scrape_citylab_berlin(
# 		url="https://citylab-berlin.org/de/projects/",
# 		save_to_csv=True
# 	)

# citylab_berlin_projects_enriched = enrich_projects_data_with_ai(
#     projects_data=citylab_berlin_projects,
#     type_of_data="Citylab_Berlin",
#     fetch_project_links_from_scrape=True
#     )

# # Scrape Code For Germany Projects
# codefor_projects = scrape_codefor(
# 		url="https://codefor.de/projekte/alle/",
# 		save_to_csv=True
# 	)

# codefor_projects_enriched = enrich_projects_data_with_ai(
#     projects_data=codefor_projects,
#     use_selenium=True,
#     type_of_data="CodeFor",
#     project_status_via_llm=True
#     )

# Scrape Civic Coding Projects
civic_coding_projects = scrape_civic_coding(
    save_to_csv=True
)

civic_coding_projects_enriched = enrich_projects_data_with_ai(
    civic_coding_projects,
    type_of_data="Civic_Coding",
    project_status_via_llm=True,
    fetch_project_links_from_scrape=True
    )


combine_projects_data(
    individual_projects_data_files=[
        "project_code/Webscraping/Correlaid-Projektdatenbank/2026-01-19_Correlaid-Projekte-via-API_enriched.csv",
        "project_code/Webscraping/PublicInterestAI/PublicInterestAI_Projekte_enriched.csv",
        "project_code/Webscraping/Erfolgsgeschichten/Liste der Projekte Datenerfolgsgeschichten.csv",
        # citylab_berlin_projects_enriched,
        # codefor_projects_enriched,
        civic_coding_projects_enriched
    ]  
)

find_correct_organization_links()

today = str(date.today())
joint_projects_file_path=f"project_code/MarkdownConverter/data/csv/{today}_combined_projects_with_term_dictionaries.csv"
check_websites(
    joint_projects_file_path,
    url_column="Webseite-Link",
    date=today,
    timeout=5,
    max_workers=20,
)

create_obsidian_vault(
    joint_projects_file_path=joint_projects_file_path,
    organization_urls_file_path=f"project_code/MarkdownConverter/OrganizationLinkFinder/{today}_organization_websites.json",
)