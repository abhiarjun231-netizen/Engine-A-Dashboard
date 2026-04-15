"""
App.py - Engine A Dashboard v3 (8.1 + 8.2 + 8.3 + 8.4)
Hero + allocation + live data + breakdown + INPUT FORM with save-back to GitHub.
"""

import streamlit as st
import pandas as pd
import json
import base64
import requests
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
# GITHUB CONFIG (for save-back functionality)
# ============================================================
GITHUB_OWNER = "abhiarjun231-netizen"
GITHUB_REPO = "Engine-A-Dashboard"
GITHUB_BRANCH = "main"
MANUAL_FILE_PATH = "manual_inputs.json"
WORKFLOW_FILE = "test.yml"

def get_github_token():
    """Fetch GitHub PAT from Streamlit secrets."""
    try:
        return st.secrets["GITHUB_TOKEN"]
    except Exception:
        return None

# ============================================================
# STYLES
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

    .input-card-label {
        font-size: 13px; font-weight: 600; color: #e2e8f0; margin-top: 8px;
    }
    .input-card-current { font-size: 11px; color: #94a3b8; margin-bottom: 4px; }

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

def load_manual_full():
    """Load full manual_inputs.json including metadata fields."""
    if not MANUAL_FILE.exists(): return {}
    with open(MANUAL_FILE, "r") as f:
        return json.load(f)

manual_full = load_manual_full()
score  = load_latest_score()
live   = load_live()
glob   = load_global()
manual = {k: v.get("value") for k, v in manual_full.items() if not k.startswith("_")}

if score is None:
    st.error("⚠️ No score data yet. Trigger the workflow to generate the first score.")
    st.stop()

# ============================================================
# HELPERS
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
    if pct < 0.30: return "#ef4444"
    if pct < 0.55: return "#f59e0b"
    if pct < 0.75: return "#38bdf8"
    return "#22c55e"

def fmt_num(n, decimals=2):
    if n is None or pd.isna(n): return "—"
    try: return f"{float(n):,.{decimals}f}"
    except: return str(n)

def fmt_signed(n):
    if n is None or pd.isna(n): return "—"
    try:
        v = int(n); sign = "+" if v >= 0 else ""
        return f"{sign}{v:,}"
    except: return str(n)

# ============================================================
# HEADER
# ============================================================
st.markdown("<div class='score-title'>Engine A — Market Strength</div>", unsafe_allow_html=True)

# HERO
sc = score["raw_score"]; cond = score["market_condition"]; ts = score["timestamp"]
try:
    ts_pretty = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y, %I:%M %p")
except: ts_pretty = ts

st.markdown(f"""
<div class='score-card'>
    <div class='score-title'>Current Score</div>
    <div class='score-number' style='color:{score_color(sc)}'>{sc}</div>
    <div class='score-denominator'>/ 100</div>
    <div class='score-condition' style='color:{condition_color(cond)}'>{cond}</div>
    <div class='score-timestamp'>Last updated: {ts_pretty}</div>
</div>
""", unsafe_allow_html=True)

# ALLOCATION
eq = int(score["equity_pct"]); eb = int(score["engine_b_pct"]); ec = int(score["engine_c_pct"])
debt = int(score["debt_pct"]); gold = int(score["gold_pct"])
dur = score["duration_signal"]; gsig = score["gold_signal"]

st.markdown("<div class='section-title'>Suggested Allocation</div>", unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"<div class='alloc-tile'><div class='alloc-label'>Equity</div><div class='alloc-pct' style='color:#22c55e'>{eq}%</div><div class='alloc-sub'>B: {eb}%<br>C: {ec}%</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='alloc-tile'><div class='alloc-label'>Debt</div><div class='alloc-pct' style='color:#38bdf8'>{debt}%</div><div class='alloc-sub'>{dur}</div></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='alloc-tile'><div class='alloc-label'>Gold</div><div class='alloc-pct' style='color:#fbbf24'>{gold}%</div><div class='alloc-sub'>{gsig}</div></div>", unsafe_allow_html=True)

# SAFETY
red_flag = score["red_flag"]; pe_bubble = score["pe_bubble"]
rf_color = "bad" if red_flag == "YES" else "ok"
pe_color = "bad" if pe_bubble == "YES" else "ok"
st.markdown(f"<div class='safety-row'><div class='safety-badge'><div class='label'>Red Flag</div><div class='value {rf_color}'>{red_flag}</div></div><div class='safety-badge'><div class='label'>PE Bubble</div><div class='value {pe_color}'>{pe_bubble}</div></div></div>", unsafe_allow_html=True)

# COMPONENT BREAKDOWN
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
    rows_html += (
        f"<div class='data-row'>"
        f"<div style='flex:0 0 90px;color:#cbd5e1;'>{label}</div>"
        f"<div style='flex:1;height:10px;background:#0f172a;border-radius:6px;overflow:hidden;margin:0 10px;'>"
        f"<div style='height:100%;width:{bar_w}%;background:{color};border-radius:6px;'></div></div>"
        f"<div style='flex:0 0 60px;text-align:right;font-family:Courier New,monospace;font-weight:700;color:{color}'>{val} / {mx}</div>"
        f"</div>"
    )
st.markdown(f"<div class='data-card'>{rows_html}</div>", unsafe_allow_html=True)

# INDIAN MARKETS
st.markdown("<div class='section-title'>Indian Markets (Live)</div>", unsafe_allow_html=True)
indian_rows = [
    ("Nifty 50", live.get("Nifty 50")),
    ("India VIX", live.get("India VIX")),
    ("Nifty 500", live.get("Nifty 500")),
    ("Nifty Midcap 100", live.get("Nifty Midcap 100")),
    ("Nifty Midcap 50", live.get("Nifty Midcap 50")),
]
ind_html = ""
for label, val in indian_rows:
    ind_html += f"<div class='data-row'><div class='data-label'>{label}</div><div class='data-value'>{fmt_num(val)}</div></div>"
st.markdown(f"<div class='data-card'>{ind_html}</div>", unsafe_allow_html=True)

# GLOBAL
st.markdown("<div class='section-title'>Global (Live)</div>", unsafe_allow_html=True)
global_rows = [
    ("US 10Y Yield", glob.get("US 10Y Yield"), "%"),
    ("DXY", glob.get("DXY"), ""),
    ("Global VIX", glob.get("Global VIX"), ""),
    ("INR/USD", glob.get("INR/USD"), ""),
    ("Brent Crude", glob.get("Brent Crude"), " USD"),
]
glb_html = ""
for label, val, suffix in global_rows:
    val_str = fmt_num(val) + suffix if val is not None else "—"
    glb_html += f"<div class='data-row'><div class='data-label'>{label}</div><div class='data-value'>{val_str}</div></div>"
st.markdown(f"<div class='data-card'>{glb_html}</div>", unsafe_allow_html=True)

# MANUAL INPUTS (display)
st.markdown("<div class='section-title'>Manual Inputs (Current)</div>", unsafe_allow_html=True)
manual_rows = [
    ("Nifty PE", fmt_num(manual.get("nifty_pe"), 1)),
    ("FII (30-day)", fmt_signed(manual.get("fii_30day_net_cr")) + " Cr"),
    ("DII (30-day)", fmt_signed(manual.get("dii_30day_net_cr")) + " Cr"),
    ("Breadth", fmt_num(manual.get("breadth_pct_above_200dma"), 1) + "%"),
    ("RBI Stance", str(manual.get("rbi_stance", "—"))),
    ("CPI", fmt_num(manual.get("cpi_pct"), 1) + "%"),
    ("PMI Mfg", fmt_num(manual.get("pmi_manufacturing"), 1)),
    ("Yield Inverted", str(manual.get("yield_curve_inverted", "—"))),
]
man_html = ""
for label, val in manual_rows:
    man_html += f"<div class='data-row'><div class='data-label'>{label}</div><div class='data-value'>{val}</div></div>"
st.markdown(f"<div class='data-card'>{man_html}</div>", unsafe_allow_html=True)

# ============================================================
# 8.4 INPUT UPDATE FORM
# ============================================================
st.markdown("<div class='section-title'>📝 Update Inputs</div>", unsafe_allow_html=True)

token = get_github_token()
if not token:
    st.warning("⚠️ GITHUB_TOKEN not set in Streamlit secrets — input form will work locally but cannot save back to GitHub.")

with st.expander("Tap to expand & edit", expanded=False):
    st.caption("For each input: tap the source link, read the value, type it in, then hit Save & Rescore at the bottom.")

    new_values = {}

    # Build form fields based on manual_inputs.json structure
    input_order = [
        "nifty_pe", "fii_30day_net_cr", "dii_30day_net_cr",
        "breadth_pct_above_200dma", "yield_curve_inverted",
        "rbi_stance", "cpi_pct", "pmi_manufacturing"
    ]
    pretty_labels = {
        "nifty_pe": "Nifty PE Ratio",
        "fii_30day_net_cr": "FII 30-day Net (Cr)",
        "dii_30day_net_cr": "DII 30-day Net (Cr)",
        "breadth_pct_above_200dma": "Breadth (% above 200 DMA)",
        "yield_curve_inverted": "Yield Curve Inverted?",
        "rbi_stance": "RBI Stance",
        "cpi_pct": "CPI %",
        "pmi_manufacturing": "PMI Manufacturing",
    }

    for key in input_order:
        obj = manual_full.get(key, {})
        if not obj:
            continue
        label = pretty_labels.get(key, key)
        cur_val = obj.get("value")
        url = obj.get("where_to_find", "")
        source_label = obj.get("source_label", "Source")
        input_type = obj.get("input_type", "number")

        st.markdown(f"<div class='input-card-label'>{label}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='input-card-current'>Current: <b>{cur_val}</b></div>", unsafe_allow_html=True)
        if url:
            st.markdown(f"[🔗 Open in {source_label}]({url})")

        if input_type == "dropdown":
            options = obj.get("options", [])
            try:
                default_idx = options.index(cur_val) if cur_val in options else 0
            except Exception:
                default_idx = 0
            new_values[key] = st.selectbox(
                f"New value for {label}",
                options=options,
                index=default_idx,
                key=f"input_{key}",
                label_visibility="collapsed",
            )
        else:
            try:
                cur_float = float(cur_val) if cur_val is not None else 0.0
            except (ValueError, TypeError):
                cur_float = 0.0
            new_values[key] = st.number_input(
                f"New value for {label}",
                value=cur_float,
                key=f"input_{key}",
                label_visibility="collapsed",
                format="%.2f",
            )

        st.markdown("<div style='margin-bottom:12px'></div>", unsafe_allow_html=True)

    st.markdown("---")

    if st.button("💾 Save & Rescore", type="primary", use_container_width=True):
        if not token:
            st.error("Cannot save: GITHUB_TOKEN not configured in Streamlit secrets.")
        else:
            with st.spinner("Saving values to GitHub..."):
                # Build updated JSON
                updated = json.loads(json.dumps(manual_full))  # deep copy
                for key, val in new_values.items():
                    if key in updated:
                        # Convert to int for fields stored as int
                        if key in ("fii_30day_net_cr", "dii_30day_net_cr"):
                            try: val = int(val)
                            except: pass
                        updated[key]["value"] = val
                updated["_last_updated"] = datetime.now().strftime("%Y-%m-%d")

                new_content = json.dumps(updated, indent=2, ensure_ascii=False)

                # GitHub API: get current SHA of file
                api_base = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{MANUAL_FILE_PATH}"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                }
                try:
                    get_resp = requests.get(api_base, headers=headers, params={"ref": GITHUB_BRANCH}, timeout=15)
                    if get_resp.status_code != 200:
                        st.error(f"GitHub GET failed: {get_resp.status_code} {get_resp.text[:200]}")
                        st.stop()
                    cur_sha = get_resp.json().get("sha")

                    # PUT new content
                    put_body = {
                        "message": f"Dashboard update: manual inputs ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
                        "content": base64.b64encode(new_content.encode("utf-8")).decode("ascii"),
                        "sha": cur_sha,
                        "branch": GITHUB_BRANCH,
                    }
                    put_resp = requests.put(api_base, headers=headers, json=put_body, timeout=15)
                    if put_resp.status_code in (200, 201):
                        st.success("✅ Saved to GitHub! Triggering rescore...")
                    else:
                        st.error(f"GitHub PUT failed: {put_resp.status_code} {put_resp.text[:200]}")
                        st.stop()

                    # Trigger workflow
                    wf_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches"
                    wf_body = {"ref": GITHUB_BRANCH}
                    wf_resp = requests.post(wf_url, headers=headers, json=wf_body, timeout=15)
                    if wf_resp.status_code == 204:
                        st.success("✅ Rescore triggered! New score will appear in ~45 sec. Refresh the page after.")
                        st.balloons()
                    else:
                        st.warning(f"Save succeeded but workflow trigger failed ({wf_resp.status_code}). You can manually trigger via Actions tab.")

                except requests.RequestException as e:
                    st.error(f"Network error: {e}")

# FOOTER
st.markdown("<div style='text-align:center; margin-top:24px; color:#64748b; font-size:11px'>Engine A v1.4 · Sunday-only scoring · 2-week smoothing</div>", unsafe_allow_html=True)
