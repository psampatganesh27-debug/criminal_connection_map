from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from neo4j import GraphDatabase
import networkx as nx
import spacy
from rapidfuzz import process, fuzz
import re
from datetime import datetime
from fastapi import UploadFile, File, Form
import pandas as pd
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io

# Load the local NLP model into memory on startup
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    # Auto-downloads if missing during initial deployment
    import spacy.cli
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database Config ---
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "sih2026password" # Update to match your local instance

def get_db_session():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

class FIRInput(BaseModel):
    fir_number: str
    filing_date: str
    narrative: str
    analyst_id: str

# --- 1. Full Network Dump (Normal Mode) ---
@app.get("/api/network")
def get_network():
    driver = get_db_session()
    query = """
    MATCH (n)
    OPTIONAL MATCH (n)-[r]->(m)
    RETURN 
        elementId(n) as source_id, labels(n)[0] as source_label, n as source_props,
        elementId(m) as target_id, labels(m)[0] as target_label, m as target_props,
        type(r) as rel_type, properties(r) as rel_props
    """
    nodes_dict = {}
    links = []
    
    try:
        with driver.session() as session:
            result = session.run(query)
            for record in result:
                s_id = record["source_id"]
                if s_id and s_id not in nodes_dict:
                    nodes_dict[s_id] = {"id": s_id, "group": record["source_label"], "properties": dict(record["source_props"])}
                
                t_id = record["target_id"]
                if t_id and t_id not in nodes_dict:
                    nodes_dict[t_id] = {"id": t_id, "group": record["target_label"], "properties": dict(record["target_props"])}
                    
                if s_id and t_id:
                    links.append({
                        "source": s_id, "target": t_id,
                        "label": record["rel_type"], "properties": dict(record["rel_props"])
                    })
    finally:
        driver.close()
        
    return {"nodes": list(nodes_dict.values()), "links": links}

# --- 2. Map Propagation (Double-Click Expand) ---
@app.get("/api/network/expand")
def expand_node(node_id: str):
    driver = get_db_session()
    query = """
    MATCH (n)-[r]-(m)
    WHERE elementId(n) = $node_id
    RETURN 
        elementId(n) as source_id, labels(n)[0] as source_label, n as source_props,
        elementId(m) as target_id, labels(m)[0] as target_label, m as target_props,
        type(r) as rel_type, properties(r) as rel_props
    """
    nodes_dict = {}
    links = []
    
    try:
        with driver.session() as session:
            result = session.run(query, node_id=node_id)
            for record in result:
                s_id = record["source_id"]
                if s_id not in nodes_dict:
                    nodes_dict[s_id] = {"id": s_id, "group": record["source_label"], "properties": dict(record["source_props"])}
                    
                t_id = record["target_id"]
                if t_id not in nodes_dict:
                    nodes_dict[t_id] = {"id": t_id, "group": record["target_label"], "properties": dict(record["target_props"])}
                    
                links.append({
                    "source": s_id, "target": t_id,
                    "label": record["rel_type"], "properties": dict(record["rel_props"])
                })
    finally:
        driver.close()
    
    return {"nodes": list(nodes_dict.values()), "links": links}

# --- 3. Pathfinding Analytics ---
@app.get("/api/network/path")
def get_path(source_id: str, target_id: str):
    driver = get_db_session()
    query = """
    MATCH p = shortestPath((source)-[*]-(target))
    WHERE elementId(source) = $source_id AND elementId(target) = $target_id
    RETURN [node in nodes(p) | elementId(node)] as path_nodes
    """
    try:
        with driver.session() as session:
            result = session.run(query, source_id=source_id, target_id=target_id)
            record = result.single()
            path = record["path_nodes"] if record else []
            return {"path": path}
    finally:
        driver.close()

# --- 4. Centrality Leaderboard ---
@app.get("/api/analytics/influencers")
def get_key_influencers():
    driver = get_db_session()
    query = """
    MATCH (p1:Person)-[:OWNS]->(:Phone)-[:CALLED]-(:Phone)<-[:OWNS]-(p2:Person)
    RETURN p1.name as person_a, elementId(p1) as id_a, p2.name as person_b, elementId(p2) as id_b
    """
    G = nx.Graph()
    node_id_map = {} 
    
    try:
        with driver.session() as session:
            result = session.run(query)
            for record in result:
                name_a, id_a = record["person_a"], record["id_a"]
                name_b, id_b = record["person_b"], record["id_b"]
                
                G.add_edge(name_a, name_b)
                node_id_map[name_a] = id_a
                node_id_map[name_b] = id_b
    finally:
        driver.close() 
            
    centrality = nx.betweenness_centrality(G)
    sorted_influencers = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
    
    return [
        {"id": node_id_map.get(name), "name": name, "centrality_score": round(score, 4)} 
        for name, score in sorted_influencers if name in node_id_map
    ]

