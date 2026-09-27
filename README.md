# NET-WEAVER OSINT: Criminal Syndicate Intelligence & Link Analysis

An end-to-end OSINT platform for law enforcement intelligence teams. Net-Weaver ingests unstructured police narratives (FIRs) and structured records (CDR and Banking data), resolves named entities, maps cross-entity relationships in real time, and renders an interactive graph powered by Neo4j AuraDB.

---

## Architecture Overview

* Frontend: React, Force-Directed Graph, Dynamic Inspector, Time Slider
* Backend: FastAPI, spaCy NER Extraction (PERSON, PHONE, VEHICLE), RapidFuzz Entity Resolution, NetworkX Centrality Analytics, ReportLab PDF Pipeline
* Database: Neo4j AuraDB Cloud Labeled Property Graph via Bolt/SSC

---

## Core Capabilities

* NLP Ingestion Pipeline: Uses spaCy to extract suspects, phone numbers, and vehicle plates directly from raw text reports, validating tokens to prevent alphanumeric misclassifications.
* Fuzzy Entity Resolution: Matches incoming suspect identities against stored database nodes via RapidFuzz token sort metrics (>= 85%), preventing duplicate entries from minor spelling variations.
* Betweenness Centrality Analytics: Computes key network influencers on demand using NetworkX, identifying central communication bridges across isolated cells.
* Pathfinding: Implements Neo4j shortest-path traversal to expose intermediary links between selected entities.
* Chain of Custody Tracking: Every ingested node and edge tracks an immutable metadata trail including creator ID, timestamp, and source document.
* Intelligence Dossier Generation: Backend-driven PDF generation compiles real-time first-degree connection reports and target properties into downloadable briefs.

---

## Tech Stack

* Frontend: React, react-force-graph-2d, D3 Force Engine, Lucide Icons
* Backend: Python 3, FastAPI, Uvicorn, spaCy, RapidFuzz, NetworkX, ReportLab, Pandas
* Database: Neo4j AuraDB Cloud

---

## Local Development Setup

### 1. Clone Repository

git clone [https://github.com/your-username/net-weaver-osint.git](https://www.google.com/search?q=https://github.com/your-username/net-weaver-osint.git&utm_source=gemini)
cd net-weaver-osint

### 2. Backend Setup

cd backend
python -m venv .venv

# On Linux/macOS:

source .venv/bin/activate

# On Windows:

.venv\Scripts\activate

pip install -r requirements.txt
python -m spacy download en_core_web_sm

Create a .env file in the backend folder:
NEO4J_URI=neo4j+ssc://<YOUR_INSTANCE_ID>.databases.neo4j.io
NEO4J_USER=<YOUR_NEO4J_USER>
NEO4J_PASSWORD=<YOUR_AURA_PASSWORD>

Start the backend:
uvicorn main:app --reload

### 3. Frontend Setup

cd ../frontend
npm install

Create a .env file in the frontend folder:
VITE_API_URL=http://localhost:8000

Start the frontend:
npm run dev

---

## API Endpoints

* GET /api/network - Fetches full graph dataset (nodes and links)
* GET /api/network/expand - Traverses first-degree edges for a given node
* GET /api/network/path - Computes shortest path between source and target IDs
* GET /api/analytics/influencers - Returns nodes ranked by betweenness centrality
* POST /api/ingest/fir - Extracts entities from unstructured text and merges into the graph
* POST /api/ingest/structured - Ingests Call Detail Records or Bank CSV files
* GET /api/export/report/{node_id} - Streams an intelligence dossier PDF for an entity

---

## Deployment Configuration

* Backend: Hosted on Render (Start command: uvicorn main:app --host 0.0.0.0 --port $PORT)
* Database: Hosted on Neo4j AuraDB Cloud
* Frontend: Hosted on Vercel with VITE_API_URL mapped to the Render backend domain
