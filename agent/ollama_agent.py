import json
import os
import re
import hashlib
import requests
import time
from datetime import date

from dotenv import load_dotenv

from schemas.tourism import (
    ExtractionEnvelope,
    TourismRecord,
)

# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434"
).rstrip("/")

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:7b"
)

# Ollama protection settings
OLLAMA_TIMEOUT = int(
    os.getenv("OLLAMA_TIMEOUT", "300")
)

OLLAMA_RETRIES = int(
    os.getenv("OLLAMA_RETRIES", "2")
)

OLLAMA_RETRY_DELAY = int(
    os.getenv("OLLAMA_RETRY_DELAY", "5")
)

CHUNK_SIZE = int(
    os.getenv("OLLAMA_CHUNK_SIZE", "4500")
)

CHUNK_OVERLAP = int(
    os.getenv("OLLAMA_CHUNK_OVERLAP", "400")
)


# ============================================================
# ALLOWED CATEGORIES
# ============================================================

ALLOWED_CATEGORIES = {
    "destination",
    "trekking",
    "lake",
    "monastery",
    "historical_place",
    "hotel",
    "homestay",
    "restaurant",
    "transport",
    "taxi",
    "permit",
    "festival",
    "culture",
    "food",
    "shopping",
    "emergency",
    "travel_tip",
    "tour_package",
    "faq",
}


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM = """
You are a strict Sikkim Tourism information extraction engine.

Your ONLY source of truth is the webpage text supplied by the user.

DO NOT use:

- model knowledge
- internet knowledge
- previous requests
- previous webpages
- assumptions
- guesses
- inferred facts

IMPORTANT:

Return ONLY the JSON object requested by the user.

The JSON MUST contain exactly:

{
    "records": [...]
}

Every record MUST contain only these fields:

id
name
aliases
category
region
district
description
altitude
best_time
activities
nearby_places
how_to_reach
permit_required
safety_information
travel_tips
contact
website
price_range
duration
source
confidence
dynamic_information
status

DO NOT add any other fields.

NEVER return:

- awards_achievements
- leadership_key_officials
- experience_sikkim
- sustainable_tourism
- extra source fields
- other custom fields

CATEGORY RULES:

Allowed categories are:

destination
trekking
lake
monastery
historical_place
history
hotel
homestay
restaurant
transport
taxi
permit
festival
culture
food
shopping
emergency
travel_tip
tour_package
faq

Do not invent a category.

DESTINATION RULE:

Create a destination record only when the webpage provides
actual tourism information about that place.

Do NOT create a destination record merely because:

"Sikkim"
"Gangtok"
"Pelling"

or another place name appears.

A place name appearing only in:

- navigation
- footer
- menu
- links
- related places
- nearby attractions
- lists

is NOT enough.

TREKKING RULE:

General statements such as:

"Visitors can enjoy trekking."

must NOT create a trekking record.

Only create a trekking record when a specific trek is identified.

For example:

"Dzongri Trek is a popular trekking route."

creates:

name = "Dzongri Trek"
category = "trekking"

ACTIVITY RULE:

General activities belong in the activities field.

For example:

"Visitors can enjoy trekking and sightseeing."

becomes:

activities = [
    "trekking",
    "sightseeing"
]

Do NOT create separate trekking/activity records.

NEARBY PLACE RULE:

If:

"Pelling is near Rabdentse Ruins."

then:

Pelling.nearby_places = [
    "Rabdentse Ruins"
]

Do NOT create a separate Rabdentse Ruins record unless the webpage
also contains actual information about Rabdentse Ruins.

MISSING VALUES:

If the webpage does not support a field:

Use null for scalar fields.

Use [] for list fields.

CONTACT:

The contact field MUST be a STRING or null.

Never return an object for contact.

SOURCE:

The source object must contain exactly:

source_name
source_url
page_title
page_url
source_type
trust_level
collected_date
last_verified

Do NOT add extra source fields.

STATUS:

Every extracted record must have:

"status": "pending_review"

DYNAMIC INFORMATION:

The following may be dynamic:

- prices
- weather
- road conditions
- permits
- restrictions
- opening hours
- availability
- temporary closures
- current contact information
- travel advisories

If the webpage explicitly contains dynamic information:

dynamic_information = true

Otherwise:

dynamic_information = false

CONFIDENCE:

Use:

high
medium
low

Do not invent facts.

Before creating every record ask:

1. Is the entity actually described in the webpage?
2. Can I identify direct evidence?
3. Am I adding anything from my own knowledge?

If the answer to question 1 or 2 is NO:
DO NOT create the record.

If question 3 is YES:
REMOVE the unsupported information.

Do not create duplicate records within the same webpage.
"""


