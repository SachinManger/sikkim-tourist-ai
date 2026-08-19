"""
Sikkim Tourist Permit & Protected Area Regulations Advisor
"""
from typing import Dict, Any, List

PERMIT_DATABASE: Dict[str, Dict[str, Any]] = {
    "nathula": {
        "name": "Nathula Pass (14,140 ft / 4,310 m)",
        "region": "East Sikkim",
        "indian_nationals": {
            "allowed": True,
            "permit_type": "Protected Area Permit (PAP)",
            "requirements": [
                "Valid Government Photo ID (Voter ID, Passport, Aadhaar, Driving License)",
                "2 Passport size photographs",
                "Apply at least 1 day in advance through a registered Sikkim travel agent",
                "Closed on Mondays & Tuesdays for tourists"
            ]
        },
        "foreign_nationals": {
            "allowed": False,
            "permit_type": "Not Allowed (Restricted Border Zone)",
            "requirements": ["Foreign tourists (including OCI/PIO) are currently not permitted due to border proximity."]
        },
        "issuing_authorities": ["Tourism and Civil Aviation Department, Gangtok", "Police Check Post Office, Gangtok"],
        "route": "Gangtok → Tsomgo Lake → Baba Mandir → Nathula Pass (approx. 56 km from Gangtok)"
    },
    "tsomgo_lake": {
        "name": "Tsomgo (Changu) Lake & Baba Mandir (12,310 ft)",
        "region": "East Sikkim",
        "indian_nationals": {
            "allowed": True,
            "permit_type": "Protected Area Permit (PAP)",
            "requirements": [
                "Valid Photo ID Card (Voter ID, Passport, Aadhaar)",
                "2 Passport size photographs",
                "Permit arranged via registered Sikkim tour operator"
            ]
        },
        "foreign_nationals": {
            "allowed": True,
            "permit_type": "Protected Area Permit (PAP)",
            "requirements": [
                "Valid Passport and Indian Tourist Visa",
                "Valid Restricted Area Permit (RAP / ILP) for entering Sikkim",
                "Must travel in a group of at least 2 foreigners with a registered local tour operator"
            ]
        },
        "issuing_authorities": ["Tourism & Civil Aviation Department, Gangtok"],
        "route": "Gangtok → Tsomgo Lake (approx. 38 km, 2 hours)"
    },
    "gurudongmar": {
        "name": "Gurudongmar Lake (17,800 ft / 5,430 m)",
        "region": "North Sikkim",
        "indian_nationals": {
            "allowed": True,
            "permit_type": "Protected Area Permit (PAP)",
            "requirements": [
                "Valid Government Photo ID",
                "2 Passport size photos",
                "Applied via registered travel agent in Gangtok or Mangan",
                "Acclimatization night stay in Lachen required before early morning ascent"
            ]
        },
        "foreign_nationals": {
            "allowed": False,
            "permit_type": "Not Allowed to Gurudongmar",
            "requirements": ["Foreigners can visit up to Chopta Valley / Thangu with special PAP, but not Gurudongmar Lake."]
        },
        "issuing_authorities": ["District Magistrate (DM) Office, Mangan", "Tourism Department, Gangtok"],
        "route": "Gangtok → Mangan → Chungthang → Lachen (overnight) → Thangu → Gurudongmar"
    },
    "yumthang": {
        "name": "Yumthang Valley & Zero Point (Yumesamdong)",
        "region": "North Sikkim",
        "indian_nationals": {
            "allowed": True,
            "permit_type": "Protected Area Permit (PAP)",
            "requirements": [
                "Valid Photo ID & 2 passport photos",
                "Organized via registered Sikkim tour agent",
                "Overnight stay in Lachung recommended"
            ]
        },
        "foreign_nationals": {
            "allowed": True,
            "permit_type": "Protected Area Permit (PAP)",
            "requirements": [
                "Allowed up to Yumthang Valley (Zero Point may require extra army clearance)",
                "Minimum 2 foreigners accompanied by registered guide / tour agent"
            ]
        },
        "issuing_authorities": ["Tourism Department, Gangtok", "DM Office, Mangan"],
        "route": "Gangtok → Mangan → Chungthang → Lachung (overnight) → Yumthang Valley (25 km from Lachung)"
    },
    "dzongri_trek": {
        "name": "Dzongri & Goecha La Trek",
        "region": "West Sikkim (Khangchendzonga National Park)",
        "indian_nationals": {
            "allowed": True,
            "permit_type": "KNP Wildlife Entry Permit + Police Verification",
            "requirements": [
                "Permit from Wildlife Department (Yuksom / Gangtok)",
                "Photo ID & photographs",
                "Mandatory local licensed guide and trek porter crew"
            ]
        },
        "foreign_nationals": {
            "allowed": True,
            "permit_type": "Trekking PAP + KNP Permit",
            "requirements": [
                "Minimum 2 foreign trekkers applying through registered Sikkim trekking operator",
                "Valid Passport, Indian Visa, and RAP/ILP"
            ]
        },
        "issuing_authorities": ["Forest & Wildlife Department, Yuksom / Gangtok", "Home Department, Gangtok"],
        "route": "Yuksom → Sachen → Bakhim → Tshoka → Dzongri → Thansing → Goecha La"
    }
}


def get_permit_guide(destination_key: str) -> Dict[str, Any]:
    """Returns permit information for a specific destination."""
    for key, data in PERMIT_DATABASE.items():
        if key in destination_key.lower() or destination_key.lower() in key:
            return data
    return {
        "name": destination_key.title(),
        "general_guidance": "Most standard tourist spots in Gangtok, Pelling, Namchi, and Ravangla do not require internal Protected Area Permits for Indian tourists. For international tourists, an Inner Line Permit (ILP) / Restricted Area Permit (RAP) is required to enter Sikkim and can be obtained free at Rangpo, Melli, Bagdogra Airport, or Pakyong Airport."
    }


def list_all_permit_destinations() -> List[str]:
    """Returns list of protected destinations."""
    return [d["name"] for d in PERMIT_DATABASE.values()]
