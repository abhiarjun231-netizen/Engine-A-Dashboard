"""
App.py - Engine A Dashboard v2 (8.1 + 8.2 + 8.3)
Hero score card + allocation + live data sections + component breakdown.
Read-only display. Input form comes in 8.4.
"""

import streamlit as st
import pandas as pd
import json
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
# STYLES
# ============================================================
st.markdown("""
<style>
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
        font-size: 72px; font-weight: 800; line-height: 1; margin: 8px 0;
        font-family: 'Courier New', monospace;
    }
    .score-denominator { font-size: 18px; color: #94a3b8; margin-top: -8px; }
    .score-condition {
        font-size: 22px; font-weight: 700; letter-spacing: 2px; margin-top: 12px;
    }
    .score-title {
        font-size: 13px; color: #94a3b8; text-transform: uppercase;
        letter-spacing: 1.5px; margin-bottom: 4px;
    }
    .score-timestamp { font-size: 12px; color: #64748b; margin-top: 8px; }

    /* Allocation tiles */
    .alloc-tile {
        background: #1e293b; border-radius: 12px; padding: 14px 8px;
        text-align: center; border: 1px solid #334155; height: 100%;
    }
    .alloc-label {
        font-size: 11px; color: #94a3b8; text-transform: uppercase;
        letter-spacing: 1px; margin-bottom: 4px;
    }
    .alloc-pct {
        font-size: 32px; font-weight: 800; font-family: 'Courier New', monospace; margin: 4px 0;
    }
    .alloc-sub { font-size: 11px; color: #cbd5e1; line-height: 1.3; }

    /* Safety badges */
    .safety-row { display: flex; gap: 8px; margin-top: 12px; }
    .safety-badge {
        flex: 1; background: #1e293b; border-radius: 10px; padding: 10px;
        text-align: center; font-size: 12px; border: 1px solid #334155;
    }
    .safety-badge .label {
        color: #94a3b8; font-size: 10px; text-transform: uppercase; letter-spacing: 1px;
    }
    .safety-badge .value { font-weight: 700; margin-top: 4px; font-size: 14px; }

    /* Section headers */
    .section-title {
        font-size: 12px; color: #94a3b8; text-transform: uppercase;
        letter-spacing: 2px; margin: 24px 0 8px 0; font-weight: 600;
    }

    /* Data table card */
    .data-card {
        background: #1e293b; border-radius: 12px; padding: 4px 0;
        border: 1px solid #334155; margin-bottom: 4px;
    }
    .data-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 10px 14px; border-bottom: 1px solid #293548;
        font-size: 14px;
    }
    .data-row:last-child { border-bottom: none; }
    .data-label { color: #cbd5e1; }
    .data-value {
        font-family: 'Courier New', monospace; font-weight: 600; color: #e2e8f0;
    }
    .data-tag { font-size: 11px; color: #94a3b8; margin-left: 8px; }

    /* Component breakdown */
    .comp-row {
        display: flex; align-items: center; padding: 10px 14px;
        border-bottom: 1px solid #293548; font-size: 13px;
    }
    .comp-row:last-child { border-bottom: none; }
    .comp-label { flex: 0 0 90px; color: #cbd5e1; font-size: 13px; }
    .comp-bar-wrap {
        flex: 1; height: 10px; background: #0f172a;
        border-radius: 6px; overflow: hidden; margin: 0 10px;
    }
    .comp-bar { height: 100%; border-radius: 6px; }
    .comp-score {
        flex: 0 0 60px; text-align: right;
        font-family: 'Courier New', monospace; font-weight: 700; font-size: 13px;
    }

    /* Color utilities */
    .ok    { color: #22c55e; }
    .warn  { color: #f59e0b; }
    .bad   { color: #ef4444; }
    .blue  { color: #38bdf8; }
    .gold  { color: #fbbf24; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATA LOADERS
# ============================================================
SCORE_FILE  = Path("data/engine_a_score.csv")
LIVE_FILE   = Path("data/live_prices.csv")
GLOBAL_FILE = Path("data/global_prices.csv")
MANUAL_FILE = Path("manual_inputs.json")

def load_latest_score():
    if not SCORE_FILE.exists(): return None
    df = pd.read_csv(SCORE_FILE)
    return None if df.empty else df.iloc[-1].to_dict()

def load_live():
    if not LIVE_FILE.exists(): return {}
    df = pd.read_csv(LIVE_FILE)
    return dict(zip(df["symbol"], df["price"]))

def load_global():
    if not GLOBAL_FILE.exists(): return {}
    df = pd.read_csv(GLOBAL_FILE)
    return dict(zip(df["symbol"], df["price"]))

def load_manual():
    if not MANUAL_FILE.exists(): return {}
    with open(MANUAL_FILE, "r") as f:
        data = json.load(f)
    out = {}
    for k, obj in data.items():
        if k.startswith("_"): continue
        out[k] = obj.get("value")
    return out

score  = load_latest_score()
live   = load_live()
glob   = load_global()
manual = load_manual()

if score is None:
    st.error("⚠️ No score data yet. Trigger the workflow to generate the first score.")
    st.stop()

# ============================================================
# COLOR HELPERS
# ============================================================
def condition_color(c):
    return {
        "TERRIBLE": "#ef4444", "WEAK": "#f59e0b", "BELOW AVG": "#f59e0b",
        "NEUTRAL": "#38bdf8", "GOOD": "#22c55e", "EXCELLENT": "#22c55e",
    }.get(c, "#94a3b8")

def score_color(s):
    if s <= 30: return "#ef4444"
    if s <= 40: return "#f59e0b"
    if s <= 52: return "#38bdf8"
    return "#22c55e"

def bar_color(pct):
    """Color for component bar based on % of max."""
    if pct < 0.30: return "#ef4444"
    if pct < 0.55: return "#f59e0b"
    if pct < 0.75: return "#38bdf8"
    return "#22c55e"

def fmt_num(n, decimals=2):
    if n is None or pd.isna(n): return "—"
    try:
        return f"{float(n):,.{decimals}f}"
    except (ValueError, TypeError):
        return str(n)

def fmt_int(n):
    if n is None or pd.isna(n): return "—"
    try:
        return f"{int(n):,}"
    except (ValueError, TypeError):
        return str(n)

def fmt_signed(n):
    """Format with + or - sign for FII/DII flows."""
    if n is None or pd.isna(n): return "—"
    try:
        v = int(n)
        sign = "+" if v >= 0 else ""
        return f"{sign}{v:,}"
    except (ValueError, TypeError):
        return str(n)

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
sc   = score["raw_score"]
cond = score["market_condition"]
ts   = score["timestamp"]

try:
    ts_pretty = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y, %I:%M %p")
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
eq   = int(score["equity_pct"])
eb   = int(score["engine_b_pct"])
ec   = int(score["engine_c_pct"])
debt = int(score["debt_pct"])
gold = int(score["gold_pct"])
dur  = score["duration_signal"]
gsig = score["gold_signal"]

st.markdown("<div class='section-title'>Suggested Allocation</div>", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"""
    <div class='alloc-tile'>
        <div class='alloc-label'>Equity</div>
        <div class='alloc-pct' style='color:#22c55e'>{eq}%</div>
        <div class='alloc-sub'>B: {eb}%<br>C: {ec}%</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class='alloc-tile'>
        <div class='alloc-label'>Debt</div>
        <div class='alloc-pct' style='color:#38bdf8'>{debt}%</div>
        <div class='alloc-sub'>{dur}</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class='alloc-tile'>
        <div class='alloc-label'>Gold</div>
        <div class='alloc-pct' style='color:#fbbf24'>{gold}%</div>
        <div class='alloc-sub'>{gsig}</div>
    </div>""", unsafe_allow_html=True)

# Safety badges
red_flag  = score["red_flag"]
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
# SECTION: COMPONENT BREAKDOWN
# ============================================================
st.markdown("<div class='section-title'>Component Breakdown</div>", unsafe_allow_html=True)

components = [
    ("Valuation",  int(score["score_valuation"]),  15),
    ("Trend",      int(score["score_trend"]),      15),
    ("Breadth",    int(score["score_breadth"]),    12),
    ("Volatility", int(score["score_volatility"]), 10),
    ("Flows",      int(score["score_flows"]),      12),
    ("Macro",      int(score["score_macro"]),      12),
    ("Global",     int(score["score_global"]),     12),
    ("Crude",      int(score["score_crude"]),      12),
]

rows_html = ""
for label, val, mx in components:
    pct = val / mx if mx > 0 else 0
    bar_w = int(pct * 100)
    color = bar_color(pct)
    rows_html = ""
for label, val, mx in components:
    pct = val / mx if mx > 0 else 0
    bar_w = int(pct * 100)
    color = bar_color(pct)
    rows_html += (
        f"<div class='comp-row'>"
        f"<div class='comp-label'>{label}</div>"
        f"<div class='comp-bar-wrap'>"
        f"<div class='comp-bar' style='width:{bar_w}%; background:{color}'></div>"
        f"</div>"
        f"<div class='comp-score' style='color:{color}'>{val} / {mx}</div>"
        f"</div>"
    )

st.markdown(f"<div class='data-card'>{rows_html}</div>", unsafe_allow_html=True)

# ============================================================
# SECTION: INDIAN MARKETS (live)
# ============================================================
st.markdown("<div class='section-title'>Indian Markets (Live)</div>", unsafe_allow_html=True)

indian_rows = [
    ("Nifty 50",         live.get("Nifty 50")),
    ("India VIX",        live.get("India VIX")),
    ("Nifty 500",        live.get("Nifty 500")),
    ("Nifty Midcap 100", live.get("Nifty Midcap 100")),
    ("Nifty Midcap 50",  live.get("Nifty Midcap 50")),
]

ind_html = ""
for label, val in indian_rows:
    ind_html += f"""
    <div class='data-row'>
        <div class='data-label'>{label}</div>
        <div class='data-value'>{fmt_num(val)}</div>
    </div>"""

st.markdown(f"<div class='data-card'>{ind_html}</div>", unsafe_allow_html=True)

# ============================================================
# SECTION: GLOBAL (live)
# ============================================================
st.markdown("<div class='section-title'>Global (Live)</div>", unsafe_allow_html=True)

# Pull directions from score for visual badges
us10y_dir_emoji = ""  # we don't store directions in score CSV; could be added later
inr_weak = score.get("dma_direction")  # placeholder - not used here

global_rows = [
    ("US 10Y Yield",  glob.get("US 10Y Yield"), "%"),
    ("DXY",           glob.get("DXY"),          ""),
    ("Global VIX",    glob.get("Global VIX"),   ""),
    ("INR/USD",       glob.get("INR/USD"),      ""),
    ("Brent Crude",   glob.get("Brent Crude"),  " USD"),
]

glb_html = ""
for label, val, suffix in global_rows:
    val_str = fmt_num(val) + suffix if val is not None else "—"
    glb_html += f"""
    <div class='data-row'>
        <div class='data-label'>{label}</div>
        <div class='data-value'>{val_str}</div>
    </div>"""

st.markdown(f"<div class='data-card'>{glb_html}</div>", unsafe_allow_html=True)

# ============================================================
# SECTION: MANUAL INPUTS
# ============================================================
st.markdown("<div class='section-title'>Manual Inputs</div>", unsafe_allow_html=True)

manual_rows = [
    ("Nifty PE",       fmt_num(manual.get("nifty_pe"), 1)),
    ("FII (30-day)",   fmt_signed(manual.get("fii_30day_net_cr")) + " Cr"),
    ("DII (30-day)",   fmt_signed(manual.get("dii_30day_net_cr")) + " Cr"),
    ("Breadth",        fmt_num(manual.get("breadth_pct_above_200dma"), 1) + "%"),
    ("RBI Stance",     str(manual.get("rbi_stance", "—"))),
    ("CPI",            fmt_num(manual.get("cpi_pct"), 1) + "%"),
    ("PMI Mfg",        fmt_num(manual.get("pmi_manufacturing"), 1)),
    ("Yield Inverted", str(manual.get("yield_curve_inverted", "—"))),
]

man_html = ""
for label, val in manual_rows:
    man_html += f"""
    <div class='data-row'>
        <div class='data-label'>{label}</div>
        <div class='data-value'>{val}</div>
    </div>"""

st.markdown(f"<div class='data-card'>{man_html}</div>", unsafe_allow_html=True)

# Hint about updating
st.markdown("""
<div style='text-align:center; margin-top:8px; color:#64748b; font-size:11px'>
    💡 Tap-to-update form coming in next release (8.4)
</div>
""", unsafe_allow_html=True)

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
<div style='text-align:center; margin-top:24px; color:#64748b; font-size:11px'>
    Engine A v1.2 · Sunday-only scoring · 2-week smoothing
</div>
""", unsafe_allow_html=True)
