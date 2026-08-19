"""
Comprehensive Grounded Sikkim Tourist AI Agent - "Tenzing: The Warm Himalayan Guide"
Combines local persona, multi-turn memory, traveler profiling, intent routing, and grounded knowledge retrieval.
"""
import json
import os
import re
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from retrieval.search import search_approved_records
from database.db import search_document_assets
from agent.permit_advisor import get_permit_guide
from agent.itinerary_builder import generate_itinerary, itinerary_to_markdown

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


SYSTEM_PROMPT = """You are Tenzing, a knowledgeable and friendly Sikkim travel assistant.

CONVERSATION STYLE:
- Sound natural and human. Answer the question first, in plain language.
- After the direct answer, add the most useful verified context for that specific topic.
- Aim for a complete but focused response: normally 3–6 compact bullets or short paragraphs.
- Never make an answer longer by adding unrelated travel topics or filler.
- Do not greet the traveler again on every turn.
- Use bullets only when they make the answer easier to scan.
- Use traveler-profile details only when they are relevant to the current question.

RELEVANCE RULES:
1. Discuss only what the traveler asked about, plus a necessary clarification or safety caveat.
2. Never add cuisine, sightseeing, photography, altitude, packing, permits, or itinerary suggestions unless the question asks for them or they are essential to safety.
3. Treat the current question as primary. Do not carry unrelated topics forward from chat history.
4. For a specific fare question, give the exact requested route and available vehicle/fare options only. Do not list other routes.
5. For an SNT or bus question, use only SNT/bus evidence. Never substitute a taxi, cab, or shared-Sumo fare.
6. Do not apply a fixed travel template blindly. Include a section only when it helps answer the current question.
7. When no transport mode is specified, mention every verified mode found for the requested journey; do not omit SNT buses.

GROUNDING RULES:
1. Ground all specific places, routes, timings, and prices strictly in the PROVIDED VERIFIED KNOWLEDGE BASE.
2. Never invent or estimate a price that is absent from the provided records.
3. If the exact requested detail is unavailable, say so briefly and suggest one practical way to verify it.
4. If verified records contain different figures, distinguish what each figure represents instead of blending them.
5. Do not call a fare current or latest unless the record includes a verification date. Say "according to the verified fare chart" and note that fares can change.
"""


ANSWER_GUIDES = {
    "image": (
        "Show only knowledge-base images matching the requested person, place, or topic. "
        "Do not replace a missing image with general destination advice."
    ),
    "history": (
        "Answer with the relevant chronology, people, events, dates, and historical significance only. "
        "Do not add best time to visit, permits, transport, nearby places, food, or sightseeing unless explicitly asked."
    ),
    "destination": (
        "Explain what the place is and why it is relevant; then include only available details among "
        "location, best time, opening/visit timing, entry fee, permit, how to reach, and genuinely nearby places."
    ),
    "transport": (
        "Cover the requested route or mode only: available fares, timing, approximate duration, booking point, "
        "permit/checkpoint information, road caveat, and places directly on the route."
    ),
    "permit": (
        "State clearly whether a permit is required, who needs it, required documents, where/how to obtain it, "
        "fees or processing time if verified, validity, and important restrictions."
    ),
    "trekking": (
        "Cover route, duration, difficulty, altitude, suitable season, permit/guide requirements, essential safety, "
        "and the correct starting point when those facts are verified."
    ),
    "food": (
        "Describe the requested dish or food topic, key ingredients, vegetarian/non-vegetarian status, taste, "
        "and where it is commonly available; include allergy or dietary notes only when relevant."
    ),
    "culture": (
        "Explain the requested tradition, monastery, festival, or cultural topic; include timing, location, "
        "visitor etiquette, entry rules, and photography restrictions only when relevant and verified."
    ),
    "lake": (
        "Cover location, access route, best season, permit, altitude, visit timing, and essential safety, "
        "using only details verified for that lake."
    ),
    "safety": (
        "Answer the safety concern first, then give practical action steps, relevant warning signs, "
        "and verified emergency contacts or escalation guidance."
    ),
    "itinerary": (
        "Give a realistic sequence with travel times, route logic, permits, and overnight stops; "
        "exclude attractions that do not fit the route or available time."
    ),
}


