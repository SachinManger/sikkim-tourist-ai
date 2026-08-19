from database.db import (
    get_or_create_source,
    add_document,
    add_record,
    stats
)
import hashlib


# 1. Create/get a tourism source
source_id = get_or_create_source(
    name="Sikkim Tourism Test",
    base_url="https://example.com",
    source_type="website",
    trust_level="medium"
)

print("Source ID:", source_id)


# 2. Sample webpage content
content = """
Pelling is a popular tourist destination in West Sikkim.
It is known for views of Mount Kanchenjunga, monasteries,
trekking and nearby tourist attractions.
"""


# 3. Create a hash for the webpage content
content_hash = hashlib.sha256(
    content.encode("utf-8")
).hexdigest()


# 4. Store the webpage/document
document_id = add_document(
    source_id=source_id,
    url="https://example.com/pelling",
    title="Pelling Tourism",
    content=content,
    content_hash=content_hash
)

print("Document ID:", document_id)


# 5. Tourism record produced by our AI
record = {
    "id": "test_pelling_001",
    "name": "Pelling",
    "category": "destination",
    "description": (
        "A popular tourist destination in West Sikkim "
        "known for mountain views, monasteries and trekking."
    ),
    "activities": [
        "sightseeing",
        "trekking",
        "nature"
    ],
    "nearby_places": [
        "Pemayangtse Monastery",
        "Rabdentse Ruins"
    ],
    "source": {
        "source_name": "Sikkim Tourism Test",
        "source_url": "https://example.com"
    }
}


# 6. Store the AI record
record_id = add_record(
    document_id=document_id,
    record=record,
    confidence="medium"
)

print("Record ID:", record_id)


# 7. Show database statistics
print("\nDatabase statistics:")
print(stats())

print("\n===== DATABASE TEST SUCCESSFUL =====")