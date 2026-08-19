"""Public-facing Sikkim travel landing page and grounded assistant."""
import base64
import html
import importlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db import connect, init_db, stats as database_stats
import agent.tourist_agent as tourist_agent_module


init_db()


def commons_image(file_name):
    return (
        "https://commons.wikimedia.org/wiki/Special:FilePath/"
        + quote(file_name, safe="")
        + "?width=1200"
    )


DESTINATION_SPECS = [
    {
        "name": "Gangtok", "aliases": ["gangtok"], "location": "Gangtok District",
        "category": "City & Culture", "best_time": "March–June · October–December",
        "description": "Sikkim’s energetic capital, shaped by mountain views, monasteries, markets and warm local hospitality.",
        "image": commons_image("Gangtok panoramic view.jpg"),
        "experiences": ["mountains", "monasteries", "culture", "food", "photography"],
    },
    {
        "name": "Tsomgo Lake", "aliases": ["tsomgo lake", "tsomgo baba mandir"], "location": "Gangtok District",
        "category": "Alpine Lake", "best_time": "March–May · October–December",
        "description": "A sacred glacial lake surrounded by steep alpine slopes on the high road from Gangtok toward Nathula.",
        "image": commons_image("Tsomgo Lake , Sikkim.jpg"),
        "experiences": ["lakes", "mountains", "nature", "photography"],
    },
    {
        "name": "Pelling", "aliases": ["pelling"], "location": "Gyalshing District",
        "category": "Hill Town", "best_time": "March–May · September–December",
        "description": "A tranquil hill town known for clear Khangchendzonga views, monasteries, forest walks and historic ruins.",
        "image": commons_image("Kanchenjunga from Pelling.jpg"),
        "experiences": ["mountains", "monasteries", "culture", "photography", "nature"],
    },
    {
        "name": "Yumthang Valley", "aliases": ["yumthang valley", "yumthang"], "location": "North Sikkim",
        "category": "Valley of Flowers", "best_time": "April–June · September–October",
        "description": "A wide Himalayan valley where wildflowers, rivers and high ridges create one of North Sikkim’s signature landscapes.",
        "image": commons_image("Yumthang Valley at North Sikkim, India 35.jpg"),
        "experiences": ["mountains", "nature", "photography", "adventure"],
    },
    {
        "name": "Gurudongmar Lake", "aliases": ["gurudongmar lake", "gurudongmar"], "location": "North Sikkim",
        "category": "High-altitude Lake", "best_time": "May–June · October–November",
        "description": "A remote high-altitude lake set within the stark, powerful landscape of Sikkim’s northern frontier.",
        "image": commons_image("Gurudongmar Lake Sikkim, India.jpg"),
        "experiences": ["lakes", "mountains", "adventure", "nature", "photography"],
    },
    {
        "name": "Namchi", "aliases": ["namchi"], "location": "Namchi District",
        "category": "Culture & Pilgrimage", "best_time": "March–June · September–November",
        "description": "South Sikkim’s main town, surrounded by hilltop landmarks, pilgrimage centres and broad valley views.",
        "image": commons_image("Char Dham Namchi Sikkim.jpg"),
        "experiences": ["mountains", "monasteries", "culture", "food", "photography"],
    },
    {
        "name": "Ravangla", "aliases": ["ravangla"], "location": "Namchi District",
        "category": "Culture & Nature", "best_time": "March–May · September–November",
        "description": "A serene ridge town best known for Buddha Park, monasteries and sweeping Himalayan panoramas.",
        "image": commons_image("Ravangla Buddha Park, Sikkim.jpg"),
        "experiences": ["mountains", "monasteries", "culture", "nature", "photography"],
    },
    {
        "name": "Yuksom", "aliases": ["yuksom"], "location": "Gyalshing District",
        "category": "Heritage Village", "best_time": "March–May · September–November",
        "description": "Sikkim’s historic first capital and a quiet, forest-fringed gateway to important West Sikkim treks.",
        "image": commons_image("Dubde alias Dubdi Monastery, Yuksom, West Sikkim 05.jpg"),
        "experiences": ["villages", "trekking", "culture", "monasteries", "nature"],
    },
]


