import sqlite3
import json
from pathlib import Path


DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "database"
    / "sikkim_tourist_ai.db"
)


def normalize_record(record):
    """
    Convert a record into a consistent JSON string
    so identical records can be detected.
    """

    return json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True
    )


def cleanup_duplicates():

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    rows = connection.execute(
        """
        SELECT
            id,
            record_json,
            status
        FROM records
        WHERE status = 'approved'
        ORDER BY id ASC
        """
    ).fetchall()

    seen = {}

    duplicates = []

    for row in rows:

        try:
            record = json.loads(row["record_json"])

        except json.JSONDecodeError:
            continue

        normalized = normalize_record(record)

        if normalized in seen:

            duplicates.append(
                {
                    "duplicate_id": row["id"],
                    "keep_id": seen[normalized]
                }
            )

        else:

            seen[normalized] = row["id"]

    print()
    print("===================================")
    print("APPROVED RECORD DUPLICATE CHECK")
    print("===================================")

    if not duplicates:

        print()
        print("No duplicate approved records found.")

        connection.close()

        return

    print()
    print("Duplicates found:", len(duplicates))

    for item in duplicates:

        print(
            f"Duplicate Record {item['duplicate_id']} "
            f"→ keeping Record {item['keep_id']}"
        )

    print()
    answer = input(
        "Delete these duplicate records? (yes/no): "
    )

    if answer.lower() != "yes":

        print()
        print("Cleanup cancelled.")

        connection.close()

        return

    for item in duplicates:

        connection.execute(
            """
            DELETE FROM records
            WHERE id = ?
            AND status = 'approved'
            """,
            (item["duplicate_id"],)
        )

    connection.commit()

    print()
    print(
        f"Deleted {len(duplicates)} duplicate "
        "approved records."
    )

    connection.close()


if __name__ == "__main__":

    cleanup_duplicates()