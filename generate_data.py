import csv
import json
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker("en_IN")

# 1. Ground Truth Suspects & Entities
SUSPECTS = {
    "rahul": {
        "name": "Rahul Verma",
        "phone": "+919835012345",
        "account": "AC9988112233",
        "role": "Field Thief",
        "city": "Ranchi",
    },
    "vikram": {
        "name": "Vikram Singh",
        "phone": "+919431054321",
        "account": "AC4455667788",
        "role": "Fence / Handler",
        "city": "Ranchi",
    },
    "tariq": {
        "name": "Tariq Khan",
        "phone": "+919732098765",
        "account": "AC1122334455",
        "role": "Broker / Bridge",
        "city": "Dhanbad",
    },
    "amit": {
        "name": "Amit Banerjee",
        "phone": "+919830011223",
        "account": "AC6677889900",
        "role": "Hawala Operator",
        "city": "Kolkata",
    },
    "sunita": {
        "name": "Sunita Sharma",
        "phone": "+919831122334",
        "account": "AC5544332211",
        "role": "Shell Co Director",
        "city": "Kolkata",
    },
}

VEHICLES = ["JH01-BV-4321", "WB02-AK-9988", "JH10-CC-1122"]
COMPANIES = ["Apex Logistics Pvt Ltd", "Kolkata Trading Co"]

# 2. Generate 30 Innocent Background Entities
NOISE_USERS = []
for _ in range(30):
    NOISE_USERS.append(
        {
            "name": fake.name(),
            "phone": fake.phone_number()[-10:],
            "account": f"AC{random.randint(1000000000, 9999999999)}",
            "city": random.choice(["Ranchi", "Patna", "Kolkata", "Jamshedpur"]),
        }
    )

# Format noise phones with +91 prefix
for user in NOISE_USERS:
    user["phone"] = f"+91{user['phone']}"


# 3. Generate Call Detail Records (CDRs)
def generate_cdrs(filename="cdrs.csv", count=500):
    records = []
    base_time = datetime(2026, 8, 1, 8, 0, 0)

    # Coordinated suspicious calls (The Crime Chain)
    crime_pairs = [
        ("rahul", "vikram", 18),  # Frequent calls between thief and fence
        ("vikram", "tariq", 12),  # Fence contacts broker
        ("tariq", "amit", 10),    # Broker contacts Kolkata hawala
        ("amit", "sunita", 15),   # Hawala contacts shell company director
    ]

    for p1, p2, freq in crime_pairs:
        for _ in range(freq):
            call_time = base_time + timedelta(
                days=random.randint(0, 20),
                hours=random.choice([1, 2, 3, 23, 14]),  # Suspicious late night hours
                minutes=random.randint(1, 59),
            )
            records.append(
                {
                    "caller_number": SUSPECTS[p1]["phone"],
                    "receiver_number": SUSPECTS[p2]["phone"],
                    "timestamp": call_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "duration_seconds": random.randint(45, 900),
                    "tower_location": SUSPECTS[p1]["city"],
                    "call_type": "Voice",
                }
            )

    # Random background calls (Noise)
    # New logic: Ensure random calls always involve at least one innocent person
    suspect_phones = [s["phone"] for s in SUSPECTS.values()]
    noise_phones = [u["phone"] for u in NOISE_USERS]

    for _ in range(count - len(records)):
        c1 = random.choice(noise_phones) # Caller is always noise
        c2 = random.choice(suspect_phones + noise_phones) # Receiver can be anyone
        while c1 == c2:
            c2 = random.choice(suspect_phones + noise_phones)
        call_time = base_time + timedelta(
            days=random.randint(0, 25),
            hours=random.randint(8, 21),
            minutes=random.randint(1, 59),
        )
        records.append(
            {
                "caller_number": c1,
                "receiver_number": c2,
                "timestamp": call_time.strftime("%Y-%m-%d %H:%M:%S"),
                "duration_seconds": random.randint(10, 300),
                "tower_location": random.choice(["Ranchi", "Kolkata", "Patna"]),
                "call_type": "Voice",
            }
        )

    records.sort(key=lambda x: x["timestamp"])

    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

    print(f"[+] Generated {len(records)} CDR entries in {filename}")


