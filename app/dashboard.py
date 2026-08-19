import sys
import json
import importlib
import runpy
import hmac
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# Path Setup
# ---------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database.db as database_module
importlib.reload(database_module)

from database.db import (
    init_db,
    stats,
    list_records,
    update_record,
    delete_record,
    remove_duplicate_records,
    list_document_assets,
    connect,
)
import agent.collector as collector_module
importlib.reload(collector_module)

collect = collector_module.collect
collect_from_pdf = collector_module.collect_from_pdf
collect_from_manual_entry = collector_module.collect_from_manual_entry
import agent.tourist_agent as tourist_agent_module
from agent.itinerary_builder import generate_itinerary, itinerary_to_markdown
from agent.permit_advisor import PERMIT_DATABASE, get_permit_guide


def render_chat_images(images):
    """Render knowledge-base images returned by the assistant."""
    for item in images or []:
        image_path = ROOT / Path(item.get("file_path", ""))
        if not image_path.is_file():
            continue
        caption = item.get("file_name", image_path.name).replace("_", " ")
        document_title = item.get("document_title")
        if document_title:
            caption = f"{caption} — {document_title}"
        st.image(str(image_path), caption=caption, use_container_width=True)


# Preserve the original full-width admin appearance when this file is
# launched directly. When it is loaded through streamlit_app.py, the router
# has already configured the page.
if __name__ == "__main__":
    st.set_page_config(
        page_title="Sikkim Tourist AI — Admin Console",
        page_icon="🏔️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    if not st.query_params.get("admin"):
        runpy.run_path(str(ROOT / "app" / "landing.py"), run_name="__page__")
        st.stop()


def _configured_admin_password():
    """Read the admin password without ever placing it in published source."""
    password = os.getenv("ADMIN_PASSWORD", "").strip()
    if not password:
        try:
            password = str(st.secrets.get("ADMIN_PASSWORD", "")).strip()
        except Exception:
            password = ""

    # Keeps the existing local workflow working. This directory is excluded
    # from source control and is never required in a cloud deployment.
    local_password_file = ROOT / "passscode" / "pass.txt"
    if not password and local_password_file.is_file():
        try:
            password = local_password_file.read_text(encoding="utf-8").strip()
        except OSError:
            password = ""
    return password


def require_admin_login():
    """Protect ingestion, review, and database-write tools on public hosts."""
    if st.session_state.get("admin_authenticated"):
        return

    configured_password = _configured_admin_password()
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] { background:#061f30; }
        .block-container { max-width:520px; padding-top:12vh; }
        .admin-login-card { color:#fff; margin-bottom:1.2rem; }
        .admin-login-card span { color:#48d9a0; font-size:.72rem; font-weight:800; letter-spacing:.14em; text-transform:uppercase; }
        .admin-login-card h1 { color:#fff; font-size:2.15rem; margin:.55rem 0; }
        .admin-login-card p { color:rgba(255,255,255,.64); line-height:1.65; }
        </style>
        <div class="admin-login-card">
          <span>Protected workspace</span>
          <h1>Sikkim AI Admin Console</h1>
          <p>Sign in to manage verified records, ingestion and knowledge review.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not configured_password:
        st.error("Admin access is disabled until ADMIN_PASSWORD is configured.")
        st.markdown("[← Return to the public website](/)")
        st.stop()

    with st.form("admin_login", clear_on_submit=True):
        entered_password = st.text_input("Admin password", type="password")
        submitted = st.form_submit_button("Open secure console", type="primary", use_container_width=True)

    if submitted:
        if hmac.compare_digest(entered_password, configured_password):
            st.session_state["admin_authenticated"] = True
            st.rerun()
        st.error("The password is incorrect.")

    st.markdown("[← Return to the public website](/)")
    st.stop()


require_admin_login()


# ---------------------------------------------------------
# Page Configuration & Styling
# ---------------------------------------------------------
init_db()

# Custom CSS for styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1A237E;
        margin-bottom: 0.2rem;
    }
    .badge-approved {
        background-color: #E8F5E9;
        color: #2E7D32;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.82rem;
    }
    .badge-pending {
        background-color: #FFF3E0;
        color: #E65100;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.82rem;
    }
    .badge-rejected {
        background-color: #FFEBEE;
        color: #C62828;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.82rem;
    }
    .info-box {
        background-color: #F0F4F8;
        border-left: 5px solid #0288D1;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 12px;
    }
    .permit-card {
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        padding: 16px;
        background-color: #FAFAFA;
        margin-bottom: 15px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# App Header & Global KPI Metrics
# ---------------------------------------------------------
st.markdown('<div class="main-header">🏔️ Sikkim Tourist AI — Travel Assistant & Knowledge System</div>', unsafe_allow_html=True)
st.caption("AI Travel Guide • Custom Itinerary Generator • Permit Advisor • Knowledge Curation Studio")

db_stats = stats()
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("Verified Knowledge", f"{db_stats.get('approved', 0)} Records")
kpi2.metric("Pending Review", f"{db_stats.get('pending', 0)} Records")
kpi3.metric("Indexed Sources", db_stats.get('sources', 0))
kpi4.metric("Documents", db_stats.get('documents', 0))
kpi5.metric("System Engine", "Qwen 2.5 (7B)")

st.divider()

# ---------------------------------------------------------
# Primary Navigation Tabs
# ---------------------------------------------------------
tab_assistant, tab_review, tab_ingest, tab_analytics = st.tabs([
    "💬 Sikkim Tourist AI Assistant",
    "📋 Knowledge Review & Curation (HITL)",
    "🌐 Data Ingestion (Web, PDF & Manual)",
    "📊 Knowledge Analytics & Stats"
])


# =========================================================
# TAB 1: SIKKIM TOURIST AI ASSISTANT
# =========================================================
with tab_assistant:
    sub_chat, sub_itinerary, sub_permits, sub_safety = st.tabs([
        "🤖 Conversational Travel Guide",
        "🗺️ Custom Itinerary Planner",
        "📜 Permit & Regulations Advisor",
        "🚨 Altitude & Emergency Safety"
    ])

    # -----------------------------------------------------
    # SUB-TAB A: CONVERSATIONAL TRAVEL GUIDE (TENZING)
    # -----------------------------------------------------
    with sub_chat:
        # Header & Persona Welcome
        st.markdown("### 🏔️ Chat with Tenzing — Your Local Himalayan Host")
        st.caption("Warm local guidance, storytelling, and authentic travel advice grounded strictly in verified Sikkim knowledge.")

        # Traveler Profile Expander for Personalization
        with st.expander("🎒 Traveler Profile & Preferences (Customize your advice)", expanded=False):
            prof_c1, prof_c2, prof_c3, prof_c4, prof_c5 = st.columns(5)
            with prof_c1:
                t_name = st.text_input("Your Name", value="Traveler", key="prof_name")
            with prof_c2:
                t_group = st.selectbox(
                    "Traveling With",
                    ["Solo Backpacker", "Couple / Honeymoon", "Family with Kids", "Family with Seniors", "Group of Friends"],
                    key="prof_group"
                )
            with prof_c3:
                t_diet = st.selectbox(
                    "Dietary Preference",
                    ["Local Foodie (Everything)", "Vegetarian", "Jain / Pure Veg", "Vegan"],
                    key="prof_diet"
                )
            with prof_c4:
                t_pace = st.selectbox(
                    "Travel Pace",
                    ["Relaxed & Scenic", "Moderate Explorer", "Active Trekker & Thrills"],
                    key="prof_pace"
                )
            with prof_c5:
                t_budget = st.selectbox(
                    "Budget Level",
                    ["Moderate Comfort", "Budget Friendly", "Luxury Stays"],
                    key="prof_budget"
                )

            traveler_profile = {
                "name": t_name,
                "group": t_group,
                "diet": t_diet,
                "pace": t_pace,
                "budget": t_budget
            }

        # Initialize session state for chat
        if "conversation_history" not in st.session_state:
            st.session_state.conversation_history = [
                {
                    "role": "assistant",
                    "content": f"Tashi Delek! 🙏 I am Tenzing, your local Sikkim mountain guide. Welcome to the land of snow-capped peaks, serene monasteries, and alpine lakes. How can I help you plan your journey across Sikkim today?",
                    "sources": [],
                    "results": [],
                    "suggested_followups": [
                        "🏔️ Must-Visit Places in Sikkim",
                        "📜 Nathula & Gurudongmar Permits",
                        "🍲 Traditional Food & Cuisine"
                    ]
                }
            ]

        # Top Bar: Quick Topics & Reset Button
        top_c1, top_c2 = st.columns([5, 1])
        with top_c1:
            st.markdown("**Quick Topics:**")
            q1, q2, q3, q4 = st.columns(4)
            quick_query = None
            if q1.button("🏔️ Must-Visit Places in Sikkim", key="btn_top_must", use_container_width=True):
                quick_query = "What are the must-visit tourist destinations and lakes in Sikkim?"
            if q2.button("📜 Nathula & Gurudongmar Permits", key="btn_top_perm", use_container_width=True):
                quick_query = "What are the permit requirements for visiting Nathula Pass and Gurudongmar Lake?"
            if q3.button("🍲 Traditional Food & Cuisine", key="btn_top_food", use_container_width=True):
                quick_query = "Tell me about traditional Sikkimese food, drinks, and cuisine."
            if q4.button("🥾 Best Treks in Sikkim", key="btn_top_trek", use_container_width=True):
                quick_query = "What are the popular trekking routes in Sikkim like Dzongri and Goecha La?"
        with top_c2:
            st.write("")
            if st.button("🧹 Reset Chat", key="btn_reset_chat", use_container_width=True):
                st.session_state.conversation_history = [
                    {
                        "role": "assistant",
                        "content": f"Tashi Delek! 🙏 I am Tenzing. How may I help you today?",
                        "sources": [],
                        "results": [],
                        "suggested_followups": [
                            "🏔️ Must-Visit Places in Sikkim",
                            "📜 Nathula & Gurudongmar Permits",
                            "🍲 Traditional Food & Cuisine"
                        ]
                    }
                ]
                st.rerun()

        # Display chat history
        last_followups = []
        for msg in st.session_state.conversation_history:
            avatar_icon = "🏔️" if msg["role"] == "assistant" else "🎒"
            with st.chat_message(msg["role"], avatar=avatar_icon):
                st.write(msg["content"])
                render_chat_images(msg.get("images", []))
                if msg.get("sources"):
                    with st.expander("📚 Verified Knowledge Sources Cited"):
                        for s in msg["sources"]:
                            st.markdown(f"- [{s}]({s})")
                if msg.get("results"):
                    with st.expander(f"🔍 Supporting Knowledge Records ({len(msg['results'])})"):
                        for res in msg["results"]:
                            r = res["record"]
                            st.markdown(f"**#{res['record_id']} - {r.get('name')}** (`{r.get('category')}`) — Score: `{res['score']}`")
                            if r.get("description"):
                                st.caption(r.get("description"))

            if msg["role"] == "assistant" and msg.get("suggested_followups"):
                last_followups = msg["suggested_followups"]

        # Follow-up interactive chips (if any)
        clicked_followup = None
        if last_followups:
            st.markdown("💬 **Recommended Next Questions:**")
            f_cols = st.columns(len(last_followups))
            for i, chip_text in enumerate(last_followups):
                if f_cols[i].button(chip_text, key=f"chip_{i}_{len(st.session_state.conversation_history)}", use_container_width=True):
                    clicked_followup = chip_text

        # User input box
        user_text = st.chat_input("Ask Tenzing anything about your Sikkim trip...") or quick_query or clicked_followup

        if user_text:
            st.session_state.conversation_history.append({"role": "user", "content": user_text})
            with st.chat_message("user", avatar="🎒"):
                st.write(user_text)

            with st.chat_message("assistant", avatar="🏔️"):
                with st.spinner("Tenzing is checking the mountain trails & notes..."):
                    # Reload local assistant changes without requiring a full
                    # Streamlit server restart during development.
                    importlib.reload(tourist_agent_module)
                    chat_resp = tourist_agent_module.tourist_chat(
                        user_message=user_text,
                        conversation_history=st.session_state.conversation_history,
                        traveler_profile=traveler_profile,
                        max_records=6
                    )

                st.write(chat_resp["answer"])
                render_chat_images(chat_resp.get("images", []))

                if chat_resp.get("sources"):
                    with st.expander("📚 Verified Knowledge Sources Cited"):
                        for s in chat_resp["sources"]:
                            st.markdown(f"- [{s}]({s})")

                if chat_resp.get("results"):
                    with st.expander(f"🔍 Supporting Knowledge Records ({len(chat_resp['results'])})"):
                        for res in chat_resp["results"]:
                            r = res["record"]
                            st.markdown(f"**#{res['record_id']} - {r.get('name')}** (`{r.get('category')}`) — Score: `{res['score']}`")
                            if r.get("description"):
                                st.caption(r.get("description"))

            st.session_state.conversation_history.append({
                "role": "assistant",
                "content": chat_resp["answer"],
                "sources": chat_resp.get("sources", []),
                "results": chat_resp.get("results", []),
                "images": chat_resp.get("images", []),
                "suggested_followups": chat_resp.get("suggested_followups", [])
            })
            st.rerun()

    # -----------------------------------------------------
    # SUB-TAB B: CUSTOM ITINERARY PLANNER
    # -----------------------------------------------------
    with sub_itinerary:
        st.subheader("🗺️ Customized Sikkim Trip & Itinerary Builder")
        st.write("Generate optimized, realistic day-by-day travel plans grounded in verified places and altitude transit times.")

        ic1, ic2, ic3, ic4 = st.columns(4)
        with ic1:
            trip_days = st.slider("Trip Duration (Days)", min_value=2, max_value=8, value=5)
        with ic2:
            trip_theme = st.selectbox(
                "Travel Theme",
                ["Scenic & Leisure", "Monasteries & Culture", "High-Altitude Adventure", "Family & Relaxed", "Budget Explorer"]
            )
        with ic3:
            start_point = st.selectbox("Starting Base", ["Gangtok", "Bagdogra Airport / NJP", "Pelling"])
        with ic4:
            travelers_group = st.selectbox(
                "Travel Group",
                ["Family with Kids/Seniors", "Couple / Honeymoon", "Solo Traveler", "Group of Friends"]
            )

        if st.button("✨ Build Customized Itinerary", key="btn_gen_itinerary", use_container_width=True):
            with st.spinner("Generating day-by-day route and checking altitude logistics..."):
                itin = generate_itinerary(
                    days=trip_days,
                    theme=trip_theme,
                    start_city=start_point,
                    travelers_type=travelers_group
                )

            st.markdown(f"### 📍 {itin['title']}")
            st.caption(f"Starting Point: **{start_point}** | Group: **{travelers_group}** | Verified Places Grounded: {len(itin['approved_records_referenced'])}")

            for day_info in itin["days"]:
                with st.container():
                    st.markdown(f"#### 📅 Day {day_info['day']}: {day_info['title']}")
                    dc1, dc2 = st.columns([2, 1])
                    with dc1:
                        st.markdown(f"- 🌅 **Morning:** {day_info['morning']}")
                        st.markdown(f"- ☀️ **Afternoon:** {day_info['afternoon']}")
                        st.markdown(f"- 🌙 **Evening:** {day_info['evening']}")
                    with dc2:
                        st.markdown(f"🏨 **Stay:** `{day_info['stay']}`")
                        st.markdown(f"📜 **Permits:** `{day_info['permits_needed']}`")
                        st.markdown(f"⛰️ **Altitude:** `{day_info['altitude']}`")
                    st.divider()

            st.markdown("#### 🛡️ Essential Safety & Travel Guidelines:")
            for note in itin["safety_notes"]:
                st.markdown(f"- {note}")

            # Export button
            itin_md = itinerary_to_markdown(itin)
            st.download_button(
                label="📥 Download Itinerary Brief (Markdown)",
                data=itin_md,
                file_name=f"Sikkim_{trip_days}Day_{trip_theme.replace(' ', '_')}_Itinerary.md",
                mime="text/markdown",
                use_container_width=True
            )

    # -----------------------------------------------------
    # SUB-TAB C: PERMIT & REGULATIONS ADVISOR
    # -----------------------------------------------------
    with sub_permits:
        st.subheader("📜 Sikkim Permit & Protected Area Navigator")
        st.write("Sikkim borders Tibet (China), Bhutan, and Nepal. Certain sensitive high-altitude and border zones require a **Protected Area Permit (PAP)** or **Restricted Area Permit (RAP/ILP)**.")

        selected_dest_key = st.selectbox(
            "Select Protected Destination for Permit Rules:",
            [
                ("nathula", "Nathula Pass (14,140 ft)"),
                ("gurudongmar", "Gurudongmar Lake (17,800 ft)"),
                ("tsomgo_lake", "Tsomgo (Changu) Lake & Baba Mandir (12,310 ft)"),
                ("yumthang", "Yumthang Valley & Zero Point (11,800 ft – 15,300 ft)"),
                ("dzongri_trek", "Dzongri & Goecha La Trek (Khangchendzonga National Park)")
            ],
            format_func=lambda x: x[1]
        )[0]

        permit_data = get_permit_guide(selected_dest_key)

        st.markdown(f"### 📍 {permit_data['name']} — `{permit_data.get('region')}`")
        st.markdown(f"**Travel Route:** {permit_data.get('route', 'Check route from Gangtok')}")

        p_col1, p_col2 = st.columns(2)
        with p_col1:
            st.markdown("#### 🇮🇳 Indian Nationals")
            ind = permit_data.get("indian_nationals", {})
            if ind.get("allowed"):
                st.success(f"✅ **Permitted** ({ind.get('permit_type')})")
                st.markdown("**Requirements:**")
                for req in ind.get("requirements", []):
                    st.markdown(f"- {req}")
            else:
                st.error("❌ Not Permitted")

        with p_col2:
            st.markdown("#### 🌍 Foreign Nationals / OCI / PIO")
            forn = permit_data.get("foreign_nationals", {})
            if forn.get("allowed"):
                st.success(f"✅ **Permitted with Conditions** ({forn.get('permit_type')})")
                st.markdown("**Requirements:**")
                for req in forn.get("requirements", []):
                    st.markdown(f"- {req}")
            else:
                st.warning("⚠️ **Restricted:** Foreign tourists are not permitted due to international border security regulations.")

        st.markdown("---")
        st.markdown("#### 🏢 Issuing Authorities & Checkpoints:")
        for auth in permit_data.get("issuing_authorities", []):
            st.markdown(f"- **{auth}**")

    # -----------------------------------------------------
    # SUB-TAB D: ALTITUDE & EMERGENCY SAFETY
    # -----------------------------------------------------
    with sub_safety:
        st.subheader("🚨 Altitude Sickness (AMS) Prevention & Emergency Contacts")
        
        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown("### ⛰️ High-Altitude Safety Guidelines")
            st.markdown(
                """
                - **Gradual Acclimatization:** Spend at least 1–2 nights in Gangtok (5,500 ft) before ascending to Lachen (8,800 ft) or Gurudongmar (17,800 ft).
                - **Hydration is Vital:** Drink 3–4 liters of warm water/electrolytes daily. Avoid alcohol at high altitudes.
                - **Watch for AMS Symptoms:** Headache, nausea, dizziness, shortness of breath, and fatigue.
                - **Golden Rule:** If severe AMS symptoms develop, **descend immediately** to lower altitude.
                - **Portable Oxygen:** Keep portable oxygen canisters when traveling to Gurudongmar or Nathula, especially for seniors.
                """
            )

        with sc2:
            st.markdown("### 📞 Key Emergency Helplines")
            st.markdown(
                """
                | Service / Authority | Contact Number / Details |
                | :--- | :--- |
                | **Sikkim Police Control Room** | `112` / `03592-202022` |
                | **STNM Government Hospital Gangtok** | `03592-202944` |
                | **Sikkim Tourism Department (HQ)** | `03592-209090` |
                | **District Hospital Mangan (North)** | `03592-234224` |
                | **District Hospital Gyalshing (West)** | `03595-250834` |
                | **Rangpo Foreigners Registration (FRO)** | `03592-240833` |
                """
            )


# =========================================================
# TAB 2: KNOWLEDGE REVIEW & CURATION (HITL)
# =========================================================
with tab_review:
    st.subheader("Human-in-the-Loop Quality Control & Curation")
    st.caption("Verify and curate AI-extracted records before they become active in the tourist AI search engine.")

    # Top Toolbar / Actions
    tool_col1, tool_col2, tool_col3, tool_col4 = st.columns([2, 2, 2, 2])
    with tool_col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["pending_review", "approved", "rejected", "all"],
            index=0,
            key="rev_status_filter"
        )
    with tool_col2:
        search_query = st.text_input("Search Name / Place", placeholder="e.g. Gangtok, Nathula...", key="rev_search")
    with tool_col3:
        all_records_raw = list_records()
        categories = sorted(list({
            json.loads(r["record_json"]).get("category", "unknown")
            for r in all_records_raw if r["record_json"]
        }))
        category_filter = st.selectbox("Filter Category", ["All Categories"] + categories, key="rev_cat_filter")
    with tool_col4:
        st.write("")
        st.write("")
        if st.button("🧹 Clean Duplicates", use_container_width=True, key="rev_btn_dedup"):
            removed = remove_duplicate_records()
            st.success(f"Cleaned {removed} duplicate records!")
            st.rerun()

    # Filter Records
    filtered_rows = list_records(None if status_filter == "all" else status_filter)

    if category_filter != "All Categories":
        filtered_rows = [
            r for r in filtered_rows
            if json.loads(r["record_json"]).get("category") == category_filter
        ]

    if search_query.strip():
        q = search_query.strip().lower()
        filtered_rows = [
            r for r in filtered_rows
            if q in json.loads(r["record_json"]).get("name", "").lower()
            or q in json.loads(r["record_json"]).get("description", "").lower()
        ]

    st.write(f"Showing **{len(filtered_rows)}** records")

    if not filtered_rows:
        st.info("No records found matching current filters.")
    else:
        for row in filtered_rows:
            rec_id = row["id"]
            try:
                data = json.loads(row["record_json"])
            except Exception:
                continue

            name = data.get("name", "Unnamed")
            cat = data.get("category", "unknown")
            rec_status = row["status"]
            confidence = row["confidence"]
            district = data.get("district") or "Not specified"

            status_badge = (
                f'<span class="badge-approved">APPROVED</span>' if rec_status == "approved"
                else (f'<span class="badge-rejected">REJECTED</span>' if rec_status == "rejected"
                      else f'<span class="badge-pending">PENDING REVIEW</span>')
            )

            expander_title = f"#{rec_id} • {name} [{cat.upper()}] — District: {district} — Status: {rec_status.upper()}"

            with st.expander(expander_title, expanded=False):
                col_left, col_right = st.columns([1.2, 1], gap="medium")

                with col_left:
                    st.markdown(f"### {name}")
                    st.markdown(f"**Category:** `{cat}` | **District:** `{district}` | **Confidence:** `{confidence}`")
                    st.markdown(f"**Status:** {status_badge}", unsafe_allow_html=True)
                    st.markdown("---")

                    if data.get("description"):
                        st.markdown(f"**Description:**\n{data.get('description')}")
                    if data.get("activities"):
                        st.markdown(f"**Activities:** {', '.join(data.get('activities'))}")
                    if data.get("best_time"):
                        st.markdown(f"**Best Time:** {', '.join(data.get('best_time'))}")
                    if data.get("permit_required") is not None:
                        st.markdown(f"**Permit Required:** `{'Yes' if data.get('permit_required') else 'No'}`")
                    if data.get("how_to_reach"):
                        st.markdown(f"**How to Reach:** {data.get('how_to_reach')}")
                    if data.get("safety_information"):
                        st.markdown(f"**Safety:** {', '.join(data.get('safety_information'))}")
                    if data.get("contact"):
                        st.markdown(f"**Contact:** `{data.get('contact')}`")

                    st.caption(f"Source URL: [{row['url']}]({row['url']})")

                    evidence_assets = list_document_assets(row["document_id"])
                    if evidence_assets:
                        st.markdown("#### 🖼️ Linked Image Evidence")
                        evidence_columns = st.columns(min(3, len(evidence_assets)))
                        for asset_index, asset in enumerate(evidence_assets):
                            asset_path = ROOT / asset["file_path"]
                            if asset_path.exists():
                                with evidence_columns[asset_index % len(evidence_columns)]:
                                    st.image(
                                        str(asset_path),
                                        caption=asset["file_name"],
                                        use_container_width=True,
                                    )

                with col_right:
                    st.markdown("#### ✏️ Edit Record Data (JSON)")
                    json_str = json.dumps(data, ensure_ascii=False, indent=2)
                    edited_json_str = st.text_area(
                        "Structured JSON",
                        value=json_str,
                        height=280,
                        key=f"edit_json_{rec_id}"
                    )
                    reviewer_note = st.text_input(
                        "Reviewer Note / Remark",
                        value=row["reviewer_note"] or "",
                        key=f"note_{rec_id}"
                    )

                    btn_c1, btn_c2, btn_c3, btn_c4 = st.columns(4)
                    with btn_c1:
                        if st.button("✅ Approve", key=f"btn_app_{rec_id}", use_container_width=True):
                            try:
                                obj = json.loads(edited_json_str)
                                obj["status"] = "approved"
                                update_record(rec_id, obj, "approved", reviewer_note)
                                st.success("Approved!")
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Invalid JSON: {ex}")

                    with btn_c2:
                        if st.button("💾 Keep Pending", key=f"btn_pend_{rec_id}", use_container_width=True):
                            try:
                                obj = json.loads(edited_json_str)
                                obj["status"] = "pending_review"
                                update_record(rec_id, obj, "pending_review", reviewer_note)
                                st.info("Saved as pending.")
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Invalid JSON: {ex}")

                    with btn_c3:
                        if st.button("❌ Reject", key=f"btn_rej_{rec_id}", use_container_width=True):
                            try:
                                obj = json.loads(edited_json_str)
                                obj["status"] = "rejected"
                                update_record(rec_id, obj, "rejected", reviewer_note)
                                st.warning("Rejected.")
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Invalid JSON: {ex}")

                    with btn_c4:
                        if st.button("🗑️ Delete", key=f"btn_del_{rec_id}", use_container_width=True):
                            delete_record(rec_id)
                            st.warning(f"Deleted record #{rec_id}")
                            st.rerun()


# =========================================================
# TAB 3: DATA INGESTION (WEB, PDF & MANUAL)
# =========================================================
with tab_ingest:
    st.subheader("Data Ingestion Engine (Web, PDF & Manual)")
    st.caption("Crawl websites, ingest PDFs, or add text with linked image evidence to extract structured records using Ollama Qwen.")

    col_web, col_pdf = st.columns([1, 1], gap="large")

    with col_web:
        st.markdown("### 🕸️ Playwright Web Crawler")
        seed_url = st.text_input(
            "Seed URL",
            value="https://www.sikkimtourism.gov.in/",
            placeholder="https://www.sikkimtourism.gov.in/",
            key="ingest_seed_url"
        )
        max_pages = st.slider("Maximum Pages to Crawl", min_value=1, max_value=50, value=5, key="ingest_max_pages")

        if st.button("🚀 Start Web Crawl & Extraction", key="btn_ingest_crawl", use_container_width=True):
            if not seed_url.startswith(("http://", "https://")):
                st.error("Please enter a valid HTTP or HTTPS URL.")
            else:
                progress_box = st.empty()
                status_text = st.empty()

                def web_progress(stage, current, total, message):
                    percent = min(1.0, max(0.0, current / max(total, 1)))
                    progress_box.progress(percent)
                    status_text.info(f"[{stage.upper()}] {message}")

                try:
                    with st.spinner("Crawling website with Playwright & structuring with Qwen..."):
                        result = collect(
                            seed_url=seed_url,
                            max_pages=max_pages,
                            progress_callback=web_progress
                        )
                    st.success(f"✅ Crawl Complete! Pages: {result['pages']}, Documents: {result['documents']}, New records: {result['records']}.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error during crawl: {e}")

    with col_pdf:
        st.markdown("### 📑 PDF Document Ingestion")
        uploaded_file = st.file_uploader("Upload Tourism PDF", type=["pdf"], key="pdf_uploader_main")
        doc_source_name = st.text_input("Source Department / Publisher", value="Sikkim Tourism Department", key="pdf_source_name")
        doc_source_url = st.text_input("Reference URL / Document Tag", value="https://www.sikkimtourism.gov.in/documents", key="pdf_source_url")

        if uploaded_file is not None:
            st.write(f"📁 **File:** `{uploaded_file.name}` ({round(uploaded_file.size / 1024, 1)} KB)")

            if st.button("📥 Parse & Extract Records from PDF", key="btn_parse_pdf_main", use_container_width=True):
                progress_box_pdf = st.empty()
                status_text_pdf = st.empty()

                def pdf_progress(stage, current, total, message):
                    percent = min(1.0, max(0.0, current / max(total, 1)))
                    progress_box_pdf.progress(percent)
                    status_text_pdf.info(f"[{stage.upper()}] {message}")

                try:
                    with st.spinner("Reading PDF, splitting into chunks, and extracting entities with Qwen..."):
                        pdf_bytes = uploaded_file.read()
                        res = collect_from_pdf(
                            pdf_source=pdf_bytes,
                            filename=uploaded_file.name,
                            source_name=doc_source_name,
                            source_url=doc_source_url,
                            progress_callback=pdf_progress
                        )

                    if res.get("error"):
                        st.error(f"Failed to process PDF: {res['error']}")
                    elif res["total_extracted"] == 0:
                        st.warning(
                            "PDF text was saved, but no valid tourism records were extracted. "
                            "The Pending Review and Verified Knowledge counters were not changed."
                        )
                    elif res["records"] == 0:
                        st.info(
                            f"PDF extraction found {res['total_extracted']} records, but all were "
                            "already present in the knowledge base. No counters were changed."
                        )
                    else:
                        st.success(
                            f"✅ PDF Extracted! Pages: {res['pages']}, "
                            f"Total extracted: {res['total_extracted']} "
                            f"({res['records']} new Pending Review records added)."
                        )

                    if res["records"] > 0:
                        st.rerun()
                except Exception as e:
                    st.error(f"Error extracting PDF: {e}")

    st.divider()
    st.markdown("### 📝 Manual Knowledge Entry — Text + Images")
    st.caption(
        "Add trusted tourism information manually and attach images as supporting evidence. "
        "The text is structured by Qwen; extracted records remain Pending Review until approved."
    )

    manual_flash = st.session_state.pop("manual_ingest_flash", None)
    if manual_flash:
        if manual_flash.get("error"):
            st.error(manual_flash["error"])
        elif manual_flash.get("records", 0) > 0:
            canonical_status = manual_flash.get("canonical_status", "pending_review").replace("_", " ").title()
            st.success(
                f"Saved document #{manual_flash['document_id']} with "
                f"{manual_flash['images']} linked image(s) and "
                f"{manual_flash['records']} new record(s). "
                f"Canonical text record #{manual_flash.get('canonical_record_id')}: {canonical_status}."
            )
            if manual_flash.get("canonical_status") == "pending_review":
                st.info(
                    "Open Knowledge Review & Curation and approve the canonical record "
                    "before expecting the chat assistant to use it."
                )
        else:
            st.warning(
                f"Saved document #{manual_flash['document_id']} and "
                f"{manual_flash['images']} image(s), but Qwen produced no new records. "
                "Add more specific descriptive text and try again."
            )

    manual_meta_left, manual_meta_right = st.columns(2)
    with manual_meta_left:
        manual_title = st.text_input(
            "Knowledge Title",
            placeholder="e.g. Updated Nathula permit instructions",
            key="manual_knowledge_title",
        )
        manual_source_name = st.text_input(
            "Source / Publisher",
            value="Manual Knowledge Entry",
            key="manual_source_name",
        )
    with manual_meta_right:
        manual_source_url = st.text_input(
            "Reference URL or Source Tag",
            value="manual://tourism-knowledge",
            key="manual_source_url",
        )
        manual_trust = st.selectbox(
            "Source Trust Level",
            ["medium", "high", "low"],
            key="manual_trust_level",
        )

    manual_option_left, manual_option_right = st.columns(2)
    with manual_option_left:
        manual_category = st.selectbox(
            "Knowledge Category",
            [
                "auto",
                "history",
                "destination",
                "transport",
                "permit",
                "culture",
                "food",
                "trekking",
                "lake",
                "safety",
            ],
            key="manual_knowledge_category",
            help="Auto detects the topic from the title and text.",
        )
    with manual_option_right:
        manual_approve = st.checkbox(
            "I verified this text — make the canonical record available to chat immediately",
            value=False,
            key="manual_approve_canonical",
            help=(
                "Only select this for information you have personally checked. "
                "Individual AI-extracted entity records still require review."
            ),
        )

    manual_text = st.text_area(
        "Knowledge Text / Image Description",
        height=180,
        placeholder=(
            "Enter the facts visible in the images and any supporting details. "
            "Include names, location, prices, dates, permit rules, timings and source context where applicable."
        ),
        key="manual_knowledge_text",
    )
    manual_images = st.file_uploader(
        "Attach Supporting Images",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        key="manual_knowledge_images",
        help="Images are stored as linked evidence. Enter their relevant facts in the text box for extraction.",
    )

    if manual_images:
        st.markdown("**Image preview**")
        preview_columns = st.columns(min(4, len(manual_images)))
        for image_index, image_file in enumerate(manual_images):
            with preview_columns[image_index % len(preview_columns)]:
                st.image(
                    image_file.getvalue(),
                    caption=image_file.name,
                    use_container_width=True,
                )

    if st.button(
        "💾 Save & Extract Manual Knowledge",
        key="btn_manual_knowledge",
        use_container_width=True,
        type="primary",
    ):
        if not manual_title.strip():
            st.error("Please enter a knowledge title.")
        elif len(manual_text.strip()) < 30:
            st.error("Please enter at least 30 characters describing the knowledge or attached images.")
        else:
            manual_progress = st.empty()
            manual_status = st.empty()

            def manual_progress_callback(stage, current, total, message):
                manual_progress.progress(min(1.0, current / max(total, 1)))
                manual_status.info(f"[{stage.upper()}] {message}")

            image_payloads = [
                {
                    "name": image_file.name,
                    "type": image_file.type,
                    "data": image_file.getvalue(),
                }
                for image_file in manual_images or []
            ]

            try:
                with st.spinner("Saving evidence and extracting structured knowledge with Qwen..."):
                    manual_result = collect_from_manual_entry(
                        text=manual_text,
                        title=manual_title,
                        source_name=manual_source_name,
                        source_url=manual_source_url,
                        trust_level=manual_trust,
                        category=manual_category,
                        approve_canonical=manual_approve,
                        images=image_payloads,
                        progress_callback=manual_progress_callback,
                    )
                st.session_state.manual_ingest_flash = manual_result
                st.rerun()
            except Exception as exc:
                st.error(f"Error saving manual knowledge: {exc}")


# =========================================================
# TAB 4: KNOWLEDGE ANALYTICS & STATS
# =========================================================
with tab_analytics:
    st.subheader("Knowledge Base Analytics & System Overview")

    with connect() as conn:
        records_df_raw = conn.execute("""
            SELECT id, document_id, status, confidence, created_at, record_json
            FROM records
        """).fetchall()

        sources_list = conn.execute("""
            SELECT id, name, base_url, source_type, trust_level, created_at
            FROM sources
        """).fetchall()

    if records_df_raw:
        parsed_records = []
        for r in records_df_raw:
            try:
                j = json.loads(r["record_json"])
                parsed_records.append({
                    "id": r["id"],
                    "status": r["status"],
                    "confidence": r["confidence"],
                    "category": j.get("category", "unknown"),
                    "district": j.get("district") or "Unspecified",
                    "name": j.get("name", "Unnamed"),
                })
            except Exception:
                pass

        df = pd.DataFrame(parsed_records)

        chart_c1, chart_c2 = st.columns(2)
        with chart_c1:
            st.markdown("#### Records Distribution by Category")
            category_counts = df["category"].value_counts()
            st.bar_chart(category_counts)

        with chart_c2:
            st.markdown("#### Verification Status")
            status_counts = df["status"].value_counts()
            st.bar_chart(status_counts)

        st.markdown("---")
        st.markdown("#### Indexed Tourism Knowledge Sources")
        if sources_list:
            sources_data = [
                {
                    "ID": s["id"],
                    "Source Name": s["name"],
                    "Base URL": s["base_url"],
                    "Type": s["source_type"],
                    "Trust Level": s["trust_level"],
                    "First Indexed": s["created_at"][:19]
                }
                for s in sources_list
            ]
            st.dataframe(pd.DataFrame(sources_data), use_container_width=True)