EXPERIENCES = [
    ("mountains", "Mountains", "⛰️"), ("lakes", "Lakes", "💧"),
    ("monasteries", "Monasteries", "☸️"), ("trekking", "Trekking", "🥾"),
    ("adventure", "Adventure", "🧭"), ("culture", "Culture", "🎭"),
    ("food", "Food", "🥟"), ("photography", "Photography", "📷"),
    ("nature", "Nature", "🌿"), ("villages", "Villages", "🏡"),
]


def normalize(value):
    return " ".join(re.findall(r"[a-z0-9]+", str(value).lower()))


def compact(value, limit=150):
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0] + "…"


def best_time_text(value):
    if isinstance(value, list):
        return " · ".join(str(item) for item in value if item)
    return str(value or "").strip()


def load_public_destinations():
    """Use approved records first and curated fallbacks only for missing fields."""
    records = []
    assets_by_document = {}
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT r.id, r.document_id, r.record_json
            FROM records r
            WHERE r.status = 'approved'
            """
        ).fetchall()
        assets = connection.execute(
            "SELECT document_id, file_path, mime_type FROM document_assets ORDER BY id"
        ).fetchall()

    for row in rows:
        try:
            record = json.loads(row["record_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        record["_document_id"] = row["document_id"]
        records.append(record)

    for asset in assets:
        assets_by_document.setdefault(asset["document_id"], []).append(asset)

    cards = []
    for spec in DESTINATION_SPECS:
        aliases = {normalize(alias) for alias in spec["aliases"]}
        matches = [record for record in records if normalize(record.get("name")) in aliases]
        matches.sort(
            key=lambda item: (
                bool(item.get("description")),
                bool(item.get("district") or item.get("region")),
                len(str(item.get("description") or "")),
            ),
            reverse=True,
        )
        record = matches[0] if matches else {}
        image_url = spec["image"]
        linked_assets = assets_by_document.get(record.get("_document_id"), [])
        if linked_assets:
            asset = linked_assets[0]
            asset_path = ROOT / Path(asset["file_path"])
            if asset_path.is_file():
                mime_type = asset["mime_type"] or "image/jpeg"
                image_url = f"data:{mime_type};base64," + base64.b64encode(asset_path.read_bytes()).decode("ascii")

        cards.append({
            **spec,
            "location": record.get("district") or record.get("region") or spec["location"],
            "category": str(record.get("category") or spec["category"]).replace("_", " ").title(),
            "description": compact(record.get("description") or spec["description"]),
            "best_time": best_time_text(record.get("best_time")) or spec["best_time"],
            "image": image_url,
            "verified": bool(record),
        })
    return cards


def render_assistant_images(images):
    for item in images or []:
        image_path = ROOT / Path(item.get("file_path", ""))
        if image_path.is_file():
            caption = item.get("file_name", image_path.name).replace("_", " ")
            st.image(str(image_path), caption=caption, use_container_width=True)


ROBOT_ASSET = ROOT / "data" / "landing_assets" / "sikkim-ai-robot.png"
ROBOT_DATA_URI = ""
if ROBOT_ASSET.is_file():
    ROBOT_DATA_URI = "data:image/png;base64," + base64.b64encode(ROBOT_ASSET.read_bytes()).decode("ascii")


if st.query_params.get("admin"):
    try:
        st.switch_page("app/dashboard.py")
    except Exception:
        pass


cards = load_public_destinations()
public_stats = database_stats()
active_experience = str(st.query_params.get("experience", "")).lower()
visible_cards = (
    [card for card in cards if active_experience in card["experiences"]]
    if active_experience else cards
)
places_heading = (
    f"{active_experience.title()} journeys, thoughtfully selected."
    if active_experience else "Remarkable places, without the noise."
)
places_intro = (
    '<a href="?view=all#places">View every curated destination →</a>'
    if active_experience
    else "A considered selection drawn from the approved knowledge base—not a generic list of attractions."
)


st.markdown(
    """
    <style>
    :root {
      --forest:#061f30; --forest-2:#0a4050; --sage:#e7f6f0; --paper:#ffffff;
      --paper-2:#f0f8f5; --ink:#102b38; --muted:#627681; --gold:#1fb979; --line:rgba(15,55,68,.12);
    }
    html { scroll-behavior:smooth; color-scheme:light; }
    body { margin:0; background:var(--forest); }
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
      background:var(--paper); color:var(--ink); font-family:Inter,Manrope,"Segoe UI",sans-serif;
    }
    [data-testid="stHeader"], [data-testid="stDecoration"], [data-testid="stSidebarCollapsedControl"], #MainMenu {
      display:none!important;
    }
    .block-container { max-width:none; padding:0!important; margin:0!important; }

    .site-nav {
      position:absolute; z-index:20; top:0; left:0; right:0; height:84px;
      display:flex; align-items:center; justify-content:space-between; padding:0 clamp(1.2rem,5vw,5.5rem);
      border-bottom:1px solid rgba(255,255,255,.12); background:linear-gradient(180deg,rgba(3,21,34,.46),rgba(3,21,34,0)); color:#fff;
    }
    .wordmark { display:flex; align-items:center; gap:.75rem; }
    .wordmark-mark { position:relative; width:39px; height:39px; display:grid; place-items:center; border:1px solid rgba(255,255,255,.35); border-radius:50%; font-size:1.15rem; }
    .wordmark strong { display:block; color:#fff; font-size:.86rem; letter-spacing:.14em; }
    .wordmark small { display:block; color:rgba(255,255,255,.58); font-size:.58rem; letter-spacing:.09em; margin-top:.1rem; }
    .nav-menu { display:flex; align-items:center; gap:1.8rem; }
    .nav-menu a { color:rgba(255,255,255,.78)!important; text-decoration:none!important; font-size:.72rem; font-weight:650; }
    .nav-menu a:hover { color:#fff!important; }
    .nav-cta { padding:.62rem .9rem; border:1px solid rgba(54,214,150,.5); border-radius:999px; background:rgba(31,185,121,.2); box-shadow:0 8px 24px rgba(0,0,0,.12); backdrop-filter:blur(12px); }

    .editorial-hero {
      position:relative; min-height:700px; overflow:hidden;
      background:
        linear-gradient(90deg,rgba(3,23,37,.98) 0%,rgba(5,46,61,.9) 44%,rgba(5,46,61,.34) 74%,rgba(5,46,61,.15) 100%),
        url('https://commons.wikimedia.org/wiki/Special:FilePath/Kangchenjunga%2C%20India.jpg?width=2000') center/cover;
    }
    .editorial-hero::after { content:""; position:absolute; left:0; right:0; bottom:0; height:170px; background:linear-gradient(transparent,rgba(3,26,39,.48)); pointer-events:none; }
    .hero-grid { position:relative; z-index:2; display:grid; grid-template-columns:1.18fr .82fr; align-items:center; gap:4rem; max-width:1380px; min-height:700px; margin:auto; padding:9.5rem 5rem 7rem; }
    .hero-kicker { display:flex; align-items:center; gap:.6rem; color:#61e1ad; font-size:.67rem; font-weight:800; letter-spacing:.19em; text-transform:uppercase; }
    .hero-kicker::before { content:""; width:34px; height:2px; background:#31c98b; }
    .hero-copy h1 { color:#fff; font-size:clamp(3.5rem,6.7vw,7rem); line-height:.88; letter-spacing:-.065em; max-width:800px; margin:1.2rem 0 1.45rem; }
    .hero-copy h1 em { color:#36d696; font-style:normal; font-weight:760; }
    .hero-copy>p { color:rgba(255,255,255,.7); font-size:1.02rem; line-height:1.75; max-width:590px; margin:0; }
    .hero-actions { display:flex; flex-wrap:wrap; gap:.75rem; margin-top:2rem; }
    .button-solid,.button-ghost { display:inline-flex; align-items:center; gap:.55rem; padding:.82rem 1.15rem; border-radius:999px; text-decoration:none!important; font-size:.74rem; font-weight:800; }
    .button-solid { color:#fff!important; background:#1fb979; box-shadow:0 12px 30px rgba(31,185,121,.28); }
    .button-solid:hover { background:#18a86d; transform:translateY(-1px); }
    .button-ghost { color:#fff!important; border:1px solid rgba(255,255,255,.28); background:rgba(255,255,255,.06); backdrop-filter:blur(10px); }
    .hero-facts { display:flex; gap:2rem; margin-top:2.8rem; }
    .hero-fact { border-left:1px solid rgba(255,255,255,.23); padding-left:.9rem; }
    .hero-fact strong { display:block; color:#fff; font-size:1.18rem; }
    .hero-fact span { color:rgba(255,255,255,.51); font-size:.62rem; letter-spacing:.07em; text-transform:uppercase; }

    .guide-card {
      position:relative; min-height:440px; border:1px solid rgba(255,255,255,.2); border-radius:30px;
      background:linear-gradient(160deg,rgba(255,255,255,.14),rgba(255,255,255,.045)); backdrop-filter:blur(14px);
      box-shadow:0 35px 80px rgba(0,0,0,.24); overflow:hidden;
    }
    .guide-label { position:absolute; z-index:3; top:1.35rem; left:1.4rem; display:flex; align-items:center; gap:.45rem; color:#fff; font-size:.68rem; font-weight:750; }
    .online-dot { width:8px; height:8px; border-radius:50%; background:#5de0a0; box-shadow:0 0 0 5px rgba(93,224,160,.12); }
    .guide-card img { position:absolute; right:-2rem; bottom:-3.5rem; width:78%; max-height:420px; object-fit:contain; filter:drop-shadow(0 22px 30px rgba(0,0,0,.28)); }
    .guide-dialogue { position:absolute; z-index:4; left:1.4rem; bottom:1.5rem; width:48%; padding:1rem; border:1px solid rgba(255,255,255,.1); border-radius:16px; background:rgba(3,25,39,.82); color:#fff; font-size:.7rem; line-height:1.55; backdrop-filter:blur(12px); }
    .guide-dialogue strong { display:block; color:#50dca4; font-size:.75rem; margin-bottom:.35rem; }

    /* Public assistant panel */
    [data-testid="stVerticalBlockBorderWrapper"] {
      position:relative; z-index:8; width:min(1180px,calc(100% - 3rem)); margin:-72px auto 5rem;
      padding:1.35rem 1.5rem 1.45rem; border:1px solid rgba(15,55,68,.1)!important; border-radius:24px!important;
      background:rgba(255,255,255,.98)!important; box-shadow:0 24px 65px rgba(5,42,57,.16);
      color:var(--ink)!important;
    }
    .ask-header { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-bottom:.8rem; }
    .ask-title { display:flex; align-items:center; gap:.75rem; }
    .ask-icon { display:grid; place-items:center; width:42px; height:42px; border-radius:13px; background:var(--forest); color:#fff; }
    .ask-title h2 { color:var(--ink); font-size:1.05rem; margin:0 0 .1rem; }
    .ask-title p { color:var(--muted); font-size:.68rem; margin:0; }
    .knowledge-status { color:#16885d; font-size:.64rem; font-weight:750; }
    [data-testid="stVerticalBlockBorderWrapper"] label,
    [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stWidgetLabel"],
    [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stCaptionContainer"],
    [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stSpinner"] {
      color:var(--muted)!important;
    }
    .stTextInput input { height:50px; border:1px solid #d7e5e8!important; border-radius:12px!important; background:#f8fbfb!important; color:#102b38!important; caret-color:#159b67!important; }
    .stTextInput input::placeholder { color:#80929a!important; opacity:1!important; }
    .stButton>button { min-height:42px; border:1px solid #d7e5e8!important; border-radius:999px!important; background:#fff!important; color:#264754!important; font-size:.69rem; font-weight:700; }
    .stButton>button:hover { color:#0d8458; border-color:#75c9a6; }
    button[kind="primary"] { height:50px!important; border-color:var(--forest)!important; border-radius:12px!important; background:var(--forest)!important; color:#fff!important; }
    [data-testid="stChatMessage"] { border:1px solid #deeaec!important; border-radius:14px!important; background:#f8fbfb!important; padding:.65rem .85rem!important; color:var(--ink)!important; }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] strong,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] span {
      color:#102b38!important;
    }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] a { color:#0d8b5c!important; }
    [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stAlert"] {
      background:#eaf8f2!important; color:#174b3a!important; border-color:#c8eadb!important;
    }

    .section-shell { max-width:1320px; margin:auto; padding:0 3rem 6rem; }
    .section-label { color:#168b61; font-size:.64rem; font-weight:850; letter-spacing:.18em; text-transform:uppercase; }
    .section-heading { display:flex; align-items:end; justify-content:space-between; gap:2rem; margin:.7rem 0 1.8rem; }
    .section-heading h2 { max-width:680px; color:var(--ink); font-size:clamp(2.2rem,4vw,4.2rem); line-height:.97; letter-spacing:-.055em; margin:0; }
    .section-heading p { max-width:390px; color:var(--muted); font-size:.77rem; line-height:1.65; margin:0; }
    .destination-mosaic { display:grid; grid-template-columns:repeat(12,1fr); grid-auto-rows:300px; gap:1rem; }
    .place-card { position:relative; overflow:hidden; grid-column:span 4; border-radius:22px; background:#0c4050 center/cover; box-shadow:0 16px 40px rgba(5,42,57,.14); }
    .place-card:nth-child(1) { grid-column:span 7; }
    .place-card:nth-child(2) { grid-column:span 5; }
    .place-card::before { content:""; position:absolute; inset:0; background:linear-gradient(180deg,rgba(3,23,37,.03) 30%,rgba(3,23,37,.92)); transition:.3s ease; }
    .place-card:hover::before { background:linear-gradient(180deg,rgba(3,23,37,.01) 18%,rgba(3,23,37,.82)); }
    .place-card:hover .place-arrow { transform:translate(3px,-3px); }
    .place-top { position:absolute; z-index:2; top:1rem; left:1rem; right:1rem; display:flex; justify-content:space-between; }
    .place-category { padding:.4rem .62rem; border:1px solid rgba(255,255,255,.25); border-radius:999px; background:rgba(3,25,39,.48); color:#fff; font-size:.58rem; font-weight:800; backdrop-filter:blur(8px); }
    .place-arrow { display:grid; place-items:center; width:35px; height:35px; border-radius:50%; background:rgba(255,255,255,.9); color:#0d6f4e; transition:.2s; }
    .place-copy { position:absolute; z-index:2; left:1.2rem; right:1.2rem; bottom:1.15rem; color:#fff; }
    .place-copy small { color:rgba(255,255,255,.67); font-size:.65rem; }
    .place-copy strong { display:block; color:#fff; font-size:1.42rem; letter-spacing:-.025em; margin:.15rem 0 .3rem; }
    .place-copy p { max-width:480px; color:rgba(255,255,255,.72); font-size:.66rem; line-height:1.45; margin:0; }

    .experience-band { padding:5.5rem 3rem; background:var(--forest); color:#fff; }
    .experience-inner { max-width:1320px; margin:auto; }
    .experience-band .section-label { color:#55dda7; }
    .experience-title { display:flex; justify-content:space-between; align-items:end; gap:2rem; margin:.7rem 0 2rem; }
    .experience-title h2 { color:#fff; font-size:clamp(2.1rem,4vw,3.8rem); letter-spacing:-.05em; margin:0; }
    .experience-title p { max-width:440px; color:rgba(255,255,255,.58); font-size:.75rem; line-height:1.65; }
    .experience-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:.75rem; }
    .experience-card { min-height:150px; padding:1.15rem; border:1px solid rgba(255,255,255,.12); border-radius:18px; background:rgba(255,255,255,.045); color:#fff!important; text-decoration:none!important; transition:.22s ease; }
    .experience-card:hover { transform:translateY(-5px); border-color:rgba(70,216,159,.65); background:rgba(31,185,121,.11); box-shadow:0 18px 32px rgba(0,0,0,.14); }
    .experience-card span { display:block; font-size:1.5rem; margin-bottom:2.25rem; }
    .experience-card strong { display:block; color:#fff; font-size:.78rem; }
    .experience-card small { color:rgba(255,255,255,.48); font-size:.61rem; }

    .trust-section { display:grid; grid-template-columns:1.05fr .95fr; max-width:1320px; margin:auto; padding:6rem 3rem; gap:4rem; align-items:center; }
    .trust-copy h2 { color:var(--ink); font-size:clamp(2.2rem,4vw,4rem); line-height:.98; letter-spacing:-.055em; margin:.8rem 0 1.2rem; }
    .trust-copy>p { color:var(--muted); font-size:.82rem; line-height:1.75; max-width:570px; }
    .trust-list { display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-top:1.8rem; }
    .trust-item { padding:1rem; border-top:1px solid var(--line); }
    .trust-item strong { display:block; color:var(--ink); font-size:.75rem; margin:.45rem 0 .25rem; }
    .trust-item p { color:var(--muted); font-size:.65rem; line-height:1.5; margin:0; }
    .trust-number { color:var(--gold); font-weight:850; font-size:1.1rem; }
    .knowledge-card { padding:2rem; border-radius:28px; background:var(--sage); }
    .knowledge-card h3 { color:var(--forest); font-size:1.35rem; margin:0 0 1rem; }
    .knowledge-stat { display:flex; align-items:center; justify-content:space-between; padding:1rem 0; border-bottom:1px solid rgba(8,37,31,.12); }
    .knowledge-stat:last-child { border-bottom:0; }
    .knowledge-stat span { color:#4d675e; font-size:.7rem; }
    .knowledge-stat strong { color:var(--forest); font-size:1.45rem; }

    .final-cta { padding:6rem 3rem; background:var(--paper-2); }
    .cta-box { display:flex; align-items:center; justify-content:space-between; gap:2rem; max-width:1320px; margin:auto; padding:3.2rem; border:1px solid rgba(255,255,255,.08); border-radius:30px; background:linear-gradient(135deg,#061f30 0%,#0a4050 100%); box-shadow:0 24px 60px rgba(5,42,57,.18); }
    .cta-box h2 { color:#fff; font-size:clamp(2rem,4vw,3.7rem); letter-spacing:-.05em; margin:0 0 .5rem; }
    .cta-box p { color:rgba(255,255,255,.64); font-size:.76rem; }
    .cta-box a { flex:0 0 auto; padding:.9rem 1.15rem; border-radius:999px; background:var(--gold); box-shadow:0 12px 28px rgba(31,185,121,.25); color:#fff!important; text-decoration:none!important; font-size:.72rem; font-weight:800; }

    .site-footer { background:#041a28; color:#fff; padding:4rem 3rem 1.5rem; }
    .footer-inner { display:grid; grid-template-columns:1.6fr repeat(3,1fr); gap:4rem; max-width:1320px; margin:auto; }
    .footer-brand p { max-width:330px; color:rgba(255,255,255,.48); font-size:.67rem; line-height:1.7; margin-top:1rem; }
    .footer-col strong { display:block; color:#fff; font-size:.72rem; margin-bottom:.8rem; }
    .footer-col a { display:block; color:rgba(255,255,255,.5)!important; text-decoration:none!important; font-size:.66rem; line-height:1.9; }
    .footer-bottom { display:flex; justify-content:space-between; max-width:1320px; margin:3rem auto 0; padding-top:1.1rem; border-top:1px solid rgba(255,255,255,.08); color:rgba(255,255,255,.35); font-size:.59rem; }

    @media(max-width:1000px) {
      .hero-grid{grid-template-columns:1fr .7fr;padding-left:3rem;padding-right:3rem}.hero-copy h1{font-size:4.5rem}
      .experience-grid{grid-template-columns:repeat(3,1fr)}.trust-section{grid-template-columns:1fr}.place-card{grid-column:span 6!important}.footer-inner{grid-template-columns:1.5fr 1fr 1fr}.footer-col:last-child{display:none}
    }
    @media(max-width:700px) {
      .site-nav{height:70px;padding:0 1rem}.nav-menu a:not(.nav-cta):not(:last-child){display:none}.nav-menu{gap:.7rem}
      .editorial-hero{min-height:760px}.hero-grid{display:block;min-height:760px;padding:8.5rem 1.2rem 7rem}.hero-copy h1{font-size:3.7rem;max-width:460px}.hero-copy>p{font-size:.86rem}
      .hero-facts{gap:1rem}.guide-card{position:absolute;right:-4rem;bottom:-2rem;width:63vw;min-height:330px;opacity:.82}.guide-dialogue{display:none}
      [data-testid="stVerticalBlockBorderWrapper"]{width:calc(100% - 1.4rem);margin-top:-55px;padding:.9rem!important}.knowledge-status{display:none}
      .section-shell{padding:0 1rem 4rem}.section-heading{display:block}.section-heading p{margin-top:1rem}.destination-mosaic{display:flex;overflow-x:auto;scroll-snap-type:x mandatory}.place-card{flex:0 0 82vw;min-height:330px;scroll-snap-align:start}
      .experience-band{padding:4rem 1rem}.experience-title{display:block}.experience-grid{grid-template-columns:repeat(2,1fr)}.experience-card{min-height:130px}
      .trust-section{padding:4rem 1rem;gap:2rem}.trust-list{grid-template-columns:1fr 1fr}.final-cta{padding:3rem 1rem}.cta-box{display:block;padding:2rem}.cta-box a{display:inline-block;margin-top:1rem}
      .site-footer{padding:3rem 1rem 1.2rem}.footer-inner{grid-template-columns:1fr 1fr;gap:2rem}.footer-brand{grid-column:1/-1}.footer-bottom{display:block}.footer-bottom span{display:block;margin-top:.4rem}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    f"""
    <nav class="site-nav">
      <div class="wordmark"><span class="wordmark-mark">△</span><span><strong>SIKKIM / AI</strong><small>HIMALAYAN TRAVEL INTELLIGENCE</small></span></div>
      <div class="nav-menu">
        <a href="#places">Places</a><a href="#experiences">Experiences</a><a href="#knowledge">Travel intelligence</a>
        <a class="nav-cta" href="#ask-tenzing">Ask Tenzing ↗</a>
      </div>
    </nav>
    <section class="editorial-hero">
      <div class="hero-grid">
        <div class="hero-copy">
          <div class="hero-kicker">The Eastern Himalaya, thoughtfully explored</div>
          <h1>Travel deeper into <em>Sikkim.</em></h1>
          <p>One intelligent companion for mountain roads, protected areas, local transport and the places that make Sikkim unforgettable.</p>
          <div class="hero-actions"><a class="button-solid" href="#ask-tenzing">Plan with Tenzing →</a><a class="button-ghost" href="#places">Explore the map</a></div>
          <div class="hero-facts">
            <div class="hero-fact"><strong>{public_stats.get('approved', 0)}</strong><span>Reviewed records</span></div>
            <div class="hero-fact"><strong>{public_stats.get('sources', 0)}</strong><span>Indexed sources</span></div>
            <div class="hero-fact"><strong>24×7</strong><span>Travel guidance</span></div>
          </div>
        </div>
        <div class="guide-card">
          <div class="guide-label"><i class="online-dot"></i>Tenzing is ready</div>
          <img src="{ROBOT_DATA_URI}" alt="Tenzing AI travel guide">
          <div class="guide-dialogue"><strong>A clearer way to plan.</strong>Ask about fares, permits, routes or a place. I’ll keep the answer focused and grounded.</div>
        </div>
      </div>
    </section>
    <span id="ask-tenzing"></span>
    """,
    unsafe_allow_html=True,
)


if "public_chat_history" not in st.session_state:
    st.session_state.public_chat_history = []

quick_prompt = None
with st.container(border=True):
    st.markdown(
        '<div class="ask-header"><div class="ask-title"><span class="ask-icon">✦</span><span><h2>Ask Tenzing</h2><p>Practical Sikkim guidance, grounded in reviewed knowledge.</p></span></div><span class="knowledge-status">● Knowledge base connected</span></div>',
        unsafe_allow_html=True,
    )
    question_col, send_col = st.columns([12, 1])
    typed_question = question_col.text_input(
        "Ask a Sikkim travel question",
        placeholder="Where would you like to go, and what do you need to know?",
        label_visibility="collapsed",
        key="public_question_input",
    )
    send_clicked = send_col.button("→", key="public_send", type="primary", use_container_width=True)

    quick_questions = [
        "Siliguri to Gangtok options",
        "Tsomgo permit requirements",
        "Plan four days in Sikkim",
        "Best season for Pelling",
    ]
    quick_columns = st.columns(len(quick_questions))
    for index, question in enumerate(quick_questions):
        if quick_columns[index].button(question, key=f"public_quick_{index}", use_container_width=True):
            quick_prompt = question

    for message in st.session_state.public_chat_history:
        avatar = "🏔️" if message["role"] == "assistant" else "🎒"
        with st.chat_message(message["role"], avatar=avatar):
            st.write(message["content"])
            render_assistant_images(message.get("images", []))

    user_message = (typed_question if send_clicked else None) or quick_prompt
    if user_message:
        st.session_state.public_chat_history.append({"role": "user", "content": user_message})
        with st.chat_message("user", avatar="🎒"):
            st.write(user_message)
        with st.chat_message("assistant", avatar="🏔️"):
            with st.spinner("Checking reviewed Sikkim knowledge…"):
                importlib.reload(tourist_agent_module)
                response = tourist_agent_module.tourist_chat(
                    user_message=user_message,
                    conversation_history=st.session_state.public_chat_history,
                    max_records=6,
                )
            st.write(response["answer"])
            render_assistant_images(response.get("images", []))
        st.session_state.public_chat_history.append({
            "role": "assistant",
            "content": response["answer"],
            "images": response.get("images", []),
        })
        st.rerun()


place_markup = []
for card in visible_cards:
    place_markup.append(f"""
    <article class="place-card" style="background-image:url('{html.escape(card['image'], quote=True)}')">
      <div class="place-top"><span class="place-category">{html.escape(card['category'])}</span><span class="place-arrow">↗</span></div>
      <div class="place-copy"><small>{html.escape(str(card['location']))}</small><strong>{html.escape(card['name'])}</strong><p>{html.escape(card['description'])}</p></div>
    </article>
    """)

st.markdown(
    f"""
    <section class="section-shell" id="places">
      <div class="section-label">Curated destinations</div>
      <div class="section-heading"><h2>{html.escape(places_heading)}</h2><p>{places_intro}</p></div>
      <div class="destination-mosaic">{''.join(place_markup)}</div>
    </section>
    """,
    unsafe_allow_html=True,
)


experience_markup = []
for slug, label, icon in EXPERIENCES:
    count = sum(slug in card["experiences"] for card in cards)
    experience_markup.append(
        f'<a class="experience-card" href="?experience={slug}#places"><span>{icon}</span><strong>{label}</strong><small>{count} curated places</small></a>'
    )

st.markdown(
    f"""
    <section class="experience-band" id="experiences">
      <div class="experience-inner">
        <div class="section-label">Choose your rhythm</div>
        <div class="experience-title"><h2>Experience Sikkim your way.</h2><p>Build a journey around what matters to you—from remote valleys and monastery trails to food, photography and village life.</p></div>
        <div class="experience-grid">{''.join(experience_markup)}</div>
      </div>
    </section>

    <section class="trust-section" id="knowledge">
      <div class="trust-copy">
        <div class="section-label">Travel intelligence</div>
        <h2>Answers with a reason to trust them.</h2>
        <p>Tenzing is connected to the reviewed knowledge in your administration system. Specific fares, permits and routes are used only when the supporting record is available.</p>
        <div class="trust-list">
          <div class="trust-item"><span class="trust-number">01</span><strong>Reviewed knowledge</strong><p>Human-approved records power precise answers.</p></div>
          <div class="trust-item"><span class="trust-number">02</span><strong>Relevant by design</strong><p>No unrelated food, sightseeing or filler.</p></div>
          <div class="trust-item"><span class="trust-number">03</span><strong>Route-aware guidance</strong><p>Transport modes stay tied to the journey asked about.</p></div>
          <div class="trust-item"><span class="trust-number">04</span><strong>Honest uncertainty</strong><p>Missing or dynamic facts are identified clearly.</p></div>
        </div>
      </div>
      <div class="knowledge-card">
        <h3>Live knowledge overview</h3>
        <div class="knowledge-stat"><span>Verified tourism records</span><strong>{public_stats.get('approved', 0)}</strong></div>
        <div class="knowledge-stat"><span>Indexed source collections</span><strong>{public_stats.get('sources', 0)}</strong></div>
        <div class="knowledge-stat"><span>Documents processed</span><strong>{public_stats.get('documents', 0)}</strong></div>
        <div class="knowledge-stat"><span>Pending human review</span><strong>{public_stats.get('pending', 0)}</strong></div>
      </div>
    </section>

    <section class="final-cta">
      <div class="cta-box"><div><h2>Your Sikkim journey starts with one good question.</h2><p>Ask Tenzing about the route, permit, fare or place on your mind.</p></div><a href="#ask-tenzing">Start planning →</a></div>
    </section>

    <footer class="site-footer">
      <div class="footer-inner">
        <div class="footer-brand"><div class="wordmark"><span class="wordmark-mark">△</span><span><strong>SIKKIM / AI</strong><small>HIMALAYAN TRAVEL INTELLIGENCE</small></span></div><p>A grounded travel companion for discovering Sikkim with more clarity, confidence and respect for the mountains.</p></div>
        <div class="footer-col"><strong>Explore</strong><a href="#places">Destinations</a><a href="#experiences">Experiences</a><a href="#ask-tenzing">Ask Tenzing</a></div>
        <div class="footer-col"><strong>Travel essentials</strong><a href="#ask-tenzing">Permits</a><a href="#ask-tenzing">Transport</a><a href="#ask-tenzing">Itineraries</a></div>
        <div class="footer-col"><strong>System</strong><a href="?admin=1">Admin console</a><a href="https://www.sikkimtourism.gov.in/" target="_blank">Official tourism website</a></div>
      </div>
      <div class="footer-bottom"><span>© 2026 Sikkim Tourist AI</span><span>Designed for thoughtful Himalayan travel.</span></div>
    </footer>
    """,
    unsafe_allow_html=True,
)
