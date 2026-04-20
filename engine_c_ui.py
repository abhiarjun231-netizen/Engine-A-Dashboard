"""
engine_c_ui.py - Engine C: Long-Term Compounders
Fundamentals-first exit rules. Holds through price volatility.
C1: PEG+YoY | C2: PE+3Yr Growth
"""
import streamlit as st
import pandas as pd
import json
import base64
import requests
import io
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
# GITHUB API HELPERS (reuse same as Engine B)
# ============================================================
def get_github_token():
    return st.secrets.get("GITHUB_TOKEN", "")

def get_file_from_github(token):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{STOCKS_PATH}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content), data["sha"]
    return None, None

def save_file_to_github(token, new_content, sha, message):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{STOCKS_PATH}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    encoded = base64.b64encode(json.dumps(new_content, indent=2).encode("utf-8")).decode("utf-8")
    body = {"message": message, "content": encoded, "sha": sha}
    resp = requests.put(url, headers=headers, json=body)
    return resp.status_code in [200, 201]

def trigger_workflow(token):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/test.yml/dispatches"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    resp = requests.post(url, headers=headers, json={"ref": "main"})
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
        prices[row["stock"]] = {"price": row.get("price", ""), "status": row.get("status", "")}
    return prices

def load_positions():
    if STOCKS_FILE.exists():
        with open(STOCKS_FILE, "r") as f:
            return json.load(f).get("engine_c", [])
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
# STAGE INDICATOR (fundamentals-first)
# ============================================================
def get_stage(pct_change):
    if pct_change <= -40:
        return "HARD STOP", "#ef4444"
    if pct_change <= -25:
        return "REVIEW", "#f59e0b"
    if pct_change <= -10:
        return "WATCH", "#fbbf24"
    return "HEALTHY", "#22c55e"

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
# CSV/EXCEL PARSER (Engine C needs D/E and PEG too)
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
        col_sma200 = find_column(df, ["Day SMA200", "Day SMA 200", "SMA200"])
        col_sector = find_column(df, ["Sector", "Industry", "Trendlyne Sector"])
        col_result = find_column(df, ["Latest Financial Result"])
        col_rev_qoq = find_column(df, ["Revenue QoQ Growth %"])
        col_profit_qoq = find_column(df, ["Net Profit QoQ Growth %"])
        col_de = find_column(df, ["Total Debt to Total Equity Ann", "Debt to Equity", "Debt/Equity", "D/E", "DE Ratio"])
        col_peg = find_column(df, ["PEG TTM", "PEG", "PEG Ratio"])
        col_profit_yoy = find_column(df, ["Net Profit Ann  YoY Growth %", "Net Profit Ann YoY Growth %",
                                          "Net Profit 3Y Growth %", "Profit Growth Annual YoY %",
                                          "Profit Growth YoY %", "Profit Growth Annual %"])

        if not col_stock or not col_ticker:
            st.error("Could not find 'Stock' or 'NSE Code' columns.")
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
                "sma200": float(row.get(col_sma200, 0)) if col_sma200 else 0,
                "sector": str(row.get(col_sector, "")).strip() if col_sector else "",
                "result_date": str(row.get(col_result, "")).strip() if col_result else "",
                "rev_qoq": float(row.get(col_rev_qoq, 0)) if col_rev_qoq else 0,
                "profit_qoq": float(row.get(col_profit_qoq, 0)) if col_profit_qoq else 0,
                "de": float(row.get(col_de, 0)) if col_de else 0,
                "peg": float(row.get(col_peg, 0)) if col_peg else 0,
                "profit_yoy": float(row.get(col_profit_yoy, 0)) if col_profit_yoy else 0,
            })
        return stocks
    except Exception as e:
        st.error(f"File parse error: {e}")
        return []

