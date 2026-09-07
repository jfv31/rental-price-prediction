import streamlit as st

st.set_page_config(
    page_title="GADA — Rental Market Analysis",
    page_icon="🏠",
    layout="wide",
)

st.title("🏠 German Rental Market — Interpretable ML Analysis")
st.markdown("""
**GADA Project | TU Dresden SS 2026**

This app explores what drives rental prices and time-to-let in the German housing market
using the RWI-GEO-RED dataset (~20M listings, ImmoScout24, 2007–2025).

### Pages
- **Model Comparison** — Performance overview across all 7 models
- **Shape Explorer** — Compare IGANN & EBM shape functions for price vs. duration
- **Apartment Simulator** — Get predictions and explanations for a custom apartment

> Use the sidebar to navigate between pages.
""")

st.info("Navigate using the sidebar on the left.")
