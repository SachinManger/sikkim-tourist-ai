"""
Authoritative Sikkim Transit, Connectivity & How-To-Reach Reference
"""
from typing import Dict, Any

TRANSIT_FACTS: Dict[str, Any] = {
    "how_to_reach_summary": {
        "gateway": "Siliguri / New Jalpaiguri (NJP) / Bagdogra in West Bengal is the mandatory transit gateway to Sikkim.",
        "by_air": {
            "primary_airport": "Bagdogra International Airport (IXB) in Siliguri, West Bengal (~125 km from Gangtok, approx. 4.5 to 5 hours drive via NH10).",
            "sikkim_airport": "Pakyong Airport (PYG) (~30 km from Gangtok, approx. 1 to 1.5 hours drive, flights are limited and weather-dependent).",
            "helicopter": "Sikkim Tourism operates a daily 5-seater helicopter flight between Bagdogra Airport and Gangtok (Burtuk Helipad), subject to weather conditions (approx. 20-30 mins flight time)."
        },
        "by_train": {
            "primary_station": "New Jalpaiguri Railway Station (NJP) in Siliguri (~120 km from Gangtok, 4.5 to 5 hours drive via NH10). NJP is well-connected to Delhi, Kolkata, Mumbai, Guwahati, and major Indian cities.",
            "secondary_station": "Siliguri Junction (for buses and regional connections).",
            "upcoming_rail": "The Sevoke-Rangpo railway project is currently under construction to bring rail connectivity into Sikkim."
        },
        "by_road": {
            "main_highway": "National Highway 10 (NH10) connects Siliguri/Bagdogra/NJP to Gangtok via Sevoke, Coronation Bridge, Teesta Bazaar, and Rangpo Border.",
            "distance_duration": "Siliguri / NJP to Gangtok is approx. 114–125 km and takes 4 to 5.5 hours depending on traffic and monsoon road conditions.",
            "entry_checkposts": [
                "Rangpo Checkpost (for East and North Sikkim, Gangtok entry)",
                "Melli Checkpost (for West and South Sikkim, Pelling/Namchi entry)"
            ],
            "public_transport": "Sikkim Nationalised Transport (SNT) buses and shared Tata Sumos/Boleros operate regularly from Siliguri SNT Bus Terminus (near Sevoke Road) to Gangtok, Jorethang, Pelling, and Namchi.",
            "long_distance_warning": "There are NO direct 12-hour buses from New Delhi to Gangtok (Delhi is ~1,550 km away). Travelers from Delhi/Mumbai/South India must fly or take a train to Bagdogra/NJP first, and then take road transport into Sikkim."
        },
        "border_and_protected_areas": "Nathula Pass, Tsomgo Lake, and Gurudongmar are high-altitude border zones located 40–120 km PAST Gangtok towards the Tibetan border. They require Protected Area Permits (PAP) and are NOT en-route transit stops when traveling from the plains."
    }
}


def get_transit_guidance() -> str:
    """Returns verified transit and road facts to inject into LLM prompts."""
    return """
[VERIFIED SIKKIM TRANSIT & HOW-TO-REACH RULES]:
1. GATEWAY: All travel to Sikkim enters via the gateway of Siliguri / Bagdogra / New Jalpaiguri (NJP) in West Bengal.
2. BY AIR: 
   - Bagdogra Airport (IXB) (~125 km to Gangtok, 4.5–5 hrs drive along NH10).
   - Pakyong Airport (PYG) (30 km to Gangtok, limited flights/weather dependent).
   - Daily Sikkim Tourism helicopter service operates between Bagdogra and Gangtok helipad.
3. BY TRAIN:
   - Nearest major broad-gauge railway junction is New Jalpaiguri (NJP) (~120 km to Gangtok, 4.5–5 hrs drive).
4. BY ROAD:
   - Entry into Sikkim is via National Highway 10 (NH10) through Rangpo Checkpost (for Gangtok/East) or Melli Checkpost (for Pelling/South/West).
   - Distance from Siliguri/NJP to Gangtok is approx. 114–125 km (4.5–5.5 hours).
   - Shared jeeps / Tata Sumos and SNT buses depart from Siliguri SNT Bus Terminus.
   - Long-distance cities (Delhi ~1,550 km, Mumbai ~2,200 km, Kolkata ~670 km) require taking a train/flight to NJP/Bagdogra first. There are NO short direct road buses from Delhi.
5. SENSITIVE BORDER SPOTS:
   - Nathula Pass and Tsomgo Lake are 40–55 km PAST Gangtok up at the China border (12,000–14,000 ft) requiring special PAP permits; they are NEVER en-route transit stops on highways entering Sikkim!
"""
