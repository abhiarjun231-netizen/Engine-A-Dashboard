"""
App.py - Dashboard Router v3.0
Premium dark glassmorphism theme
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
# PREMIUM DARK GLASSMORPHISM STYLES
# ============================================================
st.markdown("""
<style>
    /* === BASE === */
    .stApp {
        background: linear-gradient(160deg, #0a0e1a 0%, #0f172a 40%, #101c2e 100%);
    }
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 720px;
    }

    /* === GLASSMORPHISM CARDS === */
    .score-card {
        background: linear-gradient(135deg, rgba(30,41,59,0.8) 0%, rgba(15,23,42,0.9) 100%);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-radius: 20px;
        padding: 32px 16px;
        text-align: center;
        margin-bottom: 20px;
        border: 1px solid rgba(71,85,105,0.4);
        box-shadow: 0 8px 32px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05);
    }
    .score-number {
        font-size: 80px;
        font-weight: 900;
        line-height: 1;
        margin: 8px 0;
        font-family: 'Courier New', monospace;
        text-shadow: 0 0 40px rgba(56,189,248,0.3);
    }
    .score-denominator {
        font-size: 18px;
        color: #64748b;
        margin-top: -8px;
        font-weight: 300;
    }
    .score-condition {
        font-size: 22px;
        font-weight: 800;
        letter-spacing: 3px;
        margin-top: 14px;
        text-transform: uppercase;
    }
    .score-title {
        font-size: 11px;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 2.5px;
        margin-bottom: 4px;
        font-weight: 500;
    }
    .score-timestamp {
        font-size: 11px;
        color: #475569;
        margin-top: 10px;
        font-weight: 300;
    }

    /* === ALLOCATION TILES === */
    .alloc-tile {
        background: rgba(30,41,59,0.6);
        backdrop-filter: blur(8px);
        border-radius: 14px;
        padding: 16px 8px;
        text-align: center;
        border: 1px solid rgba(71,85,105,0.3);
        height: 100%;
        box-shadow: 0 4px 16px rgba(0,0,0,0.2);
    }
    .alloc-label {
        font-size: 10px;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 4px;
        font-weight: 500;
    }
    .alloc-pct {
        font-size: 36px;
        font-weight: 900;
        font-family: 'Courier New', monospace;
        margin: 6px 0;
    }
    .alloc-sub {
        font-size: 11px;
        color: #94a3b8;
        line-height: 1.4;
        font-weight: 400;
    }

    /* === SAFETY BADGES === */
    .safety-row {
        display: flex;
        gap: 10px;
        margin-top: 14px;
    }
    .safety-badge {
        flex: 1;
        background: rgba(30,41,59,0.5);
        border-radius: 12px;
        padding: 12px;
        text-align: center;
        font-size: 12px;
        border: 1px solid rgba(71,85,105,0.3);
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }
    .safety-badge .label {
        color: #64748b;
        font-size: 9px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 500;
    }
    .safety-badge .value {
        font-weight: 800;
        margin-top: 4px;
        font-size: 14px;
    }

    /* === SECTION TITLES === */
    .section-title {
        font-size: 11px;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 2.5px;
        margin: 28px 0 10px 0;
        font-weight: 600;
        border-bottom: 1px solid rgba(71,85,105,0.2);
        padding-bottom: 6px;
    }

    /* === DATA CARDS === */
    .data-card {
        background: rgba(30,41,59,0.5);
        border-radius: 14px;
        padding: 4px 0;
        border: 1px solid rgba(71,85,105,0.25);
        margin-bottom: 6px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.15);
    }
    .data-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 11px 16px;
        border-bottom: 1px solid rgba(51,65,85,0.3);
        font-size: 14px;
    }
    .data-row:last-child {
        border-bottom: none;
    }
    .data-label {
        color: #94a3b8;
        font-weight: 400;
    }
    .data-value {
        font-family: 'Courier New', monospace;
        font-weight: 700;
        color: #e2e8f0;
        font-size: 14px;
    }

    /* === INPUT FORM === */
    .input-card-label {
        font-size: 13px;
        font-weight: 600;
        color: #e2e8f0;
        margin-top: 10px;
    }
    .input-card-current {
        font-size: 11px;
        color: #64748b;
        margin-bottom: 4px;
    }

    /* === COLOR CLASSES === */
    .ok    { color: #22c55e; }
    .warn  { color: #f59e0b; }
    .bad   { color: #ef4444; }
    .blue  { color: #38bdf8; }
    .gold  { color: #fbbf24; }

    /* === TAB STYLING === */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        background: rgba(15,23,42,0.6);
        border-radius: 12px;
        padding: 4px;
        border: 1px solid rgba(71,85,105,0.2);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #64748b;
        font-weight: 600;
        font-size: 13px;
        letter-spacing: 0.5px;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(56,189,248,0.15);
        color: #38bdf8;
        border-bottom: none;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        display: none;
    }
    .stTabs [data-baseweb="tab-border"] {
        display: none;
    }

    /* === BUTTONS === */
    .stButton > button {
        background: linear-gradient(135deg, rgba(34,197,94,0.2) 0%, rgba(34,197,94,0.1) 100%);
        border: 1px solid rgba(34,197,94,0.3);
        color: #22c55e;
        font-weight: 700;
        border-radius: 10px;
        letter-spacing: 0.5px;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, rgba(34,197,94,0.3) 0%, rgba(34,197,94,0.2) 100%);
        border-color: rgba(34,197,94,0.5);
        box-shadow: 0 0 20px rgba(34,197,94,0.15);
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
        color: #fff;
        border: none;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
        box-shadow: 0 0 24px rgba(34,197,94,0.3);
    }

    /* === EXPANDERS === */
    .streamlit-expanderHeader {
        background: rgba(30,41,59,0.4);
        border-radius: 10px;
        border: 1px solid rgba(71,85,105,0.2);
        font-weight: 600;
        color: #94a3b8;
    }

    /* === NUMBER INPUTS === */
    .stNumberInput > div > div > input {
        background: rgba(15,23,42,0.8);
        border: 1px solid rgba(71,85,105,0.3);
        color: #e2e8f0;
        border-radius: 8px;
    }

    /* === FILE UPLOADER === */
    .stFileUploader > div {
        background: rgba(30,41,59,0.3);
        border: 1px dashed rgba(71,85,105,0.3);
        border-radius: 12px;
    }

    /* === SCROLLBAR === */
    ::-webkit-scrollbar {
        width: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #0f172a;
    }
    ::-webkit-scrollbar-thumb {
        background: #334155;
        border-radius: 3px;
    }

    /* === FOOTER === */
    .footer-text {
        text-align: center;
        margin-top: 32px;
        color: #334155;
        font-size: 10px;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        font-weight: 400;
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
st.markdown("<div class='footer-text'>Investment Dashboard v3.0 · Systematic · Emotion-Free</div>", unsafe_allow_html=True)
