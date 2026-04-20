"""
App.py - Dashboard Router v3.1
Clean premium dark theme — optimized for Streamlit mobile
Tabs: Engine A | Engine B | Engine C
"""

import streamlit as st
from engine_a_ui import show_engine_a
from engine_b_ui import show_engine_b
from engine_c_ui import show_engine_c

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Investment Dashboard",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ============================================================
# CLEAN PREMIUM DARK THEME
# ============================================================
st.markdown("""
<style>
    /* === DARK BASE === */
    .stApp { background-color: #0b1120; }
    .block-container { padding-top: 0.8rem; padding-bottom: 2rem; }
    header[data-testid="stHeader"] { background: #0b1120; }

    /* === SCORE HERO CARD === */
    .score-card {
        background: linear-gradient(145deg, #111b2e 0%, #0d1526 100%);
        border-radius: 18px; padding: 28px 16px; text-align: center;
        margin-bottom: 18px;
        border: 1px solid #1e3050;
        box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    }
    .score-number {
        font-size: 76px; font-weight: 900; line-height: 1; margin: 8px 0;
        font-family: 'Courier New', monospace;
    }
    .score-denominator { font-size: 16px; color: #4a5568; margin-top: -6px; }
    .score-condition {
        font-size: 20px; font-weight: 800; letter-spacing: 4px;
        margin-top: 12px; text-transform: uppercase;
    }
    .score-title {
        font-size: 11px; color: #4a5568; text-transform: uppercase;
        letter-spacing: 2px; margin-bottom: 4px; font-weight: 600;
    }
    .score-timestamp { font-size: 11px; color: #374151; margin-top: 8px; }

    /* === ALLOCATION TILES === */
    .alloc-tile {
        background: #111b2e; border-radius: 14px; padding: 14px 8px;
        text-align: center; border: 1px solid #1e3050; height: 100%;
        box-shadow: 0 2px 12px rgba(0,0,0,0.25);
    }
    .alloc-label {
        font-size: 10px; color: #4a5568; text-transform: uppercase;
        letter-spacing: 1.5px; margin-bottom: 4px; font-weight: 600;
    }
    .alloc-pct {
        font-size: 34px; font-weight: 900;
        font-family: 'Courier New', monospace; margin: 4px 0;
    }
    .alloc-sub { font-size: 11px; color: #7c8ba0; line-height: 1.3; }

    /* === SAFETY BADGES === */
    .safety-row { display: flex; gap: 8px; margin-top: 12px; }
    .safety-badge {
        flex: 1; background: #111b2e; border-radius: 10px; padding: 10px;
        text-align: center; font-size: 12px; border: 1px solid #1e3050;
    }
    .safety-badge .label {
        color: #4a5568; font-size: 9px; text-transform: uppercase;
        letter-spacing: 1.5px; font-weight: 600;
    }
    .safety-badge .value { font-weight: 800; margin-top: 4px; font-size: 14px; }

    /* === SECTION TITLES === */
    .section-title {
        font-size: 10px; color: #3d5070; text-transform: uppercase;
        letter-spacing: 2.5px; margin: 24px 0 8px 0; font-weight: 700;
    }

    /* === DATA CARDS === */
    .data-card {
        background: #111b2e; border-radius: 12px; padding: 4px 0;
        border: 1px solid #1e3050; margin-bottom: 4px;
    }
    .data-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 10px 14px; border-bottom: 1px solid #172240; font-size: 14px;
    }
    .data-row:last-child { border-bottom: none; }
    .data-label { color: #7c8ba0; }
    .data-value {
        font-family: 'Courier New', monospace; font-weight: 700;
        color: #d1dbe8; font-size: 14px;
    }

    /* === INPUTS === */
    .input-card-label { font-size: 13px; font-weight: 600; color: #d1dbe8; margin-top: 8px; }
    .input-card-current { font-size: 11px; color: #4a5568; margin-bottom: 4px; }

    /* === COLORS === */
    .ok    { color: #10b981; }
    .warn  { color: #f59e0b; }
    .bad   { color: #ef4444; }
    .blue  { color: #38bdf8; }
    .gold  { color: #fbbf24; }

    /* === TABS (FIXED FOR MOBILE) === */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        background: #111b2e;
        border-radius: 10px;
        padding: 3px;
        border: 1px solid #1e3050;
        margin-bottom: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #4a5568;
        font-weight: 700;
        font-size: 14px;
        padding: 10px 0;
        flex: 1;
        text-align: center;
    }
    .stTabs [aria-selected="true"] {
        background: #1a2942;
        color: #38bdf8;
    }
    .stTabs [data-baseweb="tab-highlight"] { display: none; }
    .stTabs [data-baseweb="tab-border"] { display: none; }

    /* === BUTTONS === */
    .stButton > button {
        border: 1px solid #1e3a5f;
        color: #7c8ba0;
        font-weight: 600;
        border-radius: 10px;
        background: #111b2e;
    }
    .stButton > button:hover {
        background: #162238;
        border-color: #2d5a8e;
        color: #d1dbe8;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #10b981, #059669);
        color: #fff; border: none; font-weight: 700;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #059669, #047857);
    }

    /* === EXPANDERS === */
    details {
        background: #0e1829;
        border: 1px solid #1e3050;
        border-radius: 10px;
    }
    details summary {
        color: #7c8ba0;
        font-weight: 600;
    }

    /* === NUMBER INPUT === */
    .stNumberInput input {
        background: #0b1120;
        border: 1px solid #1e3050;
        color: #d1dbe8;
        border-radius: 8px;
    }

    /* === FILE UPLOADER === */
    [data-testid="stFileUploader"] {
        background: #0e1829;
        border-radius: 10px;
        border: 1px solid #1e3050;
    }

    /* === SELECT BOX === */
    .stSelectbox > div > div {
        background: #0b1120;
        border-color: #1e3050;
    }

    /* === SCROLLBAR === */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: #0b1120; }
    ::-webkit-scrollbar-thumb { background: #1e3050; border-radius: 2px; }

    /* === FOOTER === */
    .footer-text {
        text-align: center; margin-top: 28px;
        color: #1e3050; font-size: 10px;
        letter-spacing: 2px; text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# TABS
# ============================================================
tab1, tab2, tab3 = st.tabs(["Engine A", "Engine B", "Engine C"])

with tab1:
    show_engine_a()

with tab2:
    show_engine_b()

with tab3:
    show_engine_c()

# FOOTER
st.markdown("<div class='footer-text'>Investment Dashboard v3.1 · Systematic · Emotion-Free</div>", unsafe_allow_html=True)