# ============================================================
# DETERMINISTIC RECORD ID
# ============================================================

def make_record_id(name, category):
    """
    Generate deterministic ID from name + category.
    """

    value = (
        f"{name.strip().lower()}::"
        f"{category.strip().lower()}"
    )

    digest = hashlib.sha1(
        value.encode("utf-8")
    ).hexdigest()[:12]

    return f"tourism_{digest}"


# ============================================================
# CLEAN URL
# ============================================================

def clean_url(value):
    """
    Convert Markdown URLs into normal URLs.
    """

    if value is None:
        return None

    value = str(value).strip()

    match = re.search(
        r"\((https?://[^)]+)\)",
        value
    )

    if match:
        return match.group(1)

    match = re.search(
        r"(https?://[^\s\]]+)",
        value
    )

    if match:
        return match.group(1)

    return value


# ============================================================
# CLEAN JSON RESPONSE
# ============================================================

def clean_json_response(raw):
    """
    Clean common Qwen JSON formatting problems.
    """

    if not raw:
        return ""

    raw = str(raw).strip()

    # Remove code fences
    raw = re.sub(
        r"^```(?:json)?\s*",
        "",
        raw,
        flags=re.IGNORECASE
    )

    raw = re.sub(
        r"\s*```$",
        "",
        raw
    )

    raw = raw.strip()

    # Find first JSON object
    start = raw.find("{")

    if start >= 0:
        raw = raw[start:]

    # Find last JSON object
    end = raw.rfind("}")

    if end >= 0:
        raw = raw[:end + 1]

    return raw.strip()


# ============================================================
# TEXT CHUNKING
# ============================================================