def combine_screeners(c1_stocks, c2_stocks):
    combined = {}
    for s in c1_stocks:
        combined[s["ticker"]] = {**s, "source": "C1"}
    for s in c2_stocks:
        key = s["ticker"]
        if key in combined:
            combined[key]["source"] = "Double"
        else:
            combined[key] = {**s, "source": "C2"}
    return list(combined.values())

# ============================================================
# CONVICTION SCORE (Engine C — growth + quality weighted)
# ============================================================
def calc_conviction(stock):
    score = 0
    if stock.get("source") == "Double":
        score += 3
    else:
        score += 1
    pio = stock.get("piotroski", 0)
    if pio >= 9: score += 2
    elif pio >= 8: score += 1
    roe = stock.get("roe", 0)
    if roe > 25: score += 2
    elif roe > 15: score += 1
    # D/E low = strong balance sheet
    de = stock.get("de", 99)
    if de < 0.3: score += 2
    elif de < 0.7: score += 1
    # Profit growth
    profit_qoq = stock.get("profit_qoq", 0)
    profit_yoy = stock.get("profit_yoy", 0)
    profit_val = profit_qoq if profit_qoq != 0 else profit_yoy
    if profit_val > 30: score += 2
    elif profit_val > 10: score += 1
    # Entry timing
    ltp = stock.get("ltp", 0)
    sma = stock.get("sma200", 0)
    if sma > 0 and ltp > 0:
        pct = (ltp - sma) / sma * 100
        if pct < 10: score += 1
    return min(score, 10)

# ============================================================
# POSITION CARD (Engine C — different stops)
# ============================================================
def render_position(stock_name, entry, qty, peak, current_price, de_val, peg_val):
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
        pct_str = pnl_str = ""
        pct_color = pnl_color = "#64748b"
        price_str = "awaiting"
        pnl_str = "awaiting"

    review_stop = round(entry * 0.75, 0)
    hard_stop = round(entry * 0.60, 0)

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
        f"<div style='color:#94a3b8;'>Review: <span style='color:#f59e0b;font-family:Courier New,monospace;'>₹{review_stop:,.0f}</span></div>"
        f"</div>"
        f"<div style='display:flex;justify-content:space-between;margin-top:4px;font-size:12px;'>"
        f"<div style='color:#94a3b8;'>Invested: <span style='color:#e2e8f0;font-family:Courier New,monospace;'>₹{entry * qty:,.0f}</span></div>"
        f"<div style='color:#94a3b8;'>P&L: <span style='color:{pnl_color};font-family:Courier New,monospace;font-weight:600;'>{pnl_str}</span></div>"
        f"</div>"
        f"</div>"
    )
    st.markdown(card_html, unsafe_allow_html=True)

