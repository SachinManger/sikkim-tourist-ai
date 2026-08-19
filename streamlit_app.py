"""Application router: public travel experience plus the admin console."""
import streamlit as st


st.set_page_config(
    page_title="Discover Sikkim",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

public_page = st.Page(
    "app/landing.py",
    title="Explore Sikkim",
    icon="🏔️",
    default=True,
)
admin_page = st.Page(
    "app/dashboard.py",
    title="Admin Console",
    icon="🔐",
    url_path="admin",
)

selected_page = st.navigation([public_page, admin_page], position="sidebar")
selected_page.run()