# --- 5. Real-Time NLP Ingestion & Resolution ---
@app.post("/api/ingest/fir")
def ingest_fir(fir: FIRInput):
    doc = nlp(fir.narrative)
    
    raw_suspects = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
    phones = re.findall(r'\+91\d{10}', fir.narrative)
    plates = re.findall(r'[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}', fir.narrative)
    
    driver = get_db_session()
    resolved_suspects = set()
    
    # Generate the exact moment of ingestion
    ingest_timestamp = datetime.utcnow().isoformat() + "Z"
    
    try:
        with driver.session() as session:
            result = session.run("MATCH (p:Person) RETURN p.name AS name")
            existing_db_suspects = [record["name"] for record in result if record["name"]]
            
            for name in raw_suspects:
                if not existing_db_suspects:
                    resolved_suspects.add(name)
                    continue
                
                match = process.extractOne(name, existing_db_suspects, scorer=fuzz.token_sort_ratio)
                if match and match[1] >= 85: 
                    resolved_suspects.add(match[0])
                else:
                    resolved_suspects.add(name)
                    existing_db_suspects.append(name) 

            suspect_list = list(resolved_suspects)

            # --- Audited Graph Construction ---
            session.run("""
                MERGE (f:FIR {fir_number: $fir_number})
                ON CREATE SET f.created_by = $analyst, f.ingested_at = $timestamp
                SET f.filing_date = $filing_date, f.narrative = $narrative
            """, fir_number=fir.fir_number, filing_date=fir.filing_date, narrative=fir.narrative, analyst=fir.analyst_id, timestamp=ingest_timestamp)
            
            for s_name in suspect_list:
                session.run("""
                    MATCH (f:FIR {fir_number: $fir_number})
                    MERGE (p:Person {name: $name})
                    ON CREATE SET p.created_by = $analyst, p.ingested_at = $timestamp, p.source_document = $fir_number
                    MERGE (p)-[rel:MENTIONED_IN]->(f)
                    ON CREATE SET rel.created_by = $analyst, rel.ingested_at = $timestamp
                """, fir_number=fir.fir_number, name=s_name, analyst=fir.analyst_id, timestamp=ingest_timestamp)
                
            for phone in phones:
                session.run("""
                    MATCH (f:FIR {fir_number: $fir_number})
                    MERGE (ph:Phone {number: $phone})
                    ON CREATE SET ph.created_by = $analyst, ph.ingested_at = $timestamp, ph.source_document = $fir_number
                    MERGE (ph)-[rel:MENTIONED_IN]->(f)
                    ON CREATE SET rel.created_by = $analyst, rel.ingested_at = $timestamp
                """, fir_number=fir.fir_number, phone=phone, analyst=fir.analyst_id, timestamp=ingest_timestamp)
            
            for plate in plates:
                session.run("""
                    MATCH (f:FIR {fir_number: $fir_number})
                    MERGE (v:Vehicle {plate_number: $plate})
                    ON CREATE SET v.created_by = $analyst, v.ingested_at = $timestamp, v.source_document = $fir_number
                    MERGE (v)-[rel:MENTIONED_IN]->(f)
                    ON CREATE SET rel.created_by = $analyst, rel.ingested_at = $timestamp
                """, fir_number=fir.fir_number, plate=plate, analyst=fir.analyst_id, timestamp=ingest_timestamp)

            if suspect_list and phones:
                session.run("""
                    MATCH (p:Person {name: $name}), (ph:Phone {number: $phone})
                    MERGE (p)-[rel:OWNS]->(ph)
                    ON CREATE SET rel.created_by = $analyst, rel.ingested_at = $timestamp, rel.source_document = $fir_number
                """, name=suspect_list[0], phone=phones[0], fir_number=fir.fir_number, analyst=fir.analyst_id, timestamp=ingest_timestamp)
                
            if len(phones) >= 2:
                session.run("""
                    MATCH (ph1:Phone {number: $phone1}), (ph2:Phone {number: $phone2})
                    MERGE (ph1)-[rel:CALLED {timestamp: $date}]->(ph2)
                    ON CREATE SET rel.created_by = $analyst, rel.ingested_at = $ingest_time, rel.source_document = $fir_number
                """, phone1=phones[0], phone2=phones[1], date=fir.filing_date, fir_number=fir.fir_number, analyst=fir.analyst_id, ingest_time=ingest_timestamp)

    finally:
        driver.close()
        
    return {
        "status": "success",
        "extracted": {
            "suspects": suspect_list,
            "phones": phones,
            "plates": plates
        }
    }

