"""
App.py - Engine A Dashboard v1
Hero score card + allocation tiles. Read-only display of latest score.
Reads from data/engine_a_score.csv (produced by calculate_engine_a_score.py).
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Engine A — Market Strength",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ============================================================
# STYLES (Bloomberg-aesthetic, mobile-first)
# ============================================================
st.markdown("""
<style>
    /* Tighten default Streamlit padding for mobile */
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

    /* Hero score card */
    .score-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 16px;
        padding: 28px 16px;
        text-align: center;
        margin-bottom: 16px;
        border: 1px solid #334155;
    }
    .score-number {
        font-size: 72px;
        font-weight: 800;
        line-height: 1;
        margin: 8px 0;
        font-family: 'Courier New', monospace;
    }
    .score-denominator {
        font-size: 18px;
        color: #94a3b8;
        margin-top: -8px;
    }
    .score-condition {
        font-size: 22px;
        font-weight: 700;
        letter-spacing: 2px;
        margin-top: 12px;
    }
    .score-title {
        font-size: 13px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 4px;
    }
    .score-timestamp {
        font-size: 12px;
        color: #64748b;
        margin-top: 8px;
    }

    /* Allocation tiles */
    .alloc-tile {
        background: #1e293b;
        border-radius: 12px;
        padding: 14px 8px;
        text-align: center;
        border: 1px solid #334155;
        height: 100%;
    }
    .alloc-label {
        font-size: 11px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 4px;
    }
    .alloc-pct {
        font-size: 32px;
        font-weight: 800;
        font-family: 'Courier New', monospace;
        margin: 4px 0;
    }
    .alloc-sub {
        font-size: 11px;
        color: #cbd5e1;
        line-height: 1.3;
    }

    /* Safety override badges */
    .safety-row {
        display: flex;
        gap: 8px;
        margin-top: 12px;
    }
    .safety-badge {
        flex: 1;
        background: #1e293b;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        font-size: 12px;
        border: 1px solid #334155;
    }
    .safety-badge .label {
        color: #94a3b8;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .safety-badge .value {
        font-weight: 700;
        margin-top: 4px;
        font-size: 14px;
    }
    .ok    { color: #22c55e; }
    .warn  { color: #f59e0b; }
    .bad   { color: #ef4444; }
    .blue  { color: #38bdf8; }
    .gold  { color: #fbbf24; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# LOAD LATEST SCORE
# ============================================================
SCORE_FILE = Path("data/engine_a_score.csv")

def load_latest_score():
    if not SCORE_FILE.exists():
        return None
    df = pd.read_csv(SCORE_FILE)
    if df.empty:
        return None
    return df.iloc[-1].to_dict()  # latest row

score = load_latest_score()

if score is None:
    st.error("⚠️ No score data yet. Trigger the workflow to generate the first score.")
    st.stop()

# ============================================================
# COLOR LOGIC
# ============================================================
def condition_color(cond):
    return {
        "TERRIBLE":   "#ef4444",
        "WEAK":       "#f59e0b",
        "BELOW AVG":  "#f59e0b",
        "NEUTRAL":    "#38bdf8",
        "GOOD":       "#22c55e",
        "EXCELLENT":  "#22c55e",
    }.get(cond, "#94a3b8")

def score_color(s):
    if s <= 30:  return "#ef4444"
    if s <= 40:  return "#f59e0b"
    if s <= 52:  return "#38bdf8"
    if s <= 62:  return "#22c55e"
    return "#22c55e"

# ============================================================
# HEADER
# ============================================================
st.markdown(
    "<div class='score-title'>Engine A — Market Strength</div>",
    unsafe_allow_html=True
)

# ============================================================
# HERO SCORE CARD
# ============================================================
sc = score["raw_score"]
cond = score["market_condition"]
ts = score["timestamp"]

# Format timestamp nicely
try:
    ts_dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    ts_pretty = ts_dt.strftime("%d %b %Y, %I:%M %p")
except Exception:
    ts_pretty = ts

st.markdown(f"""
<div class='score-card'>
    <div class='score-title'>Current Score</div>
    <div class='score-number' style='color:{score_color(sc)}'>{sc}</div>
    <div class='score-denominator'>/ 100</div>
    <div class='score-condition' style='color:{condition_color(cond)}'>{cond}</div>
    <div class='score-timestamp'>Last updated: {ts_pretty}</div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# ALLOCATION TILES
# ============================================================
eq    = int(score["equity_pct"])
eb    = int(score["engine_b_pct"])
ec    = int(score["engine_c_pct"])
debt  = int(score["debt_pct"])
gold  = int(score["gold_pct"])
dur   = score["duration_signal"]
gsig  = score["gold_signal"]

st.markdown("<div class='score-title' style='margin-bottom:8px'>Suggested Allocation</div>", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"""
    <div class='alloc-tile'>
        <div class='alloc-label'>Equity</div>
        <div class='alloc-pct' style='color:#22c55e'>{eq}%</div>
        <div class='alloc-sub'>B: {eb}%<br>C: {ec}%</div>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class='alloc-tile'>
        <div class='alloc-label'>Debt</div>
        <div class='alloc-pct' style='color:#38bdf8'>{debt}%</div>
        <div class='alloc-sub'>{dur}</div>
    </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class='alloc-tile'>
        <div class='alloc-label'>Gold</div>
        <div class='alloc-pct' style='color:#fbbf24'>{gold}%</div>
        <div class='alloc-sub'>{gsig}</div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# SAFETY BADGES
# ============================================================
red_flag = score["red_flag"]
pe_bubble = score["pe_bubble"]

rf_color = "bad" if red_flag == "YES" else "ok"
pe_color = "bad" if pe_bubble == "YES" else "ok"

st.markdown(f"""
<div class='safety-row'>
    <div class='safety-badge'>
        <div class='label'>Red Flag</div>
        <div class='value {rf_color}'>{red_flag}</div>
    </div>
    <div class='safety-badge'>
        <div class='label'>PE Bubble</div>
        <div class='value {pe_color}'>{pe_bubble}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# FOOTER NOTE
# ============================================================
st.markdown("""
<div style='text-align:center; margin-top:24px; color:#64748b; font-size:11px'>
    Engine A v1.0 · Sunday-only scoring · 2-week smoothing
</div>
""", unsafe_allow_html=True)
