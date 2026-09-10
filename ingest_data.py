import json
import pandas as pd
from neo4j import GraphDatabase

# Neo4j Connection Credentials
URI = "neo4j://localhost:7687"
USER = "neo4j"
PASSWORD = "sih2026password"


class CriminalGraphIngestion:

  def __init__(self, uri, user, password):
    self.driver = GraphDatabase.driver(uri, auth=(user, password))

  def close(self):
    self.driver.close()

  def clear_database(self):
    with self.driver.session() as session:
      session.run("MATCH (n) DETACH DELETE n")
      print("[!] Cleared existing graph database.")

  def load_firs(self, filepath="firs.json"):
    with open(filepath, "r", encoding="utf-8") as f:
      firs = json.load(f)

    with self.driver.session() as session:
      for fir in firs:
        query = """
                MERGE (f:FIR {fir_number: $fir_number})
                SET f.police_station = $police_station,
                    f.filing_date = $filing_date,
                    f.narrative = $narrative
                """
        session.run(
            query,
            fir_number=fir["fir_number"],
            police_station=fir["police_station"],
            filing_date=fir["filing_date"],
            narrative=fir["narrative"],
        )
    print(f"[+] Loaded {len(firs)} FIR nodes into Neo4j.")

  def load_cdrs(self, filepath="cdrs.csv"):
    df = pd.read_csv(filepath, dtype=str)

    with self.driver.session() as session:
      for _, row in df.iterrows():
        query = """
                MERGE (p1:Phone {number: $caller})
                MERGE (p2:Phone {number: $receiver})
                CREATE (p1)-[c:CALLED {
                    timestamp: $timestamp,
                    duration_seconds: $duration,
                    tower: $tower
                }]->(p2)
                """
        session.run(
            query,
            caller=str(row["caller_number"]),
            receiver=str(row["receiver_number"]),
            timestamp=str(row["timestamp"]),
            duration=int(row["duration_seconds"]),
            tower=str(row["tower_location"]),
        )
    print(f"[+] Loaded {len(df)} CDR relationships into Neo4j.")

  def load_bank_transactions(self, filepath="bank_transactions.csv"):
    df = pd.read_csv(filepath, dtype=str)

    with self.driver.session() as session:
      for _, row in df.iterrows():
        query = """
                MERGE (s:Account {account_number: $sender_acc})
                ON CREATE SET s.name = $sender_name
                
                MERGE (r:Account {account_number: $receiver_acc})
                ON CREATE SET r.name = $receiver_name
                
                CREATE (s)-[t:TRANSFERRED {
                    transaction_id: $tx_id,
                    amount_inr: $amount,
                    timestamp: $timestamp,
                    type: $tx_type
                }]->(r)
                """
        session.run(
            query,
            sender_acc=str(row["sender_account"]),
            sender_name=str(row["sender_name"]),
            receiver_acc=str(row["receiver_account"]),
            receiver_name=str(row["receiver_name"]),
            tx_id=str(row["transaction_id"]),
            amount=float(row["amount_inr"]),
            timestamp=str(row["timestamp"]),
            tx_type=str(row["transaction_type"]),
        )
    print(f"[+] Loaded {len(df)} financial transaction relationships into Neo4j.")

  def link_suspect_identities(self):
      """Bridges phone numbers and bank accounts to known suspect profiles."""
      suspects = [
          {
              "phone": "+919835012345",
              "account": "AC9988112233",
              "name": "Rahul Verma",
          },
          {
              "phone": "+919431054321",
              "account": "AC4455667788",
              "name": "Vikram Singh",
          },
          {
              "phone": "+919732098765",
              "account": "AC1122334455",
              "name": "Tariq Khan",
          },
          {
              "phone": "+919830011223",
              "account": "AC6677889900",
              "name": "Amit Banerjee",
          },
          {
              "phone": "+919831122334",
              "account": "AC5544332211",
              "name": "Sunita Sharma",
          },
      ]

      # Using MERGE ensures the nodes and relationships are created even if
      # the entity wasn't in the random noise transactions.
      query = """
        MERGE (per:Person {name: $name})
        MERGE (ph:Phone {number: $phone})
        MERGE (ac:Account {account_number: $account})
        MERGE (per)-[:OWNS]->(ph)
        MERGE (per)-[:OWNS]->(ac)
        """

      with self.driver.session() as session:
        for suspect in suspects:
          session.run(
              query,
              phone=suspect["phone"],
              account=suspect["account"],
              name=suspect["name"],
          )

      print("[+] Unified person identities with phone and bank records.")

if __name__ == "__main__":
  ingestor = CriminalGraphIngestion(URI, USER, PASSWORD)
  ingestor.clear_database()
  ingestor.load_firs()
  ingestor.load_cdrs()
  ingestor.load_bank_transactions()
  ingestor.link_suspect_identities()
  ingestor.close()
  print(
      "\nPipeline execution complete. All data successfully loaded into graph"
      " database."
  )