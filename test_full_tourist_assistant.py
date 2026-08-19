import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.tourist_agent import tourist_chat
from agent.itinerary_builder import generate_itinerary, itinerary_to_markdown
from agent.permit_advisor import get_permit_guide, list_all_permit_destinations
from retrieval.search import search_approved_records

print("\n==============================================")
print("TESTING FULL SIKKIM TOURIST AI ASSISTANT SUITE")
print("==============================================\n")

# 1. Test Permit Advisor
print("[TEST 1] Testing Permit Advisor...")
nathula_guide = get_permit_guide("nathula")
print(f"Permit Guide for Nathula: {nathula_guide['name']}")
assert nathula_guide["indian_nationals"]["allowed"] is True
assert nathula_guide["foreign_nationals"]["allowed"] is False
print("[TEST 1 PASSED]\n")

# 2. Test Custom Itinerary Builder
print("[TEST 2] Testing Custom Itinerary Builder (5-Day Trip)...")
itin = generate_itinerary(days=5, theme="Scenic & Leisure", start_city="Gangtok", travelers_type="Family")
print(f"Generated Itinerary: {itin['title']}")
print(f"Days count: {len(itin['days'])}")
assert len(itin["days"]) == 5
itin_md = itinerary_to_markdown(itin)
assert "# 🏔️" in itin_md
print("Itinerary Preview:\n", itin_md[:350], "...\n")
print("[TEST 2 PASSED]\n")

# 3. Test Multi-Turn Conversational Agent
print("[TEST 3] Testing Multi-Turn Conversational Agent...")
history = []
q1 = "What are the best places to visit in Sikkim?"
r1 = tourist_chat(q1, conversation_history=history)
print(f"Q1: {q1}")
print(f"A1 Preview: {r1['answer'][:250]}...\n")
assert len(r1["answer"]) > 20
history.append({"role": "user", "content": q1})
history.append({"role": "assistant", "content": r1["answer"]})

q2 = "How can I visit Nathula Pass and do I need a permit?"
r2 = tourist_chat(q2, conversation_history=history)
print(f"Q2: {q2}")
print(f"A2 Preview: {r2['answer'][:250]}...\n")
print(f"Intent detected: {r2['intent']}")
assert "permit" in r2["answer"].lower() or "pap" in r2["answer"].lower() or "protected" in r2["answer"].lower()
print("[TEST 3 PASSED]\n")

print("==============================================")
print("ALL TOURIST ASSISTANT TESTS PASSED!")
print("==============================================")