def answer_guide_for_intent(intent: str) -> str:
    """Return the relevance checklist for the classified question type."""
    return ANSWER_GUIDES.get(intent, ANSWER_GUIDES["destination"])


def available_transport_modes(results: List[Dict[str, Any]]) -> List[str]:
    """Identify road-transport modes explicitly supported by retrieved records."""
    text = " ".join(
        json.dumps(result.get("record", {}), ensure_ascii=False)
        for result in results
    ).lower()
    modes = []
    if "snt" in text and "bus" in text:
        modes.append("SNT bus")
    if "shared sumo" in text or "shared taxi" in text:
        modes.append("shared taxi/Sumo")
    if "reserved taxi" in text or "private taxi" in text:
        modes.append("reserved/private taxi")
    return modes


def append_missing_snt_option(answer: str, results: List[Dict[str, Any]]) -> str:
    """Guarantee that an available SNT option is not dropped by the model."""
    if re.search(r"\b(?:snt|bus)\b", answer, flags=re.IGNORECASE):
        return answer

    snt_record = next(
        (
            result["record"]
            for result in results
            if "snt" in str(result["record"].get("name", "")).lower()
        ),
        None,
    )
    if not snt_record:
        return answer

    price_text = str(snt_record.get("price_range", ""))
    normal_match = re.search(r"normal bus:\s*(₹[\d,]+)", price_text, flags=re.IGNORECASE)
    ac_match = re.search(r"a/c bus:\s*(₹[\d,]+)", price_text, flags=re.IGNORECASE)
    generic_amounts = re.findall(r"₹[\d,]+", price_text)

    fare_parts = []
    if normal_match:
        fare_parts.append(f"normal bus {normal_match.group(1)}")
    if ac_match:
        fare_parts.append(f"A/C bus {ac_match.group(1)}")
    if not fare_parts and generic_amounts:
        fare_parts.append(f"fare {generic_amounts[0]}")

    sentence = "SNT bus service is also available"
    if fare_parts:
        sentence += ": " + " and ".join(fare_parts)

    schedule = snt_record.get("schedule", [])
    if schedule:
        sentence += ". Listed departures are " + "; ".join(str(item) for item in schedule)

    return f"{answer}\n\n{sentence}."


def classify_intent(query: str) -> str:
    """Classifies the primary tourism topic for optimal retrieval strategy."""
    q = query.lower()
    image_words = ("photo", "image", "picture", "photograph")
    image_request_words = ("old", "historic", "historical", "show", "see", "display", "find", "have")
    if (
        any(word in q for word in image_words)
        and any(word in q for word in image_request_words)
        and not any(phrase in q for phrase in ("photo spot", "photography spot", "best photo time"))
    ):
        return "image"
    if any(w in q for w in [
        "history", "historical", "kingdom", "chogyal", "monarchy", "annexed", "merger"
    ]):
        return "history"
    if any(w in q for w in [
        "taxi", "cab", "fare", "vehicle rate", "transport", "shared sumo",
        "bus fare", "train", "flight", "airport transfer", "how to reach",
        "road", "drive", "driving", "travel time", "journey time", "route condition"
    ]):
        return "transport"
    if any(w in q for w in ["itinerary", "plan", "days", "trip to", "tour", "schedule", "how many days"]):
        return "itinerary"
    if any(w in q for w in ["permit", "pap", "rap", "ilp", "pass", "restricted", "foreign", "foreigner", "passport", "allowed"]):
        return "permit"
    if any(w in q for w in ["trek", "trekking", "hike", "hiking", "dzongri", "goecha", "singalila", "trail"]):
        return "trekking"
    if any(w in q for w in ["food", "cuisine", "eat", "drink", "dish", "momos", "thukpa", "tongba", "restaurant", "veg", "vegetarian"]):
        return "food"
    if any(w in q for w in ["monastery", "culture", "festival", "dance", "tradition", "gompa", "buddhist", "temple"]):
        return "culture"
    if any(w in q for w in ["altitude", "safety", "oxygen", "ams", "sickness", "emergency", "hospital", "police", "weather", "doctor"]):
        return "safety"
    if any(w in q for w in ["lake", "tsomgo", "gurudongmar", "khecheopalri"]):
        return "lake"
    return "destination"


