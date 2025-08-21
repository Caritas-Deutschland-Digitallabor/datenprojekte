# datenprojekte
Hier sammelt das Civic Data Lab gemeinwohlorientierte Datenprojekte


***
## Obsidian-Vault to Cosma-Graph

1. Installation of Cosma
2. `python3 obsidian2cosma.py -i CaritasDigitaleLandkarte-Vault -o CaritasDigitaleLandkarte-cosma/data`
3. go to the `data/CaritasDigitaleLandkarte-cosma/data` folder and type `cosma c` for new project or `cosma m` if you want to generate the html document from the converted vault


# TODOs
## Webscraping
- [x] Add urls for all projects
- [x] Create one csv structure from Vorlage_Project.md
- [x] Build AI based scraping to fill csv file
- [ ] Scrape and fill into all csv files

## Data preparation
- [ ] Create csv to project md

## Deployment
- [x] Check template structure
- [x] Change example to new structure
- [ ] Make deployment pipeline
- [ ] Deploy cosma in github pages

Notes 21.08:
- converter
  - bleiben wir bei tags oder nested tags oder gehen wir zu links
- prompt anpassen
  - projekt abkürzung in neuer spalte, falls existiert
  - webseieten  links, github, etc scrapen
