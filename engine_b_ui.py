"""
engine_b_ui.py - Engine B display logic
Phase 1: Upload CSVs, parse, deduplicate, Double Qualifiers
Phase 2: Confirm Buy button — adds stock to engine_b_stocks.json via GitHub API
"""
import streamlit as st
import pandas as pd
import json
import base64
import requests
from pathlib import Path

# ============================================================
# CONSTANTS
# ============================================================
SCORE_FILE = Path("data/engine_a_score.csv")
PRICES_FILE = Path("data/engine_b_prices.csv")
STOCKS_FILE = Path("data/engine_b_stocks.json")
REPO_OWNER = "abhiarjun231-netizen"
REPO_NAME = "Engine-A-Dashboard"
STOCKS_PATH = "data/engine_b_stocks.json"

# ============================================================
# GITHUB API HELPERS
# ============================================================
def get_github_token():
    token = st.secrets.get("GITHUB_TOKEN", "")
    return token

def get_file_from_github(token):
    """GET current engine_b_stocks.json from GitHub (for SHA + content)."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{STOCKS_PATH}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content), data["sha"]
    return None, None

def save_file_to_github(token, new_content, sha, message):
    """PUT updated engine_b_stocks.json to GitHub."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{STOCKS_PATH}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    encoded = base64.b64encode(json.dumps(new_content, indent=2).encode("utf-8")).decode("utf-8")
    body = {"message": message, "content": encoded, "sha": sha}
    resp = requests.put(url, headers=headers, json=body)
    return resp.status_code in [200, 201]

