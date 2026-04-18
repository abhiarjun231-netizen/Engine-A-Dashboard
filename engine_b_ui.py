"""
engine_b_ui.py - Engine B & C display logic
Called by App.py via show_engine_b()
"""

import streamlit as st

def show_engine_b():
    st.markdown("<div class='score-title'>Engine B & C — Stock Engines</div>", unsafe_allow_html=True)
    st.caption("Paper trading dashboard for short-term (B) and long-term (C) engines")
    st.info("Baby Step 2 complete — skeleton ready. Positions coming next.")
