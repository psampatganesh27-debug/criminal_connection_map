# Net-Weaver OSINT

**Criminal Syndicate Relationship Mapping Platform**

Net-Weaver is a full-stack open-source intelligence (OSINT) and law enforcement platform. It ingests both structured financial logs and unstructured police narratives to automatically generate interactive, time-aware network graphs for criminal syndicate investigation.

## Core Features

*   **Multi-Modal Intelligence Ingestion:** Process unstructured police narratives (FIRs) via NLP entity extraction or upload structured CSVs for Call Data Records (CDR) and Bank Ledgers.
*   **Temporal Ghosting:** An interactive timeline slider that filters the graph based on the exact time of intelligence ingestion, allowing analysts to watch the syndicate network evolve chronologically.
*   **Live Visual Pinging:** Newly ingested entities automatically trigger a camera auto-focus and a 12-second neon pulsing highlight to ensure analysts never lose track of fresh data.
*   **Advanced Pathfinding & Analytics:** Instantly calculate the shortest operational path between any two targets and track syndicate leadership via a real-time Betweenness Centrality leaderboard.
*   **Evidentiary Dossier Generation:** One-click export of court-ready PDF intelligence reports directly from the database, ensuring strict data integrity and exact timestamps.

## Tech Stack

*   **Frontend:** React, ForceGraph2D
*   **Backend:** Python, FastAPI
*   **Database:** Neo4j (Graph Database)
*   **Data Processing & Export:** spaCy (NLP), pandas (DataFrames), ReportLab (PDF Generation)

## Prerequisites

Before running this project locally, ensure you have the following installed:
*   [Node.js](https://nodejs.org/) (v16 or higher)
*   [Python](https://www.python.org/) (v3.9 or higher)
*   [Neo4j Desktop](https://neo4j.com/download/) (Running locally on port 7687)

## Local Setup

### 1. Database Configuration
1. Start your local Neo4j database.
2. Ensure the credentials in `main.py` match your local Neo4j instance. By default, the app looks for:
   *   **URI:** `bolt://localhost:7687`
   *   **User:** `neo4j`
   *   **Password:** `_______`

### 2. Backend Initialization
Open a terminal in the root directory and set up the Python environment:

```bash
# Install required Python dependencies
pip install fastapi uvicorn neo4j networkx spacy rapidfuzz pandas python-multipart reportlab

# Download the NLP model for entity extraction
python -m spacy download en_core_web_sm

# Boot the FastAPI server
uvicorn main:app --reload
