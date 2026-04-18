"""
App.py - Dashboard Router
Tabs: Engine A | Engine B & C
Each engine lives in its own file.
"""

import streamlit as st
from engine_a_ui import show_engine_a
from engine_b_ui import show_engine_b

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
# STYLES (shared across all tabs)
# ============================================================
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

    .score-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 16px; padding: 28px 16px; text-align: center;
        margin-bottom: 16px; border: 1px solid #334155;
    }
    .score-number {
        font-size: 72px; font-weight: 800; line-height: 1; margin: 8px 0;
        font-family: 'Courier New', monospace;
    }
    .score-denominator { font-size: 18px; color: #94a3b8; margin-top: -8px; }
    .score-condition { font-size: 22px; font-weight: 700; letter-spacing: 2px; margin-top: 12px; }
    .score-title {
        font-size: 13px; color: #94a3b8; text-transform: uppercase;
        letter-spacing: 1.5px; margin-bottom: 4px;
    }
    .score-timestamp { font-size: 12px; color: #64748b; margin-top: 8px; }

    .alloc-tile {
        background: #1e293b; border-radius: 12px; padding: 14px 8px;
        text-align: center; border: 1px solid #334155; height: 100%;
    }
    .alloc-label {
        font-size: 11px; color: #94a3b8; text-transform: uppercase;
        letter-spacing: 1px; margin-bottom: 4px;
    }
    .alloc-pct { font-size: 32px; font-weight: 800; font-family: 'Courier New', monospace; margin: 4px 0; }
    .alloc-sub { font-size: 11px; color: #cbd5e1; line-height: 1.3; }

    .safety-row { display: flex; gap: 8px; margin-top: 12px; }
    .safety-badge {
        flex: 1; background: #1e293b; border-radius: 10px; padding: 10px;
        text-align: center; font-size: 12px; border: 1px solid #334155;
    }
    .safety-badge .label { color: #94a3b8; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }
    .safety-badge .value { font-weight: 700; margin-top: 4px; font-size: 14px; }

    .section-title {
        font-size: 12px; color: #94a3b8; text-transform: uppercase;
        letter-spacing: 2px; margin: 24px 0 8px 0; font-weight: 600;
    }

    .data-card {
        background: #1e293b; border-radius: 12px; padding: 4px 0;
        border: 1px solid #334155; margin-bottom: 4px;
    }
    .data-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 10px 14px; border-bottom: 1px solid #293548; font-size: 14px;
    }
    .data-row:last-child { border-bottom: none; }
    .data-label { color: #cbd5e1; }
    .data-value { font-family: 'Courier New', monospace; font-weight: 600; color: #e2e8f0; }

    .input-card-label { font-size: 13px; font-weight: 600; color: #e2e8f0; margin-top: 8px; }
    .input-card-current { font-size: 11px; color: #94a3b8; margin-bottom: 4px; }

    .ok    { color: #22c55e; }
    .warn  { color: #f59e0b; }
    .bad   { color: #ef4444; }
    .blue  { color: #38bdf8; }
    .gold  { color: #fbbf24; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# TABS
# ============================================================
tab1, tab2 = st.tabs(["Engine A", "Engine B & C"])

with tab1:
    show_engine_a()

with tab2:
    show_engine_b()

# FOOTER
st.markdown("<div style='text-align:center; margin-top:24px; color:#64748b; font-size:11px'>Investment Dashboard v2.0 · Live data</div>", unsafe_allow_html=True)
