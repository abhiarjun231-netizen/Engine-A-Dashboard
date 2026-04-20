"""
App.py - Dashboard Router v3.2
Zerodha Kite-inspired dark theme
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
# ZERODHA-INSPIRED DARK THEME
# ============================================================
st.markdown("""
<style>
    /* === HIDE STREAMLIT DEFAULTS === */
    #MainMenu { visibility: hidden; }
    header { visibility: hidden; height: 0px; }
    footer { visibility: hidden; }
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }

    /* === DARK BASE (Zerodha dark blue-grey) === */
    .stApp { background-color: #1b1b2d; }

    /* === SCORE HERO CARD === */
    .score-card {
        background: #25253d; border-radius: 16px; padding: 28px 16px;
        text-align: center; margin-bottom: 16px; border: 1px solid #35355a;
    }
    .score-number {
        font-size: 76px; font-weight: 900; line-height: 1; margin: 8px 0;
        font-family: 'Courier New', monospace;
    }
    .score-denominator { font-size: 16px; color: #6b6b8a; margin-top: -6px; }
    .score-condition {
        font-size: 20px; font-weight: 800; letter-spacing: 4px;
        margin-top: 12px; text-transform: uppercase;
    }
    .score-title {
        font-size: 11px; color: #6b6b8a; text-transform: uppercase;
        letter-spacing: 2px; margin-bottom: 4px; font-weight: 600;
    }
    .score-timestamp { font-size: 11px; color: #4a4a6a; margin-top: 8px; }

    /* === ALLOCATION TILES === */
    .alloc-tile {
        background: #25253d; border-radius: 12px; padding: 14px 8px;
        text-align: center; border: 1px solid #35355a; height: 100%;
    }
    .alloc-label {
        font-size: 10px; color: #6b6b8a; text-transform: uppercase;
        letter-spacing: 1.5px; margin-bottom: 4px; font-weight: 600;
    }
    .alloc-pct {
        font-size: 34px; font-weight: 900;
        font-family: 'Courier New', monospace; margin: 4px 0;
    }
    .alloc-sub { font-size: 11px; color: #8888a8; line-height: 1.3; }

    /* === SAFETY BADGES === */
    .safety-row { display: flex; gap: 8px; margin-top: 12px; }
    .safety-badge {
        flex: 1; background: #25253d; border-radius: 10px; padding: 10px;
        text-align: center; font-size: 12px; border: 1px solid #35355a;
    }
    .safety-badge .label {
        color: #6b6b8a; font-size: 9px; text-transform: uppercase;
        letter-spacing: 1.5px; font-weight: 600;
    }
    .safety-badge .value { font-weight: 800; margin-top: 4px; font-size: 14px; }

    /* === SECTION TITLES === */
    .section-title {
        font-size: 10px; color: #5555778; text-transform: uppercase;
        letter-spacing: 2.5px; margin: 24px 0 8px 0; font-weight: 700;
    }

    /* === DATA CARDS === */
    .data-card {
        background: #25253d; border-radius: 12px; padding: 4px 0;
        border: 1px solid #35355a; margin-bottom: 4px;
    }
    .data-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 10px 14px; border-bottom: 1px solid #2e2e4a; font-size: 14px;
    }
    .data-row:last-child { border-bottom: none; }
    .data-label { color: #8888a8; }
    .data-value {
        font-family: 'Courier New', monospace; font-weight: 700;
        color: #e0e0f0; font-size: 14px;
    }

    /* === INPUTS === */
    .input-card-label { font-size: 13px; font-weight: 600; color: #e0e0f0; margin-top: 8px; }
    .input-card-current { font-size: 11px; color: #6b6b8a; margin-bottom: 4px; }

    /* === COLORS (Zerodha palette) === */
    .ok    { color: #4caf50; }
    .warn  { color: #ff9800; }
    .bad   { color: #ff5252; }
    .blue  { color: #387ed1; }
    .gold  { color: #ffc107; }

    /* === TABS (VISIBLE + ZERODHA STYLE) === */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        background: #25253d;
        border-radius: 10px;
        padding: 4px;
        border: 1px solid #35355a;
        margin-bottom: 14px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #6b6b8a;
        font-weight: 700;
        font-size: 14px;
        padding: 10px 0;
        flex: 1;
        text-align: center;
    }
    .stTabs [aria-selected="true"] {
        background: #387ed1;
        color: #ffffff;
    }
    .stTabs [data-baseweb="tab-highlight"] { display: none; }
    .stTabs [data-baseweb="tab-border"] { display: none; }

    /* === BUTTONS (Zerodha green) === */
    .stButton > button {
        border: 1px solid #35355a;
        color: #8888a8;
        font-weight: 600;
        border-radius: 8px;
        background: #25253d;
    }
    .stButton > button:hover {
        background: #2e2e4a;
        border-color: #387ed1;
        color: #e0e0f0;
    }
    .stButton > button[kind="primary"] {
        background: #387ed1;
        color: #fff; border: none; font-weight: 700;
    }
    .stButton > button[kind="primary"]:hover {
        background: #2d6db8;
    }

    /* === EXPANDERS === */
    details {
        background: #20203a;
        border: 1px solid #35355a;
        border-radius: 8px;
    }
    details summary { color: #8888a8; font-weight: 600; }

    /* === FORM INPUTS === */
    .stNumberInput input, .stTextInput input {
        background: #1b1b2d;
        border: 1px solid #35355a;
        color: #e0e0f0;
        border-radius: 6px;
    }
    .stSelectbox > div > div {
        background: #1b1b2d;
        border-color: #35355a;
    }

    /* === FILE UPLOADER === */
    [data-testid="stFileUploader"] {
        background: #20203a;
        border-radius: 8px;
        border: 1px solid #35355a;
    }

    /* === SCROLLBAR === */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: #1b1b2d; }
    ::-webkit-scrollbar-thumb { background: #35355a; border-radius: 2px; }

    /* === FOOTER === */
    .footer-text {
        text-align: center; margin-top: 28px;
        color: #35355a; font-size: 10px;
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
st.markdown("<div class='footer-text'>Investment Dashboard v3.2 · Systematic · Emotion-Free</div>", unsafe_allow_html=True)
