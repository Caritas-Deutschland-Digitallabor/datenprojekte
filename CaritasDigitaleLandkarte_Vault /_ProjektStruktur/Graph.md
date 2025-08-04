```mermaid
flowchart TD
	subgraph "Struktur des Graphen"
		direction TB
		
		subgraph s2["Mit Projekten verlinkte Objekte"]
			direction LR
			A(["Organisationen (z.b. Caritas)"])
			C(["Oberthemen (z.b. Gesundheit)"])
		end
		
		P1{"Projekte"}
		
		subgraph s1["Tags & Labels"]
			W["Allgemeines Label: Klasse (z.b Projekt)"]
			X["Projekt Tag: Art (z.b Verzeichnis)"]
			Y["Projekt Tag: Einsatzbereiche (z.b Rettungsdienst)"]
			Z["Projekt Tag: Status (z.b. Testbetrieb)"]
		end
	end
	P1 --- s1
	P1 ==> A & C 
	s2 --- W
```
***
## Knoten
- Projekt
- Organisation 
- Thema (Zusammengefasste Einsatzbereiche) 
***
## Links
- Projekte -> Organisationen
- Projekte -> Themen
- Organisationen -> Themen 
***
## Tags / Labels 
- Klassen 
	- Projekt
	- Organisation
	- Thema
### Projekt Labels 
- Projekt: Art (Methodik)
	- KI Anwendung
	- Verzeichnis
	- Dokumentation
	- ...
- Projekt: Einsatzbereiche
	- Demokratie
	- Soziale Arbeit
	- Rettungsdienst 
	- ...
- Projekt: Status 
	- Online // Offline
	- Aktiv // Inaktiv
	- Planung/ Testbetrieb / Weiterentwicklung /Betrieb/ Abgeschlossen & Eingestellt
***