def generate_suggested_followups(intent: str, query: str) -> List[str]:
    """Generates 3 contextual next-step prompts based on what the user asked."""
    if intent == "image":
        return [
            "🖼️ Show other historical images of Sikkim",
            "📜 Tell me the history connected to this image",
        ]
    if intent == "itinerary":
        return [
            "📜 What permits are needed for this itinerary?",
            "🍲 What local dishes should we try along this route?",
            "⛰️ Any altitude precautions for this trip?"
        ]
    elif intent == "permit":
        return [
            "🗺️ Suggest a day-by-day plan covering these spots",
            "🥾 How is the road condition and travel time?",
            "📸 Best time of year to visit for clear views"
        ]
    elif intent == "food":
        return [
            "🍲 Top cafes and food spots in Gangtok",
            "📜 Do I need permits for food & cultural trails?",
            "🏔️ Recommend scenic destinations nearby"
        ]
    elif intent == "trekking":
        return [
            "📜 Permit and guide requirements for Dzongri",
            "🎒 Essential packing list for high-altitude treks",
            "🏕️ Best season for trekking in West Sikkim"
        ]
    elif intent == "safety":
        return [
            "📜 Emergency contacts and hospital locations in Sikkim",
            "🚗 Road travel times between Gangtok and North Sikkim",
            "🗺️ Recommend a relaxed, low-altitude itinerary"
        ]
    elif intent == "lake":
        return [
            "📜 Permit rules for Tsomgo and Gurudongmar Lakes",
            "🚗 How early should we leave for lake excursions?",
            "🧥 What warm clothes should we pack for high lakes?"
        ]
    elif intent == "transport":
        return [
            "🚕 Is a shared or reserved taxi better for this route?",
            "🕒 How long does this journey usually take?",
            "📍 Where can I book a prepaid taxi?"
        ]
    else:
        return [
            "🗺️ Plan a customized 4-day Sikkim itinerary",
            "📜 Check permit requirements for border areas",
            "🍲 Tell me about traditional Sikkimese food"
        ]


def asks_for_current_road_condition(query: str) -> bool:
    """Detect road-status questions that require current verified data."""
    q = query.lower()
    phrases = [
        "road condition",
        "road status",
        "how is the road",
        "is the road open",
        "roads open",
        "road closed",
        "road closure",
        "landslide",
    ]
    return any(phrase in q for phrase in phrases)


def requested_transport_mode(query: str) -> str:
    """Return the explicitly requested mode, or all when none was named."""
    q = query.lower()
    if "snt" in q or "bus" in q:
        return "bus"
    if any(term in q for term in ("taxi", "cab", "reserved", "reserve taxi")):
        return "taxi"
    return "all"


def extract_requested_route(query: str) -> Optional[tuple[str, str]]:
    """Extract common 'from X to Y' and 'reach Y from X' route wording."""
    match = re.search(
        r"\bfrom\s+(.+?)\s+to\s+(.+?)(?:\s+(?:on|by|using)\s+|[?.!,]|$)",
        query.strip(),
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1).strip().lower(), match.group(2).strip().lower()

    reverse_match = re.search(
        r"\b(?:reach|get to|go to|travel to)\s+(.+?)\s+from\s+(.+?)(?:\s+(?:on|by|using)\s+|[?.!,]|$)",
        query.strip(),
        flags=re.IGNORECASE,
    )
    if reverse_match:
        return reverse_match.group(2).strip().lower(), reverse_match.group(1).strip().lower()

    return None


