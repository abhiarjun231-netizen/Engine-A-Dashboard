"""
engine_a_ui.py - All Engine A display logic
Called by App.py via show_engine_a()
White Theme v5.1 — 5 improvements added
"""

import streamlit as st
import pandas as pd
import json
import base64
import requests
from pathlib import Path
from datetime import datetime, date

# ============================================================
# GITHUB CONFIG
# ============================================================
GITHUB_OWNER = "abhiarjun231-netizen"
GITHUB_REPO = "Engine-A-Dashboard"
GITHUB_BRANCH = "main"
MANUAL_FILE_PATH = "manual_inputs.json"
WORKFLOW_FILE = "test.yml"

# PAT expiry date (update when renewed)
PAT_EXPIRY = date(2026, 5, 15)

def get_github_token():
    try:
        return st.secrets["GITHUB_TOKEN"]
    except Exception:
        return None

def trigger_workflow():
    token = get_github_token()
    if not token:
        return False, "GITHUB_TOKEN not configured in Streamlit secrets."
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    wf_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches"
    try:
        resp = requests.post(wf_url, headers=headers, json={"ref": GITHUB_BRANCH}, timeout=15)
        if resp.status_code == 204:
            return True, "Refresh triggered. Reload the page in ~45 seconds to see new data."
        return False, f"Trigger failed ({resp.status_code}). Try again or use Save & Rescore."
    except requests.RequestException as e:
        return False, f"Network error: {e}"

# ============================================================
# DATA LOADERS
# ============================================================
SCORE_FILE    = Path("data/engine_a_score.csv")
LIVE_FILE     = Path("data/live_prices.csv")
GLOBAL_FILE   = Path("data/global_prices.csv")
MANUAL_FILE   = Path("manual_inputs.json")
STOCKS_FILE   = Path("data/engine_b_stocks.json")
PRICES_FILE   = Path("data/engine_b_prices.csv")
HISTORY_FILE  = Path("data/score_history.csv")
HIST_PRICE    = Path("data/historical_prices.csv")

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
    if not MANUAL_FILE.exists(): return {}
    with open(MANUAL_FILE, "r") as f:
        return json.load(f)

def load_stocks_data():
    if not STOCKS_FILE.exists(): return {}
    with open(STOCKS_FILE, "r") as f:
        return json.load(f)

def load_stock_prices():
    if not PRICES_FILE.exists(): return {}
    df = pd.read_csv(PRICES_FILE)
    result = {}
    for _, row in df.iterrows():
        ticker = row.get("ticker", "")
        price = row.get("price", "")
        if ticker and price != "" and pd.notna(price):
            try: result[ticker] = float(price)
            except: pass
    return result

def load_score_history():
    if not HISTORY_FILE.exists(): return pd.DataFrame()
    try:
        df = pd.read_csv(HISTORY_FILE)
        if "timestamp" in df.columns and "raw_score" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            df = df.dropna(subset=["timestamp", "raw_score"])
            df = df.sort_values("timestamp")
            return df
    except: pass
    return pd.DataFrame()

def load_200dma():
    if not HIST_PRICE.exists(): return None
    try:
        df = pd.read_csv(HIST_PRICE)
        nifty_col = None
        for col in df.columns:
            if "nifty" in col.lower() and "50" in col:
                nifty_col = col
                break
        if nifty_col is None:
            for col in df.columns:
                if col.lower() not in ("date", "timestamp"):
                    nifty_col = col
                    break
        if nifty_col is None: return None
        vals = pd.to_numeric(df[nifty_col], errors="coerce").dropna()
        if len(vals) >= 200:
            dma = vals.tail(200).mean()
            return round(dma, 2)
        elif len(vals) > 0:
            dma = vals.mean()
            return round(dma, 2)
    except: pass
    return None

# ============================================================
# HELPERS
# ============================================================
def condition_color(c):
    return {
        "TERRIBLE": "#dc2626", "WEAK": "#d97706", "BELOW AVG": "#d97706",
        "NEUTRAL": "#2563eb", "GOOD": "#16a34a", "EXCELLENT": "#16a34a",
    }.get(c, "#64748b")

def score_color(s):
    if s <= 30: return "#dc2626"
    if s <= 40: return "#d97706"
    if s <= 52: return "#2563eb"
    return "#16a34a"

