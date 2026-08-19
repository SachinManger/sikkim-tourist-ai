from crawler.web import crawl
from agent.ollama_agent import extract_records
from database.db import get_or_create_source, add_document, add_record_if_new
import hashlib


SEED_URL = "https://www.sikkimtourism.gov.in/"


print("\n===================================")
print("SIKKIM TOURIST AI DATA AGENT")
print("CRAWLER → QWEN TEST")
print("===================================\n")


# --------------------------------------------------
# STEP 1: Crawl one webpage
# --------------------------------------------------

print("[STEP 1] Starting crawler...\n")

pages = crawl(
    seed_url=SEED_URL,
    max_pages=1,
)


if not pages:
    print("[ERROR] No webpage was collected.")
    raise SystemExit(1)


page = pages[0]


print("\n[STEP 1 COMPLETE]")
print("URL:", page["url"])
print("TITLE:", page["title"])
print("TEXT LENGTH:", len(page["text"]))


# --------------------------------------------------
# STEP 2: Send webpage text to Qwen
# --------------------------------------------------

print("\n[STEP 2] Sending webpage to Qwen...")


records = extract_records(
    text=page["text"],
    source_name="Sikkim Tourism",
    source_url=SEED_URL,
    page_title=page["title"],
    page_url=page["url"]
)
    # STEP 3: Save source and webpage to SQLite
source_id = get_or_create_source(
    name="Sikkim Tourism",
    base_url="https://www.sikkimtourism.gov.in/",
    source_type="website",
    trust_level="high"
)

content_hash = hashlib.sha256(
    page["text"].encode("utf-8")
).hexdigest()

document_id, document_is_new = add_document(
    source_id=source_id,
    url=page["url"],
    title=page["title"],
    content=page["text"],
    content_hash=content_hash
)

# Save each extracted tourism record
for record in records:
    record_data = (
        record.model_dump()
        if hasattr(record, "model_dump")
        else record
    )

    record_id, is_new = add_record_if_new(
        document_id=document_id,
        record=record_data,
        confidence=record.confidence
    )

    if is_new:
        print(f"[DATABASE] New record saved: {record_id}")
    else:
        print(f"[DATABASE] Duplicate record skipped: {record_id}")

print("[STEP 3 COMPLETE] Records saved to SQLite.")


# --------------------------------------------------
# STEP 3: Display extracted records
# --------------------------------------------------

print("\n===================================")
print("AI EXTRACTION RESULTS")
print("===================================\n")


print("Records extracted:", len(records))


for number, record in enumerate(records, start=1):

    print("\n-----------------------------------")
    print(f"RECORD {number}")
    print("-----------------------------------")

    print("ID:", record.id)
    print("NAME:", record.name)
    print("CATEGORY:", record.category)
    print("DESCRIPTION:", record.description)
    print("CONFIDENCE:", record.confidence)
    print("STATUS:", record.status)

    print("SOURCE:", record.source.source_name)
    print("SOURCE URL:", record.source.source_url)


print("\n===================================")
print("PIPELINE TEST FINISHED")
print("===================================")