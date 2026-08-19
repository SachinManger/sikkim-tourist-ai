import json
import os
import requests
from dotenv import load_dotenv

from retrieval.search import search_approved_records

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


SYSTEM_PROMPT = """
You are Sikkim Tourist AI.

You are a retrieval-based tourism assistant for Sikkim, India.

IMPORTANT KNOWLEDGE RULE:

You MUST answer ONLY using information contained in the
APPROVED KNOWLEDGE provided in the user prompt.

You are NOT allowed to use your own general knowledge.

You MUST NOT add:
- places
- monasteries
- activities
- distances
- prices
- dates
- travel information
- historical facts
- names
- recommendations

unless that information appears in the APPROVED KNOWLEDGE.

If the requested information is not contained in the
APPROVED KNOWLEDGE, say:

"I don't currently have enough approved information in my knowledge base to answer that."

Do not guess.
Do not complete missing information from your own knowledge.
Do not invent facts.

When answering, prefer a clear, helpful, and accurate response based strictly on the retrieved records.
"""


def answer_question(question: str, max_records: int = 5):
    """
    Retrieves approved records matching user question and generates an answer strictly grounded in that knowledge.
    """
    print("[RETRIEVAL] Searching knowledge base...")

    # 1. Search approved records
    results = search_approved_records(
        question,
        limit=max_records
    )

    print(f"[RETRIEVAL] Records found: {len(results)}")

    if not results:
        return {
            "answer": "I don't currently have enough approved information in my knowledge base to answer that question. You can collect data from tourism sources and approve records in the Review tab.",
            "sources": [],
            "results": []
        }

    # 2. Build knowledge context
    context_parts = []
    for result in results:
        record = result["record"]
        context_parts.append(
            json.dumps(record, ensure_ascii=False, indent=2)
        )

    context = "\n\n".join(context_parts)

    # 3. Create Qwen prompt
    prompt = f"""USER QUESTION:
{question}

APPROVED KNOWLEDGE:
{context}

STRICT INSTRUCTIONS:
Answer the USER QUESTION using ONLY the APPROVED KNOWLEDGE above.
The APPROVED KNOWLEDGE is the only source of truth.
DO NOT use your existing knowledge about Sikkim.
DO NOT add any information that is not explicitly present in the APPROVED KNOWLEDGE.
If the answer cannot be found in the APPROVED KNOWLEDGE, respond:
"I don't currently have enough approved information in my knowledge base to answer that."
Keep the answer concise, pleasant, and useful with bullet points if appropriate.
"""

    # 4. Query Ollama / Qwen
    print("[AI] Sending question to Qwen...")
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "system": SYSTEM_PROMPT,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2
                }
            },
            timeout=180
        )
        response.raise_for_status()
        data = response.json()
        answer = data.get("response", "").strip()
    except Exception as e:
        answer = f"Error querying local Ollama engine: {e}"

    # 5. Collect sources
    sources = []
    for result in results:
        source_url = result.get("source_url")
        if source_url and source_url not in sources:
            sources.append(source_url)

    return {
        "answer": answer,
        "sources": sources,
        "results": results
    }