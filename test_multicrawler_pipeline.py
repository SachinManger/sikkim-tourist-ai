from crawler.web import crawl
from agent.ollama_agent import extract_records
from database.db import (
    get_or_create_source,
    add_document,
    add_record_if_new
)

import hashlib


# ============================================================
# CONFIGURATION
# ============================================================

SEED_URL = "https://www.sikkimtourism.gov.in/"
MAX_PAGES = 20


# ============================================================
# HEADER
# ============================================================

print("\n===================================")
print("SIKKIM TOURIST AI - MULTI PAGE PIPELINE")
print("===================================\n")


# ============================================================
# STEP 1: CRAWL WEBSITE
# ============================================================

print("[STEP 1] Starting multi-page crawler...\n")

try:
    pages = crawl(
        SEED_URL,
        max_pages=MAX_PAGES
    )

except Exception as e:
    print("[ERROR] Crawler failed:")
    print(e)
    raise


print(
    f"\n[STEP 1 COMPLETE] Pages collected: {len(pages)}"
)


if not pages:
    print("[ERROR] No pages were collected.")
    raise SystemExit(1)


# ============================================================
# STEP 2: CREATE / GET DATABASE SOURCE
# ============================================================

print("\n[STEP 2] Preparing database source...")

source_id = get_or_create_source(
    name="Sikkim Tourism",
    base_url=SEED_URL,
    source_type="website",
    trust_level="high"
)

print(f"[DATABASE] Source ID: {source_id}")


# ============================================================
# STEP 3: PROCESS EVERY PAGE
# ============================================================

total_records = 0
new_records = 0
duplicate_records = 0
skipped_pages = 0
processed_pages = 0


for page_number, page in enumerate(pages, start=1):

    print("\n===================================")
    print(
        f"PROCESSING PAGE {page_number}/{len(pages)}"
    )
    print("===================================")

    url = page["url"]
    title = page["title"]
    text = page["text"]

    print("URL:", url)
    print("TITLE:", title)
    print("TEXT LENGTH:", len(text))


    # ========================================================
    # STEP 3A: CREATE CONTENT HASH
    # ========================================================

    content_hash = hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


    # ========================================================
    # STEP 3B: SAVE / UPDATE DOCUMENT
    # ========================================================

    print("\n[DATABASE] Saving document...")

    result = add_document(
        source_id=source_id,
        url=url,
        title=title,
        content=text,
        content_hash=content_hash
    )


    # --------------------------------------------------------
    # Support both possible return formats:
    #
    # New function:
    #     (document_id, document_changed)
    #
    # Older function:
    #     document_id
    # --------------------------------------------------------

    if isinstance(result, tuple):

        document_id = result[0]
        document_changed = result[1]

    else:

        document_id = result

        # If old add_document() returns only ID,
        # assume the document should be processed.
        document_changed = True


    print(
        f"[DATABASE] Document ID: {document_id}"
    )


    # ========================================================
    # STEP 3C: SKIP UNCHANGED PAGE
    # ========================================================

    if not document_changed:

        print(
            "[DATABASE] Page unchanged - "
            "skipping Qwen."
        )

        skipped_pages += 1

        continue


    processed_pages += 1


    print(
        "[DATABASE] New or changed page - "
        "sending to Qwen."
    )


    # ========================================================
    # STEP 4: SEND PAGE TO QWEN
    # ========================================================

    print("\n[AI] Sending page to Qwen...")


    try:

        records = extract_records(
            text=text,
            source_name="Sikkim Tourism",
            source_url=SEED_URL,
            page_title=title,
            page_url=url
        )

    except Exception as e:

        print(
            "[ERROR] Qwen extraction failed:"
        )

        print(e)

        continue


    print(
        "[AI] Records extracted:",
        len(records)
    )


    # ========================================================
    # STEP 5: SAVE EXTRACTED RECORDS
    # ========================================================

    for record in records:

        total_records += 1


        # ----------------------------------------------------
        # Convert Pydantic model to dictionary
        # ----------------------------------------------------

        if hasattr(record, "model_dump"):

            record_data = record.model_dump()

        elif hasattr(record, "dict"):

            record_data = record.dict()

        elif isinstance(record, dict):

            record_data = record

        else:

            print(
                "[WARNING] Unknown record format. "
                "Skipping."
            )

            continue


        # ----------------------------------------------------
        # Get confidence
        # ----------------------------------------------------

        confidence = record_data.get(
            "confidence",
            "medium"
        )


        # ----------------------------------------------------
        # Save only if record is new
        # ----------------------------------------------------

        try:

            record_id, is_new = add_record_if_new(
                document_id=document_id,
                record=record_data,
                confidence=confidence
            )

        except Exception as e:

            print(
                "[ERROR] Failed to save record:"
            )

            print(e)

            continue


        # ----------------------------------------------------
        # New record
        # ----------------------------------------------------

        if is_new:

            new_records += 1

            print(
                f"[DATABASE] NEW record saved: "
                f"{record_id}"
            )


        # ----------------------------------------------------
        # Duplicate record
        # ----------------------------------------------------

        else:

            duplicate_records += 1

            print(
                f"[DATABASE] Duplicate skipped: "
                f"{record_id}"
            )


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n\n===================================")
print("PIPELINE COMPLETE")
print("===================================")

print(
    "Pages collected:",
    len(pages)
)

print(
    "Pages processed:",
    processed_pages
)

print(
    "Pages skipped:",
    skipped_pages
)

print(
    "Total AI records:",
    total_records
)

print(
    "New records:",
    new_records
)

print(
    "Duplicate records:",
    duplicate_records
)


# ============================================================
# NEXT STEP
# ============================================================

print("\n===================================")
print("NEXT STEP")
print("===================================")

print(
    "Open the Streamlit dashboard and "
    "review the newly extracted records."
)

print("\n===================================")
print("PIPELINE FINISHED")
print("===================================\n")