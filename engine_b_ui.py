"""
engine_b_ui.py - Engine B display logic
Phase 1: Upload B1+B2 CSVs, parse, deduplicate, flag Double Qualifiers
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
    if pct_change <= -5:
        return "WATCHING", "#f59e0b"
    if pct_change >= 15:
        return "TRAILING", "#38bdf8"
    return "RUNNING", "#22c55e"

# ============================================================
# FLEXIBLE COLUMN FINDER
# ============================================================
def find_column(df, candidates):
    """Find a column by trying multiple name variants."""
    # Normalize df columns: strip whitespace
    col_map = {c.strip(): c for c in df.columns}
    for candidate in candidates:
        candidate_clean = candidate.strip()
        if candidate_clean in col_map:
            return col_map[candidate_clean]
        # Try case-insensitive
        for col_clean, col_orig in col_map.items():
            if col_clean.lower() == candidate_clean.lower():
                return col_orig
    return None

# ============================================================
# CSV/EXCEL PARSER
# ============================================================
def parse_trendlyne_file(uploaded_file):
    """Parse Trendlyne export — handles CSV and Excel."""
    try:
        fname = uploaded_file.name.lower()
        if fname.endswith(".xlsx") or fname.endswith(".xls"):
            df = pd.read_excel(uploaded_file)
        else:
            df = pd.read_csv(uploaded_file)

        # Flexible column matching
        col_stock = find_column(df, ["Stock"])
        col_ticker = find_column(df, ["NSE Code"])
        col_ltp = find_column(df, ["LTP"])
        col_roe = find_column(df, ["ROE Ann  %", "ROE Ann %", "ROE Annual %"])
        col_pe = find_column(df, ["PE TTM", "PE TTM Price to Earnings"])
        col_pio = find_column(df, ["Piotroski Score"])
        col_mcap = find_column(df, ["Market Cap"])

        if not col_stock or not col_ticker:
            st.error("Could not find 'Stock' or 'NSE Code' columns in file.")
            return []

        stocks = []
        for _, row in df.iterrows():
            stocks.append({
                "stock": str(row.get(col_stock, "")).strip(),
                "ticker": str(row.get(col_ticker, "")).strip(),
                "ltp": float(row.get(col_ltp, 0)) if col_ltp else 0,
                "roe": float(row.get(col_roe, 0)) if col_roe else 0,
                "pe": float(row.get(col_pe, 0)) if col_pe else 0,
                "piotroski": int(float(row.get(col_pio, 0))) if col_pio else 0,
                "mcap": float(row.get(col_mcap, 0)) if col_mcap else 0,
            })
        return stocks
    except Exception as e:
        st.error(f"File parse error: {e}")
        return []

def combine_screeners(b1_stocks, b2_stocks):
    combined = {}
    for s in b1_stocks:
        key = s["ticker"]
        combined[key] = {**s, "source": "B1"}
    for s in b2_stocks:
        key = s["ticker"]
        if key in combined:
            combined[key]["source"] = "Double"
        else:
            combined[key] = {**s, "source": "B2"}
    return list(combined.values())

# ============================================================
# POSITION CARD (existing holdings)
# ============================================================
def render_position(stock_name, entry, qty, stop, peak, current_price):
    has_price = current_price is not None and current_price != ""
    if has_price:
        current = float(current_price)
        if peak and float(peak) > current:
            trail_stop = round(float(peak) * 0.93, 2)
        else:
            trail_stop = stop
        actual_stop = max(stop, trail_stop)
        pct_change = round((current - entry) / entry * 100, 2)
        pnl = round((current - entry) * qty, 2)
        stage_label, stage_color = get_stage(pct_change)
        pct_str = f"{'+' if pct_change >= 0 else ''}{pct_change}%"
        pct_color = "#22c55e" if pct_change >= 0 else "#ef4444"
        price_str = f"₹{current:,.2f}"
        pnl_sign = "+" if pnl >= 0 else ""
        pnl_color = "#22c55e" if pnl >= 0 else "#ef4444"
        pnl_str = f"{pnl_sign}₹{pnl:,.0f}"
        stop_display = f"₹{actual_stop:,.0f}"
    else:
        stage_label, stage_color = "AWAITING", "#64748b"
        pct_str = ""
        pct_color = "#64748b"
        price_str = "awaiting"
        pnl_str = "awaiting"
        pnl_color = "#64748b"
        stop_display = f"₹{stop:,.0f}"
        actual_stop = stop

    card_html = (
        f"<div style='background:#1e293b;border-radius:12px;padding:14px 16px;"
        f"border:1px solid #334155;margin-bottom:8px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
        f"<div style='font-size:14px;font-weight:600;color:#e2e8f0;'>{stock_name}</div>"
        f"<div style='font-size:12px;font-weight:700;color:{stage_color};'>{stage_label}</div>"
        f"</div>"
        f"<div style='display:flex;justify-content:space-between;margin-top:6px;font-size:13px;'>"
        f"<div style='color:#94a3b8;'>Now: <span style='color:#e2e8f0;font-family:Courier New,monospace;font-weight:600;'>{price_str}</span></div>"
        f"<div style='font-family:Courier New,monospace;font-weight:700;color:{pct_color};'>{pct_str}</div>"
        f"</div>"
        f"<div style='display:flex;justify-content:space-between;margin-top:6px;font-size:12px;'>"
        f"<div style='color:#94a3b8;'>Entry: <span style='color:#e2e8f0;font-family:Courier New,monospace;'>₹{entry:,.0f}</span></div>"
        f"<div style='color:#94a3b8;'>Qty: <span style='color:#e2e8f0;font-family:Courier New,monospace;'>{qty}</span></div>"
        f"<div style='color:#94a3b8;'>Stop: <span style='color:#ef4444;font-family:Courier New,monospace;'>{stop_display}</span></div>"
        f"</div>"
        f"<div style='display:flex;justify-content:space-between;margin-top:6px;font-size:12px;'>"
        f"<div style='color:#94a3b8;'>Invested: <span style='color:#e2e8f0;font-family:Courier New,monospace;'>₹{entry * qty:,.0f}</span></div>"
        f"<div style='color:#94a3b8;'>P&L: <span style='color:{pnl_color};font-family:Courier New,monospace;font-weight:600;'>{pnl_str}</span></div>"
        f"</div>"
        f"</div>"
    )
    st.markdown(card_html, unsafe_allow_html=True)

# ============================================================
# QUALIFIER CARD (from screener upload)
# ============================================================
def render_qualifier(stock, source_label, source_color, is_holding):
    status_label = "HOLDING" if is_holding else "NEW"
    status_color = "#38bdf8" if is_holding else "#22c55e"

    card_html = (
        f"<div style='background:#1e293b;border-radius:12px;padding:12px 16px;"
        f"border:1px solid #334155;margin-bottom:6px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
        f"<div style='font-size:14px;font-weight:600;color:#e2e8f0;'>{stock['stock']}</div>"
        f"<div style='display:flex;gap:8px;'>"
        f"<span style='font-size:10px;font-weight:700;color:{source_color};background:{source_color}22;padding:2px 6px;border-radius:4px;'>{source_label}</span>"
        f"<span style='font-size:10px;font-weight:700;color:{status_color};background:{status_color}22;padding:2px 6px;border-radius:4px;'>{status_label}</span>"
        f"</div>"
        f"</div>"
        f"<div style='display:flex;justify-content:space-between;margin-top:6px;font-size:12px;'>"
        f"<div style='color:#94a3b8;'>LTP: <span style='color:#e2e8f0;font-family:Courier New,monospace;'>₹{stock['ltp']:,.2f}</span></div>"
        f"<div style='color:#94a3b8;'>ROE: <span style='color:#e2e8f0;font-family:Courier New,monospace;'>{stock['roe']:.1f}%</span></div>"
        f"<div style='color:#94a3b8;'>PE: <span style='color:#e2e8f0;font-family:Courier New,monospace;'>{stock['pe']:.1f}</span></div>"
        f"<div style='color:#94a3b8;'>Pio: <span style='color:#e2e8f0;font-family:Courier New,monospace;'>{stock['piotroski']}</span></div>"
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

    # --- ACTIVE POSITIONS ---
    st.markdown("<div class='section-title'>Engine B — Active Positions</div>", unsafe_allow_html=True)

    # Read from JSON (single source of truth)
    import json
    positions_file = Path("data/engine_b_stocks.json")
    if positions_file.exists():
        with open(positions_file, "r") as f:
            stock_data = json.load(f)
        positions = stock_data.get("engine_b", [])
    else:
        positions = []

    if not positions:
        st.markdown(
            "<div style='background:#1e293b;border-radius:12px;padding:20px 16px;"
            "border:1px solid #334155;text-align:center;color:#64748b;font-size:13px;'>"
            "No active positions. Upload screener CSVs below to find stocks."
            "</div>",
            unsafe_allow_html=True
        )
    else:
        total_invested = 0
        total_current = 0
        total_pnl = 0
        all_have_prices = True

        for p in positions:
            entry = p.get("entry", 0)
            qty = p.get("qty", 0)
            stop = round(entry * 0.93, 2)
            peak = p.get("peak", entry)
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

            render_position(p["stock"], entry, qty, stop, peak, current_price)

        # Portfolio summary
        if all_have_prices:
            pnl_color = "#22c55e" if total_pnl >= 0 else "#ef4444"
            pnl_sign = "+" if total_pnl >= 0 else ""
            pnl_pct = round(total_pnl / total_invested * 100, 2) if total_invested > 0 else 0
            summary_value = f"₹{total_current:,.0f}"
            summary_detail = f"Invested: ₹{total_invested:,.0f} · P&L: <span style='color:{pnl_color};font-weight:700;'>{pnl_sign}₹{total_pnl:,.0f} ({pnl_sign}{pnl_pct}%)</span>"
        else:
            summary_value = f"₹{total_invested:,.0f}"
            summary_detail = f"{len(positions)} positions · Live prices pending"

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

    # --- SCREENER UPLOAD ---
    st.markdown("<div class='section-title'>Upload Screener Results</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        b1_files = st.file_uploader(
            "B1 CSVs (4-filter)",
            type=None,
            accept_multiple_files=True,
            key="b1_upload"
        )
    with col2:
        b2_files = st.file_uploader(
            "B2 CSVs (6-filter)",
            type=None,
            accept_multiple_files=True,
            key="b2_upload"
        )

    if b1_files or b2_files:
        b1_stocks = []
        b2_stocks = []
        for f in (b1_files or []):
            b1_stocks.extend(parse_trendlyne_file(f))
        for f in (b2_files or []):
            b2_stocks.extend(parse_trendlyne_file(f))

        combined = combine_screeners(b1_stocks, b2_stocks)

        if combined:
            # Count stats
            double_count = sum(1 for s in combined if s["source"] == "Double")
            b1_only = sum(1 for s in combined if s["source"] == "B1")
            b2_only = sum(1 for s in combined if s["source"] == "B2")
            holding_tickers = [p.get("ticker", "") for p in positions]

            stats_html = (
                f"<div style='background:#0f172a;border-radius:12px;padding:14px 16px;"
                f"border:1px solid #334155;margin-bottom:12px;'>"
                f"<div style='font-size:13px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;'>Screener Results</div>"
                f"<div style='display:flex;justify-content:space-between;font-size:13px;'>"
                f"<div style='color:#e2e8f0;'>Total: <span style='font-weight:700;'>{len(combined)}</span></div>"
                f"<div style='color:#fbbf24;'>Double: <span style='font-weight:700;'>{double_count}</span></div>"
                f"<div style='color:#22c55e;'>B1: <span style='font-weight:700;'>{b1_only}</span></div>"
                f"<div style='color:#38bdf8;'>B2: <span style='font-weight:700;'>{b2_only}</span></div>"
                f"</div>"
                f"</div>"
            )
            st.markdown(stats_html, unsafe_allow_html=True)

            # Sort: Double first, then B1, then B2
            sort_order = {"Double": 0, "B1": 1, "B2": 2}
            combined.sort(key=lambda x: sort_order.get(x["source"], 3))

            for stock in combined:
                source = stock["source"]
                if source == "Double":
                    source_label = "DOUBLE"
                    source_color = "#fbbf24"
                elif source == "B1":
                    source_label = "B1"
                    source_color = "#22c55e"
                else:
                    source_label = "B2"
                    source_color = "#38bdf8"
                is_holding = stock["ticker"] in holding_tickers
                render_qualifier(stock, source_label, source_color, is_holding)

    # --- ENGINE C PLACEHOLDER ---
    st.markdown("<div class='section-title'>Engine C — Long-Term Compounders</div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='background:#1e293b;border-radius:12px;padding:20px 16px;"
        "border:1px solid #334155;text-align:center;color:#64748b;font-size:13px;'>"
        "Engine C will have its own tab — coming next"
        "</div>",
        unsafe_allow_html=True
                            )
