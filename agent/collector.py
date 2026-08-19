import sys
import os
import hashlib
import re
from datetime import date
from urllib.parse import urlparse
from typing import Callable, Optional, Dict, Any, Union
from pathlib import Path

from dotenv import load_dotenv

from crawler.web import crawl
from agent.cleaner import clean_text, content_hash
from agent.ollama_agent import extract_records
from agent.pdf_extractor import extract_text_from_pdf

from database.db import (
    init_db,
    get_or_create_source,
    add_document,
    add_document_asset,
    add_record_if_new,
    update_record,
)

load_dotenv()


def collect(
    seed_url: str,
    max_pages: Optional[int] = None,
    progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
) -> Dict[str, int]:
    """
    Crawl a website, clean webpage text, extract tourism records
    using Ollama/Qwen, and save the records into the database.
    
    progress_callback(stage: str, current: int, total: int, message: str)
    """

    print("=" * 60)
    print("SIKKIM TOURISM DATA COLLECTION")
    print("=" * 60)

    print(f"[START] Seed URL: {seed_url}")

    init_db()

    if max_pages is None:
        max_pages = int(os.getenv("MAX_PAGES", "10"))

    timeout = int(os.getenv("REQUEST_TIMEOUT", "20"))

    print(f"[CONFIG] Maximum pages : {max_pages}")
    print(f"[CONFIG] Timeout       : {timeout} seconds")

    parsed = urlparse(seed_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid URL: {seed_url}")

    domain = parsed.netloc
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    print(f"[SOURCE] Domain : {domain}")
    print(f"[SOURCE] Base   : {base_url}")

    source_id = get_or_create_source(
        domain,
        base_url,
        "website",
        "medium"
    )

    print(f"[DATABASE] Source ID: {source_id}")
    print()
    print("[CRAWLER] Starting website crawl...")

    if progress_callback:
        progress_callback("crawling", 0, max_pages, f"Crawling website {domain}...")

    pages = crawl(seed_url, max_pages)

    print(f"[CRAWLER] Pages collected: {len(pages)}")

    document_count = 0
    record_count = 0
    total_pages = len(pages)

    for index, page in enumerate(pages, start=1):
        print()
        print("-" * 60)
        print(f"[PAGE {index}/{total_pages}]")

        page_url = page.get("url", "")
        page_title = page.get("title", "")
        raw_text = page.get("text", "")

        print(f"URL   : {page_url}")
        print(f"TITLE : {page_title}")

        if progress_callback:
            progress_callback(
                "processing_page",
                index,
                total_pages,
                f"Processing page {index}/{total_pages}: {page_title or page_url[:50]}"
            )

        text = clean_text(raw_text)
        print(f"[TEXT] Cleaned length: {len(text)} characters")

        if len(text) < 100:
            print("[SKIP] Page contains insufficient text.")
            continue

        text_hash = content_hash(text)

        try:
            document_result = add_document(
                source_id,
                page_url,
                page_title,
                text,
                text_hash
            )

            if isinstance(document_result, tuple):
                document_id = document_result[0]
                document_created = document_result[1] if len(document_result) > 1 else True
            else:
                document_id = document_result
                document_created = True

            if document_created:
                document_count += 1
                print(f"[DATABASE] New document saved: {document_id}")
            else:
                print(f"[DATABASE] Existing document: {document_id}")

        except Exception as e:
            print(f"[ERROR] Could not save document: {e}")
            continue

        print("[AI] Sending webpage text to Qwen...")
        try:
            records = extract_records(
                text=text,
                source_name=domain,
                source_url=base_url,
                page_title=page_title,
                page_url=page_url
            )
        except Exception as e:
            print(f"[WARN] AI extraction failed for {page_url}: {e}")
            continue

        print(f"[AI] Records extracted: {len(records)}")

        for record in records:
            try:
                record_data = record.model_dump(mode="json")
                record_name = record_data.get("name", "Unknown")
                record_category = record_data.get("category", "unknown")

                result = add_record_if_new(
                    document_id,
                    record_data,
                    record.confidence
                )

                if isinstance(result, tuple):
                    record_id = result[0]
                    record_created = result[1] if len(result) > 1 else True
                else:
                    record_id = result
                    record_created = True

                if record_created:
                    record_count += 1
                    print(f"[DATABASE] Record saved: {record_name} ({record_category}) [ID: {record_id}]")
                else:
                    print(f"[DATABASE] Duplicate skipped: {record_name} ({record_category})")

            except Exception as e:
                print(f"[WARN] Could not save record: {e}")

    if progress_callback:
        progress_callback("completed", total_pages, total_pages, f"Complete: {record_count} records from {total_pages} pages.")

    print()
    print("=" * 60)
    print("COLLECTION COMPLETED")
    print("=" * 60)
    print(f"Pages collected     : {len(pages)}")
    print(f"Documents saved     : {document_count}")
    print(f"Tourism records     : {record_count}")
    print("=" * 60)

    return {
        "pages": len(pages),
        "documents": document_count,
        "records": record_count,
    }


def collect_from_pdf(
    pdf_source: Any,
    filename: str = "uploaded_document.pdf",
    source_name: str = "PDF Document",
    source_url: str = "document://sikkim_tourism_pdf",
    progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
) -> Dict[str, Any]:
    """
    Extracts text from a PDF, chunks & structures it with Ollama/Qwen, and saves records.
    """
    init_db()

    if progress_callback:
        progress_callback("extracting_text", 1, 4, f"Reading and extracting text from {filename}...")

    parsed = extract_text_from_pdf(pdf_source)
    text = parsed["text"]
    total_pages = parsed["total_pages"]

    if len(text) < 80:
        if progress_callback:
            progress_callback("error", 4, 4, "PDF has insufficient extractable text.")
        return {
            "pages": total_pages,
            "documents": 0,
            "records": 0,
            "error": "Insufficient extractable text in PDF."
        }

    source_id = get_or_create_source(
        name=source_name,
        base_url=source_url,
        source_type="document",
        trust_level="high"
    )

    if progress_callback:
        progress_callback("saving_doc", 2, 4, f"Saving PDF document ({total_pages} pages, {len(text)} chars)...")

    doc_result = add_document(
        source_id=source_id,
        url=f"{source_url}#{filename}",
        title=filename,
        content=text,
        content_hash=parsed["content_hash"]
    )
    document_id = doc_result[0] if isinstance(doc_result, tuple) else doc_result
    document_created = doc_result[1] if isinstance(doc_result, tuple) else True

    if progress_callback:
        progress_callback("ai_extraction", 3, 4, "Extracting structured tourism records with Qwen...")

    records = extract_records(
        text=text,
        source_name=source_name,
        source_url=source_url,
        page_title=filename,
        page_url=f"{source_url}#{filename}"
    )

    saved_records = 0
    for record in records:
        try:
            record_data = record.model_dump(mode="json")
            result = add_record_if_new(
                document_id=document_id,
                record=record_data,
                confidence=record.confidence
            )
            created = result[1] if isinstance(result, tuple) else True
            if created:
                saved_records += 1
        except Exception as e:
            print(f"[WARN] Failed saving record from PDF: {e}")

    if progress_callback:
        progress_callback("completed", 4, 4, f"Finished! Extracted {len(records)} records ({saved_records} new).")

    return {
        "pages": total_pages,
        "documents": 1 if document_created else 0,
        "records": saved_records,
        "total_extracted": len(records),
        "duplicates": len(records) - saved_records,
        "error": None
    }


def _safe_asset_name(file_name: str) -> str:
    """Return a filesystem-safe evidence filename."""
    original = Path(file_name or "image").name
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(original).stem).strip("._")
    suffix = Path(original).suffix.lower()
    return f"{stem or 'image'}{suffix}"


