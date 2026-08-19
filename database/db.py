import sqlite3
import json
import re
from pathlib import Path
from datetime import datetime, timezone


# ============================================================
# DATABASE PATH
# ============================================================

DB_PATH = (
    Path(__file__).resolve().parent
    / "sikkim_tourist_ai.db"
)


# ============================================================
# DATABASE SCHEMA
# ============================================================

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    name TEXT NOT NULL,

    base_url TEXT UNIQUE NOT NULL,

    source_type TEXT DEFAULT 'website',

    trust_level TEXT DEFAULT 'medium',

    created_at TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    source_id INTEGER,

    url TEXT UNIQUE NOT NULL,

    title TEXT,

    content TEXT,

    content_hash TEXT,

    collected_at TEXT NOT NULL,

    FOREIGN KEY(source_id)
        REFERENCES sources(id)
);


CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    document_id INTEGER,

    record_json TEXT NOT NULL,

    status TEXT DEFAULT 'pending_review',

    confidence TEXT DEFAULT 'medium',

    created_at TEXT NOT NULL,

    reviewed_at TEXT,

    reviewer_note TEXT,

    FOREIGN KEY(document_id)
        REFERENCES documents(id)
);


CREATE TABLE IF NOT EXISTS document_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    document_id INTEGER NOT NULL,

    file_name TEXT NOT NULL,

    file_path TEXT NOT NULL,

    mime_type TEXT,

    content_hash TEXT NOT NULL,

    created_at TEXT NOT NULL,

    UNIQUE(document_id, content_hash),

    FOREIGN KEY(document_id)
        REFERENCES documents(id)
);


CREATE TABLE IF NOT EXISTS conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    record_id INTEGER,

    topic TEXT,

    details TEXT,

    status TEXT DEFAULT 'open',

    created_at TEXT NOT NULL
);


CREATE INDEX IF NOT EXISTS idx_records_status
ON records(status);


CREATE INDEX IF NOT EXISTS idx_records_document
ON records(document_id);


CREATE INDEX IF NOT EXISTS idx_document_assets_document
ON document_assets(document_id);
"""


# ============================================================
# TIME
# ============================================================

def now():
    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# CONNECTION
# ============================================================

def connect():
    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(
        DB_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_db():

    with connect() as connection:

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        connection.executescript(
            SCHEMA
        )

        connection.commit()


# ============================================================
# SOURCE
# ============================================================

def get_or_create_source(
    name,
    base_url,
    source_type="website",
    trust_level="medium"
):

    init_db()

    with connect() as connection:

        row = connection.execute(
            """
            SELECT id
            FROM sources
            WHERE base_url = ?
            """,
            (base_url,)
        ).fetchone()

        if row:

            return row["id"]

        cursor = connection.execute(
            """
            INSERT INTO sources
            (
                name,
                base_url,
                source_type,
                trust_level,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                base_url,
                source_type,
                trust_level,
                now()
            )
        )

        connection.commit()

        return cursor.lastrowid


# ============================================================
# DOCUMENT
# ============================================================

def add_document(
    source_id,
    url,
    title,
    content,
    content_hash
):

    init_db()

    with connect() as connection:

        row = connection.execute(
            """
            SELECT
                id,
                content_hash
            FROM documents
            WHERE url = ?
            """,
            (url,)
        ).fetchone()

        # ----------------------------------------------------
        # EXISTING DOCUMENT
        # ----------------------------------------------------

        if row:

            document_id = row["id"]

            # Same content
            if row["content_hash"] == content_hash:

                print(
                    f"[DATABASE] Existing document: "
                    f"{document_id}"
                )

                return document_id, False

            # Content changed
            connection.execute(
                """
                UPDATE documents
                SET
                    title = ?,
                    content = ?,
                    content_hash = ?,
                    collected_at = ?
                WHERE id = ?
                """,
                (
                    title,
                    content,
                    content_hash,
                    now(),
                    document_id
                )
            )

            connection.commit()

            print(
                f"[DATABASE] Document updated: "
                f"{document_id}"
            )

            return document_id, True

        # ----------------------------------------------------
        # NEW DOCUMENT
        # ----------------------------------------------------

        cursor = connection.execute(
            """
            INSERT INTO documents
            (
                source_id,
                url,
                title,
                content,
                content_hash,
                collected_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                url,
                title,
                content,
                content_hash,
                now()
            )
        )

        connection.commit()

        document_id = cursor.lastrowid

        print(
            f"[DATABASE] Document saved: "
            f"{document_id}"
        )

        return document_id, True


# ============================================================
# DOCUMENT EVIDENCE ASSETS
# ============================================================

def add_document_asset(
    document_id,
    file_name,
    file_path,
    mime_type,
    content_hash,
):
    """Link an uploaded evidence file to an indexed document."""
    init_db()

    with connect() as connection:
        existing = connection.execute(
            """
            SELECT id
            FROM document_assets
            WHERE document_id = ? AND content_hash = ?
            """,
            (int(document_id), content_hash),
        ).fetchone()

        if existing:
            return existing["id"], False

        cursor = connection.execute(
            """
            INSERT INTO document_assets
            (
                document_id,
                file_name,
                file_path,
                mime_type,
                content_hash,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                int(document_id),
                file_name,
                file_path,
                mime_type,
                content_hash,
                now(),
            ),
        )
        connection.commit()
        return cursor.lastrowid, True


