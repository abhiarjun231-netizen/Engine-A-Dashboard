"""
engine_b_ui.py - Engine B & C display logic
Reads live prices from engine_b_prices.csv
"""

import streamlit as st
import pandas as pd
from pathlib import Path

# ============================================================
# DATA
# ============================================================
SCORE_FILE = Path("data/engine_a_score.csv")
PRICES_FILE = Path("data/engine_b_prices.csv")

def load_engine_a_score():
    if not SCORE_FILE.exists(): return None
    df = pd.read_csv(SCORE_FILE)
    return None if df.empty else df.iloc[-1].to_dict()

def load_stock_prices():
    if not PRICES_FILE.exists(): return {}
    df = pd.read_csv(PRICES_FILE)
    prices = {}
    for _, row in df.iterrows():
        prices[row["stock"]] = {
            "price": row.get("price", ""),
            "status": row.get("status", ""),
            "entry": row.get("entry", ""),
            "qty": row.get("qty", ""),
            "timestamp": row.get("timestamp", ""),
        }
    return prices

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
# POSITION CARD
# ============================================================
def render_position(stock_name, entry, qty, stop, current_price):
    has_price = current_price is not None and current_price != ""
    
    if has_price:
        current = float(current_price)
        pct_change = round((current - entry) / entry * 100, 2)
        pnl = round((current - entry) * qty, 2)
        stage_label, stage_color = get_stage(pct_change)
        pct_str = f"{'+' if pct_change >= 0 else ''}{pct_change}%"
        pct_color = "#22c55e" if pct_change >= 0 else "#ef4444"
        price_str = f"₹{current:,.2f}"
        pnl_sign = "+" if pnl >= 0 else ""
        pnl_color = "#22c55e" if pnl >= 0 else "#ef4444"
        pnl_str = f"{pnl_sign}₹{pnl:,.0f}"
    else:
        stage_label, stage_color = "AWAITING", "#64748b"
        pct_str = ""
        pct_color = "#64748b"
        price_str = "awaiting"
        pnl_str = "awaiting"
        pnl_color = "#64748b"

    card_html = (
        f"<div style='background:#1e293b;border-radius:12px;padding:14px 16px;"
        f"border:1px solid #334155;margin-bottom:8px;'>"
        # Row 1: stock name + stage
        f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
        f"<div style='font-size:14px;font-weight:600;color:#e2e8f0;'>{stock_name}</div>"
        f"<div style='font-size:12px;font-weight:700;color:{stage_color};'>{stage_label}</div>"
        f"</div>"
        # Row 2: current price + change
        f"<div style='display:flex;justify-content:space-between;margin-top:6px;font-size:13px;'>"
        f"<div style='color:#94a3b8;'>Now: <span style='color:#e2e8f0;font-family:Courier New,monospace;font-weight:600;'>{price_str}</span></div>"
        f"<div style='font-family:Courier New,monospace;font-weight:700;color:{pct_color};'>{pct_str}</div>"
        f"</div>"
        # Row 3: entry, qty, stop
        f"<div style='display:flex;justify-content:space-between;margin-top:6px;font-size:12px;'>"
        f"<div style='color:#94a3b8;'>Entry: <span style='color:#e2e8f0;font-family:Courier New,monospace;'>₹{entry:,.0f}</span></div>"
        f"<div style='color:#94a3b8;'>Qty: <span style='color:#e2e8f0;font-family:Courier New,monospace;'>{qty}</span></div>"
        f"<div style='color:#94a3b8;'>Stop: <span style='color:#ef4444;font-family:Courier New,monospace;'>₹{stop:,.0f}</span></div>"
        f"</div>"
        # Row 4: invested + P&L
        f"<div style='display:flex;justify-content:space-between;margin-top:6px;font-size:12px;'>"
        f"<div style='color:#94a3b8;'>Invested: <span style='color:#e2e8f0;font-family:Courier New,monospace;'>₹{entry * qty:,.0f}</span></div>"
        f"<div style='color:#94a3b8;'>P&L: <span style='color:{pnl_color};font-family:Courier New,monospace;font-weight:600;'>{pnl_str}</span></div>"
        f"</div>"
        f"</div>"
    )
    st.markdown(card_html, unsafe_allow_html=True)

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

    # --- LOAD LIVE PRICES ---
    live_prices = load_stock_prices()

    # --- ENGINE B POSITIONS ---
    st.markdown("<div class='section-title'>Engine B — Active Positions (Paper)</div>", unsafe_allow_html=True)

    engine_b_stocks = [
        {"stock": "Hindustan Zinc", "qty": 8, "entry": 559.00, "stop_pct": 7},
        {"stock": "Indus Towers", "qty": 11, "entry": 441.00, "stop_pct": 7},
        {"stock": "National Aluminium", "qty": 12, "entry": 400.00, "stop_pct": 7},
        {"stock": "Engineers India", "qty": 24, "entry": 206.00, "stop_pct": 7},
        {"stock": "Torrent Power", "qty": 3, "entry": 1448.00, "stop_pct": 7},
    ]

    total_invested = 0
    total_current = 0
    total_pnl = 0
    all_have_prices = True

    for p in engine_b_stocks:
        entry = p["entry"]
        qty = p["qty"]
        stop = round(entry * (1 - p["stop_pct"] / 100), 2)
        invested = entry * qty
        total_invested += invested

        live = live_prices.get(p["stock"], {})
        current_price = live.get("price", "")

        if current_price != "" and current_price is not None:
            try:
                cp = float(current_price)
                total_current += cp * qty
                total_pnl += (cp - entry) * qty
            except:
                all_have_prices = False
        else:
            all_have_prices = False

        render_position(p["stock"], entry, qty, stop, current_price)

    # --- PORTFOLIO SUMMARY ---
    if all_have_prices:
        pnl_color = "#22c55e" if total_pnl >= 0 else "#ef4444"
        pnl_sign = "+" if total_pnl >= 0 else ""
        pnl_pct = round(total_pnl / total_invested * 100, 2)
        summary_value = f"₹{total_current:,.0f}"
        summary_detail = f"Invested: ₹{total_invested:,.0f} · P&L: <span style='color:{pnl_color};font-weight:700;'>{pnl_sign}₹{total_pnl:,.0f} ({pnl_sign}{pnl_pct}%)</span>"
    else:
        summary_value = f"₹{total_invested:,.0f}"
        summary_detail = "5 positions · Live prices pending (next market day)"

    summary_html = (
        f"<div style='background:#0f172a;border-radius:12px;padding:14px 16px;"
        f"border:1px solid #334155;margin-top:12px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
        f"<div style='font-size:13px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;'>Engine B Total</div>"
        f"<div style='font-size:18px;font-weight:700;color:#e2e8f0;font-family:Courier New,monospace;'>{summary_value}</div>"
        f"</div>"
        f"<div style='font-size:11px;color:#64748b;margin-top:4px;'>{summary_detail}</div>"
        f"</div>"
    )
    st.markdown(summary_html, unsafe_allow_html=True)

    # --- LAST UPDATED ---
    if live_prices:
        first_stock = list(live_prices.values())[0]
        ts = first_stock.get("timestamp", "")
        if ts:
            st.markdown(f"<div style='text-align:center;font-size:10px;color:#475569;margin-top:8px;'>Prices last fetched: {ts}</div>", unsafe_allow_html=True)

    # --- ENGINE C PLACEHOLDER ---
    st.markdown("<div class='section-title'>Engine C — Long-Term Compounders</div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='background:#1e293b;border-radius:12px;padding:20px 16px;"
        "border:1px solid #334155;text-align:center;color:#64748b;font-size:13px;'>"
        "Engine C positions will appear here once deployed"
        "</div>",
        unsafe_allow_html=True
    )