#Determines if it is phone data or bank data
@app.post("/api/ingest/structured")
async def ingest_csv(
    file: UploadFile = File(...),
    data_type: str = Form(...),
    analyst_id: str = Form(...)
):
    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents), dtype=str)
    
    driver = get_db_session()
    ingest_timestamp = datetime.utcnow().isoformat() + "Z"
    
    try:
        with driver.session() as session:
            if data_type == "CDR":
                for _, row in df.iterrows():
                    session.run("""
                        MERGE (p1:Phone {number: $caller})
                        ON CREATE SET p1.created_by = $analyst, p1.ingested_at = $timestamp, p1.source_document = $filename
                        MERGE (p2:Phone {number: $receiver})
                        ON CREATE SET p2.created_by = $analyst, p2.ingested_at = $timestamp, p2.source_document = $filename
                        MERGE (p1)-[r:CALLED {timestamp: $call_time}]->(p2)
                        ON CREATE SET r.duration = $duration, r.created_by = $analyst, r.ingested_at = $timestamp, r.source_document = $filename
                    """, caller=str(row['caller']), receiver=str(row['receiver']), call_time=str(row['timestamp']), duration=str(row['duration']), analyst=analyst_id, timestamp=ingest_timestamp, filename=file.filename)
                    
            elif data_type == "BANK":
                for _, row in df.iterrows():
                    session.run("""
                        MERGE (a1:Account {account_number: $sender})
                        ON CREATE SET a1.created_by = $analyst, a1.ingested_at = $timestamp, a1.source_document = $filename
                        MERGE (a2:Account {account_number: $receiver})
                        ON CREATE SET a2.created_by = $analyst, a2.ingested_at = $timestamp, a2.source_document = $filename
                        MERGE (a1)-[r:TRANSFERRED_TO {timestamp: $tx_time}]->(a2)
                        ON CREATE SET r.amount = $amount, r.created_by = $analyst, r.ingested_at = $timestamp, r.source_document = $filename
                    """, sender=str(row['sender']), receiver=str(row['receiver']), tx_time=str(row['timestamp']), amount=str(row['amount']), analyst=analyst_id, timestamp=ingest_timestamp, filename=file.filename)
                    
    finally:
        driver.close()
        
    return {"status": "success", "processed_rows": len(df)}

@app.get("/api/export/report/{node_id}")
def export_node_report(node_id: str):
    driver = get_db_session()
    node_data = {}
    connections = []

    # Pull the absolute truth from the database
    query = """
    MATCH (n) WHERE elementId(n) = $node_id
    OPTIONAL MATCH (n)-[r]-(m)
    RETURN n, type(r) as rel_type, m
    """
    
    try:
        with driver.session() as session:
            result = session.run(query, node_id=node_id)
            records = list(result)
            if not records:
                raise HTTPException(status_code=404, detail="Entity not found")
            
            # Extract target properties
            node_data = dict(records[0]["n"].items())
            
            # Extract connections
            for record in records:
                if record["m"]:
                    conn_prop = dict(record["m"].items())
                    rel = record["rel_type"]
                    target_name = conn_prop.get("name") or conn_prop.get("number") or conn_prop.get("account_number") or conn_prop.get("fir_number") or "Unknown"
                    connections.append([rel, target_name])
    finally:
        driver.close()

    # Build the PDF buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Document Header
    elements.append(Paragraph("NET-WEAVER INTELLIGENCE DOSSIER", styles['Title']))
    elements.append(Spacer(1, 12))

    # Entity Details Table
    elements.append(Paragraph("Target Entity Specifications", styles['Heading2']))
    
    details_data = [[k.replace('_', ' ').title(), str(v)] for k, v in node_data.items()]
    t_details = Table(details_data, colWidths=[150, 300])
    t_details.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_details)
    elements.append(Spacer(1, 20))

    # Relationships Table
    if connections:
        elements.append(Paragraph("First-Degree Operational Network", styles['Heading2']))
        conn_data = [["Relationship", "Connected Entity"]] + connections
        t_conn = Table(conn_data, colWidths=[150, 300])
        t_conn.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkslategray),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_conn)

    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer, 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename=Intelligence_Report_{node_id}.pdf"}
    )