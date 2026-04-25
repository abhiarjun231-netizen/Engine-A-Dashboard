"""
App.py - Investment Dashboard Router v4.0
Safe imports: Engine A always loads even if B/C have issues.
"""
import streamlit as st

st.set_page_config(page_title="Investment Dashboard", layout="wide", initial_sidebar_state="collapsed")

# --- SHARED CSS (Zerodha-inspired dark theme) ---
st.markdown("""
<style>
    .stApp { background-color: #0f172a; }
    [data-testid="stHeader"] { background-color: #0f172a; }
    [data-testid="stToolbar"] { display: none; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        background-color: #1e293b;
        border-radius: 12px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 600;
        font-size: 14px;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #334155;
        color: #e2e8f0;
    }
    .section-title {
        font-size: 13px;
        font-weight: 700;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin: 24px 0 12px 0;
    }
    div[data-testid="stExpander"] {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
    }
    .stButton > button {
        background-color: #334155;
        color: #e2e8f0;
        border: 1px solid #475569;
        border-radius: 8px;
        font-weight: 600;
    }
    footer { display: none; }
</style>
""", unsafe_allow_html=True)

# --- SAFE IMPORTS ---
from engine_a_ui import show_engine_a

try:
    from engine_b_ui import show_engine_b
    engine_b_ok = True
except Exception as e:
    engine_b_ok = False
    engine_b_error = str(e)

try:
    from engine_c_ui import show_engine_c
    engine_c_ok = True
except Exception as e:
    engine_c_ok = False
    engine_c_error = str(e)

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["Engine A", "Engine B", "Engine C"])

with tab1:
    show_engine_a()

with tab2:
    if engine_b_ok:
        show_engine_b()
    else:
        st.error(f"Engine B failed to load: {engine_b_error}")

with tab3:
    if engine_c_ok:
        show_engine_c()
    else:
        st.error(f"Engine C failed to load: {engine_c_error}")

# --- FOOTER ---
st.markdown(
    "<div style='text-align:center;color:#475569;font-size:11px;"
    "margin-top:40px;padding:16px;letter-spacing:1px;'>"
    "INVESTMENT DASHBOARD V4.0 · EMOTION-FREE SYSTEMATIC INVESTING"
    "</div>",
    unsafe_allow_html=True
)