# ============================================================
# QUALIFIER CARD (Engine C)
# ============================================================
def render_qualifier(stock, source_label, source_color, is_holding, live_price=None):
    status_label = "HOLDING" if is_holding else "NEW"
    status_color = "#38bdf8" if is_holding else "#22c55e"
    ltp = stock.get('ltp', 0)
    sma200 = stock.get('sma200', 0)
    if sma200 > 0 and ltp > 0:
        pct_above_dma = round((ltp - sma200) / sma200 * 100, 1)
        dma_str = f"{'+' if pct_above_dma >= 0 else ''}{pct_above_dma}%"
        dma_color = "#22c55e" if pct_above_dma >= 0 else "#ef4444"
    else:
        dma_str = "—"
        dma_color = "#64748b"
    mcap = stock.get('mcap', 0)
    if mcap >= 100000: mcap_str = f"₹{mcap/100000:.0f}L Cr"
    elif mcap >= 1000: mcap_str = f"₹{mcap/1000:.0f}K Cr"
    else: mcap_str = f"₹{mcap:,.0f} Cr"
    conv = calc_conviction(stock)
    if conv >= 8: conv_color = "#22c55e"
    elif conv >= 5: conv_color = "#fbbf24"
    else: conv_color = "#94a3b8"
    sector = stock.get('sector', '')
    sector_str = f" · {sector}" if sector else ""
    rev_qoq = stock.get('rev_qoq', 0)
    profit_qoq = stock.get('profit_qoq', 0)
    profit_yoy = stock.get('profit_yoy', 0)
    # Use YoY if QoQ not available
    profit_display = profit_qoq if profit_qoq != 0 else profit_yoy
    profit_label = "Profit QoQ" if profit_qoq != 0 else "Profit YoY"
    rev_color = "#22c55e" if rev_qoq > 0 else "#ef4444" if rev_qoq < 0 else "#64748b"
    prof_color = "#22c55e" if profit_display > 0 else "#ef4444" if profit_display < 0 else "#64748b"
    rev_sign = "+" if rev_qoq > 0 else ""
    prof_sign = "+" if profit_display > 0 else ""
    result_date = stock.get('result_date', '')[:10] if stock.get('result_date') else ""
    de = stock.get('de', 0)
    peg = stock.get('peg', 0)

    # Live price + Opportunity tracker
    if live_price is not None and ltp > 0:
        opp_pct = round((live_price - ltp) / ltp * 100, 2)
        opp_sign = "+" if opp_pct >= 0 else ""
        if opp_pct > 0:
            opp_label = "Opp Lost"
            opp_color = "#ef4444"
        elif opp_pct < 0:
            opp_label = "Opp Gained"
            opp_color = "#22c55e"
        else:
            opp_label = "Flat"
            opp_color = "#94a3b8"
        price_row = (
            f"<div style='display:flex;justify-content:space-between;margin-top:6px;font-size:12px;'>"
            f"<div style='color:#94a3b8;'>Now: <span style='color:#e2e8f0;font-family:Courier New,monospace;font-weight:600;'>₹{live_price:,.2f}</span></div>"
            f"<div style='color:#94a3b8;'>Upload: <span style='color:#64748b;font-family:Courier New,monospace;'>₹{ltp:,.2f}</span></div>"
            f"<div style='color:{opp_color};font-family:Courier New,monospace;font-weight:700;font-size:11px;'>{opp_label}: {opp_sign}{opp_pct}%</div>"
            f"</div>")
    else:
        price_row = (
            f"<div style='display:flex;justify-content:space-between;margin-top:6px;font-size:12px;'>"
            f"<div style='color:#94a3b8;'>LTP: <span style='color:#e2e8f0;font-family:Courier New,monospace;'>₹{ltp:,.2f}</span></div>"
            f"<div></div><div></div>"
            f"</div>")

    card_html = (
        f"<div style='background:#1e293b;border-radius:12px;padding:12px 16px;"
        f"border:1px solid #334155;margin-bottom:6px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
        f"<div style='font-size:14px;font-weight:600;color:#e2e8f0;'>{stock['stock']}</div>"
        f"<div style='display:flex;gap:8px;align-items:center;'>"
        f"<span style='font-size:11px;font-weight:700;color:{conv_color};'>{conv}/10</span>"
        f"<span style='font-size:10px;font-weight:700;color:{source_color};background:{source_color}22;padding:2px 6px;border-radius:4px;'>{source_label}</span>"
        f"<span style='font-size:10px;font-weight:700;color:{status_color};background:{status_color}22;padding:2px 6px;border-radius:4px;'>{status_label}</span>"
        f"</div>"
        f"</div>"
        f"{price_row}"
        f"<div style='display:flex;justify-content:space-between;margin-top:4px;font-size:12px;'>"
        f"<div style='color:#94a3b8;'>ROE: <span style='color:#e2e8f0;font-family:Courier New,monospace;'>{stock['roe']:.1f}%</span></div>"
        f"<div style='color:#94a3b8;'>PE: <span style='color:#e2e8f0;font-family:Courier New,monospace;'>{stock['pe']:.1f}</span></div>"
        f"<div style='color:#94a3b8;'>Pio: <span style='color:#e2e8f0;font-family:Courier New,monospace;'>{stock['piotroski']}</span></div>"
        f"</div>"
        f"<div style='display:flex;justify-content:space-between;margin-top:4px;font-size:11px;'>"
        f"<div style='color:#64748b;'>D/E: <span style='color:#94a3b8;'>{de:.2f}</span>"
        f" · PEG: <span style='color:#94a3b8;'>{peg:.1f}</span></div>"
        f"<div style='color:#64748b;'>vs 200DMA: <span style='color:{dma_color};font-weight:600;'>{dma_str}</span></div>"
        f"</div>"
        f"<div style='display:flex;justify-content:space-between;margin-top:4px;font-size:11px;'>"
        f"<div style='color:#64748b;'>MCap: <span style='color:#94a3b8;'>{mcap_str}</span>{sector_str}</div>"
        f"<div style='color:#64748b;'>Results: <span style='color:#94a3b8;'>{result_date}</span></div>"
        f"</div>"
        f"<div style='display:flex;justify-content:space-between;margin-top:4px;font-size:11px;'>"
        f"<div style='color:#64748b;'>{profit_label}: <span style='color:{prof_color};'>{prof_sign}{profit_display:.1f}%</span></div>"
        f"</div>"
        f"</div>"
    )
    st.markdown(card_html, unsafe_allow_html=True)