def record_contains_route(record: Dict[str, Any], origin: str, destination: str) -> bool:
    """Check whether a record explicitly names the requested route."""
    route_fields = [
        record.get("name", ""),
        record.get("description", ""),
        record.get("price_range", ""),
        " ".join(str(alias) for alias in record.get("aliases", [])),
    ]
    text = " ".join(str(value) for value in route_fields).lower()
    text = re.sub(r"\s*(?:→|↔|–|—|-)\s*", " to ", text)
    text = re.sub(r"\s+", " ", text)
    return f"{origin} to {destination}" in text


def build_route_context(
    results: List[Dict[str, Any]],
    origin: str,
    destination: str,
) -> str:
    """Build concise, route-only logistics from a structured route record."""
    route_record = None
    snt_departure = None

    for result in results:
        record = result["record"]
        if not record_contains_route(record, origin, destination):
            continue

        if record.get("permit_information") and record.get("how_to_reach"):
            route_record = record

        if "snt" in str(record.get("name", "")).lower():
            departure_match = re.search(
                r"departs at\s+([0-9:]+\s*[ap]m)",
                str(record.get("description", "")),
                flags=re.IGNORECASE,
            )
            if departure_match:
                snt_departure = departure_match.group(1).upper()

    if not route_record:
        return ""

    distance = route_record.get("distance")
    duration = route_record.get("duration")
    route_path = route_record.get("how_to_reach")
    permit_info = route_record.get("permit_information")
    en_route_places = route_record.get("nearby_places", [])

    sections = []
    travel_bits = []
    if distance:
        travel_bits.append(f"The road journey is {distance}")
    if duration:
        travel_bits.append(str(duration).rstrip("."))
    if travel_bits:
        sections.append(". ".join(travel_bits) + ".")
    if route_path:
        sections.append(f"The usual route is {route_path}")
    if snt_departure:
        sections.append(f"The listed normal SNT bus departs Namchi at {snt_departure}.")
    if permit_info:
        sections.append(f"**Permit:** {permit_info}")
    if en_route_places:
        places = ", ".join(str(place) for place in en_route_places)
        sections.append(
            f"**On the way:** You pass through or alongside {places}. "
            "These are on the normal route, not separate sightseeing detours."
        )

    return "\n\n".join(sections)


def build_exact_fare_answer(
    results: List[Dict[str, Any]],
    origin: str,
    destination: str,
    transport_mode: str,
) -> Optional[str]:
    """Format route-specific fares directly, without generative rewriting."""
    fares = []
    route_context = build_route_context(results, origin, destination)

    def with_route_context(answer: str) -> str:
        return f"{answer}\n\n{route_context}" if route_context else answer

    for result in results:
        record = result["record"]
        identity_record = {
            "name": record.get("name", ""),
            "aliases": record.get("aliases", []),
        }
        if not record_contains_route(identity_record, origin, destination):
            continue

        price_text = str(record.get("price_range", ""))
        matching_segment = next(
            (
                segment.strip()
                for segment in price_text.split(";")
                if record_contains_route(
                    {"price_range": segment},
                    origin,
                    destination,
                )
            ),
            "",
        )
        amount_match = re.search(r"₹\s*[\d,]+", matching_segment)
        if not amount_match:
            continue

        amount = amount_match.group(0).replace("₹ ", "₹")
        category = str(record.get("category", "")).lower()
        record_name = str(record.get("name", "")).lower()

        if category == "taxi" or "taxi" in record_name or "cab" in record_name:
            label = "Reserved taxi"
            value = f"starts at {amount} one way"
            if record.get("dynamic_information"):
                value += " (dynamic booking price; extra charges may apply)"
            order = 1
        else:
            label = "SNT bus"
            value = amount
            order = 0

        fares.append((order, label, value))

    if not fares:
        return None

    fares.sort(key=lambda item: item[0])

    if transport_mode != "all" and len(fares) == 1:
        _, label, value = fares[0]
        clean_value = value.replace(
            " (dynamic booking price; extra charges may apply)",
            "",
        )
        if value.startswith("starts at "):
            return with_route_context(
                f"For a reserved taxi from {origin.title()} to {destination.title()}, "
                f"prices currently {clean_value.replace('starts at', 'start at about', 1)}. "
                "It’s a dynamic booking price, so extra charges may apply."
            )
        return with_route_context(
            f"If you’re taking the {label} from {origin.title()} to {destination.title()}, "
            f"the fare is {clean_value}."
        )

    clauses = []
    has_dynamic_fare = False
    for _, label, value in fares:
        clean_value = value.replace(
            " (dynamic booking price; extra charges may apply)",
            "",
        )
        if value.startswith("starts at "):
            clauses.append(
                f"a {label.lower()} {clean_value.replace('starts at', 'starts at about', 1)}"
            )
            has_dynamic_fare = True
        else:
            clauses.append(f"the {label} is {clean_value}")

    if len(clauses) == 2:
        answer = (
            f"For {origin.title()} to {destination.title()}, {clauses[0]}, "
            f"while {clauses[1]}."
        )
    else:
        answer = f"For {origin.title()} to {destination.title()}, " + ", while ".join(clauses) + "."

    if has_dynamic_fare:
        answer += " Taxi prices are dynamic, so extra charges may apply."

    return with_route_context(answer)


