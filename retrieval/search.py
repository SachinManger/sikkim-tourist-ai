import json
import sqlite3
from pathlib import Path
import re
from typing import List, Dict, Any, Optional

DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "database"
    / "sikkim_tourist_ai.db"
)

STOP_WORDS = {
    "what", "is", "are", "the", "in", "of", "to",
    "a", "an", "can", "i", "tell", "me", "about",
    "for", "on", "do", "you", "how", "where",
    "which", "and", "please", "give", "some",
    "want", "need", "know", "like", "any", "with"
}


def tokenize(text: str) -> List[str]:
    """Convert text into clean search keywords."""
    words = re.findall(r"[a-zA-Z0-9]+", str(text).lower())
    return [
        word
        for word in words
        if word not in STOP_WORDS and len(word) > 2
    ]


def search_approved_records(
    query: str,
    category: Optional[str] = None,
    district: Optional[str] = None,
    limit: int = 6
) -> List[Dict[str, Any]]:
    """
    Search approved tourism records with relevance scoring and optional filters.
    """
    query = query.strip()
    if not query and not category and not district:
        return []

    keywords = tokenize(query) if query else []

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    rows = connection.execute(
        """
        SELECT
            r.id,
            r.document_id,
            r.record_json,
            r.confidence,
            d.url,
            d.title
        FROM records r
        JOIN documents d
            ON d.id = r.document_id
        WHERE r.status = 'approved'
        """
    ).fetchall()

    connection.close()

    results = []
    query_lower = query.lower() if query else ""

    for row in rows:
        try:
            record = json.loads(row["record_json"])
        except json.JSONDecodeError:
            continue

        rec_category = str(record.get("category", "")).lower()
        rec_district = str(record.get("district", "")).lower() if record.get("district") else ""

        # Filter check
        if category and category.lower() != "all":
            requested_category = category.lower()
            allowed_categories = (
                {"transport", "taxi"}
                if requested_category == "transport"
                else {requested_category}
            )
            if rec_category not in allowed_categories:
                continue
        if district and district.lower() != "all" and rec_district and district.lower() not in rec_district:
            continue

        name = str(record.get("name", "")).lower()
        aliases = [str(a).lower() for a in record.get("aliases", [])]
        description = str(record.get("description", "")).lower()
        activities = " ".join(str(x).lower() for x in record.get("activities", []))
        nearby_places = " ".join(str(x).lower() for x in record.get("nearby_places", []))
        how_to_reach = str(record.get("how_to_reach", "")).lower()
        price_range = str(record.get("price_range", "")).lower()
        travel_tips = " ".join(str(x).lower() for x in record.get("travel_tips", []))

        searchable_text = (
            f"{name} {rec_category} {rec_district} {description} {activities} "
            f"{nearby_places} {how_to_reach} {price_range} {travel_tips} "
            f"{' '.join(aliases)}"
        )

        # Respect the requested transport mode. A bus-fare question must not
        # be answered from a taxi-only rate chart, and vice versa.
        asks_for_bus = "bus" in keywords or "snt" in keywords
        asks_for_taxi = any(term in keywords for term in ("taxi", "cab", "reserved", "reserve"))

        if asks_for_bus and not any(term in searchable_text for term in ("bus", "snt")):
            continue
        if asks_for_taxi and not any(term in searchable_text for term in ("taxi", "cab")):
            continue

        score = 0

        # If no specific query, match filter with baseline score
        if not query:
            score = 10
        else:
            if query_lower == name:
                score += 50
            elif query_lower in aliases:
                score += 40
            elif query_lower in name:
                score += 30

            for keyword in keywords:
                if keyword == name:
                    score += 20
                elif keyword in aliases:
                    score += 15
                elif keyword == rec_category:
                    score += 12
                elif keyword == rec_district:
                    score += 10
                elif keyword in activities:
                    score += 8
                elif keyword in nearby_places:
                    score += 6
                elif keyword in description:
                    score += 4
                elif keyword in price_range:
                    score += 10
                elif keyword in travel_tips:
                    score += 4
                elif keyword in searchable_text:
                    score += 2

        if score > 0:
            results.append({
                "record_id": row["id"],
                "score": score,
                "record": record,
                "source_url": row["url"],
                "source_title": row["title"],
                "confidence": row["confidence"]
            })

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:limit]