def split_text(
    text,
    chunk_size=CHUNK_SIZE,
    overlap=CHUNK_OVERLAP
):
    """
    Split large webpage text into overlapping chunks.

    This is the important part that was missing from your
    previous ollama_agent.py.

    Example:

        7932 characters
             ↓
        chunk 1 ≈ 4500
        chunk 2 ≈ remaining text

    Overlap allows a small amount of context to carry
    between chunks.
    """

    if not text:
        return []

    text = str(text).strip()

    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    # Prevent unreasonable overlap
    overlap = min(
        max(0, overlap),
        max(0, chunk_size // 4)
    )

    chunks = []

    start = 0
    total = len(text)

    while start < total:

        end = min(
            start + chunk_size,
            total
        )

        # Try to end at a sensible text boundary
        if end < total:

            candidates = [
                text.rfind(
                    "\n\n",
                    start,
                    end
                ),

                text.rfind(
                    "\n",
                    start,
                    end
                ),

                text.rfind(
                    ". ",
                    start,
                    end
                ),
            ]

            good = [
                position
                for position in candidates
                if position >
                start + int(chunk_size * 0.60)
            ]

            if good:
                end = max(good)

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= total:
            break

        start = max(
            end - overlap,
            start + 1
        )

    return chunks


# ============================================================
# ASK OLLAMA
# ============================================================

def ask_ollama(
    prompt,
    chunk_number=None,
    total_chunks=None
):
    """
    Call Ollama with bounded retries.

    A failed chunk does not automatically fail
    the entire webpage.
    """

    attempts = OLLAMA_RETRIES + 1

    for attempt in range(
        1,
        attempts + 1
    ):

        if chunk_number is not None:

            print(
                f"[OLLAMA] Processing chunk "
                f"{chunk_number}/{total_chunks}"
            )

        print(
            f"[OLLAMA] Request attempt "
            f"{attempt}/{attempts}"
        )

        try:

            response = requests.post(
                f"{OLLAMA_URL}/api/generate",

                json={
                    "model": OLLAMA_MODEL,

                    "system": SYSTEM,

                    "prompt": prompt,

                    "stream": False,

                    "format": "json",

                    "options": {
                        "temperature": 0.0
                    },
                },

                timeout=OLLAMA_TIMEOUT,
            )

            response.raise_for_status()

            result = response.json()

            if "response" not in result:

                raise ValueError(
                    "Ollama response does not "
                    "contain 'response'."
                )

            return result["response"]

        except (
            requests.RequestException,
            ValueError
        ) as e:

            print(
                "[OLLAMA ERROR]",
                e
            )

            if attempt < attempts:

                print(
                    f"[OLLAMA] Retrying in "
                    f"{OLLAMA_RETRY_DELAY} seconds..."
                )

                time.sleep(
                    OLLAMA_RETRY_DELAY
                )

            else:

                print(
                    "[OLLAMA] All attempts failed "
                    "for this chunk."
                )

    return None


# ============================================================
# NORMALIZE CONTACT
# ============================================================

def normalize_contact(contact):
    """
    Convert contact information into schema-compatible
    string format.
    """

    if contact is None:
        return None

    if isinstance(contact, str):

        return contact.strip() or None

    if isinstance(contact, dict):

        parts = []

        for key in (
            "phone",
            "mobile",
            "fax",
            "email",
            "address",
            "website",
        ):

            value = contact.get(key)

            if value:

                parts.append(
                    f"{key}: {value}"
                )

        if parts:
            return "; ".join(parts)

        return None

    return str(contact)


# ============================================================
# NORMALIZE LIST
# ============================================================

def normalize_list(value):
    """
    Ensure list fields are actually lists.
    """

    if value is None:
        return []

    if isinstance(value, list):

        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    if isinstance(value, str):

        value = value.strip()

        if not value:
            return []

        return [value]

    return []


# ============================================================
# NORMALIZE SOURCE
# ============================================================

def normalize_source(
    source,
    source_name,
    source_url,
    page_title,
    page_url,
    collected_date,
):
    """
    Rebuild source information using trusted Python values.

    This prevents Qwen from inventing source fields.
    """

    if not isinstance(
        source,
        dict
    ):
        source = {}

    return {
        "source_name": source_name,

        "source_url": clean_url(
            source_url
        ),

        "page_title": page_title,

        "page_url": clean_url(
            page_url
        ),

        "source_type": "website",

        "trust_level": "medium",

        "collected_date": collected_date,

        "last_verified": source.get(
            "last_verified"
        ),
    }


# ============================================================
# NORMALIZE RECORD DICTIONARY
# ============================================================

def normalize_record_dict(
    record,
    source_name,
    source_url,
    page_title,
    page_url,
    collected_date,
):
    """
    Convert raw Qwen output into the exact TourismRecord schema.

    Unsupported fields are intentionally discarded.
    """

    if not isinstance(
        record,
        dict
    ):
        return None

    # --------------------------------------------------------
    # REQUIRED VALUES
    # --------------------------------------------------------

    name = record.get("name")

    category = record.get("category")

    if not isinstance(
        name,
        str
    ):
        return None

    if not isinstance(
        category,
        str
    ):
        return None

    name = name.strip()

    category = category.strip().lower()

    if not name:
        return None

    if category not in ALLOWED_CATEGORIES:

        print(
            f"[AI] Removed unsupported category: "
            f"{name} / {category}"
        )

        return None

    # --------------------------------------------------------
    # DESCRIPTION
    # --------------------------------------------------------

    description = record.get(
        "description"
    )

    if description is not None:

        description = str(
            description
        ).strip()

        if not description:
            description = None

    # --------------------------------------------------------
    # CONTACT
    # --------------------------------------------------------

    contact = normalize_contact(
        record.get("contact")
    )

    # --------------------------------------------------------
    # WEBSITE
    # --------------------------------------------------------

    website = record.get(
        "website"
    )

    if website:

        website = clean_url(
            website
        )

    # --------------------------------------------------------
    # BUILD EXACT SCHEMA
    # --------------------------------------------------------

    data = {

        "id": make_record_id(
            name,
            category
        ),

        "name": name,

        "aliases": normalize_list(
            record.get("aliases")
        ),

        "category": category,

        "region": (
            str(record["region"]).strip()
            if record.get("region") is not None
            else None
        ),

        "district": (
            str(record["district"]).strip()
            if record.get("district") is not None
            else None
        ),

        "description": description,

        "altitude": record.get(
            "altitude"
        ),

        "best_time": normalize_list(
            record.get("best_time")
        ),

        "activities": normalize_list(
            record.get("activities")
        ),

        "nearby_places": normalize_list(
            record.get("nearby_places")
        ),

        "how_to_reach": (
            str(record["how_to_reach"]).strip()
            if record.get("how_to_reach") is not None
            else None
        ),

        "permit_required": record.get(
            "permit_required"
        ),

        "safety_information": normalize_list(
            record.get(
                "safety_information"
            )
        ),

        "travel_tips": normalize_list(
            record.get(
                "travel_tips"
            )
        ),

        "contact": contact,

        "website": website,

        "price_range": (
            str(record["price_range"]).strip()
            if record.get("price_range") is not None
            else None
        ),

        "duration": (
            str(record["duration"]).strip()
            if record.get("duration") is not None
            else None
        ),

        "source": normalize_source(
            record.get("source"),
            source_name,
            source_url,
            page_title,
            page_url,
            collected_date,
        ),

        "confidence": (
            record.get(
                "confidence",
                "medium"
            )
            if record.get(
                "confidence"
            ) in {
                "high",
                "medium",
                "low",
            }
            else "medium"
        ),

        "dynamic_information": bool(
            record.get(
                "dynamic_information",
                False
            )
        ),

        "status": "pending_review",
    }

    return data


# ============================================================
# EVIDENCE NORMALIZATION
# ============================================================

def normalize_text_for_evidence(text):
    """
    Normalize text for basic evidence matching.
    """

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def normalize_phrase_for_evidence(text):
    """Normalize a short phrase while tolerating basic plural variants."""

    tokens = re.findall(
        r"[a-z0-9]+",
        normalize_text_for_evidence(text),
    )

    normalized_tokens = []

    for token in tokens:
        if len(token) > 4 and token.endswith("ies"):
            token = f"{token[:-3]}y"
        elif len(token) > 4 and token.endswith("es"):
            token = token[:-2]
        elif len(token) > 3 and token.endswith("s"):
            token = token[:-1]

        normalized_tokens.append(token)

    return " ".join(normalized_tokens)


# ============================================================
# EVIDENCE VALIDATION
# ============================================================

def validate_record_evidence(
    record,
    webpage_text,
):
    """
    Validate that the entity has direct textual evidence
    in the supplied webpage chunk.
    """

    if not webpage_text:
        return False

    name = str(
        record.get(
            "name",
            ""
        )
    ).strip()

    if not name:
        return False

    text = normalize_text_for_evidence(
        webpage_text
    )

    normalized_name = normalize_text_for_evidence(
        name
    )

    # --------------------------------------------------------
    # Direct entity name
    # --------------------------------------------------------

    if normalized_name in text:
        return True

    # --------------------------------------------------------
    # Common punctuation normalization
    # --------------------------------------------------------

    simplified_name = re.sub(
        r"[^a-z0-9]+",
        " ",
        normalized_name
    ).strip()

    simplified_text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text
    )

    if (
        simplified_name
        and simplified_name in simplified_text
    ):
        return True

    # --------------------------------------------------------
    # Basic singular/plural variants in an otherwise contiguous
    # phrase (for example, "Taxi Route Rates" versus
    # "Sikkim Taxi Route Rate Chart"). Keeping the phrase
    # contiguous avoids accepting names whose words merely occur
    # at unrelated locations in the source.
    # --------------------------------------------------------

    normalized_phrase = normalize_phrase_for_evidence(name)
    normalized_source = normalize_phrase_for_evidence(webpage_text)

    if (
        normalized_phrase
        and normalized_phrase in normalized_source
    ):
        return True

    # --------------------------------------------------------
    # Allow a short name to omit at most two intervening words
    # while preserving token order. This covers a model output
    # such as "Taxi Rate Chart" for the literal source phrase
    # "Sikkim Taxi Route Rate Chart", without accepting words
    # scattered across unrelated sentences.
    # --------------------------------------------------------

    name_tokens = normalized_phrase.split()
    source_tokens = normalized_source.split()

    if len(name_tokens) >= 2:
        maximum_span = len(name_tokens) + 2

        for start, token in enumerate(source_tokens):
            if token != name_tokens[0]:
                continue

            matched = 1
            end = start + 1

            while end < len(source_tokens) and end - start < maximum_span:
                if source_tokens[end] == name_tokens[matched]:
                    matched += 1

                    if matched == len(name_tokens):
                        return True

                end += 1

    return False