def _format_grounded_value(value: Any) -> str:
    """Turn a structured record value into compact, readable text."""
    if value is None or value == "" or value == [] or value == {}:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list):
        return "; ".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, dict):
        return "; ".join(
            f"{str(key).replace('_', ' ').title()}: {_format_grounded_value(item)}"
            for key, item in value.items()
            if _format_grounded_value(item)
        )
    return " ".join(str(value).split())


def build_grounded_fallback_answer(
    user_message: str,
    intent: str,
    results: List[Dict[str, Any]],
) -> str:
    """Answer from approved records when no remote language model is available."""
    if not results:
        return (
            "I couldn’t find a verified knowledge-base record that answers that yet. "
            "Try the exact place, route, or permit name and I’ll check again."
        )

    field_order = {
        "history": ["description"],
        "transport": [
            "price_range", "schedule", "duration", "distance", "how_to_reach",
            "permit_information", "safety_information",
        ],
        "permit": [
            "permit_required", "permit_information", "description", "requirements",
            "documents_required", "fees", "validity", "restrictions",
        ],
        "trekking": [
            "description", "duration", "difficulty", "altitude", "best_time",
            "permit_required", "how_to_reach", "safety_information",
        ],
        "food": ["description", "activities", "region", "travel_tips"],
        "culture": [
            "description", "district", "best_time", "timings", "price_range",
            "permit_required", "travel_tips",
        ],
        "lake": [
            "description", "district", "altitude", "best_time", "how_to_reach",
            "permit_required", "safety_information",
        ],
        "safety": ["safety_information", "description", "contact", "travel_tips"],
        "itinerary": [
            "description", "how_to_reach", "duration", "best_time",
            "permit_required", "nearby_places",
        ],
        "destination": [
            "description", "district", "region", "best_time", "how_to_reach",
            "permit_required", "price_range", "nearby_places",
        ],
    }
    labels = {
        "price_range": "Fare / price",
        "schedule": "Schedule",
        "duration": "Travel time / duration",
        "distance": "Distance",
        "how_to_reach": "How to reach",
        "permit_information": "Permit",
        "permit_required": "Permit required",
        "safety_information": "Safety",
        "best_time": "Best time",
        "nearby_places": "Nearby / on the route",
        "travel_tips": "Useful note",
        "documents_required": "Documents",
        "requirements": "Requirements",
        "price": "Price",
    }

    sections = []
    for result in results[:2]:
        record = result.get("record", {})
        name = _format_grounded_value(record.get("name")) or "Verified information"
        description = _format_grounded_value(record.get("description"))
        lines = []
        if description and "description" in field_order.get(intent, []):
            lines.append(description)

        for field in field_order.get(intent, field_order["destination"]):
            if field == "description":
                continue
            value = _format_grounded_value(record.get(field))
            if not value:
                continue
            label = labels.get(field, field.replace("_", " ").title())
            lines.append(f"**{label}:** {value}")
            if len(lines) >= 5:
                break

        if lines:
            sections.append(f"**{name}**\n\n" + "\n\n".join(lines))

    if sections:
        return "\n\n".join(sections)
    return (
        "I found a related approved record, but it doesn’t contain enough detail "
        "to answer this question accurately yet."
    )


