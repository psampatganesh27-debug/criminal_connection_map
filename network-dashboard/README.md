# Net-Weaver OSINT
A temporal graph intelligence platform designed for law enforcement and OSINT analysts to map criminal syndicates. Net-Weaver ingests both raw police narratives and structured data logs, resolving entities into a live, time-scrubbable relationship map. 

## The Core Concept
Investigations generate fragmented data spanning written reports, phone logs, and bank statements. Net-Weaver connects these pieces automatically. It extracts suspects, vehicles, and phones from unstructured text using NLP, merges them with bulk CSV uploads, and visualizes the network. Everything is tracked with strict chain-of-custody metadata to ensure the intelligence is court-ready.

## Key Features

*   **Dual Ingestion Engine:** Paste raw FIR (First Information Report) text to automatically extract suspects, phones, and vehicles via NLP. Alternatively, upload structured CSV files for Call Data Records (CDR) and Bank Ledgers.
*   **Temporal Ghosting:** A live timeline slider that allows analysts to scrub through time. Nodes and relationships fade out if they did not exist at the selected date, revealing how the syndicate evolved.
*   **Smart Entity Resolution:** Uses fuzzy string matching to prevent duplicate suspect nodes when names are misspelled or entered differently across multiple reports.
*   **Live Map Auto-Focus:** When new intelligence is ingested, the map automatically centers on the newly spawned entities and highlights them with a temporary neon pulse, ensuring analysts never lose track of expanding networks.
*   **Court-Ready PDF Generation:** Click any node to instantly generate a strict, tamper-evident PDF dossier. The backend pulls absolute truth from the database, formatting entity properties and first-degree connections into a clean ReportLab layout.
*   **Advanced Analytics:** Includes dual-node shortest pathfinding and a live "Key Influencers" leaderboard powered by network betweenness centrality.

## Tech Stack

**Frontend**
*   React.js
*   react-force-graph-2d (Canvas-based physics engine)

**Backend & Data Pipeline**
*   Python & FastAPI (REST API)
*   spaCy (NLP Entity Extraction)
*   Pandas (Structured CSV parsing)
*   NetworkX (Graph analytics and centrality scoring)
*   ReportLab (Programmatic PDF generation)
*   RapidFuzz (Fuzzy string matching)

**Database**
*   Neo4j (Graph Database)

## Getting Started

1. Start your local Neo4j database instance and ensure credentials match the backend configuration.
2. Install Python dependencies: `pip install fastapi uvicorn neo4j networkx spacy rapidfuzz pandas reportlab python-multipart`
3. Download the NLP model: `python -m spacy download en_core_web_sm`
4. Run the FastAPI backend: `uvicorn main:app --reload`
5. Install React dependencies and start the frontend: `npm install` followed by `npm start` (or `npm run dev`).
**Key Capabilities:**
* Extracts suspects, phones, and vehicles from raw police reports using real-time NLP.
* Ingests structured Call Data Records (CDR) and bank ledgers via a dedicated CSV pipeline.
* Visualizes complex criminal networks using an optimized, physics-based ForceGraph2D engine.
* Features a temporal timeline scrubber to track chain of custody and ghost out future events.
* Generates court-ready, tamper-evident PDF dossiers directly from the backend database.
* Includes auto-focus camera tracking and neon visual pinging for newly ingested intelligence.

### 💻 Tech Stack & Tools

* **Frontend:** React.js, ForceGraph2D, HTML5 Canvas
* **Backend:** Python, FastAPI
* **Database:** Neo4j (Graph Database), Cypher
* **Data Processing:** Pandas, spaCy (NLP), ReportLab (PDF Generation)