# ============================================================
# REMOVE GENERIC RECORDS
# ============================================================

def is_generic_sikkim_record(
    record,
    webpage_text,
):
    """
    Prevent generic Sikkim destination records when the
    webpage does not actually describe Sikkim as a destination.
    """

    name = str(
        record.get(
            "name",
            ""
        )
    ).strip().casefold()

    category = str(
        record.get(
            "category",
            ""
        )
    ).strip().casefold()

    if name not in {
        "sikkim",
        "sikkim tourism",
    }:
        return False

    if category != "destination":
        return False

    text = webpage_text.lower()

    destination_phrases = [
        "tourist destination",
        "tourism destination",
        "travel destination",
        "visit sikkim",
        "explore sikkim",
        "tourism in sikkim",
        "travel in sikkim",
        "tourists visit sikkim",
        "sikkim offers",
        "sikkim is a paradise",
    ]

    for phrase in destination_phrases:

        if phrase in text:
            return False

    return True


# ============================================================
# NORMALIZE + VALIDATE
# ============================================================

def normalize_records(
    raw_records,
    webpage_text,
    source_name,
    source_url,
    page_title,
    page_url,
    collected_date,
):
    """
    Normalize, validate and deduplicate Qwen records.
    """

    result = []

    seen = set()

    for raw_record in raw_records:

        record = normalize_record_dict(
            raw_record,
            source_name,
            source_url,
            page_title,
            page_url,
            collected_date,
        )

        if record is None:
            continue

        # ----------------------------------------------------
        # Evidence validation
        # ----------------------------------------------------

        if not validate_record_evidence(
            record,
            webpage_text
        ):

            print(
                "[EVIDENCE] Removed record "
                "without direct entity evidence: "
                f"{record['name']}"
            )

            continue

        # ----------------------------------------------------
        # Generic Sikkim validation
        # ----------------------------------------------------

        if is_generic_sikkim_record(
            record,
            webpage_text
        ):

            print(
                "[EVIDENCE] Removed generic Sikkim "
                "destination record from page: "
                f"{page_title}"
            )

            continue

        # ----------------------------------------------------
        # Duplicate check within chunk/page
        # ----------------------------------------------------

        key = (
            record["name"].casefold(),
            record["category"].casefold(),
        )

        if key in seen:

            print(
                "[AI] Duplicate removed: "
                f"{record['name']} / "
                f"{record['category']}"
            )

            continue

        seen.add(key)

        # ----------------------------------------------------
        # Final Pydantic validation
        # ----------------------------------------------------

        try:

            validated = TourismRecord.model_validate(
                record
            )

        except Exception as e:

            print(
                "[SCHEMA] Record rejected:"
            )

            print(
                f"        {record['name']} "
                f"({record['category']})"
            )

            print(
                f"        {e}"
            )

            continue

        result.append(
            validated
        )

    return result


