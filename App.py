"""
App.py - Investment Dashboard Router v4.0
Full Zerodha-inspired dark theme with all CSS classes for Engine A.
Safe imports: Engine A always loads even if B/C have issues.
"""
import streamlit as st

st.set_page_config(page_title="Investment Dashboard", layout="wide", initial_sidebar_state="collapsed")

# --- COMPLETE CSS (Zerodha-inspired dark theme) ---
st.markdown("""
<style>
    /* === BASE === */
    .stApp { background-color: #0f172a; }
    [data-testid="stHeader"] { background-color: #0f172a; }
    [data-testid="stToolbar"] { display: none; }
    footer { display: none; }

    /* === TABS === */
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

    /* === SCORE CARD === */
    .score-card {
        background: #1e293b;
        border-radius: 16px;
        padding: 32px 16px;
        border: 1px solid #334155;
        text-align: center;
        margin-bottom: 16px;
    }
    .score-title {
        font-size: 13px;
        font-weight: 700;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 8px;
    }
    .score-number {
        font-size: 72px;
        font-weight: 800;
        line-height: 1;
        margin: 8px 0;
        font-family: 'SF Mono', 'Courier New', monospace;
    }
    .score-denominator {
        font-size: 18px;
        color: #64748b;
        margin-bottom: 8px;
    }
    .score-condition {
        font-size: 22px;
        font-weight: 700;
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .score-timestamp {
        font-size: 12px;
        color: #64748b;
    }

    /* === SECTION TITLE === */
    .section-title {
        font-size: 13px;
        font-weight: 700;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin: 24px 0 12px 0;
    }

    /* === ALLOCATION TILES === */
    .alloc-tile {
        background: #1e293b;
        border-radius: 12px;
        padding: 16px 8px;
        border: 1px solid #334155;
        text-align: center;
    }
    .alloc-label {
        font-size: 12px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 4px;
    }
    .alloc-pct {
        font-size: 28px;
        font-weight: 800;
        font-family: 'SF Mono', 'Courier New', monospace;
    }
    .alloc-sub {
        font-size: 11px;
        color: #64748b;
        margin-top: 4px;
        line-height: 1.4;
    }

    /* === SAFETY BADGES === */
    .safety-row {
        display: flex;
        gap: 12px;
        margin: 16px 0;
    }
    .safety-badge {
        flex: 1;
        background: #1e293b;
        border-radius: 10px;
        padding: 12px;
        border: 1px solid #334155;
        text-align: center;
    }
    .safety-badge .label {
        font-size: 11px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 4px;
    }
    .safety-badge .value.ok {
        color: #22c55e;
        font-weight: 700;
        font-size: 14px;
    }
    .safety-badge .value.bad {
        color: #ef4444;
        font-weight: 700;
        font-size: 14px;
    }

    /* === DATA CARDS (tables, breakdown) === */
    .data-card {
        background: #1e293b;
        border-radius: 12px;
        padding: 12px 16px;
        border: 1px solid #334155;
        margin-bottom: 12px;
    }
    .data-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #1a2332;
    }
    .data-row:last-child {
        border-bottom: none;
    }
    .data-label {
        color: #cbd5e1;
        font-size: 13px;
    }
    .data-value {
        color: #e2e8f0;
        font-weight: 600;
        font-size: 13px;
        font-family: 'SF Mono', 'Courier New', monospace;
    }

    /* === INPUT FORM === */
    .input-card-label {
        color: #e2e8f0;
        font-weight: 600;
        font-size: 14px;
        margin-top: 12px;
    }
    .input-card-current {
        color: #64748b;
        font-size: 12px;
        margin-bottom: 4px;
    }

    /* === EXPANDER === */
    div[data-testid="stExpander"] {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
    }

    /* === BUTTONS === */
    .stButton > button {
        background-color: #334155;
        color: #e2e8f0;
        border: 1px solid #475569;
        border-radius: 8px;
        font-weight: 600;
    }
    .stButton > button[kind="primary"] {
        background-color: #ef4444;
        color: white;
        border: none;
    }

    /* === COLUMNS === */
    [data-testid="stHorizontalBlock"] {
        gap: 8px;
    }
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
