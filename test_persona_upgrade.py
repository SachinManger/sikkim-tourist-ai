import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.tourist_agent import tourist_chat

print("\n==============================================")
print("TESTING UPGRADED HUMAN PERSONA & PERSONALIZATION")
print("==============================================\n")

# Traveler Profile
profile = {
    "name": "Ananya",
    "group": "Family with Seniors",
    "diet": "Vegetarian",
    "pace": "Relaxed & Scenic",
    "budget": "Moderate Comfort"
}

query = "We want to visit North Sikkim and Gurudongmar Lake. What should we know?"
history = []

print(f"Traveler: {profile['name']} ({profile['group']}, {profile['diet']})")
print(f"Query: {query}\n")

resp = tourist_chat(
    user_message=query,
    conversation_history=history,
    traveler_profile=profile,
    max_records=5
)

print("--- TENZING'S RESPONSE ---")
print(resp["answer"])
print("\n--- SUGGESTED FOLLOWUPS ---")
for s in resp.get("suggested_followups", []):
    print("👉", s)

assert len(resp["answer"]) > 50
assert len(resp.get("suggested_followups", [])) >= 2
print("\n==============================================")
print("PERSONA & PERSONALIZATION TEST PASSED!")
print("==============================================")
