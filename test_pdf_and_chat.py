import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.pdf_extractor import extract_text_from_pdf
from agent.chat_agent import answer_question
from agent.collector import collect_from_pdf
from retrieval.search import search_approved_records

print("\n===================================")
print("TESTING UPGRADED MODULES")
print("===================================\n")

# Test 1: Test RAG Chat
print("[TEST 1] Testing RAG Chat retrieval...")
response = answer_question("What is Sikkim and what are its attractions?", max_records=3)
print("Chat Response Answer:\n", response["answer"][:300], "...")
print("Sources cited:", response["sources"])
print("Results count:", len(response["results"]))
assert len(response["answer"]) > 10, "Chat answer should not be empty"
print("[TEST 1 PASSED]\n")

# Test 2: Test Search retrieval
print("[TEST 2] Testing keyword search...")
search_res = search_approved_records("Pelling", limit=2)
print("Search results for 'Pelling':", len(search_res))
assert len(search_res) >= 1, "Should find Pelling record"
print("[TEST 2 PASSED]\n")

# Test 3: Test PDF Ingestion with mock PDF data
print("[TEST 3] Creating and testing mock PDF extraction...")
from pypdf import PdfWriter
writer = PdfWriter()
page = writer.add_blank_page(width=200, height=200)

import io
pdf_bytes_io = io.BytesIO()
writer.write(pdf_bytes_io)
pdf_bytes = pdf_bytes_io.getvalue()

parsed = extract_text_from_pdf(pdf_bytes)
print("Extracted pages from blank PDF:", parsed["total_pages"])
assert parsed["total_pages"] == 1, "Should read 1 page"
print("[TEST 3 PASSED]\n")

print("===================================")
print("ALL UNIT/INTEGRATION TESTS PASSED!")
print("===================================")