def list_document_assets(document_id):
    """Return evidence assets linked to a document."""
    init_db()

    with connect() as connection:
        return connection.execute(
            """
            SELECT *
            FROM document_assets
            WHERE document_id = ?
            ORDER BY id ASC
            """,
            (int(document_id),),
        ).fetchall()


def search_document_assets(query, limit=6):
    """Find uploaded knowledge-base images by filename and document text."""
    init_db()

    query_tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", str(query).lower())
        if len(token) >= 2
        and token not in {
            "a", "an", "the", "of", "or", "and", "for", "to", "me",
            "my", "yes", "please", "show", "display", "have", "has",
            "can", "you", "want", "need", "photo", "photos", "image",
            "images", "picture", "pictures", "photograph", "photographs",
            "old", "historic", "historical",
        }
    }
    if not query_tokens:
        return []

    with connect() as connection:
        rows = connection.execute(
            """
            SELECT
                a.id AS asset_id,
                a.document_id,
                a.file_name,
                a.file_path,
                a.mime_type,
                d.title AS document_title,
                d.content AS document_content,
                d.url AS source_url,
                CASE
                    WHEN EXISTS (
                        SELECT 1 FROM records r
                        WHERE r.document_id = a.document_id
                          AND r.status = 'approved'
                    ) THEN 'approved'
                    WHEN EXISTS (
                        SELECT 1 FROM records r
                        WHERE r.document_id = a.document_id
                          AND r.status = 'pending_review'
                    ) THEN 'pending_review'
                    ELSE 'unreviewed'
                END AS review_status
            FROM document_assets a
            JOIN documents d ON d.id = a.document_id
            ORDER BY a.id DESC
            """
        ).fetchall()

    matches = []
    for row in rows:
        file_tokens = set(re.findall(r"[a-z0-9]+", row["file_name"].lower()))
        title_tokens = set(re.findall(r"[a-z0-9]+", (row["document_title"] or "").lower()))
        document_text = (row["document_content"] or "").lower()
        score = sum(
            10 if token in file_tokens
            else 5 if token in title_tokens
            else 1 if token in document_text
            else 0
            for token in query_tokens
        )
        if score <= 0:
            continue
        match = dict(row)
        match.pop("document_content", None)
        match["score"] = score
        matches.append(match)

    matches.sort(key=lambda item: (-item["score"], item["asset_id"]))
    return matches[:max(1, int(limit))]


# ============================================================
# RECORD HELPERS
# ============================================================

def _record_to_dict(record):

    if hasattr(record, "model_dump"):

        return record.model_dump(
            mode="json"
        )

    if isinstance(record, dict):

        return record

    raise TypeError(
        "record must be a Pydantic model or dictionary"
    )


def _record_name(record):

    return str(
        record.get("name", "")
    ).strip()


def _record_category(record):

    return str(
        record.get("category", "")
    ).strip()


def _record_key(record):

    return (
        _record_name(record).casefold(),
        _record_category(record).casefold()
    )


# ============================================================
# GLOBAL DUPLICATE CHECK
# ============================================================

def find_duplicate_record(
    record,
    exclude_id=None
):

    record = _record_to_dict(
        record
    )

    name = _record_name(
        record
    ).casefold()

    category = _record_category(
        record
    ).casefold()

    if not name or not category:

        return None

    query = """
        SELECT
            id,
            document_id,
            record_json,
            status,
            confidence
        FROM records
        WHERE lower(json_extract(record_json, '$.name')) = ?
        AND lower(json_extract(record_json, '$.category')) = ?
    """

    params = [
        name,
        category
    ]

    if exclude_id is not None:

        query += """
            AND id != ?
        """

        params.append(
            exclude_id
        )

    query += """
        ORDER BY id ASC
        LIMIT 1
    """

    with connect() as connection:

        return connection.execute(
            query,
            tuple(params)
        ).fetchone()


# ============================================================
# ADD RECORD
# ============================================================