def bar_color(pct):
    if pct < 0.30: return "#ef4444"
    if pct < 0.55: return "#f59e0b"
    if pct < 0.75: return "#3b82f6"
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
# MAIN ENGINE A DISPLAY FUNCTION
# ============================================================
def show_engine_a():
    manual_full = load_manual_full()
    score = load_latest_score()
    live = load_live()
    glob = load_global()
    stocks_data = load_stocks_data()
    stock_prices = load_stock_prices()
    score_history = load_score_history()
    dma_200 = load_200dma()
    manual = {k: v.get("value") for k, v in manual_full.items() if not k.startswith("_")}

    if score is None:
        st.error("No score data yet. Trigger the workflow to generate the first score.")
        return

    today = date.today()

    # ============================================================
    # IMPROVEMENT 5: PAT EXPIRY WARNING
    # ============================================================
    days_to_expiry = (PAT_EXPIRY - today).days
    if days_to_expiry <= 0:
        st.markdown(
            "<div style='background:#fef2f2;border:1px solid #fecaca;border-radius:12px;"
            "padding:14px 18px;margin-bottom:12px;'>"
            "<span style='font-size:16px;margin-right:8px;'>&#9888;</span>"
            "<span style='color:#dc2626;font-weight:600;font-size:13px;'>"
            "GitHub PAT has EXPIRED. Dashboard cannot save or refresh. "
            "Renew now: GitHub → Settings → Developer settings → Fine-grained tokens → Regenerate."
            "</span></div>",
            unsafe_allow_html=True
        )
    elif days_to_expiry <= 7:
        st.markdown(
            f"<div style='background:#fffbeb;border:1px solid #fde68a;border-radius:12px;"
            f"padding:14px 18px;margin-bottom:12px;'>"
            f"<span style='font-size:16px;margin-right:8px;'>&#9888;</span>"
            f"<span style='color:#d97706;font-weight:600;font-size:13px;'>"
            f"GitHub PAT expires in {days_to_expiry} day{'s' if days_to_expiry != 1 else ''}. "
            f"Renew soon: GitHub → Settings → Developer settings → Fine-grained tokens → Regenerate."
            f"</span></div>",
            unsafe_allow_html=True
        )

    # ============================================================
    # IMPROVEMENT 4: SUNDAY REMINDER
    # ============================================================
    if today.weekday() == 6:  # Sunday
        st.markdown(
            "<div style='background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;"
            "padding:14px 18px;margin-bottom:12px;'>"
            "<span style='font-size:16px;margin-right:8px;'>&#128197;</span>"
            "<span style='color:#16a34a;font-weight:600;font-size:13px;'>"
            "It's Sunday — time for your weekly scoring review. "
            "Update manual inputs (FII, DII, Breadth) from Trendlyne, then Save &amp; Rescore."
            "</span></div>",
            unsafe_allow_html=True
        )

    # HEADER
    st.markdown("<div class='score-title'>Engine A — Market Strength</div>", unsafe_allow_html=True)

    # ============================================================
    # IMPROVEMENT 2: SCORE CHANGE INDICATOR
    # ============================================================
    sc = score["raw_score"]; cond = score["market_condition"]; ts = score["timestamp"]
    try:
        ts_pretty = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y, %I:%M %p")
    except: ts_pretty = ts

    # Calculate change from previous score
    change_html = ""
    if not score_history.empty and len(score_history) >= 2:
        prev_score = int(score_history.iloc[-2]["raw_score"])
        change = sc - prev_score
        if change > 0:
            change_html = (
                f"<div style='font-size:14px;color:#16a34a;font-weight:700;"
                f"margin-top:6px;'>&#9650; +{change} from previous</div>"
            )
        elif change < 0:
            change_html = (
                f"<div style='font-size:14px;color:#dc2626;font-weight:700;"
                f"margin-top:6px;'>&#9660; {change} from previous</div>"
            )
        else:
            change_html = (
                "<div style='font-size:14px;color:#94a3b8;font-weight:600;"
                "margin-top:6px;'>&#8212; No change from previous</div>"
            )

    # HERO CARD
    st.markdown(
        "<div class='score-card'>"
        "<div class='score-title'>Current Score</div>"
        f"<div class='score-number' style='color:{score_color(sc)}'>{sc}</div>"
        "<div class='score-denominator'>/ 100</div>"
        f"<div class='score-condition' style='color:{condition_color(cond)}'>{cond}</div>"
        f"{change_html}"
        f"<div class='score-timestamp'>Last updated: {ts_pretty}</div>"
        "</div>",
        unsafe_allow_html=True
    )

    # REFRESH NOW
    if st.button("Refresh Now", type="primary", use_container_width=True, key="refresh_a",
                 help="Fetch the latest market data. Takes ~45 seconds."):
        with st.spinner("Fetching latest market data... ~45 seconds"):
            ok, msg = trigger_workflow()
        if ok:
            st.success(f"{msg}")
            st.balloons()
        else:
            st.error(f"{msg}")

    # ============================================================
    # IMPROVEMENT 3: NIFTY vs 200 DMA GAP
    # ============================================================
    nifty_price = live.get("Nifty 50")
    if nifty_price and dma_200:
        try:
            nifty_val = float(nifty_price)
            gap_pct = ((nifty_val - dma_200) / dma_200) * 100
            gap_color = "#16a34a" if gap_pct >= 0 else "#dc2626"
            gap_sign = "+" if gap_pct >= 0 else ""
            above_below = "Above" if gap_pct >= 0 else "Below"
            dma_direction = str(score.get("dma_direction", ""))
            dir_badge = ""
            if dma_direction:
                dir_color = "#16a34a" if dma_direction == "Rising" else "#dc2626"
                dir_badge = (
                    f"<span style='background:{dir_color};color:white;font-size:10px;"
                    f"padding:3px 8px;border-radius:6px;font-weight:600;"
                    f"margin-left:8px;'>{dma_direction}</span>"
                )
            st.markdown(
                "<div class='data-card' style='padding:16px 18px;'>"
                "<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;'>"
                "<div style='font-size:12px;color:#94a3b8;text-transform:uppercase;"
                "letter-spacing:1.5px;font-weight:600;'>Nifty vs 200 DMA</div>"
                f"<div style='font-size:13px;font-weight:700;color:{gap_color};'>"
                f"{gap_sign}{gap_pct:.1f}% {above_below}{dir_badge}</div>"
                "</div>"
                "<div style='display:flex;justify-content:space-between;'>"
                "<div>"
                "<div style='font-size:11px;color:#94a3b8;'>Nifty 50</div>"
                f"<div style='font-size:18px;font-weight:800;color:#1e293b;'>{nifty_val:,.0f}</div>"
                "</div>"
                "<div style='text-align:right;'>"
                "<div style='font-size:11px;color:#94a3b8;'>200 DMA</div>"
                f"<div style='font-size:18px;font-weight:800;color:#64748b;'>{dma_200:,.0f}</div>"
                "</div>"
                "</div>"
                "<div style='height:6px;background:#e2e8f0;border-radius:4px;margin-top:10px;overflow:hidden;'>"
                f"<div style='height:100%;width:{min(100, max(5, 50 + gap_pct * 2))}%;"
                f"background:{gap_color};border-radius:4px;transition:width 0.5s ease;'></div>"
                "</div>"
                "</div>",
                unsafe_allow_html=True
            )
        except: pass

    # ALLOCATION
    eq = int(score["equity_pct"])
    # New 3-engine equity split: B=30%, C=30%, D=40%
    # NOTE: Don't round percentages — calculate amounts directly from equity amount to avoid banker's rounding
    debt = int(score["debt_pct"]); gold = int(score["gold_pct"])
    dur = score["duration_signal"]; gsig = score["gold_signal"]

    st.markdown("<div class='section-title'>Suggested Allocation</div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            "<div class='alloc-tile'>"
            "<div class='alloc-label'>Equity</div>"
            f"<div class='alloc-pct' style='color:#16a34a'>{eq}%</div>"
            f"<div class='alloc-sub'>B: 30% · C: 30% · D: 40%</div>"
            "</div>",
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            "<div class='alloc-tile'>"
            "<div class='alloc-label'>Debt</div>"
            f"<div class='alloc-pct' style='color:#2563eb'>{debt}%</div>"
            f"<div class='alloc-sub'>{dur}</div>"
            "</div>",
            unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            "<div class='alloc-tile'>"
            "<div class='alloc-label'>Gold</div>"
            f"<div class='alloc-pct' style='color:#d97706'>{gold}%</div>"
            f"<div class='alloc-sub'>{gsig}</div>"
            "</div>",
            unsafe_allow_html=True
        )

    # SAFETY
    red_flag = score["red_flag"]; pe_bubble = score["pe_bubble"]
    rf_color = "bad" if red_flag == "YES" else "ok"
    pe_color = "bad" if pe_bubble == "YES" else "ok"
    st.markdown(
        "<div class='safety-row'>"
        "<div class='safety-badge'>"
        "<div class='label'>Red Flag</div>"
        f"<div class='value {rf_color}'>{red_flag}</div>"
        "</div>"
        "<div class='safety-badge'>"
        "<div class='label'>PE Bubble</div>"
        f"<div class='value {pe_color}'>{pe_bubble}</div>"
        "</div>"
        "</div>",
        unsafe_allow_html=True
    )

    # ============================================================
    # CAPITAL DEPLOYMENT
    # ============================================================
    total_capital = float(stocks_data.get("_capital", stocks_data.get("capital", 100000)))

    eq_amount = round(total_capital * eq / 100)
    eb_amount = round(eq_amount * 0.30)
    ec_amount = round(eq_amount * 0.30)
    ed_amount = round(eq_amount * 0.40)
    debt_amount = round(total_capital * debt / 100)
    gold_amount = round(total_capital * gold / 100)

    b_invested = 0; b_current = 0
    for s in stocks_data.get("engine_b", []) + stocks_data.get("momentum", []):
        try:
            entry = float(s.get("entry", s.get("buy_price", s.get("avg_price", 0))))
            qty = int(s.get("qty", s.get("quantity", 0)))
            b_invested += entry * qty
            ticker = s.get("ticker", s.get("symbol", ""))
            cur_price = stock_prices.get(ticker, entry)
            b_current += cur_price * qty
        except: pass

    c_invested = 0; c_current = 0
    for s in stocks_data.get("engine_c", []) + stocks_data.get("value", []):
        try:
            entry = float(s.get("entry", s.get("buy_price", s.get("avg_price", 0))))
            qty = int(s.get("qty", s.get("quantity", 0)))
            c_invested += entry * qty
            ticker = s.get("ticker", s.get("symbol", ""))
            cur_price = stock_prices.get(ticker, entry)
            c_current += cur_price * qty
        except: pass

    d_invested = 0; d_current = 0
    for s in stocks_data.get("engine_d", []) + stocks_data.get("compounders", []):
        try:
            entry = float(s.get("entry", s.get("buy_price", s.get("avg_price", 0))))
            qty = int(s.get("qty", s.get("quantity", 0)))
            d_invested += entry * qty
            ticker = s.get("ticker", s.get("symbol", ""))
            cur_price = stock_prices.get(ticker, entry)
            d_current += cur_price * qty
        except: pass

    total_invested = b_invested + c_invested + d_invested
    total_current = b_current + c_current + d_current
    total_pnl = total_current - total_invested
    pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
    pnl_color = "#16a34a" if total_pnl >= 0 else "#dc2626"
    pnl_sign = "+" if total_pnl >= 0 else ""

    b_available = round(max(0, eb_amount - b_invested))
    c_available = round(max(0, ec_amount - c_invested))
    d_available = round(max(0, ed_amount - d_invested))

    st.markdown("<div class='section-title'>Capital Deployment</div>", unsafe_allow_html=True)

    # Total capital hero + edit
    st.markdown(
        "<div class='data-card' style='text-align:center;padding:20px;'>"
        "<div style='font-size:11px;color:#94a3b8;text-transform:uppercase;"
        "letter-spacing:2px;font-weight:600;margin-bottom:6px;'>Total Capital</div>"
        f"<div style='font-size:32px;font-weight:800;color:#1e293b;"
        f"font-family:DM Sans,sans-serif;'>₹{total_capital:,.0f}</div>"
        "</div>",
        unsafe_allow_html=True
    )

    with st.expander("Edit Capital", expanded=False):
        new_capital = st.number_input(
            "Total Capital (₹)",
            value=total_capital,
            min_value=0.0,
            step=10000.0,
            format="%.0f",
            key="edit_capital",
            label_visibility="collapsed",
        )
        if st.button("Save Capital", type="primary", use_container_width=True, key="save_capital"):
            token = get_github_token()
            if not token:
                st.error("GITHUB_TOKEN not configured.")
            else:
                with st.spinner("Saving..."):
                    try:
                        stocks_path = "data/engine_b_stocks.json"
                        api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{stocks_path}"
                        headers = {
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/vnd.github+json",
                            "X-GitHub-Api-Version": "2022-11-28",
                        }
                        get_resp = requests.get(api_url, headers=headers, params={"ref": GITHUB_BRANCH}, timeout=15)
                        if get_resp.status_code != 200:
                            st.error(f"Failed to read file: {get_resp.status_code}")
                        else:
                            cur_sha = get_resp.json().get("sha")
                            file_content = base64.b64decode(get_resp.json()["content"]).decode("utf-8")
                            file_data = json.loads(file_content)
                            file_data["_capital"] = int(new_capital)
                            file_data["capital"] = int(new_capital)
                            new_content = json.dumps(file_data, indent=2, ensure_ascii=False)
                            put_body = {
                                "message": f"Update capital to {int(new_capital)}",
                                "content": base64.b64encode(new_content.encode("utf-8")).decode("ascii"),
                                "sha": cur_sha,
                                "branch": GITHUB_BRANCH,
                            }
                            put_resp = requests.put(api_url, headers=headers, json=put_body, timeout=15)
                            if put_resp.status_code in (200, 201):
                                st.success(f"Capital updated to ₹{int(new_capital):,}. Refresh to see changes.")
                            else:
                                st.error(f"Save failed: {put_resp.status_code}")
                    except Exception as e:
                        st.error(f"Error: {e}")

    # Allocation breakdown in rupees
    alloc_html = (
        "<div class='data-row'>"
        "<div class='data-label'>Engine B (Momentum)</div>"
        f"<div class='data-value' style='color:#16a34a'>₹{eb_amount:,}</div>"
        "</div>"
        "<div class='data-row'>"
        "<div class='data-label'>Engine C (Value)</div>"
        f"<div class='data-value' style='color:#16a34a'>₹{ec_amount:,}</div>"
        "</div>"
        "<div class='data-row'>"
        "<div class='data-label'>Engine D (Compounder)</div>"
        f"<div class='data-value' style='color:#16a34a'>₹{ed_amount:,}</div>"
        "</div>"
        "<div class='data-row'>"
        "<div class='data-label'>Debt</div>"
        f"<div class='data-value' style='color:#2563eb'>₹{debt_amount:,}</div>"
        "</div>"
        "<div class='data-row'>"
        "<div class='data-label'>Gold</div>"
        f"<div class='data-value' style='color:#d97706'>₹{gold_amount:,}</div>"
        "</div>"
    )
    st.markdown(f"<div class='data-card'>{alloc_html}</div>", unsafe_allow_html=True)

    # Portfolio status
    if total_invested > 0:
        status_html = (
            "<div class='data-row'>"
            "<div class='data-label'>Total Invested</div>"
            f"<div class='data-value'>₹{total_invested:,.0f}</div>"
            "</div>"
            "<div class='data-row'>"
            "<div class='data-label'>Current Value</div>"
            f"<div class='data-value'>₹{total_current:,.0f}</div>"
            "</div>"
            "<div class='data-row'>"
            "<div class='data-label'>P&L</div>"
            f"<div class='data-value' style='color:{pnl_color}'>"
            f"{pnl_sign}₹{abs(total_pnl):,.0f} ({pnl_sign}{pnl_pct:.1f}%)</div>"
            "</div>"
            "<div class='data-row'>"
            "<div class='data-label'>Cash Available</div>"
            f"<div class='data-value'>₹{total_capital - total_invested:,.0f}</div>"
            "</div>"
        )
        st.markdown(f"<div class='data-card'>{status_html}</div>", unsafe_allow_html=True)

    # Deployment status per engine
    deploy_html = (
        "<div class='data-row'>"
        "<div class='data-label'>Engine B — Deployed</div>"
        f"<div class='data-value'>₹{b_invested:,.0f} / ₹{eb_amount:,}</div>"
        "</div>"
        "<div class='data-row'>"
        "<div class='data-label'>Engine B — Available</div>"
        f"<div class='data-value' style='color:#16a34a'>₹{b_available:,}</div>"
        "</div>"
        "<div class='data-row'>"
        "<div class='data-label'>Engine C — Deployed</div>"
        f"<div class='data-value'>₹{c_invested:,.0f} / ₹{ec_amount:,}</div>"
        "</div>"
        "<div class='data-row'>"
        "<div class='data-label'>Engine C — Available</div>"
        f"<div class='data-value' style='color:#16a34a'>₹{c_available:,}</div>"
        "</div>"
        "<div class='data-row'>"
        "<div class='data-label'>Engine D — Deployed</div>"
        f"<div class='data-value'>₹{d_invested:,.0f} / ₹{ed_amount:,}</div>"
        "</div>"
        "<div class='data-row'>"
        "<div class='data-label'>Engine D — Available</div>"
        f"<div class='data-value' style='color:#16a34a'>₹{d_available:,}</div>"
        "</div>"
    )
    st.markdown(f"<div class='data-card'>{deploy_html}</div>", unsafe_allow_html=True)

    # ============================================================
    # TAX ESTIMATE
    # ============================================================
    today_date = datetime.now().date()

    realized_stcg = 0; realized_ltcg = 0
    stcg_trades = 0; ltcg_trades = 0

    for trade in stocks_data.get("engine_b_closed", []) + stocks_data.get("engine_c_closed", []) + stocks_data.get("engine_d_closed", []):
        try:
            pnl = float(trade.get("pnl", 0))
            buy_date_str = trade.get("buy_date", "")
            sell_date_str = trade.get("exit_date", trade.get("sell_date", ""))
            if buy_date_str and sell_date_str:
                buy_dt = datetime.strptime(buy_date_str, "%Y-%m-%d").date()
                sell_dt = datetime.strptime(sell_date_str, "%Y-%m-%d").date()
                holding_days = (sell_dt - buy_dt).days
            else:
                holding_days = 0
            if holding_days >= 365:
                realized_ltcg += pnl
                ltcg_trades += 1
            else:
                realized_stcg += pnl
                stcg_trades += 1
        except: pass

    unrealized_stcg = 0; unrealized_ltcg = 0
    stcg_positions = 0; ltcg_positions = 0

    for s in stocks_data.get("engine_b", []) + stocks_data.get("engine_c", []) + stocks_data.get("engine_d", []) + stocks_data.get("momentum", []) + stocks_data.get("value", []) + stocks_data.get("compounders", []):
        try:
            entry = float(s.get("entry", s.get("buy_price", s.get("avg_price", 0))))
            qty = int(s.get("qty", s.get("quantity", 0)))
            ticker = s.get("ticker", s.get("symbol", ""))
            cur_price = stock_prices.get(ticker, entry)
            unrealized_pnl = (cur_price - entry) * qty
            buy_date_str = s.get("buy_date", "")
            if buy_date_str:
                buy_dt = datetime.strptime(buy_date_str, "%Y-%m-%d").date()
                holding_days = (today_date - buy_dt).days
            else:
                holding_days = 0
            if holding_days >= 365:
                unrealized_ltcg += unrealized_pnl
                ltcg_positions += 1
            else:
                unrealized_stcg += unrealized_pnl
                stcg_positions += 1
        except: pass

    stcg_tax = max(0, realized_stcg * 0.20)
    ltcg_taxable = max(0, realized_ltcg - 125000)
    ltcg_tax = ltcg_taxable * 0.125
    total_tax = stcg_tax + ltcg_tax
    total_realized = realized_stcg + realized_ltcg
    post_tax_pnl = total_realized - total_tax

    has_realized = (realized_stcg != 0 or realized_ltcg != 0)
    has_unrealized = (unrealized_stcg != 0 or unrealized_ltcg != 0)
    has_positions = len(stocks_data.get("engine_b", [])) + len(stocks_data.get("engine_c", [])) + len(stocks_data.get("engine_d", [])) + len(stocks_data.get("momentum", [])) + len(stocks_data.get("value", [])) + len(stocks_data.get("compounders", [])) > 0
    has_closed = len(stocks_data.get("engine_b_closed", [])) + len(stocks_data.get("engine_c_closed", [])) + len(stocks_data.get("engine_d_closed", [])) > 0

    st.markdown("<div class='section-title'>Tax Estimate (FY 2026-27)</div>", unsafe_allow_html=True)

    st.markdown(
        "<div class='data-card' style='padding:14px 18px;'>"
        "<div class='data-row'>"
        "<div class='data-label'>STCG Rate (< 12 months)</div>"
        "<div class='data-value' style='color:#d97706'>20%</div>"
        "</div>"
        "<div class='data-row'>"
        "<div class='data-label'>LTCG Rate (≥ 12 months)</div>"
        "<div class='data-value' style='color:#2563eb'>12.5%</div>"
        "</div>"
        "<div class='data-row'>"
        "<div class='data-label'>LTCG Exemption</div>"
        "<div class='data-value'>₹1,25,000 / year</div>"
        "</div>"
        "</div>",
        unsafe_allow_html=True
    )

    if has_realized or has_closed:
        r_stcg_color = "#16a34a" if realized_stcg >= 0 else "#dc2626"
        r_ltcg_color = "#16a34a" if realized_ltcg >= 0 else "#dc2626"
        r_stcg_sign = "+" if realized_stcg >= 0 else ""
        r_ltcg_sign = "+" if realized_ltcg >= 0 else ""
        post_color = "#16a34a" if post_tax_pnl >= 0 else "#dc2626"
        post_sign = "+" if post_tax_pnl >= 0 else ""

        tax_html = (
            "<div class='data-row'>"
            f"<div class='data-label'>Realized STCG ({stcg_trades} trades)</div>"
            f"<div class='data-value' style='color:{r_stcg_color}'>"
            f"{r_stcg_sign}₹{abs(realized_stcg):,.0f}</div>"
            "</div>"
            "<div class='data-row'>"
            f"<div class='data-label'>Realized LTCG ({ltcg_trades} trades)</div>"
            f"<div class='data-value' style='color:{r_ltcg_color}'>"
            f"{r_ltcg_sign}₹{abs(realized_ltcg):,.0f}</div>"
            "</div>"
            "<div class='data-row' style='border-top:2px solid #e2e8f0;margin-top:4px;padding-top:12px;'>"
            "<div class='data-label'>Estimated STCG Tax (20%)</div>"
            f"<div class='data-value' style='color:#dc2626'>₹{stcg_tax:,.0f}</div>"
            "</div>"
            "<div class='data-row'>"
            "<div class='data-label'>Estimated LTCG Tax (12.5%)</div>"
            f"<div class='data-value' style='color:#dc2626'>₹{ltcg_tax:,.0f}</div>"
            "</div>"
            "<div class='data-row' style='border-top:2px solid #e2e8f0;margin-top:4px;padding-top:12px;'>"
            "<div class='data-label' style='font-weight:700;color:#1e293b;'>Post-Tax P&L</div>"
            f"<div class='data-value' style='color:{post_color};font-size:15px;'>"
            f"{post_sign}₹{abs(post_tax_pnl):,.0f}</div>"
            "</div>"
        )
        st.markdown(f"<div class='data-card'>{tax_html}</div>", unsafe_allow_html=True)

    if has_positions:
        u_stcg_color = "#16a34a" if unrealized_stcg >= 0 else "#dc2626"
        u_ltcg_color = "#16a34a" if unrealized_ltcg >= 0 else "#dc2626"
        u_stcg_sign = "+" if unrealized_stcg >= 0 else ""
        u_ltcg_sign = "+" if unrealized_ltcg >= 0 else ""

        unr_html = (
            "<div class='data-row'>"
            f"<div class='data-label'>Unrealized STCG ({stcg_positions} pos)</div>"
            f"<div class='data-value' style='color:{u_stcg_color}'>"
            f"{u_stcg_sign}₹{abs(unrealized_stcg):,.0f}</div>"
            "</div>"
            "<div class='data-row'>"
            f"<div class='data-label'>Unrealized LTCG ({ltcg_positions} pos)</div>"
            f"<div class='data-value' style='color:{u_ltcg_color}'>"
            f"{u_ltcg_sign}₹{abs(unrealized_ltcg):,.0f}</div>"
            "</div>"
        )
        st.markdown(f"<div class='data-card'>{unr_html}</div>", unsafe_allow_html=True)

    if not has_realized and not has_positions and not has_closed:
        st.markdown(
            "<div class='data-card' style='text-align:center;padding:20px;color:#94a3b8;'>"
            "No trades yet. Tax estimates will appear once you start trading."
            "</div>",
            unsafe_allow_html=True
        )

    # ============================================================
    # IMPROVEMENT 1: SCORE HISTORY CHART
    # ============================================================
    st.markdown("<div class='section-title'>Score History</div>", unsafe_allow_html=True)

    if not score_history.empty and len(score_history) >= 2:
        chart_df = score_history[["timestamp", "raw_score"]].copy()
        chart_df = chart_df.rename(columns={"timestamp": "Date", "raw_score": "Score"})
        chart_df["Date"] = chart_df["Date"].dt.strftime("%d %b")
        chart_df["Score"] = chart_df["Score"].astype(int)

        # Show last 12 data points max for clean mobile view
        chart_df = chart_df.tail(12)

        # Build score band colors inline
        scores = chart_df["Score"].tolist()
        dates = chart_df["Date"].tolist()

        # SVG sparkline chart
        n = len(scores)
        min_s = max(0, min(scores) - 10)
        max_s = min(100, max(scores) + 10)
        range_s = max_s - min_s if max_s != min_s else 1
        w = 320; h = 120; pad = 20

        points = []
        for i, s in enumerate(scores):
            x = pad + i * ((w - 2 * pad) / max(1, n - 1))
            y = h - pad - ((s - min_s) / range_s) * (h - 2 * pad)
            points.append((x, y, s, dates[i]))

        polyline = " ".join([f"{p[0]:.1f},{p[1]:.1f}" for p in points])

        # Color-coded score bands background
        svg = f"<svg viewBox='0 0 {w} {h}' style='width:100%;height:auto;'>"
        # Score band guides
        for band_val in [30, 52]:
            band_y = h - pad - ((band_val - min_s) / range_s) * (h - 2 * pad)
            if pad < band_y < h - pad:
                svg += (f"<line x1='{pad}' y1='{band_y:.1f}' x2='{w-pad}' y2='{band_y:.1f}' "
                        f"stroke='#e2e8f0' stroke-width='1' stroke-dasharray='4,4'/>")
                label = "WEAK" if band_val == 30 else "NEUTRAL"
                svg += (f"<text x='{w-pad+4}' y='{band_y+4:.1f}' fill='#94a3b8' "
                        f"font-size='8' font-family='DM Sans'>{label}</text>")

        # Line
        svg += (f"<polyline fill='none' stroke='#3b82f6' stroke-width='2.5' "
                f"stroke-linecap='round' stroke-linejoin='round' points='{polyline}'/>")

        # Gradient fill under line
        fill_points = polyline + f" {points[-1][0]:.1f},{h-pad} {points[0][0]:.1f},{h-pad}"
        svg += (f"<defs><linearGradient id='sg' x1='0' y1='0' x2='0' y2='1'>"
                f"<stop offset='0%' stop-color='#3b82f6' stop-opacity='0.15'/>"
                f"<stop offset='100%' stop-color='#3b82f6' stop-opacity='0.02'/>"
                f"</linearGradient></defs>")
        svg += f"<polygon fill='url(#sg)' points='{fill_points}'/>"

        # Dots + labels
        for i, (x, y, s, d) in enumerate(points):
            color = score_color(s)
            svg += f"<circle cx='{x:.1f}' cy='{y:.1f}' r='4' fill='{color}' stroke='white' stroke-width='2'/>"
            # Show value on first, last, and every 3rd point
            if i == 0 or i == len(points) - 1 or i % 3 == 0:
                svg += (f"<text x='{x:.1f}' y='{y-10:.1f}' text-anchor='middle' "
                        f"fill='{color}' font-size='10' font-weight='700' font-family='DM Sans'>{s}</text>")
                svg += (f"<text x='{x:.1f}' y='{h-4:.1f}' text-anchor='middle' "
                        f"fill='#94a3b8' font-size='8' font-family='DM Sans'>{d}</text>")

        svg += "</svg>"

        st.markdown(
            f"<div class='data-card' style='padding:16px 12px;'>{svg}</div>",
            unsafe_allow_html=True
        )

        # Quick stats row
        latest = scores[-1]
        oldest = scores[0]
        high = max(scores)
        low = min(scores)
        avg = sum(scores) / len(scores)
        total_change = latest - oldest
        tc_color = "#16a34a" if total_change >= 0 else "#dc2626"
        tc_sign = "+" if total_change >= 0 else ""

        stats_html = (
            "<div class='data-row'>"
            "<div class='data-label'>Period High</div>"
            f"<div class='data-value' style='color:#16a34a'>{high}</div>"
            "</div>"
            "<div class='data-row'>"
            "<div class='data-label'>Period Low</div>"
            f"<div class='data-value' style='color:#dc2626'>{low}</div>"
            "</div>"
            "<div class='data-row'>"
            "<div class='data-label'>Average</div>"
            f"<div class='data-value'>{avg:.0f}</div>"
            "</div>"
            "<div class='data-row'>"
            "<div class='data-label'>Total Change</div>"
            f"<div class='data-value' style='color:{tc_color}'>{tc_sign}{total_change}</div>"
            "</div>"
        )
        st.markdown(f"<div class='data-card'>{stats_html}</div>", unsafe_allow_html=True)

    else:
        st.markdown(
            "<div class='data-card' style='text-align:center;padding:20px;color:#94a3b8;'>"
            "Score history chart will appear after 2+ data points are logged. "
            "Each cron run appends to score_history.csv."
            "</div>",
            unsafe_allow_html=True
        )

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
            f"<div style='flex:0 0 90px;color:#64748b;font-weight:500;'>{label}</div>"
            f"<div style='flex:1;height:8px;background:#e2e8f0;border-radius:6px;overflow:hidden;margin:0 10px;'>"
            f"<div style='height:100%;width:{bar_w}%;background:{color};border-radius:6px;"
            f"transition:width 0.5s ease;'></div></div>"
            f"<div style='flex:0 0 60px;text-align:right;font-weight:700;color:{color}'>{val}/{mx}</div>"
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
        ind_html += (
            f"<div class='data-row'>"
            f"<div class='data-label'>{label}</div>"
            f"<div class='data-value'>{fmt_num(val)}</div>"
            f"</div>"
        )
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
        glb_html += (
            f"<div class='data-row'>"
            f"<div class='data-label'>{label}</div>"
            f"<div class='data-value'>{val_str}</div>"
            f"</div>"
        )
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
        man_html += (
            f"<div class='data-row'>"
            f"<div class='data-label'>{label}</div>"
            f"<div class='data-value'>{val}</div>"
            f"</div>"
        )
    st.markdown(f"<div class='data-card'>{man_html}</div>", unsafe_allow_html=True)

    # INPUT UPDATE FORM
    st.markdown("<div class='section-title'>Update Inputs</div>", unsafe_allow_html=True)

    token = get_github_token()
    if not token:
        st.warning("GITHUB_TOKEN not set in Streamlit secrets.")

    with st.expander("Tap to expand & edit", expanded=False):
        st.caption("For each input: tap the source link, read the value, type it in, then hit Save & Rescore at the bottom.")
        new_values = {}
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
            if not obj: continue
            label = pretty_labels.get(key, key)
            cur_val = obj.get("value")
            url = obj.get("where_to_find", "")
            source_label = obj.get("source_label", "Source")
            input_type = obj.get("input_type", "number")

            st.markdown(f"<div class='input-card-label'>{label}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='input-card-current'>Current: <b>{cur_val}</b></div>", unsafe_allow_html=True)
            if url:
                st.markdown(f"[Open in {source_label}]({url})")

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

        if st.button("Save & Rescore", type="primary", use_container_width=True, key="save_a"):
            if not token:
                st.error("Cannot save: GITHUB_TOKEN not configured in Streamlit secrets.")
            else:
                with st.spinner("Saving values to GitHub..."):
                    updated = json.loads(json.dumps(manual_full))
                    for key, val in new_values.items():
                        if key in updated:
                            if key in ("fii_30day_net_cr", "dii_30day_net_cr"):
                                try: val = int(val)
                                except: pass
                            updated[key]["value"] = val
                    updated["_last_updated"] = datetime.now().strftime("%Y-%m-%d")
                    new_content = json.dumps(updated, indent=2, ensure_ascii=False)

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
                            return
                        cur_sha = get_resp.json().get("sha")

                        put_body = {
                            "message": f"Dashboard update: manual inputs ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
                            "content": base64.b64encode(new_content.encode("utf-8")).decode("ascii"),
                            "sha": cur_sha,
                            "branch": GITHUB_BRANCH,
                        }
                        put_resp = requests.put(api_base, headers=headers, json=put_body, timeout=15)
                        if put_resp.status_code in (200, 201):
                            st.success("Saved to GitHub! Triggering rescore...")
                        else:
                            st.error(f"GitHub PUT failed: {put_resp.status_code} {put_resp.text[:200]}")
                            return

                        ok, msg = trigger_workflow()
                        if ok:
                            st.success(f"{msg}")
                            st.balloons()
                        else:
                            st.warning(f"Save succeeded but: {msg}")
                    except requests.RequestException as e:
                        st.error(f"Network error: {e}")
