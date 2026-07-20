import pandas as pd
from Webscraping.Citylab_Berlin.scrape_projects_from_citylab_website import scrape_citylab_berlin
from Webscraping.CodeFor.scrape_projects_from_codefor_website import scrape_codefor
from Webscraping.Correlaid_Projektdatenbank.retrieve_projects_from_correlaid_api import fetch_correlaid_projects
from Webscraping.Civic_Coding.scrape_all_community_projects_with_playwright import scrape_civic_coding_community_projects
from Webscraping.Civic_Coding.scrape_projects_from_civic_coding_projektlandkarte_api import source_civic_coding_projektlandkarte_projects
from Webscraping.get_ai_data import enrich_projects_data_with_ai
from MarkdownConverter.data.csv.Combined_InsertDict import combine_projects_data
from MarkdownConverter.OrganizationLinkFinder.organization_link_finder import find_correct_organization_links
from MarkdownConverter.mdConverter_Projekt import create_obsidian_vault
from datetime import date
from misc.check_website_reachability import check_websites
from misc.publish_data import publish_data
from misc.deduplicate_projects_data import source_all_projects_for_deduplication, deduplicate_projects, remove_duplicated_rows

# Scrape/Fetch Projects
## Scrape CityLAB Berlin Projects
citylab_berlin_projects = scrape_citylab_berlin(
		url="https://citylab-berlin.org/de/projects/",
		save_to_csv=True
	)

## Scrape Code For Germany Projects
codefor_projects = scrape_codefor(
		url="https://codefor.de/projekte/alle/",
		save_to_csv=True
	)

## Fetch Correlaid Projects
correlaid_projects = fetch_correlaid_projects(
		save_to_csv=True
	)

## Collect Civic Coding Projects (TODO: Once Civic Coding can be scraped again regularly, this can be uncommented again)
# ### 1 - Scrape Community Projects
# civic_coding_community_projects = scrape_civic_coding_community_projects(
#     save_to_csv=True
# )

# ### 2 - Fetch Projektlandkarte Projects
# civic_coding_projektlandkarte_projects = source_civic_coding_projektlandkarte_projects(
#     save_to_csv=True
# )

# Deduplicate all project data in place
public_interest_ai_projects = pd.read_csv("project_code/Webscraping/PublicInterestAI/2026-04-15_PublicInterestAI-Projekte-via-Scraping_enriched.csv", sep=";").reset_index(names='Index')
erfolgsgeschichten_projects = pd.read_csv("project_code/Webscraping/Erfolgsgeschichten/Liste der Projekte Datenerfolgsgeschichten.csv").reset_index(names='Index')
# TODO: Remove this next line, once Civic Coding can be scraped again regularly
civic_coding_projects_enriched = pd.read_csv("project_code/Webscraping/Civic_Coding/2026-04-07_Civic_Coding-Projekte-via-Scraping_enriched.csv", sep=";").drop(columns=["Index"]).reset_index(names="Index")


# Map the string name → the actual DataFrame object
dataframe_lookup = {
    "CityLAB Berlin": citylab_berlin_projects,
    "CodeFor Germany": codefor_projects,
    # TODO: Remove this next line, once Civic Coding can be scraped again regularly
    "Civic Coding": civic_coding_projects_enriched,
    # TODO: Once Civic Coding can be scraped again regularly, this can be uncommented again
    # "Civic Coding Community": civic_coding_community_projects,
    # "Civic Coding Projektlandkarte": civic_coding_projektlandkarte_projects,
    "Correlaid": correlaid_projects,
    "Datenerfolgsgeschichten": erfolgsgeschichten_projects,
    "PublicInterestAI": public_interest_ai_projects
}

# TODO: Remove this next line, once Civic Coding can be scraped again regularly
all_projects_to_be_deduplicated = source_all_projects_for_deduplication(
    list_of_projects_dataframes=[
        citylab_berlin_projects,
        codefor_projects,
        civic_coding_projects_enriched,
        correlaid_projects,
        erfolgsgeschichten_projects,
        public_interest_ai_projects],
    dataframe_lookup=dataframe_lookup,
)
# TODO: Once Civic Coding can be scraped again regularly, this can be uncommented again
# all_projects_to_be_deduplicated = source_all_projects_for_deduplication(
#     list_of_projects_dataframes=[citylab_berlin_projects, codefor_projects, civic_coding_community_projects, civic_coding_projektlandkarte_projects, correlaid_projects, erfolgsgeschichten_projects, public_interest_ai_projects],
#     dataframe_lookup=dataframe_lookup,
# )

# Deduplicate projects data
duplicated_projects = deduplicate_projects(all_projects_to_be_deduplicated)

# Iterate over the duplicates dict and drop rows in-place
for source_name, duplicate_indices in duplicated_projects.items():
    remove_duplicated_rows(dataframe_lookup, source_name, duplicate_indices)

# Enrich regularly scraped/fetched projects with AI
## CityLAB Berlin Projects
citylab_berlin_projects_enriched = enrich_projects_data_with_ai(
    projects_data=citylab_berlin_projects,
    type_of_data="Citylab_Berlin",
    fetch_project_links_from_scrape=True
    )

## CodeFor Germany Projects
codefor_projects_enriched = enrich_projects_data_with_ai(
    projects_data=codefor_projects,
    use_selenium=True,
    type_of_data="CodeFor",
    project_status_via_llm=True
    )

## Correlaid Projects
correlaid_projects_enriched = enrich_projects_data_with_ai(
    projects_data=correlaid_projects,
    use_selenium=True,
    type_of_data="Correlaid_Projektdatenbank",
    )

## Civic Coding Projects: Community + Projektlandkarte (TODO: Once Civic Coding can be scraped again regularly, this can be uncommented again)
# civic_coding_projects_without_duplicates = pd.concat([civic_coding_community_projects, civic_coding_projektlandkarte_projects], ignore_index=True)

# civic_coding_projects_enriched = enrich_projects_data_with_ai(
#     civic_coding_projects_without_duplicates,
#     type_of_data="Civic_Coding",
#     project_status_via_llm=True,
#     fetch_project_links_from_scrape=True
# )

# Combine finally AI-enriched projects data
combine_projects_data(
    individual_projects_dataframes=[
        correlaid_projects_enriched,
        public_interest_ai_projects,
        erfolgsgeschichten_projects,
        citylab_berlin_projects_enriched,
        codefor_projects_enriched,
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

publish_data(joint_projects_file_path, output_csv="data.csv")