import io
from pathlib import Path
from typing import Union, BinaryIO, List, Dict, Any

from pypdf import PdfReader
from agent.cleaner import clean_text, content_hash
from agent.ollama_agent import extract_records
from schemas.tourism import TourismRecord


def extract_text_from_pdf(
    pdf_source: Union[str, Path, bytes, BinaryIO]
) -> Dict[str, Any]:
    """
    Extracts raw and cleaned text from a PDF file path, raw bytes, or file-like object.
    
    Returns:
        Dict containing:
            - total_pages: int
            - text: str (cleaned combined text)
            - content_hash: str (SHA-256 hash of cleaned text)
            - page_texts: List[str] (per-page cleaned text)
    """
    if isinstance(pdf_source, (str, Path)):
        reader = PdfReader(str(pdf_source))
    elif isinstance(pdf_source, bytes):
        reader = PdfReader(io.BytesIO(pdf_source))
    else:
        reader = PdfReader(pdf_source)

    page_texts: List[str] = []
    for page in reader.pages:
        raw_text = page.extract_text() or ""
        cleaned = clean_text(raw_text)
        if cleaned:
            page_texts.append(cleaned)

    combined_text = "\n\n".join(page_texts).strip()
    return {
        "total_pages": len(reader.pages),
        "text": combined_text,
        "content_hash": content_hash(combined_text) if combined_text else "",
        "page_texts": page_texts,
    }


def parse_and_extract_pdf_records(
    pdf_source: Union[str, Path, bytes, BinaryIO],
    source_name: str,
    source_url: str,
    doc_title: str = "PDF Document",
    doc_url: str = "",
) -> Dict[str, Any]:
    """
    Extracts text from a PDF and processes it with Ollama/Qwen into structured tourism records.
    """
    parsed = extract_text_from_pdf(pdf_source)
    text = parsed["text"]

    if len(text) < 100:
        return {
            "total_pages": parsed["total_pages"],
            "text": text,
            "content_hash": parsed["content_hash"],
            "records": [],
            "error": "Insufficient extractable text in PDF (scanned image or empty).",
        }

    records: List[TourismRecord] = extract_records(
        text=text,
        source_name=source_name,
        source_url=source_url,
        page_title=doc_title,
        page_url=doc_url or source_url,
    )

    return {
        "total_pages": parsed["total_pages"],
        "text": text,
        "content_hash": parsed["content_hash"],
        "records": records,
        "error": None,
    }
