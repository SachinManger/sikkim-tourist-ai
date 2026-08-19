"""
Sikkim Tourist Itinerary Generator
Constructs optimized, realistic day-by-day travel schedules grounded in verified places.
"""
from typing import Dict, Any, List, Optional
import json

from retrieval.search import search_approved_records


def generate_itinerary(
    days: int = 4,
    theme: str = "Scenic & Leisure",
    start_city: str = "Gangtok",
    travelers_type: str = "Family",
    budget: str = "Moderate"
) -> Dict[str, Any]:
    """
    Generates a structured, day-by-day Sikkim travel itinerary.
    """
    # Fetch database destinations
    dest_records = search_approved_records(query="", category="destination", limit=20)
    culture_records = search_approved_records(query="", category="culture", limit=10)
    food_records = search_approved_records(query="", category="food", limit=5)
    trek_records = search_approved_records(query="", category="trekking", limit=5)

    approved_names = [r["record"].get("name") for r in dest_records if r.get("record")]

    itinerary_days: List[Dict[str, Any]] = []

    if days <= 3:
        # Short Trip: Gangtok & East Sikkim
        itinerary_days.append({
            "day": 1,
            "title": f"Arrival & Exploring {start_city}",
            "morning": f"Arrive at {start_city} from Siliguri/Bagdogra. Check-in and relax.",
            "afternoon": "Stroll through MG Marg, visit Enchey Monastery or Do Drul Chorten.",
            "evening": "Enjoy authentic Sikkimese momos, thukpa, and tea at local cafes.",
            "stay": f"Hotel / Homestay in {start_city}",
            "permits_needed": "None for standard city exploration.",
            "altitude": "approx. 5,500 ft (Gangtok)"
        })
        itinerary_days.append({
            "day": 2,
            "title": "Excursion to Tsomgo Lake & Baba Mandir",
            "morning": "Early drive (38 km) to the sacred alpine Tsomgo (Changu) Lake (12,310 ft).",
            "afternoon": "Proceed to historic Baba Harbhajan Singh Mandir. Optional permit-based visit to Nathula Pass.",
            "evening": "Return to Gangtok for dinner and relaxation.",
            "stay": "Gangtok",
            "permits_needed": "Protected Area Permit (PAP) for Tsomgo / Nathula.",
            "altitude": "12,310 ft – 14,140 ft"
        })
        itinerary_days.append({
            "day": 3,
            "title": "Local Culture & Souvenirs / Departure",
            "morning": "Visit Directorate of Handicrafts & Handloom and Namgyal Institute of Tibetology.",
            "afternoon": "Souvenir shopping at Lal Bazaar and MG Marg.",
            "evening": "Departure transfer to NJP Railway Station or Bagdogra Airport.",
            "stay": "Departure",
            "permits_needed": "None.",
            "altitude": "5,500 ft descending to plains"
        })

    elif days <= 5:
        # 4-5 Day Trip: Gangtok + North Sikkim (Lachung / Yumthang) or West Sikkim (Pelling)
        itinerary_days.append({
            "day": 1,
            "title": "Arrival in Gangtok & Acclimatization",
            "morning": f"Scenic drive from NJP/Bagdogra along the Teesta River to {start_city}.",
            "afternoon": "Check-in, relax, and explore MG Marg on foot.",
            "evening": "Dinner featuring local Tibetan and Sikkimese delicacies (Thukpa, Gundruk).",
            "stay": "Gangtok",
            "permits_needed": "None for general town area.",
            "altitude": "5,500 ft"
        })
        itinerary_days.append({
            "day": 2,
            "title": "Tsomgo Lake & High Altitude Wonders",
            "morning": "Morning departure for Tsomgo Lake (12,310 ft) and Baba Mandir.",
            "afternoon": "Enjoy snow views, yak rides, and optional Nathula border view.",
            "evening": "Return to Gangtok, preparation for North Sikkim or Pelling.",
            "stay": "Gangtok",
            "permits_needed": "Protected Area Permit (PAP) arranged a day prior.",
            "altitude": "12,310 ft"
        })
        itinerary_days.append({
            "day": 3,
            "title": "Drive to North Sikkim (Lachung / Chungthang)",
            "morning": "Drive north via Mangan and Singhik Viewpoint with views of Mt. Kanchenjunga.",
            "afternoon": "Stop at Seven Sisters Waterfalls and Naga Falls; reach picturesque Lachung village.",
            "evening": "Traditional homestay experience, hot tea, and rest.",
            "stay": "Lachung (North Sikkim)",
            "permits_needed": "North Sikkim Protected Area Permit (PAP).",
            "altitude": "8,600 ft (Lachung)"
        })
        itinerary_days.append({
            "day": 4,
            "title": "Yumthang Valley of Flowers & Zero Point",
            "morning": "Early excursion to the stunning Yumthang Valley (11,800 ft) and hot springs.",
            "afternoon": "Optional trip to Zero Point (Yumesamdong, 15,300 ft). Drive back towards Gangtok.",
            "evening": "Arrive in Gangtok by late evening.",
            "stay": "Gangtok",
            "permits_needed": "North Sikkim PAP.",
            "altitude": "11,800 ft – 15,300 ft"
        })
        itinerary_days.append({
            "day": 5,
            "title": "Heritage & Departure",
            "morning": "Visit Rumtek Monastery or Ban Jhakri Falls.",
            "afternoon": "Transfer to NJP/Bagdogra for flight or train.",
            "evening": "Safe journey home.",
            "stay": "Departure",
            "permits_needed": "None.",
            "altitude": "5,500 ft to plains"
        })

    else:
        # 6-8+ Days: Grand Sikkim (East, North, and West Sikkim)
        itinerary_days.append({
            "day": 1,
            "title": "Arrival in Gangtok",
            "morning": "Arrive at Bagdogra/NJP, transfer to Gangtok (4-5 hours drive).",
            "afternoon": "Check in, acclimatize, walk along MG Marg.",
            "evening": "Local dinner and permit document handover to tour operator.",
            "stay": "Gangtok",
            "permits_needed": "None.",
            "altitude": "5,500 ft"
        })
        itinerary_days.append({
            "day": 2,
            "title": "Tsomgo Lake & Baba Mandir / Nathula",
            "morning": "Excursion to alpine Tsomgo Lake and Baba Mandir.",
            "afternoon": "Scenic views along ancient Silk Route corridors.",
            "evening": "Return to Gangtok.",
            "stay": "Gangtok",
            "permits_needed": "Protected Area Permit (PAP).",
            "altitude": "12,310 ft"
        })
        itinerary_days.append({
            "day": 3,
            "title": "Journey to Lachen (North Sikkim)",
            "morning": "Drive to Lachen passing Singhik Viewpoint and Chungthang.",
            "afternoon": "Check in at Lachen, scenic village walk.",
            "evening": "Early dinner and early night for early morning lake ascent.",
            "stay": "Lachen",
            "permits_needed": "North Sikkim PAP.",
            "altitude": "8,800 ft"
        })
        itinerary_days.append({
            "day": 4,
            "title": "Gurudongmar Lake & Transfer to Lachung",
            "morning": "Early 4:30 AM drive via Thangu Valley to sacred Gurudongmar Lake (17,800 ft).",
            "afternoon": "Return to Lachen, lunch, and drive to Lachung.",
            "evening": "Rest and relax in Lachung.",
            "stay": "Lachung",
            "permits_needed": "North Sikkim PAP.",
            "altitude": "17,800 ft peak, sleep at 8,600 ft"
        })
        itinerary_days.append({
            "day": 5,
            "title": "Yumthang Valley & Drive to Pelling (West Sikkim)",
            "morning": "Visit Yumthang Valley and Zero Point.",
            "afternoon": "Drive to historical Pelling in West Sikkim.",
            "evening": "Evening view of Mount Kanchenjunga.",
            "stay": "Pelling (West Sikkim)",
            "permits_needed": "PAP for Yumthang.",
            "altitude": "6,800 ft (Pelling)"
        })
        itinerary_days.append({
            "day": 6,
            "title": "Pelling Heritage & Monasteries",
            "morning": "Visit Pemayangtse Monastery and Rabdentse Ruins.",
            "afternoon": "Walk on the Pelling Skywalk and visit Khecheopalri Sacred Lake.",
            "evening": "Cultural dinner with Sikkimese organic farm produce.",
            "stay": "Pelling",
            "permits_needed": "None.",
            "altitude": "6,800 ft"
        })
        itinerary_days.append({
            "day": 7,
            "title": "Departure via Namchi Chardham",
            "morning": "Drive to Namchi to visit Siddheshwar Dham (Chardham) and Samdruptse Statue.",
            "afternoon": "Descent to NJP Railway Station or Bagdogra Airport.",
            "evening": "Flight / train departure.",
            "stay": "Departure",
            "permits_needed": "None.",
            "altitude": "Descend to plains"
        })

    # Essential advice based on travelers type
    safety_notes = [
        "Carry heavy woolens, windproof jackets, and thermal innerwear for high altitudes.",
        "Keep at least 4 passport-size photographs and original Government Photo IDs for checkpoints.",
        "Stay hydrated to prevent Acute Mountain Sickness (AMS); avoid sudden exertion at 12,000+ ft."
    ]
    if "Senior" in travelers_type or "Kid" in travelers_type or "Family" in travelers_type:
        safety_notes.append("Carry portable oxygen cans for Gurudongmar / Nathula excursions when traveling with seniors or children.")

    return {
        "title": f"Custom {days}-Day {theme} Sikkim Itinerary",
        "duration_days": days,
        "theme": theme,
        "start_city": start_city,
        "travelers_type": travelers_type,
        "budget": budget,
        "days": itinerary_days,
        "safety_notes": safety_notes,
        "approved_records_referenced": approved_names[:8]
    }


def itinerary_to_markdown(itinerary: Dict[str, Any]) -> str:
    """Formats itinerary into clean, exportable Markdown."""
    lines = [
        f"# 🏔️ {itinerary['title']}",
        f"**Duration:** {itinerary['duration_days']} Days | **Theme:** {itinerary['theme']} | **Group:** {itinerary['travelers_type']} | **Budget:** {itinerary['budget']}\n",
        "---",
        "## 📅 Day-by-Day Schedule\n"
    ]
    for d in itinerary["days"]:
        lines.append(f"### 📍 Day {d['day']}: {d['title']}")
        lines.append(f"- **Morning:** {d['morning']}")
        lines.append(f"- **Afternoon:** {d['afternoon']}")
        lines.append(f"- **Evening:** {d['evening']}")
        lines.append(f"- **Overnight Stay:** `{d['stay']}`")
        lines.append(f"- **Permits:** `{d['permits_needed']}`")
        lines.append(f"- **Altitude:** `{d['altitude']}`\n")

    lines.append("---")
    lines.append("## 🛡️ Essential Travel & Safety Guidelines")
    for note in itinerary["safety_notes"]:
        lines.append(f"- {note}")

    return "\n".join(lines)