# ============================================================
# MERGE RECORDS FROM MULTIPLE CHUNKS
# ============================================================

def merge_records(records):
    """
    Merge records from multiple chunks and remove duplicates.

    If the same entity is found in multiple chunks, useful
    information from both chunks is combined.
    """

    merged = {}

    order = []

    for record in records:

        data = (
            record.model_dump()
            if hasattr(
                record,
                "model_dump"
            )
            else dict(record)
        )

        key = (
            str(
                data.get(
                    "name",
                    ""
                )
            ).casefold(),

            str(
                data.get(
                    "category",
                    ""
                )
            ).casefold(),
        )

        if key not in merged:

            merged[key] = data

            order.append(key)

            continue

        old = merged[key]

        # ----------------------------------------------------
        # Scalar fields
        # ----------------------------------------------------

        for field in (
            "description",
            "region",
            "district",
            "altitude",
            "how_to_reach",
            "permit_required",
            "contact",
            "website",
            "price_range",
            "duration",
        ):

            if (
                not old.get(field)
                and data.get(field)
            ):

                old[field] = data[field]

        # ----------------------------------------------------
        # List fields
        # ----------------------------------------------------

        for field in (
            "aliases",
            "best_time",
            "activities",
            "nearby_places",
            "safety_information",
            "travel_tips",
        ):

            values = []

            seen_values = set()

            for value in (
                (old.get(field) or [])
                +
                (data.get(field) or [])
            ):

                value = str(
                    value
                ).strip()

                if (
                    value
                    and value.casefold()
                    not in seen_values
                ):

                    seen_values.add(
                        value.casefold()
                    )

                    values.append(
                        value
                    )

            old[field] = values

        # ----------------------------------------------------
        # Confidence
        # ----------------------------------------------------

        old_confidence = old.get(
            "confidence",
            "medium"
        )

        new_confidence = data.get(
            "confidence",
            "medium"
        )

        confidence_rank = {
            "low": 1,
            "medium": 2,
            "high": 3,
        }

        if confidence_rank.get(
            new_confidence,
            2
        ) > confidence_rank.get(
            old_confidence,
            2
        ):

            old["confidence"] = (
                new_confidence
            )

        # ----------------------------------------------------
        # Dynamic information
        # ----------------------------------------------------

        old["dynamic_information"] = bool(
            old.get(
                "dynamic_information",
                False
            )
            or
            data.get(
                "dynamic_information",
                False
            )
        )

    # --------------------------------------------------------
    # Validate merged records
    # --------------------------------------------------------

    final_records = []

    for key in order:

        try:

            final_records.append(
                TourismRecord.model_validate(
                    merged[key]
                )
            )

        except Exception as e:

            print(
                "[SCHEMA] Merged record rejected:",
                key
            )

            print(e)

    return final_records


