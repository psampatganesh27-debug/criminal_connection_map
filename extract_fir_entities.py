import re
import spacy
from neo4j import GraphDatabase

URI = "neo4j://localhost:7687"
USER = "neo4j"
PASSWORD = "sih2026password"

nlp = spacy.load("en_core_web_sm")

# Patterns for Indian identifiers
PHONE_PATTERN = r"\+91\d{10}"
VEHICLE_PATTERN = r"[A-Z]{2}\d{2}-[A-Z]{1,2}-\d{4}"


def extract_entities(text):
  doc = nlp(text)

  # Extract names identified by spaCy NER
  persons = [ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON"]

  # Extract phone numbers and vehicle plates via regex
  phones = re.findall(PHONE_PATTERN, text)
  vehicles = re.findall(VEHICLE_PATTERN, text)

  return {
      "persons": list(set(persons)),
      "phones": list(set(phones)),
      "vehicles": list(set(vehicles)),
  }


def link_fir_entities():
  driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

  with driver.session() as session:
    # Fetch all FIRs
    result = session.run("MATCH (f:FIR) RETURN f.fir_number AS fir_no, f.narrative AS text")
    firs = [(record["fir_no"], record["text"]) for record in result]

    for fir_no, narrative in firs:
      if not narrative:
        continue

      extracted = extract_entities(narrative)
      print(f"\n[FIR: {fir_no}]")
      print(f"  Extracted Entities: {extracted}")

      # Link Persons to FIR
      for person_name in extracted["persons"]:
        query = """
                MATCH (f:FIR {fir_number: $fir_no})
                MERGE (p:Person {name: $person_name})
                MERGE (p)-[:MENTIONED_IN]->(f)
                """
        session.run(query, fir_no=fir_no, person_name=person_name)

      # Link Vehicles to FIR
      for vehicle_no in extracted["vehicles"]:
        query = """
                MATCH (f:FIR {fir_number: $fir_no})
                MERGE (v:Vehicle {plate_number: $vehicle_no})
                MERGE (v)-[:INVOLVED_IN]->(f)
                """
        session.run(query, fir_no=fir_no, vehicle_no=vehicle_no)

      # Link Phones to FIR
      for phone_no in extracted["phones"]:
        query = """
                MATCH (f:FIR {fir_number: $fir_no})
                MATCH (p:Phone {number: $phone_no})
                MERGE (p)-[:ASSOCIATED_WITH]->(f)
                """
        session.run(query, fir_no=fir_no, phone_no=phone_no)

  driver.close()
  print("\n[+] Successfully linked FIR entities into the graph.")


if __name__ == "__main__":
  link_fir_entities()