def _infer_manual_category(title: str, text: str) -> str:
    """Infer a broad topic when the curator leaves category on Auto."""
    content = f"{title} {text}".lower()
    rules = [
        ("history", ("history", "historical", "kingdom", "chogyal", "monarchy")),
        ("permit", ("permit", "pap", "rap", "ilp", "restricted area")),
        ("transport", ("fare", "taxi", "bus", "transport", "route", "road")),
        ("food", ("food", "cuisine", "dish", "restaurant")),
        ("culture", ("culture", "festival", "dance", "tradition")),
        ("trekking", ("trek", "trail", "hike")),
        ("lake", ("lake",)),
    ]
    for category, keywords in rules:
        if any(keyword in content for keyword in keywords):
            return category
    return "destination"


def _has_substantive_record_content(record: Dict[str, Any]) -> bool:
    """Reject entity shells that contain a name but no usable knowledge."""
    scalar_fields = (
        "description",
        "how_to_reach",
        "price_range",
        "duration",
        "contact",
        "website",
        "altitude",
    )
    list_fields = (
        "activities",
        "best_time",
        "nearby_places",
        "safety_information",
        "travel_tips",
    )
    return any(record.get(field) for field in scalar_fields) or any(
        record.get(field) for field in list_fields
    )


def collect_from_manual_entry(
    text: str,
    title: str,
    source_name: str = "Manual Knowledge Entry",
    source_url: str = "manual://knowledge-entry",
    trust_level: str = "medium",
    category: str = "auto",
    approve_canonical: bool = False,
    images: Optional[list[Dict[str, Any]]] = None,
    progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
) -> Dict[str, Any]:
    """Save manually entered text and linked image evidence, then extract records."""
    init_db()

    cleaned_text = clean_text(text)
    title = (title or "Manual Knowledge Entry").strip()
    source_name = (source_name or "Manual Knowledge Entry").strip()
    source_url = (source_url or "manual://knowledge-entry").strip()

    if len(cleaned_text) < 30:
        return {
            "documents": 0,
            "records": 0,
            "total_extracted": 0,
            "images": 0,
            "error": "Please enter at least 30 characters of knowledge text or image description.",
        }

    if progress_callback:
        progress_callback("saving", 1, 3, "Saving text and image evidence...")

    source_id = get_or_create_source(
        name=source_name,
        base_url=source_url,
        source_type="manual",
        trust_level=trust_level,
    )

    text_digest = content_hash(cleaned_text)
    document_url = f"{source_url.rstrip('#/')}#manual-{text_digest[:16]}"
    document_result = add_document(
        source_id=source_id,
        url=document_url,
        title=title,
        content=cleaned_text,
        content_hash=text_digest,
    )
    document_id = document_result[0] if isinstance(document_result, tuple) else document_result
    document_created = document_result[1] if isinstance(document_result, tuple) else True

    manual_category = (
        _infer_manual_category(title, cleaned_text)
        if category == "auto"
        else category
    )
    canonical_status = "approved" if approve_canonical else "pending_review"
    canonical_record = {
        "id": f"manual_{text_digest[:16]}",
        "name": title,
        "aliases": [],
        "category": manual_category,
        "description": cleaned_text,
        "source": {
            "source_name": source_name,
            "source_url": source_url,
            "page_title": title,
            "page_url": document_url,
            "source_type": "manual",
            "trust_level": trust_level,
            "collected_date": date.today().isoformat(),
            "last_verified": date.today().isoformat() if approve_canonical else None,
        },
        "confidence": "high" if trust_level == "high" else "medium",
        "dynamic_information": False,
        "manual_entry": True,
        "status": canonical_status,
    }
    canonical_id, canonical_created = add_record_if_new(
        document_id=document_id,
        record=canonical_record,
        confidence=canonical_record["confidence"],
    )
    if approve_canonical:
        update_record(
            canonical_id,
            canonical_record,
            "approved",
            "Manually entered and explicitly verified by curator.",
        )

    upload_dir = Path(__file__).resolve().parents[1] / "data" / "knowledge_images"
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_images = 0
    for image in images or []:
        image_bytes = image.get("data", b"")
        if not image_bytes:
            continue

        image_digest = hashlib.sha256(image_bytes).hexdigest()
        safe_name = _safe_asset_name(str(image.get("name", "image")))
        stored_name = f"{image_digest[:16]}_{safe_name}"
        stored_path = upload_dir / stored_name
        if not stored_path.exists():
            stored_path.write_bytes(image_bytes)

        relative_path = stored_path.relative_to(Path(__file__).resolve().parents[1])
        _, created = add_document_asset(
            document_id=document_id,
            file_name=safe_name,
            file_path=str(relative_path),
            mime_type=str(image.get("type", "application/octet-stream")),
            content_hash=image_digest,
        )
        if created:
            saved_images += 1

    if progress_callback:
        progress_callback("extracting", 2, 3, "Extracting structured pending-review records...")

    records = extract_records(
        text=cleaned_text,
        source_name=source_name,
        source_url=source_url,
        page_title=title,
        page_url=document_url,
    )

    saved_records = 1 if canonical_created else 0
    usable_ai_records = 0
    for record in records:
        record_data = record.model_dump(mode="json")
        if not _has_substantive_record_content(record_data):
            print(f"[MANUAL] Skipping empty entity shell: {record_data.get('name', 'Unnamed')}")
            continue
        usable_ai_records += 1
        _, created = add_record_if_new(
            document_id=document_id,
            record=record_data,
            confidence=record.confidence,
        )
        if created:
            saved_records += 1

    if progress_callback:
        progress_callback("completed", 3, 3, "Manual knowledge entry completed.")

    return {
        "documents": 1 if document_created else 0,
        "document_id": document_id,
        "records": saved_records,
        "total_extracted": usable_ai_records + 1,
        "images": saved_images,
        "canonical_record_id": canonical_id,
        "canonical_status": canonical_status,
        "duplicates": (usable_ai_records + 1) - saved_records,
        "error": None,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage: python -m agent.collector <url_or_pdf_path> [max_pages]")
        print("Example: python -m agent.collector https://www.sikkimtourism.gov.in/ 5\n")
        raise SystemExit(1)

    target = sys.argv[1]
    if target.lower().endswith(".pdf") or os.path.isfile(target):
        print(f"[PDF MODE] Processing PDF file: {target}")
        res = collect_from_pdf(target, filename=Path(target).name)
        print("Result:", res)
    else:
        max_p = int(sys.argv[2]) if len(sys.argv) >= 3 else None
        collect(target, max_p)