def tourist_chat(
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    traveler_profile: Optional[Dict[str, Any]] = None,
    max_records: int = 6,
    **kwargs
) -> Dict[str, Any]:
    """
    Processes user queries with local guide persona, traveler profile personalization,
    multi-turn memory, and grounded knowledge retrieval.
    """
    intent = classify_intent(user_message)

    # Image requests use the uploaded evidence library directly. Returning here
    # prevents a missing text match from producing unrelated travel advice.
    if intent == "image":
        image_assets = search_document_assets(user_message, limit=max_records)
        if image_assets:
            first = image_assets[0]
            title = first.get("document_title") or "your knowledge entry"
            review_note = (
                " This entry is still pending review."
                if first.get("review_status") == "pending_review"
                else ""
            )
            answer = (
                f"Yes—I found a matching image linked to “{title}”. "
                f"Here it is.{review_note}"
            )
            sources = []
            for asset in image_assets:
                source = asset.get("source_url")
                if (
                    asset.get("review_status") == "approved"
                    and source
                    and source not in sources
                ):
                    sources.append(source)
        else:
            answer = (
                "I couldn’t find a matching image in the knowledge base. "
                "Try the exact place name, or upload the image in Manual Knowledge Entry."
            )
            sources = []

        return {
            "answer": answer,
            "intent": intent,
            "sources": sources,
            "results": [],
            "images": image_assets,
            "suggested_followups": generate_suggested_followups(intent, user_message),
        }
    transport_mode = requested_transport_mode(user_message) if intent == "transport" else "not_applicable"
    answer_guide = answer_guide_for_intent(intent)
    category_filter = None
    if intent in ["history", "trekking", "food", "culture", "lake", "transport"]:
        category_filter = intent

    # 1. Retrieval
    retrieved_results = search_approved_records(
        query=user_message,
        category=category_filter,
        limit=max_records
    )

    requested_route = extract_requested_route(user_message)
    asks_for_fare = any(term in user_message.lower() for term in ("fare", "price", "cost", "how much"))
    if intent == "transport" and requested_route:
        origin, destination = requested_route
        exact_route_results = [
            result
            for result in retrieved_results
            if record_contains_route(result["record"], origin, destination)
        ]
        if exact_route_results:
            retrieved_results = exact_route_results

    verified_transport_modes = (
        available_transport_modes(retrieved_results)
        if intent == "transport"
        else []
    )

    direct_answer = None
    if intent == "transport" and asks_for_current_road_condition(user_message):
        direct_answer = (
            "I don’t have a verified current road-condition update for that route. "
            "Please check a same-day advisory from the Sikkim Transport Department, "
            "Sikkim Police, or your driver before leaving—especially during monsoon."
        )
        # Fare and general transport records do not substantiate live road status.
        retrieved_results = []
    elif intent == "transport" and asks_for_fare and requested_route:
        origin, destination = requested_route
        direct_answer = build_exact_fare_answer(
            retrieved_results,
            origin,
            destination,
            transport_mode,
        )

    # 2. Add extra permit context if permit intent
    extra_permit_info = ""
    if intent == "permit" or any(p in user_message.lower() for p in ["nathula", "tsomgo", "gurudongmar", "yumthang", "dzongri"]):
        for key in ["nathula", "tsomgo_lake", "gurudongmar", "yumthang", "dzongri_trek"]:
            if key.replace("_", " ") in user_message.lower() or key.split("_")[0] in user_message.lower():
                guide = get_permit_guide(key)
                extra_permit_info += f"\n\n[OFFICIAL PERMIT GUIDELINE FOR {guide.get('name')}]:\n" + json.dumps(guide, indent=2)

    # 3. Build knowledge context
    context_chunks = []
    for res in retrieved_results:
        rec = res["record"]
        context_chunks.append(json.dumps(rec, ensure_ascii=False, indent=2))

    knowledge_context = "\n\n".join(context_chunks)
    if extra_permit_info:
        knowledge_context += extra_permit_info

    # 4. Construct prompt with recent conversation history & traveler profile
    history_text = ""
    if conversation_history:
        recent = conversation_history[-4:]  # Last 2 exchanges
        for turn in recent:
            role = "Tourist" if turn["role"] == "user" else "Tenzing (Guide)"
            history_text += f"{role}: {turn['content']}\n"

    profile_text = ""
    if traveler_profile and intent != "transport":
        name = traveler_profile.get("name", "Traveler")
        group = traveler_profile.get("group", "Standard")
        diet = traveler_profile.get("diet", "Flexible")
        pace = traveler_profile.get("pace", "Moderate")
        budget = traveler_profile.get("budget", "Moderate")
        profile_text = f"""TRAVELER PROFILE:
- Name: {name}
- Group Type: {group}
- Dietary Preference: {diet}
- Travel Pace: {pace}
- Budget: {budget}
(Personalize your advice for {name} considering their group, diet, and pace!).
"""

    prompt = f"""{profile_text}
CONVERSATION CONTEXT:
{history_text if history_text else "First message from traveler."}

CURRENT QUESTION:
{user_message}

VERIFIED KNOWLEDGE BASE RECORDS:
{knowledge_context if knowledge_context.strip() else "No verified knowledge-base record matched this question."}

INSTRUCTIONS FOR TENZING:
- Intent: {intent}
- Requested transport mode: {transport_mode}
- Verified transport modes found: {", ".join(verified_transport_modes) if verified_transport_modes else "none identified"}
- Relevant coverage guide: {answer_guide}
- Answer the current question directly and use only relevant verified facts.
- After the direct answer, include 3–6 compact, useful details when the knowledge base supports them.
- Omit unsupported sections instead of filling them with general model knowledge.
- Do not mention unrelated profile preferences or unrelated travel topics.
- For fare questions, read the exact requested route from price_range and do not blend it with other routes.
- For SNT/bus fare questions, never use taxi or shared-Sumo prices as an alternative.
- If transport mode is "all", list every available verified mode for the exact route, each in one short bullet.
- If transport mode is "bus" or "taxi", answer only for that mode.
- End with at most one brief, directly related follow-up question when it would genuinely help the traveler.
- If no verified record contains the exact answer, say that clearly instead of supplying general model knowledge.
"""

    # 5. Query Ollama Qwen
    max_response_tokens = 160 if intent == "transport" else 450

    try:
        if direct_answer is not None:
            answer = direct_answer
        else:
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "system": SYSTEM_PROMPT,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": max_response_tokens
                    }
                },
                timeout=180
            )
            response.raise_for_status()
            data = response.json()
            answer = data.get("response", "").strip()
    except Exception:
        answer = build_grounded_fallback_answer(
            user_message,
            intent,
            retrieved_results,
        )

    if (
        intent == "transport"
        and transport_mode == "all"
        and "SNT bus" in verified_transport_modes
    ):
        answer = append_missing_snt_option(answer, retrieved_results)

    # 6. Extract source URLs
    sources = []
    for res in retrieved_results:
        src = res.get("source_url")
        if src and src not in sources:
            sources.append(src)

    # 7. Generate follow-up prompts
    suggested_followups = generate_suggested_followups(intent, user_message)

    return {
        "answer": answer,
        "intent": intent,
        "sources": sources,
        "results": retrieved_results,
        "images": [],
        "suggested_followups": suggested_followups
    }