# ============================================================
# MAIN DISPLAY FUNCTION
# ============================================================
def show_engine_c():
    # --- ENGINE A GATE ---
    score_data = load_engine_a_score()
    score_val = int(score_data["raw_score"]) if score_data else None
    gate_status, gate_color, gate_msg = get_gate_status(score_val)

    gate_html = (
        f"<div style='background:#1e293b;border-radius:12px;padding:14px 16px;"
        f"border:1px solid {gate_color};margin-bottom:16px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
        f"<div style='font-size:13px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;'>Engine C Status</div>"
        f"<div style='font-size:15px;font-weight:700;color:{gate_color};'>{gate_status}</div>"
        f"</div>"
        f"<div style='font-size:11px;color:#64748b;margin-top:4px;'>{gate_msg} (Score: {score_val}/100)</div>"
        f"</div>"
    )
    st.markdown(gate_html, unsafe_allow_html=True)

    # --- REFRESH ---
    if st.button("🔄 Refresh Now", key="engine_c_refresh"):
        token = get_github_token()
        if token and trigger_workflow(token):
            st.success("Refresh triggered! Prices update in ~45 sec.")
        else:
            st.error("Could not trigger refresh.")

    # --- LIVE PRICES ---
    live_prices = load_stock_prices()

    # --- ACTIVE POSITIONS ---
    st.markdown("<div class='section-title'>Engine C — Active Positions</div>", unsafe_allow_html=True)
    positions = load_positions()

    if not positions:
        st.markdown(
            "<div style='background:#1e293b;border-radius:12px;padding:20px 16px;"
            "border:1px solid #334155;text-align:center;color:#64748b;font-size:13px;'>"
            "No active positions. Upload screener CSVs below to find compounders."
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

            render_position(p["stock"], entry, qty, peak, current_price,
                          p.get("de", 0), p.get("peg", 0))

            # --- SELL BUTTON ---
            ticker_key = p.get("ticker", "")
            with st.expander(f"Sell {p['stock']}?", expanded=False):
                exit_reasons = ["Piotroski Drop (≤4)", "Profit Decline (2Q neg)",
                              "PEG Breach (>2.5)", "D/E Breach (>1.5)",
                              "ROE Collapse (<10%)", "Price Review (-25%)",
                              "Hard Stop (-40%)", "Manual Exit"]
                reason = st.selectbox("Exit Reason", exit_reasons, key=f"c_reason_{ticker_key}")
                if current_price != "" and current_price is not None:
                    try:
                        cp = float(current_price)
                        exit_pnl = round((cp - entry) * qty, 2)
                        exit_pct = round((cp - entry) / entry * 100, 2)
                        pnl_sign = "+" if exit_pnl >= 0 else ""
                        st.markdown(
                            f"<div style='font-size:12px;color:#94a3b8;'>"
                            f"Exit: ₹{cp:,.2f} · P&L: {pnl_sign}₹{exit_pnl:,.0f} ({pnl_sign}{exit_pct}%)"
                            f"</div>", unsafe_allow_html=True)
                    except:
                        cp = entry
                else:
                    cp = entry
                if st.button(f"Confirm Sell {p['stock']}", key=f"c_sell_{ticker_key}"):
                    token = get_github_token()
                    if token:
                        file_data, sha = get_file_from_github(token)
                        if file_data:
                            buy_date = p.get("buy_date", "")
                            sell_date = pd.Timestamp.now().strftime("%Y-%m-%d")
                            holding_days = 0
                            if buy_date:
                                try:
                                    holding_days = (pd.Timestamp(sell_date) - pd.Timestamp(buy_date)).days
                                except: pass
                            realized_pnl = round((cp - entry) * qty, 2)
                            realized_pct = round((cp - entry) / entry * 100, 2)
                            closed_trade = {
                                "stock": p["stock"], "ticker": ticker_key,
                                "entry": entry, "exit_price": cp, "qty": qty,
                                "buy_date": buy_date, "sell_date": sell_date,
                                "holding_days": holding_days,
                                "realized_pnl": realized_pnl,
                                "realized_pct": realized_pct,
                                "exit_reason": reason,
                                "result": "WIN" if realized_pnl >= 0 else "LOSS",
                            }
                            if "engine_c_closed" not in file_data:
                                file_data["engine_c_closed"] = []
                            file_data["engine_c_closed"].append(closed_trade)
                            file_data["engine_c"] = [
                                s for s in file_data.get("engine_c", [])
                                if s.get("ticker", "") != ticker_key
                            ]
                            msg = f"Sell {p['stock']} Engine C ({reason})"
                            if save_file_to_github(token, file_data, sha, msg):
                                st.success(f"{p['stock']} sold!")
                                st.rerun()

        # Portfolio summary
        if all_have_prices and total_invested > 0:
            pnl_color = "#22c55e" if total_pnl >= 0 else "#ef4444"
            pnl_sign = "+" if total_pnl >= 0 else ""
            pnl_pct = round(total_pnl / total_invested * 100, 2)
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
            f"<div style='font-size:13px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;'>Engine C Total</div>"
            f"<div style='font-size:18px;font-weight:700;color:#e2e8f0;font-family:Courier New,monospace;'>{summary_value}</div>"
            f"</div>"
            f"<div style='font-size:11px;color:#64748b;margin-top:4px;'>{summary_detail}</div>"
            f"</div>"
        )
        st.markdown(summary_html, unsafe_allow_html=True)

    # --- POSITION SIZER (always visible) ---
    if score_data:
        eq_pct = float(score_data.get("equity_pct", 55))
        b_pct = float(score_data.get("engine_b_pct", 25))
        c_pct = float(score_data.get("engine_c_pct", 30))
        with st.expander("Position Sizer", expanded=False):
            capital = st.number_input("Total Capital (₹)", min_value=10000,
                                       value=100000, step=10000, key="c_capital_input")
            engine_c_budget = round(capital * c_pct / 100)
            max_per_stock = round(capital * 0.07)
            slots = len(positions) if positions else 0
            per_stock = round(engine_c_budget / max(slots, 1))
            per_stock_capped = min(per_stock, max_per_stock)

            sizer_html = (
                f"<div style='font-size:12px;color:#94a3b8;line-height:1.8;'>"
                f"Equity: {eq_pct:.0f}% · Engine B: {b_pct:.0f}% · Engine C: {c_pct:.0f}%<br>"
                f"Engine C budget: <span style='color:#e2e8f0;font-weight:700;'>"
                f"₹{engine_c_budget:,.0f}</span><br>"
                f"Active positions: {slots}/15<br>"
                f"Per stock: <span style='color:#e2e8f0;font-weight:700;'>"
                f"₹{per_stock_capped:,.0f}</span>"
                f" (max 7%: ₹{max_per_stock:,.0f})"
                f"</div>"
            )
            st.markdown(sizer_html, unsafe_allow_html=True)

    # --- WATCHLIST ---
    st.markdown("<div class='section-title'>Screener Watchlist</div>", unsafe_allow_html=True)

    saved_watchlist = []
    watchlist_date = ""
    if STOCKS_FILE.exists():
        with open(STOCKS_FILE, "r") as f:
            _wl = json.load(f)
        saved_watchlist = _wl.get("engine_c_watchlist", [])
        watchlist_date = _wl.get("_c_watchlist_date", "")

    with st.expander("Upload New Screener CSVs", expanded=len(saved_watchlist) == 0):
        col1, col2 = st.columns(2)
        with col1:
            c1_files = st.file_uploader("C1 CSVs (PEG+YoY)", type=None,
                                         accept_multiple_files=True, key="c1_upload")
        with col2:
            c2_files = st.file_uploader("C2 CSVs (PE+3Yr)", type=None,
                                         accept_multiple_files=True, key="c2_upload")

        if c1_files or c2_files:
            c1_stocks = []
            c2_stocks = []
            for f in (c1_files or []):
                c1_stocks.extend(parse_trendlyne_file(f))
            for f in (c2_files or []):
                c2_stocks.extend(parse_trendlyne_file(f))
            combined = combine_screeners(c1_stocks, c2_stocks)

            if combined and st.button("Save Watchlist", key="c_save_watchlist"):
                token = get_github_token()
                if token:
                    file_data, sha = get_file_from_github(token)
                    if file_data:
                        for s in combined:
                            s["action"] = "REVIEW"
                        file_data["engine_c_watchlist"] = combined
                        file_data["_c_watchlist_date"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
                        if save_file_to_github(token, file_data, sha, "Update Engine C watchlist"):
                            st.success(f"Watchlist saved: {len(combined)} stocks")
                            st.rerun()

    # Display watchlist
    if saved_watchlist:
        holding_tickers = [p.get("ticker", "") for p in positions]

        double_count = sum(1 for s in saved_watchlist if s.get("source") == "Double")
        c1_only = sum(1 for s in saved_watchlist if s.get("source") == "C1")
        c2_only = sum(1 for s in saved_watchlist if s.get("source") == "C2")

        stats_html = (
            f"<div style='background:#0f172a;border-radius:12px;padding:14px 16px;"
            f"border:1px solid #334155;margin-bottom:12px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>"
            f"<div style='font-size:13px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;'>Watchlist</div>"
            f"<div style='font-size:11px;color:#64748b;'>Updated: {watchlist_date}</div>"
            f"</div>"
            f"<div style='display:flex;justify-content:space-between;font-size:13px;'>"
            f"<div style='color:#e2e8f0;'>Total: <span style='font-weight:700;'>{len(saved_watchlist)}</span></div>"
            f"<div style='color:#fbbf24;'>Double: <span style='font-weight:700;'>{double_count}</span></div>"
            f"<div style='color:#22c55e;'>C1: <span style='font-weight:700;'>{c1_only}</span></div>"
            f"<div style='color:#38bdf8;'>C2: <span style='font-weight:700;'>{c2_only}</span></div>"
            f"</div>"
            f"</div>"
        )
        st.markdown(stats_html, unsafe_allow_html=True)

        # Sort by conviction
        saved_watchlist.sort(key=lambda x: (-calc_conviction(x),
            {"Double": 0, "C1": 1, "C2": 2}.get(x.get("source", ""), 3)))

        for stock in saved_watchlist:
            source = stock.get("source", "")
            if source == "Double":
                source_label, source_color = "DOUBLE", "#fbbf24"
            elif source == "C1":
                source_label, source_color = "C1", "#22c55e"
            else:
                source_label, source_color = "C2", "#38bdf8"

            action = stock.get("action", "REVIEW")
            is_holding = stock.get("ticker", "") in holding_tickers

            if action == "AVOID" and not is_holding:
                st.markdown(
                    f"<div style='background:#1e293b;border-radius:8px;padding:8px 12px;"
                    f"border:1px solid #334155;margin-bottom:4px;opacity:0.5;'>"
                    f"<div style='display:flex;justify-content:space-between;font-size:12px;'>"
                    f"<span style='color:#64748b;'>{stock.get('stock', '')}</span>"
                    f"<span style='color:#64748b;'>AVOIDED</span>"
                    f"</div></div>", unsafe_allow_html=True)
                continue

            # Look up live price for this watchlist stock
            _wl_live = live_prices.get(stock.get("stock", ""), {})
            _wl_live_price = None
            if _wl_live.get("price", "") != "":
                try:
                    _wl_live_price = float(_wl_live["price"])
                except:
                    pass

            render_qualifier(stock, source_label, source_color, is_holding, live_price=_wl_live_price)

            if not is_holding and gate_status == "ACTIVE":
                ticker_key = stock.get("ticker", "")
                if len(positions) >= 15:
                    st.markdown(
                        "<div style='font-size:11px;color:#f59e0b;margin-bottom:8px;'>"
                        "⚠️ Max 15 positions reached</div>", unsafe_allow_html=True)
                    continue

                bcol1, bcol2 = st.columns([3, 1])
                with bcol1:
                    with st.expander(f"Buy {stock.get('stock', '')}?", expanded=False):
                        ltp = stock.get('ltp', 0)
                        st.markdown(
                            f"<div style='font-size:12px;color:#94a3b8;margin-bottom:8px;'>"
                            f"Entry: ₹{ltp:,.2f} · Review: ₹{ltp * 0.75:,.2f} (-25%) · Hard Stop: ₹{ltp * 0.60:,.2f} (-40%)"
                            f"</div>", unsafe_allow_html=True)
                        qty = st.number_input("Quantity", min_value=1, value=1, step=1,
                                              key=f"c_qty_{ticker_key}")
                        invested = qty * ltp
                        st.markdown(f"<div style='font-size:12px;color:#e2e8f0;'>"
                                    f"Investment: ₹{invested:,.2f}</div>", unsafe_allow_html=True)
                        if st.button(f"Confirm Buy {stock.get('stock', '')}", key=f"c_buy_{ticker_key}"):
                            token = get_github_token()
                            if token:
                                file_data, sha = get_file_from_github(token)
                                if file_data:
                                    new_stock = {
                                        "stock": stock.get("stock", ""),
                                        "ticker": ticker_key,
                                        "entry": ltp, "qty": qty, "peak": ltp,
                                        "source": stock.get("source", ""),
                                        "buy_date": pd.Timestamp.now().strftime("%Y-%m-%d"),
                                        "de": stock.get("de", 0),
                                        "peg": stock.get("peg", 0),
                                    }
                                    if "engine_c" not in file_data:
                                        file_data["engine_c"] = []
                                    file_data["engine_c"].append(new_stock)
                                    for ws in file_data.get("engine_c_watchlist", []):
                                        if ws.get("ticker") == ticker_key:
                                            ws["action"] = "BOUGHT"
                                    msg = f"Add {stock.get('stock', '')} to Engine C"
                                    if save_file_to_github(token, file_data, sha, msg):
                                        trigger_workflow(token)
                                        st.success(f"{stock.get('stock', '')} added!")
                                        st.rerun()
                with bcol2:
                    if st.button("Avoid", key=f"c_avoid_{ticker_key}"):
                        token = get_github_token()
                        if token:
                            file_data, sha = get_file_from_github(token)
                            if file_data:
                                for ws in file_data.get("engine_c_watchlist", []):
                                    if ws.get("ticker") == ticker_key:
                                        ws["action"] = "AVOID"
                                if save_file_to_github(token, file_data, sha, f"Avoid {stock.get('stock', '')} in C"):
                                    st.rerun()

            elif not is_holding and gate_status == "FROZEN":
                st.markdown(
                    "<div style='font-size:11px;color:#f59e0b;margin-bottom:8px;'>"
                    "Engine A frozen — no new buys</div>", unsafe_allow_html=True)

        st.markdown("")
        if st.button("🗑️ Clear Watchlist (New Quarter)", key="c_clear_watchlist"):
            token = get_github_token()
            if token:
                file_data, sha = get_file_from_github(token)
                if file_data:
                    file_data["engine_c_watchlist"] = []
                    file_data["_c_watchlist_date"] = ""
                    if save_file_to_github(token, file_data, sha, "Clear Engine C watchlist"):
                        st.success("Watchlist cleared!")
                        st.rerun()

    # --- CLOSED POSITIONS ---
    st.markdown("<div class='section-title'>Closed Positions — Trade Log</div>", unsafe_allow_html=True)
    closed_trades = []
    if STOCKS_FILE.exists():
        with open(STOCKS_FILE, "r") as f:
            closed_trades = json.load(f).get("engine_c_closed", [])

    if not closed_trades:
        st.markdown(
            "<div style='background:#1e293b;border-radius:12px;padding:16px;"
            "border:1px solid #334155;text-align:center;color:#64748b;font-size:13px;'>"
            "No closed trades yet."
            "</div>", unsafe_allow_html=True)
    else:
        wins = sum(1 for t in closed_trades if t.get("result") == "WIN")
        losses = len(closed_trades) - wins
        total_trades = len(closed_trades)
        win_rate = round(wins / total_trades * 100, 1) if total_trades > 0 else 0
        total_realized = sum(t.get("realized_pnl", 0) for t in closed_trades)
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
            f"Total Realized: <span style='color:{r_color};font-weight:700;'>{r_sign}₹{total_realized:,.0f}</span>"
            f"</div>"
            f"</div>"
        )
        st.markdown(stats_html, unsafe_allow_html=True)

        # --- DOWNLOAD TRADE LOG AS EXCEL ---
        trade_df = pd.DataFrame(closed_trades)
        col_order = ["stock", "ticker", "entry", "exit_price", "qty",
                     "buy_date", "sell_date", "holding_days",
                     "realized_pnl", "realized_pct", "exit_reason", "result"]
        col_order = [c for c in col_order if c in trade_df.columns]
        trade_df = trade_df[col_order]
        col_rename = {
            "stock": "Stock", "ticker": "NSE Code", "entry": "Entry ₹",
            "exit_price": "Exit ₹", "qty": "Qty", "buy_date": "Buy Date",
            "sell_date": "Sell Date", "holding_days": "Days Held",
            "realized_pnl": "P&L ₹", "realized_pct": "P&L %",
            "exit_reason": "Exit Reason", "result": "Result"
        }
        trade_df.rename(columns=col_rename, inplace=True)

        stats_df = pd.DataFrame([{
            "Total Trades": total_trades,
            "Wins": wins,
            "Losses": losses,
            "Win Rate %": win_rate,
            "Total Realized ₹": total_realized,
        }])

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            stats_df.to_excel(writer, sheet_name="Trade Stats", index=False)
            trade_df.to_excel(writer, sheet_name="Trade Log", index=False)
        buf.seek(0)

        st.download_button(
            label="📥 Download Trade Log (Excel)",
            data=buf,
            file_name="Engine_C_Trade_Log.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="c_download_trade_log"
        )
