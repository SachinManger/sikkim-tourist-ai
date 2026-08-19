import sys
import json
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------
# Make project root available
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db import list_records, update_record, stats


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="Sikkim Tourism AI Data Review",
    page_icon="🏔️",
    layout="wide"
)


# ---------------------------------------------------------
# Title
# ---------------------------------------------------------

st.title("🏔️ Sikkim Tourism AI Data Review")

st.markdown(
    """
    Review tourism information collected by the Sikkim Tourism
    AI Data Collection Agent.

    AI-extracted records remain **Pending Review** until manually
    approved.
    """
)


# ---------------------------------------------------------
# Statistics
# ---------------------------------------------------------

database_stats = stats()

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Sources", database_stats["sources"])

with col2:
    st.metric("Documents", database_stats["documents"])

with col3:
    st.metric("Pending", database_stats["pending"])

with col4:
    st.metric("Approved", database_stats["approved"])

with col5:
    st.metric("Rejected", database_stats["rejected"])


st.divider()


# ---------------------------------------------------------
# Status filter
# ---------------------------------------------------------

status_filter = st.selectbox(
    "Select records to display",
    [
        "pending_review",
        "approved",
        "rejected",
        "all"
    ]
)


# ---------------------------------------------------------
# Load records
# ---------------------------------------------------------

if status_filter == "all":
    records = list_records()
else:
    records = list_records(status_filter)


st.subheader(f"Records: {len(records)}")


# ---------------------------------------------------------
# No records
# ---------------------------------------------------------

if not records:

    st.info("No records found for this filter.")

    st.stop()


# ---------------------------------------------------------
# Display records
# ---------------------------------------------------------

for row in records:

    record_id = row["id"]

    try:
        record = json.loads(row["record_json"])
    except Exception:

        st.error(
            f"Could not read record ID {record_id}"
        )

        continue


    name = record.get("name", "Unnamed")
    category = record.get("category", "unknown")
    description = record.get("description") or ""

    status = row["status"]
    confidence = row["confidence"]

    with st.expander(
        f"#{record_id} — {name} — {category} — {status}"
    ):

        # -------------------------------------------------
        # Basic information
        # -------------------------------------------------

        st.markdown("### Basic Information")

        col1, col2 = st.columns(2)

        with col1:

            st.write(
                "**Name:**",
                record.get("name")
            )

            st.write(
                "**Category:**",
                record.get("category")
            )

            st.write(
                "**Region:**",
                record.get("region")
            )

            st.write(
                "**District:**",
                record.get("district")
            )

        with col2:

            st.write(
                "**Confidence:**",
                confidence
            )

            st.write(
                "**Status:**",
                status
            )

            st.write(
                "**Altitude:**",
                record.get("altitude")
            )

            st.write(
                "**Duration:**",
                record.get("duration")
            )


        # -------------------------------------------------
        # Description
        # -------------------------------------------------

        st.markdown("### Description")

        st.write(description)


        # -------------------------------------------------
        # Activities
        # -------------------------------------------------

        activities = record.get("activities") or []

        if activities:

            st.markdown("### Activities")

            st.write(", ".join(activities))


        # -------------------------------------------------
        # Nearby places
        # -------------------------------------------------

        nearby = record.get("nearby_places") or []

        if nearby:

            st.markdown("### Nearby Places")

            for place in nearby:

                st.write(f"- {place}")


        # -------------------------------------------------
        # Travel information
        # -------------------------------------------------

        st.markdown("### Travel Information")

        st.write(
            "**How to reach:**",
            record.get("how_to_reach")
        )

        st.write(
            "**Permit required:**",
            record.get("permit_required")
        )

        st.write(
            "**Best time:**",
            record.get("best_time")
        )


        # -------------------------------------------------
        # Safety
        # -------------------------------------------------

        safety = record.get("safety_information") or []

        if safety:

            st.markdown("### Safety Information")

            for item in safety:

                st.write(f"- {item}")


        # -------------------------------------------------
        # Source
        # -------------------------------------------------

        st.markdown("### Source")

        source = record.get("source") or {}

        st.write(
            "**Source Name:**",
            source.get("source_name")
        )

        st.write(
            "**Source URL:**",
            source.get("source_url")
        )

        st.write(
            "**Page URL:**",
            source.get("page_url")
        )

        st.write(
            "**Collected Date:**",
            source.get("collected_date")
        )


        # -------------------------------------------------
        # Reviewer note
        # -------------------------------------------------

        note = st.text_area(
            "Reviewer Note",
            value=row["reviewer_note"] or "",
            key=f"note_{record_id}"
        )


        # -------------------------------------------------
        # Buttons
        # -------------------------------------------------

        col1, col2, col3 = st.columns(3)


        with col1:

            if st.button(
                "✅ Approve",
                key=f"approve_{record_id}"
            ):

                update_record(
                    record_id,
                    record,
                    "approved",
                    note
                )

                st.success(
                    f"Record {record_id} approved."
                )

                st.rerun()


        with col2:

            if st.button(
                "❌ Reject",
                key=f"reject_{record_id}"
            ):

                update_record(
                    record_id,
                    record,
                    "rejected",
                    note
                )

                st.warning(
                    f"Record {record_id} rejected."
                )

                st.rerun()


        with col3:

            if st.button(
                "🔄 Keep Pending",
                key=f"pending_{record_id}"
            ):

                update_record(
                    record_id,
                    record,
                    "pending_review",
                    note
                )

                st.info(
                    f"Record {record_id} kept pending."
                )

                st.rerun()