def trigger_workflow(token):
    """Trigger GitHub Actions workflow to fetch new stock prices."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/test.yml/dispatches"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    body = {"ref": "main"}
    resp = requests.post(url, headers=headers, json=body)
    return resp.status_code == 204

# ============================================================
# DATA LOADERS
# ============================================================
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

def load_positions():
    if STOCKS_FILE.exists():
        with open(STOCKS_FILE, "r") as f:
            stock_data = json.load(f)
        return stock_data.get("engine_b", [])
    return []

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
    col_map = {c.strip(): c for c in df.columns}
    for candidate in candidates:
        candidate_clean = candidate.strip()
        if candidate_clean in col_map:
            return col_map[candidate_clean]
        for col_clean, col_orig in col_map.items():
            if col_clean.lower() == candidate_clean.lower():
                return col_orig
    return None

# ============================================================
# CSV/EXCEL PARSER
# ============================================================
def parse_trendlyne_file(uploaded_file):
    try:
        fname = uploaded_file.name.lower()
        if fname.endswith(".xlsx") or fname.endswith(".xls"):
            df = pd.read_excel(uploaded_file)
        else:
            df = pd.read_csv(uploaded_file)

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
        if peak:
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

    # --- REFRESH NOW BUTTON ---
    if st.button("🔄 Refresh Now", key="engine_b_refresh"):
        token = get_github_token()
        if token and trigger_workflow(token):
            st.success("Refresh triggered! Prices update in ~45 sec.")
        else:
            st.error("Could not trigger refresh. Check token.")

    # --- LOAD LIVE PRICES ---
    live_prices = load_stock_prices()

    # --- ACTIVE POSITIONS ---
    st.markdown("<div class='section-title'>Engine B — Active Positions</div>", unsafe_allow_html=True)

    positions = load_positions()

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

            # --- SELL BUTTON ---
            ticker_key = p.get("ticker", "")
            with st.expander(f"Sell {p['stock']}?", expanded=False):
                exit_reasons = ["Stop Hit (-7%)", "Trailing Stop", "Filter Break", "Manual Exit"]
                reason = st.selectbox("Exit Reason", exit_reasons, key=f"reason_{ticker_key}")
                if current_price != "" and current_price is not None:
                    try:
                        cp = float(current_price)
                        exit_pnl = round((cp - entry) * qty, 2)
                        exit_pct = round((cp - entry) / entry * 100, 2)
                        pnl_sign = "+" if exit_pnl >= 0 else ""
                        st.markdown(
                            f"<div style='font-size:12px;color:#94a3b8;'>"
                            f"Exit: ₹{cp:,.2f} · P&L: {pnl_sign}₹{exit_pnl:,.0f} ({pnl_sign}{exit_pct}%)"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    except:
                        cp = entry
                else:
                    cp = entry
                if st.button(f"Confirm Sell {p['stock']}", key=f"sell_{ticker_key}"):
                    token = get_github_token()
                    if not token:
                        st.error("GitHub token not found.")
                    else:
                        file_data, sha = get_file_from_github(token)
                        if file_data is None:
                            st.error("Could not read from GitHub.")
                        else:
                            # Build closed trade record
                            buy_date = p.get("buy_date", "")
                            sell_date = pd.Timestamp.now().strftime("%Y-%m-%d")
                            holding_days = 0
                            if buy_date:
                                try:
                                    bd = pd.Timestamp(buy_date)
                                    sd = pd.Timestamp(sell_date)
                                    holding_days = (sd - bd).days
                                except:
                                    pass
                            realized_pnl = round((cp - entry) * qty, 2)
                            realized_pct = round((cp - entry) / entry * 100, 2)
                            closed_trade = {
                                "stock": p["stock"],
                                "ticker": ticker_key,
                                "entry": entry,
                                "exit_price": cp,
                                "qty": qty,
                                "buy_date": buy_date,
                                "sell_date": sell_date,
                                "holding_days": holding_days,
                                "realized_pnl": realized_pnl,
                                "realized_pct": realized_pct,
                                "exit_reason": reason,
                                "result": "WIN" if realized_pnl >= 0 else "LOSS",
                            }
                            # Add to closed array
                            if "engine_b_closed" not in file_data:
                                file_data["engine_b_closed"] = []
                            file_data["engine_b_closed"].append(closed_trade)
                            # Remove from active array
                            file_data["engine_b"] = [
                                s for s in file_data.get("engine_b", [])
                                if s.get("ticker", "") != ticker_key
                            ]
                            msg = f"Sell {p['stock']} ({reason}: {'+' if realized_pnl >= 0 else ''}₹{realized_pnl:,.0f})"
                            if save_file_to_github(token, file_data, sha, msg):
                                st.success(f"{p['stock']} sold! P&L: {'+' if realized_pnl >= 0 else ''}₹{realized_pnl:,.0f}")
                                st.rerun()
                            else:
                                st.error("Failed to save. Check token.")

        # Portfolio summary
        if all_have_prices:
            pnl_color = "#22c55e" if total_pnl >= 0 else "#ef4444"
            pnl_sign = "+" if total_pnl >= 0 else ""
            pnl_pct = round(total_pnl / total_invested * 100, 2) if total_invested > 0 else 0
            summary_value = f"₹{total_current:,.0f}"
            summary_detail = (f"Invested: ₹{total_invested:,.0f} · P&L: "
                              f"<span style='color:{pnl_color};font-weight:700;'>"
                              f"{pnl_sign}₹{total_pnl:,.0f} ({pnl_sign}{pnl_pct}%)</span>")
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

                # --- CONFIRM BUY BUTTON (only for NEW stocks) ---
                if not is_holding and gate_status == "ACTIVE":
                    ticker_key = stock["ticker"]
                    with st.expander(f"Buy {stock['stock']}?", expanded=False):
                        st.markdown(
                            f"<div style='font-size:12px;color:#94a3b8;margin-bottom:8px;'>"
                            f"Entry: ₹{stock['ltp']:,.2f} · Stop: ₹{stock['ltp'] * 0.93:,.2f} (-7%)"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        qty = st.number_input(
                            "Quantity",
                            min_value=1,
                            value=1,
                            step=1,
                            key=f"qty_{ticker_key}"
                        )
                        invested = qty * stock["ltp"]
                        st.markdown(
                            f"<div style='font-size:12px;color:#e2e8f0;'>"
                            f"Investment: ₹{invested:,.2f}</div>",
                            unsafe_allow_html=True
                        )
                        if st.button(f"Confirm Buy {stock['stock']}", key=f"buy_{ticker_key}"):
                            token = get_github_token()
                            if not token:
                                st.error("GitHub token not found in secrets.")
                            else:
                                file_data, sha = get_file_from_github(token)
                                if file_data is None:
                                    st.error("Could not read engine_b_stocks.json from GitHub.")
                                else:
                                    new_stock = {
                                        "stock": stock["stock"],
                                        "ticker": stock["ticker"],
                                        "entry": stock["ltp"],
                                        "qty": qty,
                                        "peak": stock["ltp"],
                                        "source": stock["source"],
                                        "buy_date": pd.Timestamp.now().strftime("%Y-%m-%d")
                                    }
                                    if "engine_b" not in file_data:
                                        file_data["engine_b"] = []
                                    file_data["engine_b"].append(new_stock)

                                    msg = f"Add {stock['stock']} to Engine B (qty: {qty}, entry: {stock['ltp']})"
                                    if save_file_to_github(token, file_data, sha, msg):
                                        trigger_workflow(token)
                                        st.success(f"{stock['stock']} added! Prices update in ~45 sec.")
                                        st.rerun()
                                    else:
                                        st.error("Failed to save. Check token permissions.")

                elif not is_holding and gate_status == "FROZEN":
                    st.markdown(
                        "<div style='font-size:11px;color:#f59e0b;margin-bottom:8px;'>"
                        "Engine A frozen — no new buys allowed</div>",
                        unsafe_allow_html=True
                    )

    # --- CLOSED POSITIONS (Trade Log) ---
    st.markdown("<div class='section-title'>Closed Positions — Trade Log</div>", unsafe_allow_html=True)

    # Load closed trades from local JSON
    closed_trades = []
    if STOCKS_FILE.exists():
        with open(STOCKS_FILE, "r") as f:
            all_data = json.load(f)
        closed_trades = all_data.get("engine_b_closed", [])

    if not closed_trades:
        st.markdown(
            "<div style='background:#1e293b;border-radius:12px;padding:16px;"
            "border:1px solid #334155;text-align:center;color:#64748b;font-size:13px;'>"
            "No closed trades yet. Sell a position to start tracking results."
            "</div>",
            unsafe_allow_html=True
        )
    else:
        # Stats summary
        wins = sum(1 for t in closed_trades if t.get("result") == "WIN")
        losses = sum(1 for t in closed_trades if t.get("result") == "LOSS")
        total_trades = len(closed_trades)
        win_rate = round(wins / total_trades * 100, 1) if total_trades > 0 else 0
        total_realized = sum(t.get("realized_pnl", 0) for t in closed_trades)
        avg_gain = round(total_realized / total_trades, 0) if total_trades > 0 else 0
        r_color = "#22c55e" if total_realized >= 0 else "#ef4444"
        r_sign = "+" if total_realized >= 0 else ""

        stats_html = (
            f"<div style='background:#0f172a;border-radius:12px;padding:14px 16px;"
            f"border:1px solid #334155;margin-bottom:12px;'>"
            f"<div style='font-size:13px;color:#94a3b8;text-transform:uppercase;"
            f"letter-spacing:1px;margin-bottom:8px;'>Trade Stats</div>"
            f"<div style='display:flex;justify-content:space-between;font-size:13px;'>"
            f"<div style='color:#e2e8f0;'>Trades: <span style='font-weight:700;'>{total_trades}</span></div>"
            f"<div style='color:#22c55e;'>Wins: <span style='font-weight:700;'>{wins}</span></div>"
            f"<div style='color:#ef4444;'>Losses: <span style='font-weight:700;'>{losses}</span></div>"
            f"<div style='color:#fbbf24;'>Win%: <span style='font-weight:700;'>{win_rate}%</span></div>"
            f"</div>"
            f"<div style='margin-top:8px;font-size:13px;color:#94a3b8;'>"
            f"Total Realized: <span style='color:{r_color};font-weight:700;font-family:Courier New,monospace;'>"
            f"{r_sign}₹{total_realized:,.0f}</span>"
            f" · Avg/trade: <span style='color:#e2e8f0;font-family:Courier New,monospace;'>"
            f"{r_sign}₹{avg_gain:,.0f}</span>"
            f"</div>"
            f"</div>"
        )
        st.markdown(stats_html, unsafe_allow_html=True)

        # Individual closed trades (most recent first)
        for t in reversed(closed_trades):
            pnl = t.get("realized_pnl", 0)
            pct = t.get("realized_pct", 0)
            pnl_color = "#22c55e" if pnl >= 0 else "#ef4444"
            pnl_sign = "+" if pnl >= 0 else ""
            result_label = t.get("result", "")
            result_color = "#22c55e" if result_label == "WIN" else "#ef4444"

            closed_html = (
                f"<div style='background:#1e293b;border-radius:12px;padding:12px 16px;"
                f"border:1px solid #334155;margin-bottom:6px;'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                f"<div style='font-size:14px;font-weight:600;color:#e2e8f0;'>{t.get('stock', '')}</div>"
                f"<span style='font-size:10px;font-weight:700;color:{result_color};"
                f"background:{result_color}22;padding:2px 6px;border-radius:4px;'>{result_label}</span>"
                f"</div>"
                f"<div style='display:flex;justify-content:space-between;margin-top:6px;font-size:12px;'>"
                f"<div style='color:#94a3b8;'>Entry: <span style='color:#e2e8f0;"
                f"font-family:Courier New,monospace;'>₹{t.get('entry', 0):,.0f}</span></div>"
                f"<div style='color:#94a3b8;'>Exit: <span style='color:#e2e8f0;"
                f"font-family:Courier New,monospace;'>₹{t.get('exit_price', 0):,.0f}</span></div>"
                f"<div style='color:{pnl_color};font-family:Courier New,monospace;"
                f"font-weight:700;'>{pnl_sign}₹{pnl:,.0f} ({pnl_sign}{pct}%)</div>"
                f"</div>"
                f"<div style='display:flex;justify-content:space-between;margin-top:4px;font-size:11px;'>"
                f"<div style='color:#64748b;'>{t.get('buy_date', '')} → {t.get('sell_date', '')}</div>"
                f"<div style='color:#64748b;'>{t.get('holding_days', 0)}d · {t.get('exit_reason', '')}</div>"
                f"</div>"
                f"</div>"
            )
            st.markdown(closed_html, unsafe_allow_html=True)

    # --- ENGINE C PLACEHOLDER ---
    st.markdown("<div class='section-title'>Engine C — Long-Term Compounders</div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='background:#1e293b;border-radius:12px;padding:20px 16px;"
        "border:1px solid #334155;text-align:center;color:#64748b;font-size:13px;'>"
        "Engine C will have its own tab — coming next"
        "</div>",
        unsafe_allow_html=True
    )