# 4. Generate Bank Transactions
def generate_bank_transactions(filename="bank_transactions.csv", count=250):
    txs = []
    base_time = datetime(2026, 8, 1, 10, 0, 0)

    # Laundering trail: Stolen car sale proceeds funneling into shell firm
    laundering_trail = [
        ("vikram", "tariq", 150000, "IMPS"),
        ("tariq", "amit", 350000, "RTGS"),
        ("amit", "sunita", 500000, "NEFT"),
    ]

    for src, dst, amount, tx_type in laundering_trail:
        tx_time = base_time + timedelta(days=random.randint(5, 15))
        txs.append(
            {
                "transaction_id": f"TXN{random.randint(1000000, 9999999)}",
                "sender_account": SUSPECTS[src]["account"],
                "sender_name": SUSPECTS[src]["name"],
                "receiver_account": SUSPECTS[dst]["account"],
                "receiver_name": SUSPECTS[dst]["name"],
                "amount_inr": amount,
                "timestamp": tx_time.strftime("%Y-%m-%d %H:%M:%S"),
                "transaction_type": tx_type,
            }
        )

    # Background innocent transactions
    all_accounts = [(s["name"], s["account"]) for s in SUSPECTS.values()] + [
        (u["name"], u["account"]) for u in NOISE_USERS
    ]

    for _ in range(count - len(txs)):
        sender, receiver = random.sample(all_accounts, 2)
        tx_time = base_time + timedelta(
            days=random.randint(0, 25), hours=random.randint(9, 19)
        )
        txs.append(
            {
                "transaction_id": f"TXN{random.randint(1000000, 9999999)}",
                "sender_account": sender[1],
                "sender_name": sender[0],
                "receiver_account": receiver[1],
                "receiver_name": receiver[0],
                "amount_inr": round(random.uniform(500, 15000), 2),
                "timestamp": tx_time.strftime("%Y-%m-%d %H:%M:%S"),
                "transaction_type": random.choice(["UPI", "IMPS", "POS"]),
            }
        )

    txs.sort(key=lambda x: x["timestamp"])

    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=txs[0].keys())
        writer.writeheader()
        writer.writerows(txs)

    print(f"[+] Generated {len(txs)} Bank transactions in {filename}")


# 5. Generate Unstructured FIR Documents (JSON)
def generate_firs(filename="firs.json"):
    firs = [
        {
            "fir_number": "FIR-2026-JH-0104",
            "police_station": "Kotwali, Ranchi",
            "filing_date": "2026-08-04",
            "narrative": (
                "Complainant reported theft of a white Mahindra Thar registration JH01-BV-4321 "
                "from Main Road Ranchi. CCTV surveillance identified suspect Rahul Verma fleeing "
                "the scene. Informant reports suspect was carrying mobile device +919835012345. "
                "Suspect has documented history of vehicle smuggling with associate Vikram Singh."
            ),
        },
        {
            "fir_number": "FIR-2026-JH-0189",
            "police_station": "Bistupur, Jamshedpur",
            "filing_date": "2026-08-11",
            "narrative": (
                "Raid conducted at an unauthorized garage owned by Vikram Singh (+919431054321). "
                "Recovered altered number plates and chassis documents for vehicle JH01-BV-4321. "
                "Interrogation revealed suspect operates under logistical guidance of a contact "
                "identified as Tariq Khan operating out of Dhanbad."
            ),
        },
        {
            "fir_number": "FIR-2026-WB-0552",
            "police_station": "Park Street, Kolkata",
            "filing_date": "2026-08-18",
            "narrative": (
                "Financial intelligence report received regarding suspicious accounts under "
                "Apex Logistics Pvt Ltd. The accounts are supervised by Sunita Sharma (+919831122334). "
                "Substantial unbacked credits received through an intermediary channel linked to "
                "Amit Banerjee (+919830011223), suspected of handling unregistered hawala operations."
            ),
        },
        # Unrelated FIR to test noise filtering
        {
            "fir_number": "FIR-2026-JH-0210",
            "police_station": "Lalpur, Ranchi",
            "filing_date": "2026-08-15",
            "narrative": (
                "Case of mobile phone snatching reported near Circular Road. Two unidentified "
                "individuals on a black motorcycle intercepted the victim. No known connection "
                "to organized syndicates detected so far."
            ),
        },
    ]

    with open(filename, mode="w", encoding="utf-8") as f:
        json.dump(firs, f, indent=2)

    print(f"[+] Generated {len(firs)} FIRs in {filename}")


if __name__ == "__main__":
    generate_cdrs()
    generate_bank_transactions()
    generate_firs()
    print("\nDataset ready. You now have the exact multi-source trail to build your graph.")