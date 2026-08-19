import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent / "database" / "sikkim_tourist_ai.db"

def seed_transit():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 1. Ensure source
    now_iso = datetime.now(timezone.utc).isoformat()
    c.execute("SELECT id FROM sources WHERE base_url = ?", ("https://www.sikkimtourism.gov.in/travel-logistics",))
    row = c.fetchone()
    if row:
        source_id = row["id"]
    else:
        c.execute("""
            INSERT INTO sources (name, base_url, source_type, trust_level, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, ("Sikkim Tourism Official Transit", "https://www.sikkimtourism.gov.in/travel-logistics", "website", "high", now_iso))
        source_id = c.lastrowid

    # 2. Add transit document
    doc_text = """
    How to reach Sikkim by Air, Train, and Road:
    Sikkim's primary transit gateway is Siliguri / New Jalpaiguri (NJP) / Bagdogra in West Bengal.
    By Air: Bagdogra International Airport (IXB) is located 125 km from Gangtok (4.5-5 hours drive via NH10). Pakyong Airport (PYG) is 30 km from Gangtok. Helicopter services operate between Bagdogra and Gangtok Burtuk helipad.
    By Train: New Jalpaiguri (NJP) Railway Station is the nearest broad-gauge hub (120 km from Gangtok, 4.5-5 hours via NH10).
    By Road: Entry into Sikkim is via National Highway 10 (NH10) through Rangpo checkpost (for East/North) or Melli checkpost (for West/South). Travel time from Siliguri to Gangtok is 4-5 hours. Shared sumos and SNT buses depart from Siliguri SNT terminus.
    Long distance transit: Travelers from Delhi, Kolkata, Mumbai, and Guwahati take flights/trains to Bagdogra/NJP, then proceed by road to Gangtok.
    Protected border destinations: Nathula Pass (14,140 ft) and Tsomgo Lake (12,310 ft) are located 40-56 km east of Gangtok towards the Tibet border, requiring special Protected Area Permits (PAP).
    """
    chash = hashlib.sha256(doc_text.encode()).hexdigest()

    c.execute("SELECT id FROM documents WHERE url = ?", ("https://www.sikkimtourism.gov.in/how-to-reach-sikkim",))
    drow = c.fetchone()
    if drow:
        doc_id = drow["id"]
    else:
        c.execute("""
            INSERT INTO documents (source_id, url, title, content, content_hash, collected_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (source_id, "https://www.sikkimtourism.gov.in/how-to-reach-sikkim", "How to Reach Sikkim - Air, Rail and Road Guide", doc_text, chash, now_iso))
        doc_id = c.lastrowid

    # 3. Add approved transit records
    transit_records = [
        {
            "id": "tourism_transit_air_rail_road",
            "name": "How to Reach Sikkim (Air, Train, Road)",
            "aliases": ["Reach Sikkim", "Sikkim Travel Logistics", "Bagdogra to Gangtok", "NJP to Gangtok", "Transport to Sikkim", "Delhi to Sikkim", "Kolkata to Sikkim", "By Road to Sikkim"],
            "category": "transport",
            "region": "All Sikkim",
            "district": "Gangtok / Pakyong",
            "description": "The mandatory entry gateway to Sikkim is Siliguri/Bagdogra/NJP in West Bengal. By Air: Fly to Bagdogra Airport (IXB) (125 km / 4.5-5 hrs drive to Gangtok via NH10) or Pakyong Airport (PYG). By Train: Major hub is New Jalpaiguri (NJP) (120 km / 4.5-5 hrs via NH10). By Road: Take NH10 from Siliguri through Rangpo Checkpost into Gangtok (114 km, 4-5 hours via shared Sumo or private taxi). Travelers from Delhi, Mumbai, or Kolkata take flights or express trains to Bagdogra/NJP first.",
            "altitude": "Siliguri (400 ft) ascending to Gangtok (5,500 ft)",
            "best_time": ["Throughout the year", "October to June recommended"],
            "activities": ["Scenic highway drive along Teesta River", "Helicopter joyride"],
            "nearby_places": ["Siliguri", "Sevoke Coronation Bridge", "Teesta Bazaar", "Rangpo Checkpost", "Melli"],
            "how_to_reach": "Fly to Bagdogra (IXB) or take train to New Jalpaiguri (NJP), then take reserved cab or shared Sumo from Siliguri SNT Bus Stand via NH10 to Gangtok (4.5-5 hours).",
            "permit_required": False,
            "safety_information": [
                "Road conditions along NH10 can experience monsoon landslides during July-August; check road advisories.",
                "Foreign nationals must obtain Restricted Area Permit (RAP/ILP) stamp at Rangpo or Melli border checkposts.",
                "Nathula Pass and Tsomgo Lake are 40-56 km past Gangtok and require special Protected Area Permits (PAP); they are not en-route on highway to Gangtok."
            ],
            "travel_tips": [
                "Book private or shared taxis from prepaid taxi counters at Bagdogra Airport or NJP station.",
                "SNT (Sikkim Nationalised Transport) government buses run daily from Siliguri SNT Terminus to Gangtok.",
                "Leave early from Siliguri/Bagdogra to avoid evening mountain fog and river traffic."
            ],
            "contact": "Sikkim Tourism Helipad / SNT Siliguri: 0353-2511492 / STDC Gangtok: 03592-209090",
            "website": "https://www.sikkimtourism.gov.in",
            "price_range": "Shared Sumo: ₹350–₹500 per seat; Reserved Taxi: ₹3,000–₹4,500",
            "duration": "4.5 to 5.5 hours from Siliguri/Bagdogra to Gangtok",
            "status": "approved",
            "confidence": "high"
        }
    ]

    for rec in transit_records:
        rec_json = json.dumps(rec, ensure_ascii=False, sort_keys=True)
        c.execute("""
            SELECT id FROM records 
            WHERE lower(json_extract(record_json, '$.name')) = lower(?)
        """, (rec["name"],))
        existing = c.fetchone()
        if existing:
            c.execute("""
                UPDATE records SET record_json = ?, status = 'approved', confidence = 'high'
                WHERE id = ?
            """, (rec_json, existing["id"]))
            print(f"Updated transit record ID {existing['id']}")
        else:
            c.execute("""
                INSERT INTO records (document_id, record_json, status, confidence, created_at)
                VALUES (?, ?, 'approved', 'high', ?)
            """, (doc_id, rec_json, now_iso))
            print(f"Inserted new transit record ID {c.lastrowid}")

    conn.commit()
    conn.close()
    print("Transit knowledge seeded successfully!")

if __name__ == "__main__":
    seed_transit()
