import sqlite3

DB_PATH = "database/sikkim_tourist_ai.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

rows = conn.execute(
    """
    SELECT
        id,
        document_id,
        record_json,
        status
    FROM records
    ORDER BY id
    """
).fetchall()

print("\n===== DATABASE RECORDS =====\n")

for row in rows:
    print("Record ID:", row["id"])
    print("Document ID:", row["document_id"])
    print("Status:", row["status"])
    print("Record JSON:")
    print(row["record_json"])
    print("-----------------------------------")

conn.close()

print("\n===== DATABASE CHECK COMPLETE =====")