def add_record(
    document_id,
    record,
    confidence="medium"
):

    init_db()

    record = _record_to_dict(
        record
    )

    # --------------------------------------------------------
    # GLOBAL DUPLICATE CHECK
    # --------------------------------------------------------

    duplicate = find_duplicate_record(
        record
    )

    if duplicate:

        print(
            "[DATABASE] Duplicate skipped: "
            f"{_record_name(record)} / "
            f"{_record_category(record)} "
            f"(record {duplicate['id']})"
        )

        return duplicate["id"], False

    # --------------------------------------------------------
    # INSERT
    # --------------------------------------------------------

    record_json = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True
    )

    status = record.get(
        "status",
        "pending_review"
    )

    record_confidence = record.get(
        "confidence",
        confidence
    )

    with connect() as connection:

        cursor = connection.execute(
            """
            INSERT INTO records
            (
                document_id,
                record_json,
                status,
                confidence,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                int(document_id),
                record_json,
                status,
                record_confidence,
                now()
            )
        )

        connection.commit()

        record_id = cursor.lastrowid

    print(
        f"[DATABASE] New record saved: "
        f"{record_id}"
    )

    print(
        f"[DATABASE] Record saved: "
        f"{_record_name(record)} "
        f"({_record_category(record)}) "
        f"[ID: {record_id}]"
    )

    return record_id, True


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def add_record_if_new(
    document_id,
    record,
    confidence="medium"
):

    return add_record(
        document_id,
        record,
        confidence
    )


# ============================================================
# LIST RECORDS
# ============================================================

def list_records(
    status=None
):

    init_db()

    with connect() as connection:

        query = """
            SELECT
                r.*,
                d.url,
                d.title
            FROM records r
            JOIN documents d
                ON d.id = r.document_id
        """

        if status:

            query += """
                WHERE r.status = ?
            """

            query += """
                ORDER BY r.id DESC
            """

            return connection.execute(
                query,
                (status,)
            ).fetchall()

        query += """
            ORDER BY r.id DESC
        """

        return connection.execute(
            query
        ).fetchall()


# ============================================================
# GET RECORD
# ============================================================

def get_record(
    record_id
):

    init_db()

    with connect() as connection:

        return connection.execute(
            """
            SELECT
                r.*,
                d.url,
                d.title
            FROM records r
            LEFT JOIN documents d
                ON d.id = r.document_id
            WHERE r.id = ?
            """,
            (record_id,)
        ).fetchone()


# ============================================================
# UPDATE RECORD
# ============================================================

def update_record(
    record_id,
    record,
    status,
    note=""
):

    init_db()

    record = _record_to_dict(
        record
    )

    record_json = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True
    )

    with connect() as connection:

        connection.execute(
            """
            UPDATE records
            SET
                record_json = ?,
                status = ?,
                reviewed_at = ?,
                reviewer_note = ?
            WHERE id = ?
            """,
            (
                record_json,
                status,
                now(),
                note,
                int(record_id)
            )
        )

        connection.commit()


# ============================================================
# DELETE RECORD
# ============================================================

def delete_record(
    record_id
):

    init_db()

    with connect() as connection:

        connection.execute(
            """
            DELETE FROM records
            WHERE id = ?
            """,
            (int(record_id),)
        )

        connection.commit()


# ============================================================
# STATISTICS
# ============================================================

def stats():

    init_db()

    with connect() as connection:

        return {

            "sources":
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM sources
                    """
                ).fetchone()[0],

            "documents":
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM documents
                    """
                ).fetchone()[0],

            "pending":
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM records
                    WHERE status = 'pending_review'
                    """
                ).fetchone()[0],

            "approved":
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM records
                    WHERE status = 'approved'
                    """
                ).fetchone()[0],

            "rejected":
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM records
                    WHERE status = 'rejected'
                    """
                ).fetchone()[0],

            "conflicts":
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM conflicts
                    WHERE status = 'open'
                    """
                ).fetchone()[0],
        }


# ============================================================
# CLEAN EXISTING DUPLICATES
# ============================================================

def remove_duplicate_records():

    init_db()

    removed = 0

    with connect() as connection:

        rows = connection.execute(
            """
            SELECT
                id,
                record_json
            FROM records
            ORDER BY id ASC
            """
        ).fetchall()

        seen = {}

        for row in rows:

            try:

                record = json.loads(
                    row["record_json"]
                )

            except Exception:

                continue

            key = _record_key(
                record
            )

            if key == ("", ""):

                continue

            if key in seen:

                connection.execute(
                    """
                    DELETE FROM records
                    WHERE id = ?
                    """,
                    (row["id"],)
                )

                removed += 1

            else:

                seen[key] = row["id"]

        connection.commit()

    print(
        f"[DATABASE] Existing duplicates removed: "
        f"{removed}"
    )

    return removed


# ============================================================
# DATABASE MAIN
# ============================================================

if __name__ == "__main__":

    init_db()

    print(
        "Database initialized:"
    )

    print(
        DB_PATH
    )

    print()

    print(
        "Statistics:"
    )

    print(
        json.dumps(
            stats(),
            indent=2
        )
    )