# ============================================================
# EXTRACT RECORDS
# ============================================================

def extract_records(
    text,
    source_name,
    source_url,
    page_title,
    page_url,
):
    """
    Extract tourism records using chunked local Ollama/Qwen
    processing.

    IMPORTANT:

    This function now:

    1. Splits large webpages into chunks.
    2. Sends each chunk separately to Ollama.
    3. Retries failed chunks.
    4. Validates each chunk.
    5. Merges records from all chunks.
    6. Removes duplicates.
    """

    if not text or not text.strip():

        raise ValueError(
            "Webpage text is empty."
        )

    today = date.today().isoformat()

    source_url = clean_url(
        source_url
    )

    page_url = clean_url(
        page_url
    )

    # ========================================================
    # SPLIT WEBPAGE INTO CHUNKS
    # ========================================================

    chunks = split_text(
        text,
        chunk_size=CHUNK_SIZE,
        overlap=CHUNK_OVERLAP,
    )

    print(
        f"[AI] Webpage length : "
        f"{len(text):,} characters"
    )

    print(
        f"[AI] Extraction chunks : "
        f"{len(chunks)}"
    )

    # ========================================================
    # COLLECT RECORDS FROM ALL CHUNKS
    # ========================================================

    all_records = []

    for index, chunk in enumerate(
        chunks,
        start=1
    ):

        print()
        print(
            "=" * 70
        )

        print(
            f"[AI] PROCESSING CHUNK "
            f"{index}/{len(chunks)}"
        )

        print(
            f"[AI] Chunk length : "
            f"{len(chunk):,} characters"
        )

        print(
            "=" * 70
        )

        # ----------------------------------------------------
        # JSON TEMPLATE
        # ----------------------------------------------------

        template = {
            "records": [
                {
                    "id": "unique_id",

                    "name": "Example entity",

                    "aliases": [],

                    "category": "destination",

                    "region": None,

                    "district": None,

                    "description": None,

                    "altitude": None,

                    "best_time": [],

                    "activities": [],

                    "nearby_places": [],

                    "how_to_reach": None,

                    "permit_required": None,

                    "safety_information": [],

                    "travel_tips": [],

                    "contact": None,

                    "website": None,

                    "price_range": None,

                    "duration": None,

                    "source": {
                        "source_name": source_name,
                        "source_url": source_url,
                        "page_title": page_title,
                        "page_url": page_url,
                        "source_type": "website",
                        "trust_level": "medium",
                        "collected_date": today,
                        "last_verified": None,
                    },

                    "confidence": "medium",

                    "dynamic_information": False,

                    "status": "pending_review",
                }
            ]
        }

        # ----------------------------------------------------
        # PROMPT
        # ----------------------------------------------------

        prompt = f"""
Extract tourism information from the source text below.

The webpage text is the ONLY source of truth.

Do not use:

- model knowledge
- internet knowledge
- previous webpages
- assumptions
- guesses
- invented facts

SOURCE INFORMATION

Source name:
{source_name}

Source URL:
{source_url}

Page title:
{page_title}

Page URL:
{page_url}

Collected date:
{today}

This is source-text chunk
{index} of {len(chunks)}.

# SOURCE TEXT

{chunk}

# STRICT RULES

1. Create records only for entities actually described
   in this webpage chunk.

2. A place mentioned only in navigation, footer, menu,
   hyperlink, related places or nearby lists is not enough.

3. General activities belong in the activities field.

4. Do not create activity records.

5. Create trekking records only when a specific trek
   is identified or described.

6. Do not automatically create Sikkim as a destination.

7. Do not create Sikkim Tourism as a destination merely
   because it appears in the page title.

8. Do not invent missing values.

9. Use null for missing scalar fields.

10. Use [] for missing list fields.

11. contact must be a STRING or null.

12. source must contain exactly:

source_name
source_url
page_title
page_url
source_type
trust_level
collected_date
last_verified

13. Do not create:

awards_achievements
leadership_key_officials
experience_sikkim
sustainable_tourism

14. Do not create fields outside the required schema.

15. Every record must have:

status = "pending_review"

16. Allowed categories are:

destination
trekking
lake
monastery
historical_place
hotel
homestay
restaurant
transport
taxi
permit
festival
culture
food
shopping
emergency
travel_tip
tour_package
faq

17. If direct evidence is insufficient,
    do not return the record.

18. Do not return records with null name.

19. Do not return records with null category.

20. Do not create duplicate records within this chunk.

21. Return ONLY JSON.

22. Each record name must copy wording that appears in the source
    text. Do not rename, pluralize, summarize, or invent the name.

23. A fare/rate table may be represented as one compact transport or
    taxi record named after the table or service. Preserve the vehicle
    types and representative route fares in price_range as one string.

REQUIRED JSON FORMAT:

{json.dumps(
    template,
    ensure_ascii=False,
    indent=2
)}

Return ONLY:

{{
    "records": [...]
}}
"""

        # ----------------------------------------------------
        # SEND CHUNK TO OLLAMA
        # ----------------------------------------------------

        raw_response = ask_ollama(
            prompt=prompt,
            chunk_number=index,
            total_chunks=len(chunks),
        )

        if not raw_response:

            print(
                f"[WARN] Chunk {index} "
                "returned no data."
            )

            continue

        # ----------------------------------------------------
        # CLEAN RESPONSE
        # ----------------------------------------------------

        raw = clean_json_response(
            raw_response
        )

        print()
        print(
            "[AI] Raw JSON received:"
        )

        print(
            raw[:5000]
        )

        # ----------------------------------------------------
        # PARSE JSON
        # ----------------------------------------------------

        try:

            data = json.loads(
                raw
            )

        except json.JSONDecodeError as e:

            print(
                "[JSON ERROR]",
                e
            )

            print(
                f"[WARN] Skipping chunk "
                f"{index}."
            )

            continue

        # ----------------------------------------------------
        # VALIDATE RESPONSE OBJECT
        # ----------------------------------------------------

        if not isinstance(
            data,
            dict
        ):

            print(
                "[JSON ERROR] Qwen response "
                "is not an object."
            )

            continue

        # ----------------------------------------------------
        # GET RECORDS
        # ----------------------------------------------------

        raw_records = data.get(
            "records",
            []
        )

        if raw_records is None:

            raw_records = []

        if not isinstance(
            raw_records,
            list
        ):

            print(
                "[JSON ERROR] 'records' "
                "is not a list."
            )

            continue

        # ----------------------------------------------------
        # NORMALIZE + VALIDATE CHUNK
        # ----------------------------------------------------

        records = normalize_records(
            raw_records=raw_records,

            webpage_text=chunk,

            source_name=source_name,

            source_url=source_url,

            page_title=page_title,

            page_url=page_url,

            collected_date=today,
        )

        print(
            f"[AI] Valid records from "
            f"chunk {index}: "
            f"{len(records)}"
        )

        all_records.extend(
            records
        )

    # ========================================================
    # MERGE ALL CHUNK RECORDS
    # ========================================================

    print()
    print(
        "=" * 70
    )

    print(
        "[AI] MERGING CHUNK RECORDS"
    )

    print(
        f"[AI] Raw records from all chunks: "
        f"{len(all_records)}"
    )

    print(
        "=" * 70
    )

    final_records = merge_records(
        all_records
    )

    print()
    print(
        "=" * 70
    )

    print(
        f"[AI] Total valid records "
        f"after chunk merge: "
        f"{len(final_records)}"
    )

    print(
        "=" * 70
    )

    return final_records


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print(
        "Ollama Tourism Extraction Agent"
    )

    print(
        f"Ollama URL       : {OLLAMA_URL}"
    )

    print(
        f"Ollama Model     : {OLLAMA_MODEL}"
    )

    print(
        f"Ollama Timeout   : {OLLAMA_TIMEOUT}s"
    )

    print(
        f"Ollama Retries   : {OLLAMA_RETRIES}"
    )

    print(
        f"Retry Delay      : {OLLAMA_RETRY_DELAY}s"
    )

    print(
        f"Chunk Size       : {CHUNK_SIZE}"
    )

    print(
        f"Chunk Overlap    : {CHUNK_OVERLAP}"
    )

    print(
        "Status           : READY"
    )
