"""
engine_b_ui.py - Engine B & C display logic
Called by App.py via show_engine_b()
"""

import streamlit as st
import pandas as pd
from pathlib import Path

# ============================================================
# DATA
# ============================================================
SCORE_FILE = Path("data/engine_a_score.csv")

def load_engine_a_score():
    if not SCORE_FILE.exists(): return None
    df = pd.read_csv(SCORE_FILE)
    return None if df.empty else df.iloc[-1].to_dict()

# ============================================================
# ENGINE B POSITIONS (paper portfolio)
# ============================================================
ENGINE_B_POSITIONS = [
    {"stock": "Hindustan Zinc", "qty": 8, "entry": 559.00, "stop_pct": 7},
    {"stock": "Indus Towers", "qty": 11, "entry": 441.00, "stop_pct": 7},
    {"stock": "National Aluminium", "qty": 12, "entry": 400.00, "stop_pct": 7},
    {"stock": "Engineers India", "qty": 24, "entry": 206.00, "stop_pct": 7},
    {"stock": "Torrent Power", "qty": 3, "entry": 1448.00, "stop_pct": 7},
]

def calculate_position(pos):
    entry = pos["entry"]
    stop = round(entry * (1 - pos["stop_pct"] / 100), 2)
    invested = round(entry * pos["qty"], 2)
    return {
        **pos,
        "stop": stop,
        "invested": invested,
    }

# ============================================================
# GATE STATUS
# ============================================================
def get_gate_status(score_val):
    if score_val is None:
        return "UNKNOWN", "#94a3b8", "No Engine A score available"
    if score_val <= 20:
        return "EXIT ALL", "#ef4444", "Engine A <= 20 — exit all equity positions"
    if score_val <= 30:
        return "FROZEN", "#f59e0b", "Engine A <= 30 — hold existing, no new entries"
    return "ACTIVE", "#22c55e", "Engine A > 30 — system is go"

# ============================================================
# STAGE INDICATOR
# ============================================================
def get_stage(pct_change):
    if pct_change <= -7:
        return "STOP HIT", "#ef4444"
    if pct_change <= -4:
        return "WATCHING", "#f59e0b"
    if pct_change >= 15:
        return "TRAILING", "#38bdf8"
    return "RUNNING", "#22c55e"

# ============================================================
# MAIN DISPLAY FUNCTION
# ============================================================
def show_engine_b():

    # --- ENGINE A GATE BANNER ---
    score_data = load_engine_a_score()
    score_val = int(score_data["raw_score"]) if score_data else None
    gate_status, gate_color, gate_msg = get_gate_status(score_val)

    gate_html = (
        f"<div style='background:#1e293b;border-radius:12px;padding:14px 16px;"
        f"border:1px solid {gate_color};margin-bottom:16px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
        f"<div style='font-size:13px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;'>Engine B Status</div>"
        f"<div style='font-size:15px;font-weight:700;color:{gate_color};'>{gate_status}</div>"
        f"</div>"
        f"<div style='font-size:11px;color:#64748b;margin-top:4px;'>{gate_msg} (Score: {score_val}/100)</div>"
        f"</div>"
    )
    st.markdown(gate_html, unsafe_allow_html=True)

    # --- ENGINE B POSITIONS ---
    st.markdown("<div class='section-title'>Engine B — Active Positions (Paper)</div>", unsafe_allow_html=True)

    positions = [calculate_position(p) for p in ENGINE_B_POSITIONS]

    total_invested = sum(p["invested"] for p in positions)

    for p in positions:
        entry = p["entry"]
        stop = p["stop"]
        stock = p["stock"]
        qty = p["qty"]
        invested = p["invested"]

        # For now, current price = entry (we'll add live prices next)
        current = entry
        pct_change = round((current - entry) / entry * 100, 2)
        stage_label, stage_color = get_stage(pct_change)

        card_html = (
            f"<div style='background:#1e293b;border-radius:12px;padding:14px 16px;"
            f"border:1px solid #334155;margin-bottom:8px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<div style='font-size:14px;font-weight:600;color:#e2e8f0;'>{stock}</div>"
            f"<div style='font-size:12px;font-weight:700;color:{stage_color};'>{stage_label}</div>"
            f"</div>"
            f"<div style='display:flex;justify-content:space-between;margin-top:8px;font-size:12px;'>"
            f"<div style='color:#94a3b8;'>Entry: <span style='color:#e2e8f0;font-family:Courier New,monospace;'>₹{entry:,.0f}</span></div>"
            f"<div style='color:#94a3b8;'>Qty: <span style='color:#e2e8f0;font-family:Courier New,monospace;'>{qty}</span></div>"
            f"<div style='color:#94a3b8;'>Stop: <span style='color:#ef4444;font-family:Courier New,monospace;'>₹{stop:,.0f}</span></div>"
            f"</div>"
            f"<div style='display:flex;justify-content:space-between;margin-top:6px;font-size:12px;'>"
            f"<div style='color:#94a3b8;'>Invested: <span style='color:#e2e8f0;font-family:Courier New,monospace;'>₹{invested:,.0f}</span></div>"
            f"<div style='color:#94a3b8;'>P&L: <span style='color:#64748b;font-family:Courier New,monospace;'>awaiting live</span></div>"
            f"</div>"
            f"</div>"
        )
        st.markdown(card_html, unsafe_allow_html=True)

    # --- PORTFOLIO SUMMARY ---
    summary_html = (
        f"<div style='background:#0f172a;border-radius:12px;padding:14px 16px;"
        f"border:1px solid #334155;margin-top:12px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
        f"<div style='font-size:13px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;'>Engine B Total</div>"
        f"<div style='font-size:18px;font-weight:700;color:#e2e8f0;font-family:Courier New,monospace;'>₹{total_invested:,.0f}</div>"
        f"</div>"
        f"<div style='font-size:11px;color:#64748b;margin-top:4px;'>5 positions · P&L awaiting live prices</div>"
        f"</div>"
    )
    st.markdown(summary_html, unsafe_allow_html=True)

    # --- ENGINE C PLACEHOLDER ---
    st.markdown("<div class='section-title'>Engine C — Long-Term Compounders</div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='background:#1e293b;border-radius:12px;padding:20px 16px;"
        "border:1px solid #334155;text-align:center;color:#64748b;font-size:13px;'>"
        "Engine C positions will appear here once deployed"
        "</div>",
        unsafe_allow_html=True
)
