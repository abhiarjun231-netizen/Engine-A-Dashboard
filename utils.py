"""
utils.py - Shared utilities for all engines
GitHub API, CSV parsing, formatting, card rendering
"""
import streamlit as st
import pandas as pd
import json
import base64
import requests
import io
from pathlib import Path
from datetime import datetime, date

# ============================================================
# GITHUB CONFIG
# ============================================================
GITHUB_OWNER = "abhiarjun231-netizen"
GITHUB_REPO = "Engine-A-Dashboard"
GITHUB_BRANCH = "main"

STOCKS_FILE = Path("data/engine_b_stocks.json")
PRICES_FILE = Path("data/engine_b_prices.csv")
ANALYSIS_FILE = Path("data/stock_analysis.csv")

def load_stock_analysis():
    """Load stock analysis data (volume ratio, 52W, trends) from CSV."""
    if not ANALYSIS_FILE.exists():
        return {}
    try:
        df = pd.read_csv(ANALYSIS_FILE)
        result = {}
        for _, row in df.iterrows():
            tk = str(row.get("ticker", "")).strip()
            if tk:
                result[tk] = {
                    "vol_ratio": round(float(row.get("vol_ratio", 0)), 2),
                    "high_52w_live": float(row.get("high_52w", 0)),
                    "low_52w_live": float(row.get("low_52w", 0)),
                    "pct_52w": float(row.get("pct_52w", 0)),
                    "change_60d": float(row.get("change_60d", 0)),
                    "change_90d": float(row.get("change_90d", 0)),
                }
        return result
    except:
        return {}

def get_github_token():
    try:
        return st.secrets["GITHUB_TOKEN"]
    except Exception:
        return None

def trigger_workflow():
    token = get_github_token()
    if not token:
        return False, "GITHUB_TOKEN not configured."
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/test.yml/dispatches"
    try:
        resp = requests.post(url, headers=headers, json={"ref": GITHUB_BRANCH}, timeout=15)
        if resp.status_code == 204:
            return True, "Refresh triggered. Reload in ~45 seconds."
        return False, f"Trigger failed ({resp.status_code})."
    except requests.RequestException as e:
        return False, f"Network error: {e}"

def load_stocks_json():
    if not STOCKS_FILE.exists():
        return get_default_stocks_json()
    try:
        with open(STOCKS_FILE, "r") as f:
            return json.load(f)
    except:
        return get_default_stocks_json()

def get_default_stocks_json():
    return {
        "engine_b": [], "engine_c": [], "engine_d": [],
        "engine_b_watchlist": [], "engine_c_watchlist": [], "engine_d_watchlist": [],
        "engine_b_closed": [], "engine_c_closed": [], "engine_d_closed": [],
        "_capital": 100000, "capital": 100000, "_token_cache": {},
        "_b_watchlist_date": "", "_c_watchlist_date": "", "_d_watchlist_date": "",
    }

def save_stocks_to_github(data, message="Dashboard update"):
    token = get_github_token()
    if not token:
        return False, "GITHUB_TOKEN not configured."
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    path = "data/engine_b_stocks.json"
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}"
    try:
        get_resp = requests.get(url, headers=headers, params={"ref": GITHUB_BRANCH}, timeout=15)
        if get_resp.status_code != 200:
            return False, f"GET failed: {get_resp.status_code}"
        sha = get_resp.json().get("sha")
        encoded = base64.b64encode(json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")).decode("ascii")
        put_body = {"message": message, "content": encoded, "sha": sha, "branch": GITHUB_BRANCH}
        put_resp = requests.put(url, headers=headers, json=put_body, timeout=15)
        if put_resp.status_code in (200, 201):
            return True, "Saved to GitHub."
        return False, f"PUT failed: {put_resp.status_code}"
    except requests.RequestException as e:
        return False, f"Network error: {e}"

def load_stock_prices():
    if not PRICES_FILE.exists():
        return {}
    try:
        df = pd.read_csv(PRICES_FILE)
        result = {}
        for _, row in df.iterrows():
            ticker = row.get("ticker", "")
            price = row.get("price", "")
            if ticker and price != "" and pd.notna(price):
                try:
                    result[ticker] = float(price)
                except:
                    pass
        return result
    except:
        return {}

# ============================================================
# CSV PARSING (Trendlyne)
# ============================================================
def parse_trendlyne_csv(uploaded_file):
    try:
        content = uploaded_file.read()
        try:
            text = content.decode("utf-8")
        except:
            text = content.decode("latin-1")

        df = pd.read_csv(io.StringIO(text))
        df.columns = [c.strip() for c in df.columns]

        col_map = {}
        for c in df.columns:
            cl = c.lower().replace("  ", " ")
            if "stock" in cl and "name" not in cl:
                col_map["stock"] = c
            elif "nse" in cl and "code" in cl:
                col_map["ticker"] = c
            elif "roe" in cl and "ann" in cl:
                col_map["roe"] = c
            elif "pe" in cl and "ttm" in cl and "peg" not in cl:
                col_map["pe"] = c
            elif "piotroski" in cl:
                col_map["piotroski"] = c
            elif "ltp" in cl or "price" in cl and "sma" not in cl and "change" not in cl:
                if "ltp" not in col_map:
                    col_map["ltp"] = c
            elif "market" in cl and "cap" in cl:
                col_map["mcap"] = c
            elif "debt" in cl and "equity" in cl:
                col_map["de"] = c
            elif "peg" in cl:
                col_map["peg"] = c
            elif "profit" in cl and "growth" in cl and "yoy" in cl:
                col_map["profit_growth"] = c
            elif "revenue" in cl and "qoq" in cl:
                col_map["rev_qoq"] = c
            elif "sector" in cl:
                col_map["sector"] = c
            elif "day" in cl and "sma200" in cl:
                col_map["sma200"] = c
            elif "durability" in cl:
                col_map["durability"] = c
            elif "momentum" in cl:
                col_map["momentum"] = c
            elif "promoter" in cl and "hold" in cl:
                col_map["promoter"] = c
            elif "fii" in cl and "hold" in cl:
                col_map["fii"] = c
            elif "dii" in cl and "hold" in cl:
                col_map["dii"] = c
            elif "52" in cl and "high" in cl:
                col_map["high_52w"] = c
            elif "52" in cl and "low" in cl:
                col_map["low_52w"] = c
            elif "1y high" in cl or ("1y" in cl and "high" in cl):
                col_map["high_52w"] = c
            elif "1y low" in cl or ("1y" in cl and "low" in cl):
                col_map["low_52w"] = c
            elif "roce" in cl:
                col_map["roce"] = c
            elif "mf" in cl and "hold" in cl:
                col_map["mf"] = c
            elif "institutional" in cl and "hold" in cl:
                col_map["inst"] = c
            elif "delivery" in cl and "%" in cl:
                col_map["delivery_pct"] = c
            elif "delivery" in cl and ("vol" in cl or "qty" in cl):
                if "delivery_pct" not in col_map:
                    col_map["delivery_pct"] = c
            elif "latest" in cl and "result" in cl:
                col_map["last_result"] = c
            elif "next" in cl and "result" in cl:
                col_map["next_result"] = c

        stocks = []
        for _, row in df.iterrows():
            stock = {}
            stock["name"] = str(row.get(col_map.get("stock", ""), "")).strip()
            stock["ticker"] = str(row.get(col_map.get("ticker", ""), "")).strip()

            if not stock["name"] or not stock["ticker"]:
                continue

            for key in ["roe", "pe", "piotroski", "ltp", "mcap", "de", "peg", "profit_growth", "rev_qoq", "sma200", "durability", "momentum", "promoter", "fii", "dii", "high_52w", "low_52w", "roce", "mf", "inst", "delivery_pct"]:
                if key in col_map:
                    try:
                        val = row.get(col_map[key], "")
                        stock[key] = float(str(val).replace(",", "").strip()) if pd.notna(val) and str(val).strip() != "" else None
                    except:
                        stock[key] = None
                else:
                    stock[key] = None

            if "sector" in col_map:
                stock["sector"] = str(row.get(col_map["sector"], "")).strip()
            else:
                stock["sector"] = ""

            for str_key in ["last_result", "next_result"]:
                if str_key in col_map:
                    stock[str_key] = str(row.get(col_map[str_key], "")).strip()
                else:
                    stock[str_key] = ""

            stocks.append(stock)

        return stocks, None
    except Exception as e:
        return [], str(e)

def parse_trendlyne_text(text_content):
    """Parse pasted CSV text — mobile-friendly alternative to file upload."""
    try:
        import io as _io
        fake_file = _io.BytesIO(text_content.encode("utf-8"))
        return parse_trendlyne_csv(fake_file)
    except Exception as e:
        return [], str(e)

def load_screener_from_github(prefix):
    """Load a screener CSV from GitHub data/ folder by prefix match.
    Finds the latest file starting with the given prefix.
    E.g. prefix='Mom' matches 'Mom 1_April 26, 2026.csv'
    """
    import urllib.parse
    token = get_github_token()
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # List files in data/ folder
    api_url = (
        f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
        f"/contents/data?ref={GITHUB_BRANCH}"
    )
    try:
        resp = requests.get(api_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return [], f"Could not list data/ folder ({resp.status_code})"

        files = resp.json()
        # Find CSV files matching the prefix
        matches = [
            f["name"] for f in files
            if isinstance(f, dict)
            and f.get("name", "").lower().startswith(prefix.lower())
            and f.get("name", "").lower().endswith((".csv", ".xlsx"))
        ]

        if not matches:
            return [], f"No file starting with '{prefix}' found in data/ folder."

        # Pick latest (sorted descending — date in name helps)
        matches.sort(reverse=True)
        chosen = matches[0]

        # Download the file
        raw_url = (
            f"https://raw.githubusercontent.com/"
            f"{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/data/"
            f"{urllib.parse.quote(chosen)}"
        )
        dl = requests.get(raw_url, timeout=15)
        if dl.status_code == 200:
            stocks, err = parse_trendlyne_text(dl.text)
            if err:
                return [], err
            return stocks, None
        else:
            return [], f"Download failed for {chosen} ({dl.status_code})"

    except requests.RequestException as e:
        return [], f"Network error: {e}"

# ============================================================
# FORMATTING HELPERS
# ============================================================
def fmt(n, d=2):
    if n is None or (isinstance(n, float) and pd.isna(n)):
        return "—"
    try:
        return f"{float(n):,.{d}f}"
    except:
        return str(n)

def fmt_pnl(n):
    if n is None:
        return "—", "#64748b"
    sign = "+" if n >= 0 else ""
    color = "#16a34a" if n >= 0 else "#dc2626"
    return f"{sign}{n:,.0f}", color

def fmt_pct(n):
    if n is None:
        return "—", "#64748b"
    sign = "+" if n >= 0 else ""
    color = "#16a34a" if n >= 0 else "#dc2626"
    return f"{sign}{n:.1f}%", color

def days_held(buy_date_str):
    if not buy_date_str:
        return 0
    try:
        buy_dt = datetime.strptime(buy_date_str, "%Y-%m-%d").date()
        return (date.today() - buy_dt).days
    except:
        return 0

# ============================================================
# UI CARD BUILDERS
# ============================================================
def render_section_title(text):
    st.markdown(f"<div class='section-title'>{text}</div>", unsafe_allow_html=True)

def render_info_card(text):
    st.markdown(
        f"<div class='data-card' style='text-align:center;padding:24px;color:#94a3b8;"
        f"font-size:13px;'>{text}</div>",
        unsafe_allow_html=True
    )

def render_stat_row(label, value, color=None):
    c = f" style='color:{color}'" if color else ""
    return (
        f"<div class='data-row'>"
        f"<div class='data-label'>{label}</div>"
        f"<div class='data-value'{c}>{value}</div>"
        f"</div>"
    )

def render_data_card(rows_html):
    st.markdown(f"<div class='data-card'>{rows_html}</div>", unsafe_allow_html=True)

def render_hero_number(label, value, color="#1e293b", subtitle=""):
    sub_html = f"<div style='font-size:11px;color:#94a3b8;margin-top:4px;'>{subtitle}</div>" if subtitle else ""
    st.markdown(
        f"<div class='data-card' style='text-align:center;padding:20px;'>"
        f"<div style='font-size:11px;color:#94a3b8;text-transform:uppercase;"
        f"letter-spacing:2px;font-weight:600;margin-bottom:6px;'>{label}</div>"
        f"<div style='font-size:28px;font-weight:800;color:{color};"
        f"font-family:DM Sans,sans-serif;'>{value}</div>"
        f"{sub_html}</div>",
        unsafe_allow_html=True
    )

def render_badge(text, bg_color, text_color="#ffffff"):
    return (
        f"<span style='background:{bg_color};color:{text_color};"
        f"font-size:10px;padding:3px 10px;border-radius:6px;"
        f"font-weight:700;letter-spacing:0.5px;'>{text}</span>"
    )

def render_stage_badge(stage):
    colors = {
        # Engine B stages
        "SCOUT": ("#dbeafe", "#2563eb"),
        "STALK": ("#fef3c7", "#d97706"),
        "STRIKE": ("#d1fae5", "#059669"),
        "RIDE": ("#d1fae5", "#059669"),
        "PROFIT RIDE": ("#bbf7d0", "#16a34a"),
        "PROFIT LOCKED": ("#86efac", "#15803d"),
        "PROFIT TRAIL": ("#4ade80", "#166534"),
        "GUARD": ("#fed7aa", "#ea580c"),
        "EXIT": ("#fecaca", "#dc2626"),
        # Engine C stages
        "DISCOVER": ("#dbeafe", "#2563eb"),
        "EVALUATE": ("#fef3c7", "#d97706"),
        "ACCUMULATE": ("#d1fae5", "#059669"),
        "COMPOUND": ("#d1fae5", "#059669"),
        "HARVEST": ("#86efac", "#15803d"),
        # Engine D stages
        "IDENTIFY": ("#dbeafe", "#2563eb"),
        "INVESTIGATE": ("#fef3c7", "#d97706"),
        "INITIATE": ("#d1fae5", "#059669"),
        "INCUBATE": ("#e0e7ff", "#4338ca"),
        "INTENSIFY": ("#86efac", "#15803d"),
        "IMMORTAL": ("#fbbf24", "#78350f"),
        "LEGENDARY": ("#f59e0b", "#451a03"),
        # Common
        "RISK-FREE": ("#d1fae5", "#059669"),
        "RUNNING": ("#dbeafe", "#2563eb"),
        "WATCHING": ("#fed7aa", "#ea580c"),
        "STOP HIT": ("#fecaca", "#dc2626"),
        # Intelligence badges
        "STRIKE NOW": ("#d1fae5", "#059669"),
        "STALK MORE": ("#fef3c7", "#d97706"),
        "WEAK SIGNAL": ("#f1f5f9", "#94a3b8"),
        "DEEP VALUE GEM": ("#d1fae5", "#059669"),
        "SOLID VALUE": ("#dbeafe", "#2563eb"),
        "MODERATE VALUE": ("#fef3c7", "#d97706"),
        "THIN VALUE": ("#f1f5f9", "#94a3b8"),
        "ELITE": ("#d1fae5", "#059669"),
        "STRONG": ("#dbeafe", "#2563eb"),
        "POTENTIAL": ("#fef3c7", "#d97706"),
        "DOUBLE": ("#e0e7ff", "#4338ca"),
        "LARGE": ("#dbeafe", "#2563eb"),
        "MID": ("#f3e8ff", "#7c3aed"),
        "SMALL": ("#fef3c7", "#d97706"),
        "ALL 3 ENGINES": ("#fef3c7", "#b45309"),
    }
    bg, tc = colors.get(stage, ("#f1f5f9", "#64748b"))
    return render_badge(stage, bg, tc)

def render_engine_gate(score):
    if score is None:
        return
    s = int(score)
    if s <= 20:
        st.markdown(
            "<div style='background:#fef2f2;border:2px solid #fecaca;border-radius:12px;"
            "padding:14px 18px;margin-bottom:12px;text-align:center;'>"
            f"<span style='font-size:16px;margin-right:6px;'>&#9888;</span>"
            f"<span style='color:#dc2626;font-weight:700;font-size:13px;'>"
            f"ENGINE A GATE: EXIT ALL — Score {s}/100. Sell all positions immediately."
            f"</span></div>",
            unsafe_allow_html=True
        )
    elif s <= 30:
        st.markdown(
            "<div style='background:#fffbeb;border:2px solid #fde68a;border-radius:12px;"
            "padding:14px 18px;margin-bottom:12px;text-align:center;'>"
            f"<span style='font-size:16px;margin-right:6px;'>&#9888;</span>"
            f"<span style='color:#d97706;font-weight:700;font-size:13px;'>"
            f"ENGINE A FREEZE — Score {s}/100. Hold existing. No new buys."
            f"</span></div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "<div style='background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;"
            "padding:10px 18px;margin-bottom:12px;text-align:center;'>"
            f"<span style='color:#16a34a;font-weight:600;font-size:12px;'>"
            f"Engine A > 30 — System Active (Score: {s}/100)"
            f"</span></div>",
            unsafe_allow_html=True
        )

def calculate_trailing_stop_b(entry, peak, pnl_pct):
    """Engine B trailing stop logic"""
    if pnl_pct >= 30:
        return peak * 0.90  # Trail -10% from peak
    elif pnl_pct >= 20:
        return entry * 1.10  # Lock +10%
    elif pnl_pct >= 10:
        return entry  # Risk-free
    else:
        return peak * 0.85  # Hard stop -15% from peak

def get_profit_stage_b(pnl_pct):
    if pnl_pct >= 30:
        return "PROFIT TRAIL"
    elif pnl_pct >= 20:
        return "PROFIT LOCKED"
    elif pnl_pct >= 10:
        return "RISK-FREE"
    elif pnl_pct >= 0:
        return "RIDE"
    elif pnl_pct >= -5:
        return "WATCHING"
    else:
        return "GUARD"

def calculate_trailing_stop_c(entry, peak, pnl_pct):
    """Engine C adaptive trailing stop"""
    if pnl_pct >= 40:
        return peak * 0.90  # Wide trail -10%
    elif pnl_pct >= 25:
        return peak * 0.92  # Trail -8%
    elif pnl_pct >= 15:
        return entry * 1.05  # Lock +5%
    elif pnl_pct >= 8:
        return entry  # Risk-free
    else:
        return entry * 0.93  # Fixed -7%

def get_profit_stage_c(pnl_pct):
    if pnl_pct >= 40:
        return "WIDE TRAIL"
    elif pnl_pct >= 25:
        return "PROFIT TRAIL"
    elif pnl_pct >= 15:
        return "PROFIT LOCKED"
    elif pnl_pct >= 8:
        return "RISK-FREE"
    elif pnl_pct >= 0:
        return "COMPOUND"
    else:
        return "WATCHING"

def calculate_trailing_stop_d(entry, peak, pnl_pct, is_immortal=False):
    """Engine D very wide trailing stop"""
    if is_immortal:
        return peak * 0.85  # -15% from ATH
    elif pnl_pct >= 100:
        return peak * 0.85  # -15% from peak
    elif pnl_pct >= 50:
        return peak * 0.88  # -12%
    elif pnl_pct >= 35:
        return peak * 0.90  # -10%
    elif pnl_pct >= 20:
        return entry * 1.08  # Lock +8%
    elif pnl_pct >= 10:
        return entry * 0.97  # -3% from entry
    else:
        return entry * 0.90  # -10%

def get_profit_stage_d(pnl_pct, days, is_immortal=False, is_legendary=False):
    if is_legendary:
        return "LEGENDARY"
    if is_immortal:
        return "IMMORTAL"
    if pnl_pct >= 100:
        return "MULTIBAGGER"
    if pnl_pct >= 50:
        return "WIDE TRAIL"
    if pnl_pct >= 35:
        return "PROFIT TRAIL"
    if pnl_pct >= 20:
        return "PROFIT LOCKED"
    if pnl_pct >= 10:
        return "RISK-FREE"
    if days <= 90:
        return "INCUBATE"
    if pnl_pct >= 0:
        return "COMPOUND"
    return "WATCHING"

def get_engine_a_score():
    score_file = Path("data/engine_a_score.csv")
    if not score_file.exists():
        return None
    try:
        df = pd.read_csv(score_file)
        if df.empty:
            return None
        return df.iloc[-1].to_dict()
    except:
        return None

# ============================================================
# INTELLIGENCE HELPERS
# ============================================================
def mcap_tag(mcap):
    if mcap is None: return "—", "#94a3b8"
    if mcap >= 20000: return "LARGE", "#2563eb"
    if mcap >= 5000: return "MID", "#7c3aed"
    return "SMALL", "#d97706"

def render_mini_bar(value, max_val, color="#3b82f6"):
    if value is None or max_val <= 0: return ""
    pct = min(max(value / max_val * 100, 0), 100)
    return (
        f"<div style='display:flex;align-items:center;gap:6px;'>"
        f"<div style='flex:1;height:6px;background:#e2e8f0;border-radius:3px;overflow:hidden;'>"
        f"<div style='width:{pct:.0f}%;height:100%;background:{color};border-radius:3px;'></div>"
        f"</div><span style='font-size:11px;font-weight:700;color:{color};min-width:28px;'>"
        f"{value:.0f}</span></div>"
    )

def render_52w_position(price, low, high):
    if low is None or high is None or high <= low or price is None: return ""
    pct = (price - low) / (high - low) * 100
    pct = min(max(pct, 0), 100)
    pc = "#16a34a" if pct < 40 else ("#d97706" if pct < 75 else "#dc2626")
    return (
        f"<div style='font-size:10px;color:#94a3b8;margin-top:4px;'>"
        f"<div style='display:flex;justify-content:space-between;'>"
        f"<span>₹{low:,.0f}</span><span style='color:{pc};font-weight:700;'>"
        f"{pct:.0f}%</span><span>₹{high:,.0f}</span></div>"
        f"<div style='height:4px;background:#e2e8f0;border-radius:2px;margin-top:2px;'>"
        f"<div style='width:{pct:.0f}%;height:100%;background:{pc};border-radius:2px;'>"
        f"</div></div></div>"
    )

def sector_summary(stocks):
    sectors = {}
    for s in stocks:
        sec = s.get("sector", "") or "Unknown"
        sectors[sec] = sectors.get(sec, 0) + 1
    total = len(stocks) or 1
    sorted_sec = sorted(sectors.items(), key=lambda x: -x[1])
    html = ""
    for sec, cnt in sorted_sec[:5]:
        pct = cnt / total * 100
        warn = " ⚠" if pct >= 30 else ""
        bar_w = min(pct * 2.5, 100)
        bc = "#dc2626" if pct >= 30 else ("#d97706" if pct >= 20 else "#3b82f6")
        html += (
            f"<div style='display:flex;align-items:center;gap:6px;margin-bottom:3px;font-size:11px;'>"
            f"<span style='min-width:90px;color:#64748b;'>{sec[:15]}</span>"
            f"<div style='flex:1;height:5px;background:#e2e8f0;border-radius:3px;'>"
            f"<div style='width:{bar_w:.0f}%;height:100%;background:{bc};border-radius:3px;'>"
            f"</div></div>"
            f"<span style='color:{bc};font-weight:600;min-width:40px;'>{cnt} ({pct:.0f}%){warn}</span>"
            f"</div>"
        )
    return html

def overlap_analysis(watchlist, c_set, d_set):
    in_c = [s for s in watchlist if s.get("ticker","") in c_set]
    in_d = [s for s in watchlist if s.get("ticker","") in d_set]
    in_all = [s for s in watchlist if s.get("ticker","") in c_set and s.get("ticker","") in d_set]
    return len(in_c), len(in_d), in_all

def render_check(label, passed):
    icon = "✓" if passed else "✗"
    color = "#16a34a" if passed else "#dc2626"
    return f"<span style='color:{color};font-weight:700;'>{icon}</span> <span style='font-size:11px;color:#64748b;'>{label}</span>"

def peg_reading(peg):
    if peg is None: return "—", "#94a3b8"
    if peg <= 0.5: return "EXTREME VALUE", "#16a34a"
    if peg <= 1.0: return "UNDERVALUED", "#059669"
    if peg <= 1.5: return "FAIR", "#2563eb"
    return "EXPENSIVE", "#dc2626"

def compound_stars(dns):
    if dns is None: return ""
    if dns >= 16: stars = 5
    elif dns >= 13: stars = 4
    elif dns >= 10: stars = 3
    elif dns >= 7: stars = 2
    else: stars = 1
    filled = "★" * stars
    empty = "☆" * (5 - stars)
    return f"<span style='color:#f59e0b;font-size:13px;letter-spacing:2px;'>{filled}{empty}</span>"

def render_volume_badge(vol_ratio, delivery_pct=None):
    """Render volume ratio badge + delivery % with color coding."""
    parts = []
    if vol_ratio is not None and vol_ratio > 0:
        if vol_ratio >= 2.0:
            color = "#dc2626"; label = f"Vol:{vol_ratio}x UNUSUAL"
        elif vol_ratio >= 1.5:
            color = "#16a34a"; label = f"Vol:{vol_ratio}x HIGH"
        elif vol_ratio >= 0.7:
            color = "#64748b"; label = f"Vol:{vol_ratio}x"
        elif vol_ratio >= 0.3:
            color = "#d97706"; label = f"Vol:{vol_ratio}x LOW"
        else:
            color = "#dc2626"; label = f"Vol:{vol_ratio}x DEAD"
        parts.append(f"<span style='font-size:10px;color:{color};font-weight:600;'>{label}</span>")
    if delivery_pct is not None and delivery_pct > 0:
        if delivery_pct >= 60:
            dc = "#16a34a"; dl = f"Del:{delivery_pct:.0f}%"
        elif delivery_pct >= 40:
            dc = "#64748b"; dl = f"Del:{delivery_pct:.0f}%"
        else:
            dc = "#dc2626"; dl = f"Del:{delivery_pct:.0f}%"
        parts.append(f"<span style='font-size:10px;color:{dc};font-weight:600;'>{dl}</span>")
    return " ".join(parts)

def render_earnings_info(stock):
    """Render earnings date info on card."""
    lr = stock.get("last_result", "")
    nr = stock.get("next_result", "")
    if not lr and not nr:
        return ""
    parts = []
    if lr: parts.append(f"<span>Last: <b>{lr}</b></span>")
    if nr:
        # Check if result is upcoming (simple check)
        parts.append(f"<span style='color:#d97706;font-weight:600;'>Next: {nr}</span>")
    return (
        f"<div style='display:flex;gap:10px;font-size:10px;color:#64748b;margin-top:4px;"
        f"padding:3px 8px;background:#fffbeb;border-radius:4px;border-left:3px solid #f59e0b;'>"
        f"<span style='color:#92400e;font-weight:700;'>RESULTS</span>"
        f"{'  '.join(parts)}</div>"
    )

def earnings_alert(stocks):
    """Generate earnings alert for Intelligence Summary."""
    upcoming = []
    for s in stocks:
        nr = s.get("next_result", "")
        if nr:
            upcoming.append({"name": s.get("name",""), "date": nr})
    if not upcoming:
        return ""
    upcoming.sort(key=lambda x: x["date"])
    names = ", ".join(u["name"][:12] for u in upcoming[:5])
    return (
        f"<div style='font-size:11px;color:#92400e;margin-bottom:6px;'>"
        f"📅 <b>{len(upcoming)} stocks</b> with upcoming results: {names}"
        f"{'...' if len(upcoming)>5 else ''}</div>"
    )

# ============================================================
# SMART SIGNAL TEXT GENERATORS
# ============================================================
def momentum_velocity(current_m, prev_m):
    """Calculate momentum velocity: how fast M score is changing.
    Returns (arrow_html, label, velocity_value)."""
    if current_m is None or prev_m is None:
        return "", "NO DATA", 0
    vel = current_m - prev_m
    if vel >= 5:
        arrow = "↑↑"; label = "ACCELERATING"; color = "#16a34a"
    elif vel > 0:
        arrow = "↑"; label = "STEADY"; color = "#2563eb"
    elif vel >= -5:
        arrow = "↓"; label = "COOLING"; color = "#d97706"
    elif vel >= -10:
        arrow = "↓↓"; label = "DECAYING"; color = "#ea580c"
    else:
        arrow = "↓↓↓"; label = "CRASHING"; color = "#dc2626"
    sign = "+" if vel >= 0 else ""
    return (
        f"<div style='display:flex;align-items:center;gap:6px;margin-top:4px;'>"
        f"<span style='font-size:16px;color:{color};font-weight:800;'>{arrow}</span>"
        f"<span style='font-size:10px;font-weight:700;color:{color};'>{label}</span>"
        f"<span style='font-size:10px;color:#94a3b8;'>({sign}{vel:.0f})</span></div>",
        label, vel
    )

def smart_signal_b(s, cv, in_c, in_d):
    """Generate one-liner insight for Engine B Momentum card."""
    signals = []
    dur = s.get("durability") or 0
    mom = s.get("momentum") or 0
    pe = s.get("pe")
    mcap = s.get("mcap")

    # Strength signals
    if dur >= 75: signals.append("fortress durability")
    elif dur >= 55: signals.append("solid durability")
    if mom >= 70: signals.append("momentum surge")
    elif mom >= 60: signals.append("steady momentum")
    if pe and pe < 15: signals.append("cheap PE")
    elif pe and pe < 25: signals.append("reasonable PE")
    if in_c and in_d: signals.append("ALL 3 ENGINES")
    elif in_c: signals.append("also in Value")
    elif in_d: signals.append("also in Compounder")
    if mcap and mcap < 5000: signals.append("small-cap alpha")

    # Warning signals
    warns = []
    if dur < 50: warns.append("durability fading")
    if mom < 55: warns.append("momentum cooling")
    if pe and pe > 40: warns.append("expensive PE")

    if warns:
        txt = " + ".join(signals[:3]) + " BUT " + " & ".join(warns[:2]) if signals else " & ".join(warns[:2])
    elif signals:
        txt = " + ".join(signals[:3])
    else:
        txt = "Insufficient data for signal"

    # Conviction label
    if cv >= 7: label, color = "HIGH CONVICTION", "#059669"
    elif cv >= 4: label, color = "MONITOR", "#d97706"
    else: label, color = "WEAK", "#94a3b8"

    return (
        f"<div style='font-size:10px;font-style:italic;color:#64748b;margin-top:4px;"
        f"padding:4px 8px;background:#f8fafc;border-radius:6px;border-left:3px solid {color};'>"
        f"<b style='color:{color};'>{label}:</b> {txt}</div>"
    )

def smart_signal_c(s, vds):
    """Generate one-liner insight for Engine C Value card."""
    signals = []
    roe = s.get("roe"); pe = s.get("pe"); pio = s.get("piotroski")
    pg = s.get("profit_growth"); rq = s.get("rev_qoq"); de = s.get("de")
    is_dbl = s.get("is_double", False)

    if is_dbl: signals.append("double screener")
    if roe and roe > 25: signals.append("exceptional ROE")
    elif roe and roe > 20: signals.append("strong ROE")
    if pe and pe < 12: signals.append("deep discount PE")
    elif pe and pe < 18: signals.append("attractive PE")
    if pio and pio >= 8: signals.append("near-perfect Piotroski")
    if pg and pg > 30: signals.append("profit accelerating")
    if de is not None and de < 0.3: signals.append("virtually debt-free")

    # Warnings
    warns = []
    if rq is not None and rq < -10: warns.append("revenue declining")
    if pio and pio <= 5: warns.append("weak Piotroski")
    if de is not None and de > 1: warns.append("high debt")

    if warns:
        txt = " + ".join(signals[:3]) + " BUT " + " & ".join(warns[:2]) if signals else " & ".join(warns[:2])
    elif signals:
        txt = " + ".join(signals[:3])
    else:
        txt = "Basic screener pass"

    if vds >= 12: label, color = "DEEP VALUE", "#059669"
    elif vds >= 8: label, color = "SOLID", "#2563eb"
    else: label, color = "MODERATE", "#d97706"

    return (
        f"<div style='font-size:10px;font-style:italic;color:#64748b;margin-top:4px;"
        f"padding:4px 8px;background:#f8fafc;border-radius:6px;border-left:3px solid {color};'>"
        f"<b style='color:{color};'>{label}:</b> {txt}</div>"
    )

def smart_signal_d(s, dns):
    """Generate one-liner insight for Engine D Compounder card."""
    signals = []
    roe = s.get("roe"); pe = s.get("pe"); pio = s.get("piotroski")
    pg = s.get("profit_growth"); peg = s.get("peg"); de = s.get("de")
    is_dbl = s.get("is_double", False)

    if is_dbl: signals.append("double screener")
    if peg is not None and peg <= 0.5: signals.append("PEG extreme value")
    elif peg is not None and peg <= 1.0: signals.append("PEG undervalued")
    if pg and pg > 50: signals.append("explosive growth")
    elif pg and pg > 25: signals.append("strong growth")
    if roe and roe > 25: signals.append("exceptional ROE")
    if de is not None and de < 0.3: signals.append("virtually debt-free")
    if pio and pio >= 8: signals.append("near-perfect Piotroski")

    # Kill shot warnings
    warns = []
    if pg is not None and pg < 0: warns.append("growth declining")
    if de is not None and de > 1.5: warns.append("debt creeping")
    if peg is not None and peg > 2: warns.append("overpriced vs growth")

    if warns:
        txt = " + ".join(signals[:3]) + " BUT " + " & ".join(warns[:2]) if signals else " & ".join(warns[:2])
    elif signals:
        txt = " + ".join(signals[:3])
    else:
        txt = "Basic screener pass"

    if dns >= 16: label, color = "ELITE COMPOUNDER", "#059669"
    elif dns >= 11: label, color = "STRONG PICK", "#2563eb"
    else: label, color = "POTENTIAL", "#d97706"

    return (
        f"<div style='font-size:10px;font-style:italic;color:#64748b;margin-top:4px;"
        f"padding:4px 8px;background:#f8fafc;border-radius:6px;border-left:3px solid {color};'>"
        f"<b style='color:{color};'>{label}:</b> {txt}</div>"
    )

# ============================================================
# AI STOCK ANALYST (Rule-Based — FREE, no API)
# ============================================================
def ai_analyst(stock, engine="B", engine_score=None, held=False):
    """Generate institutional-grade analysis paragraph for any stock.
    Returns (verdict, color, analysis_html)."""
    nm = stock.get("name", "Unknown")
    roe = stock.get("roe"); pe = stock.get("pe"); pio = stock.get("piotroski")
    de = stock.get("de"); pg = stock.get("profit_growth"); peg = stock.get("peg")
    mcap = stock.get("mcap"); prom = stock.get("promoter"); fii = stock.get("fii")
    inst = stock.get("inst"); rq = stock.get("rev_qoq"); sec = stock.get("sector","")
    dur = stock.get("durability"); mom = stock.get("momentum")
    h52 = stock.get("high_52w"); l52 = stock.get("low_52w")
    ltp = stock.get("ltp",0) or 0
    vds = stock.get("vds",0); dns = stock.get("dns",0)
    is_dbl = stock.get("is_double", False)

    score = 0
    strengths = []; risks = []

    # 1. VALUATION (max 9)
    if pe is not None:
        if pe < 12: score += 6; strengths.append(f"deeply undervalued at PE {pe:.0f}")
        elif pe < 18: score += 4; strengths.append(f"attractively priced at PE {pe:.0f}")
        elif pe < 25: score += 2
        elif pe < 40: score += 0; risks.append(f"PE {pe:.0f} is stretched")
        else: score -= 2; risks.append(f"PE {pe:.0f} is dangerously expensive")
    if peg is not None:
        if peg <= 0.5: score += 3; strengths.append(f"PEG {peg:.1f} = extreme value vs growth")
        elif peg <= 1.0: score += 2; strengths.append(f"PEG {peg:.1f} = undervalued")
        elif peg <= 1.5: score += 1
        else: score -= 1; risks.append(f"PEG {peg:.1f} overpriced vs growth")

    # 2. QUALITY (max 6)
    if roe is not None:
        if roe > 25: score += 3; strengths.append(f"exceptional ROE {roe:.0f}%")
        elif roe > 20: score += 2; strengths.append(f"strong ROE {roe:.0f}%")
        elif roe > 15: score += 1
        else: risks.append(f"ROE {roe:.0f}% below threshold")
    if pio is not None:
        if pio >= 8: score += 2; strengths.append(f"Piotroski {pio:.0f}/9 near-perfect")
        elif pio >= 7: score += 1
        else: risks.append(f"Piotroski {pio:.0f}/9 is weak")
    if de is not None:
        if de < 0.3: score += 1; strengths.append("virtually debt-free")
        elif de > 1.5: score -= 2; risks.append(f"D/E {de:.1f} is high leverage")

    # 3. GROWTH (max 5)
    if pg is not None:
        if pg > 50: score += 3; strengths.append(f"explosive {pg:.0f}% profit growth")
        elif pg > 25: score += 2; strengths.append(f"strong {pg:.0f}% profit growth")
        elif pg > 10: score += 1
        elif pg < 0: score -= 2; risks.append(f"profit declining {pg:.0f}%")
    if rq is not None:
        if rq > 10: score += 2; strengths.append(f"revenue accelerating +{rq:.0f}% QoQ")
        elif rq < -10: score -= 2; risks.append(f"revenue declining {rq:.0f}% QoQ")

    # 4. MOMENTUM (max 5)
    if dur is not None and mom is not None:
        if dur > 75 and mom > 65: score += 5; strengths.append("institutions aggressively accumulating")
        elif dur > 55 and mom > 59: score += 3; strengths.append("institutional buying confirmed")
        elif dur > 45: score += 1
        else: score -= 1; risks.append("institutional interest fading")

    # 5. OWNERSHIP (max 4)
    if prom is not None:
        if prom > 65: score += 1; strengths.append(f"promoter {prom:.0f}% skin in game")
        elif prom < 30: risks.append(f"promoter only {prom:.0f}%")
    if inst is not None and inst > 30: score += 2; strengths.append(f"institutional {inst:.0f}% validated")
    elif inst is not None and inst > 15: score += 1
    if fii is not None and fii > 10: score += 1; strengths.append(f"FII {fii:.1f}% smart money")

    # 6. TECHNICAL (max 3)
    if h52 is not None and l52 is not None and ltp > 0 and h52 > l52:
        pos52 = (ltp - l52) / (h52 - l52) * 100
        if pos52 < 30: score += 3; strengths.append(f"near 52W low at {pos52:.0f}%")
        elif pos52 < 50: score += 2
        elif pos52 > 90: score -= 1; risks.append(f"at {pos52:.0f}% of 52W high")

    # 7. MULTI-ENGINE (max 5)
    if is_dbl: score += 2; strengths.append("double screener")
    if engine == "C" and vds >= 12: score += 3
    elif engine == "C" and vds >= 8: score += 2
    elif engine == "D" and dns >= 16: score += 3
    elif engine == "D" and dns >= 11: score += 2

    # 8. ENGINE A GATE
    if engine_score is not None:
        if engine_score > 62: score += 5; strengths.append("Engine A FULL DEPLOY")
        elif engine_score > 52: score += 3
        elif engine_score > 30: score += 1
        elif engine_score <= 20: score -= 5; risks.append("ENGINE A: EXIT ALL")
        elif engine_score <= 30: score -= 3; risks.append("Engine A FREEZE")

    # VERDICT
    if score >= 25: verdict, vc = "STRONG BUY", "#059669"
    elif score >= 18: verdict, vc = "BUY", "#16a34a"
    elif score >= 12: verdict, vc = "ACCUMULATE", "#2563eb"
    elif score >= 6: verdict, vc = "WAIT", "#d97706"
    elif score >= 0: verdict, vc = "AVOID", "#ea580c"
    else: verdict, vc = "DANGER", "#dc2626"

    top_s = ". ".join(strengths[:4]) + "." if strengths else "No clear strengths."
    risk_s = " ".join(risks[:3]) if risks else ""
    risk_line = f" However, {risk_s}." if risk_s else ""

    if verdict in ("STRONG BUY", "BUY"):
        action = "Hold and add on dips." if held else f"Consider entry. Size per Engine {engine} rules."
    elif verdict == "ACCUMULATE":
        action = "Add on 5-10% dips only."
    elif verdict == "WAIT":
        action = "Monitor weekly. Wait for correction or improvement."
    else:
        action = "Do not deploy capital."

    html = (
        f"<div style='padding:10px 14px;background:linear-gradient(135deg,#f8fafc,#f1f5f9);"
        f"border-radius:8px;border-left:4px solid {vc};margin-top:8px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;'>"
        f"<span style='font-size:11px;color:#94a3b8;font-weight:600;letter-spacing:1px;'>AI ANALYST</span>"
        f"<span style='font-size:12px;font-weight:800;color:{vc};'>{verdict} ({score}/40)</span></div>"
        f"<div style='font-size:11px;color:#475569;line-height:1.5;'>{top_s}{risk_line}</div>"
        f"<div style='font-size:10px;color:{vc};font-weight:600;margin-top:6px;'>Action: {action}</div></div>"
    )
    return verdict, vc, html

# ============================================================
# LIVE PRICE REFRESH (yfinance)
# ============================================================
def refresh_prices_yfinance(stock_data):
    """Fetch live prices via yfinance. Returns {ticker: price}, error."""
    try:
        import yfinance as yf
    except ImportError:
        return {}, "yfinance not installed"
    all_tickers = set()
    for key in ["engine_b","engine_c","engine_d","momentum","value","compounders",
                 "engine_b_watchlist","engine_c_watchlist","engine_d_watchlist"]:
        for s in stock_data.get(key, []):
            tk = s.get("ticker","")
            if tk: all_tickers.add(tk)
    if not all_tickers: return {}, "No tickers"
    yf_tickers = [f"{tk}.NS" for tk in all_tickers]
    tk_map = {f"{tk}.NS": tk for tk in all_tickers}
    try:
        data = yf.download(yf_tickers, period="1d", progress=False, threads=True)
        prices = {}
        if len(yf_tickers) == 1:
            val = data["Close"].iloc[-1] if len(data) > 0 else None
            if val is not None and not pd.isna(val):
                prices[tk_map[yf_tickers[0]]] = round(float(val), 2)
        else:
            close = data["Close"]
            for tk_ns in close.columns:
                val = close[tk_ns].iloc[-1] if len(close[tk_ns]) > 0 else None
                if val is not None and not pd.isna(val):
                    prices[tk_map.get(tk_ns, tk_ns.replace(".NS",""))] = round(float(val), 2)
        return prices, None
    except Exception as e:
        return {}, str(e)

# ============================================================
# RULES ENGINE — Layer 1-3 Intelligence (FREE, instant)
# ============================================================

def _pill(label, color, bg=None):
    if not bg: bg = color + "18"
    return f"<span style='font-size:9px;font-weight:700;padding:2px 7px;border-radius:4px;background:{bg};color:{color};letter-spacing:.3px;white-space:nowrap;'>{label}</span>"

def _sf(v):
    """Safe float conversion — returns None if not convertible."""
    if v is None: return None
    try: return float(v)
    except: return None

def market_gate(score):
    """Layer 1: Market regime from Engine A score."""
    if score is None: return {"regime":"UNKNOWN","color":"#94a3b8","equity_pct":0,"can_buy":False}
    if score <= 20: return {"regime":"EXIT ALL","color":"#dc2626","equity_pct":10,"can_buy":False}
    if score <= 30: return {"regime":"FREEZE","color":"#dc2626","equity_pct":25,"can_buy":False}
    if score <= 40: return {"regime":"CAUTIOUS","color":"#d97706","equity_pct":40,"can_buy":True}
    if score <= 52: return {"regime":"ACTIVE","color":"#16a34a","equity_pct":55,"can_buy":True}
    if score <= 62: return {"regime":"AGGRESSIVE","color":"#059669","equity_pct":70,"can_buy":True}
    return {"regime":"FULL DEPLOY","color":"#059669","equity_pct":85,"can_buy":True}

def _earnings_freshness(result_date):
    if not result_date: return "UNKNOWN", 999, "#94a3b8"
    try:
        rd = datetime.strptime(str(result_date)[:10], "%Y-%m-%d")
        days = (datetime.now() - rd).days
        if days < 45: return "FRESH", days, "#16a34a"
        if days < 90: return "AGING", days, "#d97706"
        if days < 150: return "STALE", days, "#ea580c"
        return "OVERDUE", days, "#dc2626"
    except: return "UNKNOWN", 999, "#94a3b8"

def _growth_accel(pg_yoy, pg_3yr):
    pg_yoy = _sf(pg_yoy); pg_3yr = _sf(pg_3yr)
    if pg_yoy is None or pg_3yr is None: return None, None
    if pg_3yr == 0: return "NEW GROWTH" if pg_yoy > 0 else "NO GROWTH", "#d97706"
    ratio = pg_yoy / pg_3yr if pg_3yr != 0 else 0
    if pg_yoy < 0: return "REVERSAL", "#dc2626"
    if ratio > 1.5: return "ACCELERATING", "#059669"
    if ratio > 0.8: return "CONSISTENT", "#16a34a"
    return "DECELERATING", "#d97706"

def _rev_profit_div(rev_qoq, pg_yoy):
    rev_qoq = _sf(rev_qoq); pg_yoy = _sf(pg_yoy)
    if rev_qoq is None or pg_yoy is None: return None, None
    rev_up = rev_qoq > 0; pg_up = pg_yoy > 0
    if rev_up and pg_up: return "HEALTHY", "#16a34a"
    if rev_up and not pg_up: return "MARGIN PRESSURE", "#dc2626"
    if not rev_up and pg_up: return "COST CUTTING", "#d97706"
    return "DETERIORATING", "#dc2626"

def _volume_signal(vol_ratio, delivery_pct):
    vr = _sf(vol_ratio) or 0; dp = _sf(delivery_pct) or 0
    if vr >= 2 and dp >= 60: return "ACCUMULATION", "#059669"
    if vr >= 1.5 and dp >= 60: return "CONFIRMED", "#16a34a"
    if vr >= 2 and dp < 40: return "SPECULATIVE", "#dc2626"
    if vr < 0.8: return "NO INTEREST", "#94a3b8"
    return "NORMAL", "#64748b"

def _prom_fii(prom, fii):
    prom = _sf(prom); fii = _sf(fii)
    if prom is None: return None, None
    fii = fii or 0
    if prom > 50 and fii > 5: return "ALIGNED", "#059669"
    if prom > 50 and fii < 2: return "UNDISCOVERED", "#2563eb"
    if prom < 40 and fii > 5: return "FII DOMINANT", "#d97706"
    if prom < 40 and fii < 2: return "ABANDONED", "#dc2626"
    return "NEUTRAL", "#64748b"

def _w52_vol_cross(w52_pct, vol_ratio, delivery_pct):
    vr = _sf(vol_ratio) or 0; dp = _sf(delivery_pct) or 0; w52_pct = _sf(w52_pct)
    if w52_pct is None: return None, None
    if w52_pct > 80 and vr > 1.5 and dp > 55: return "BREAKOUT", "#059669"
    if w52_pct > 80 and vr < 1: return "EXHAUSTION", "#dc2626"
    if w52_pct < 30 and vr > 1.5 and dp > 55: return "ACCUMULATION", "#059669"
    if w52_pct < 30 and vr < 1: return "DEAD", "#94a3b8"
    return None, None

def _risk_reward(price, stop, target):
    if not price or not stop or not target or price <= 0: return None, None, None
    down = abs(price - stop)
    up = abs(target - price)
    if down <= 0: return None, None, None
    ratio = round(up / down, 1)
    color = "#059669" if ratio >= 3 else ("#16a34a" if ratio >= 2 else ("#d97706" if ratio >= 1 else "#dc2626"))
    return ratio, f"1:{ratio}", color

def _sector_weight(ticker, sector, all_positions):
    """Count sector % across all engines."""
    if not sector: return 0, "UNKNOWN", "#94a3b8"
    total = 0; same = 0
    for p in all_positions:
        total += 1
        if p.get("sector","").lower() == sector.lower(): same += 1
    if total == 0: return 0, "CLEAR", "#16a34a"
    pct = round(same / total * 100)
    if pct >= 30: return pct, "BLOCKED", "#dc2626"
    if pct >= 25: return pct, "NEAR CAP", "#d97706"
    return pct, "CLEAR", "#16a34a"

def _comparative(stock, all_stocks, fields):
    """Compare stock vs engine average on given fields."""
    result = {}
    for f in fields:
        val = stock.get(f)
        if val is None or val == 0: continue
        vals = [s.get(f) for s in all_stocks if s.get(f) is not None and s.get(f) != 0]
        if not vals: continue
        avg = sum(vals) / len(vals)
        if avg == 0: continue
        ratio = round(val / avg, 1)
        result[f] = {"val": val, "avg": round(avg, 1), "ratio": ratio}
    return result

def rules_engine_b(stock, ea_score, vol_data, all_pos, c_tickers, d_tickers):
    """Compute all Layer 1-3 signals for an Engine B stock."""
    s = {}
    dur = _sf(stock.get("durability")); mom = _sf(stock.get("momentum"))
    prev_m = _sf(stock.get("prev_momentum"))
    tk = stock.get("ticker","")
    vr = _sf(vol_data.get(tk,{}).get("vol_ratio",0)) if isinstance(vol_data.get(tk), dict) else 0
    dp = _sf(stock.get("delivery_pct")) or 0
    ltp = _sf(stock.get("ltp")) or 0
    h52 = _sf(stock.get("high_52w")); l52 = _sf(stock.get("low_52w"))
    w52 = ((ltp - l52) / (h52 - l52) * 100) if h52 and l52 and h52 > l52 and ltp > 0 else None

    # DVM Gate
    if dur and dur > 55 and mom and mom > 59: s["dvm"] = ("GREEN GATE", "#059669")
    elif dur and dur >= 45 or mom and mom >= 49: s["dvm"] = ("GREY GATE", "#d97706")
    else: s["dvm"] = ("RED GATE", "#dc2626")

    # Velocity
    if mom and prev_m is not None:
        vel = mom - prev_m
        if vel >= 5: s["velocity"] = (f"ACCEL +{vel:.0f}", "#059669")
        elif vel >= 0: s["velocity"] = (f"STEADY +{vel:.0f}", "#2563eb")
        elif vel > -5: s["velocity"] = (f"COOLING {vel:.0f}", "#d97706")
        elif vel > -10: s["velocity"] = (f"DECAYING {vel:.0f}", "#ea580c")
        else: s["velocity"] = (f"CRASH {vel:.0f}", "#dc2626")

    # Volume
    vl, vc = _volume_signal(vr, dp)
    s["volume"] = (vl, vc)

    # Growth Accel
    ga, gc = _growth_accel(stock.get("profit_growth"), stock.get("profit_growth_3yr"))
    if ga: s["growth"] = (ga, gc)

    # Rev-Profit
    rp, rc = _rev_profit_div(stock.get("rev_qoq"), stock.get("profit_growth"))
    if rp: s["rev_profit"] = (rp, rc)

    # Earnings Freshness
    el, ed, ec = _earnings_freshness(stock.get("result_date"))
    if el != "UNKNOWN": s["earnings"] = (f"{el} ({ed}d)", ec)

    # Prom-FII
    pf, pc = _prom_fii(stock.get("promoter"), stock.get("fii"))
    if pf: s["alignment"] = (pf, pc)

    # 52W + Volume cross
    wv, wc = _w52_vol_cross(w52, vr, dp)
    if wv: s["w52_vol"] = (wv, wc)

    # Fundamental Floor
    roe = _sf(stock.get("roe")); pio = _sf(stock.get("piotroski"))
    if roe and roe > 15 and pio and pio >= 7: s["fundament"] = ("QUALITY", "#16a34a")
    elif roe and roe < 10 or pio and pio < 6: s["fundament"] = ("WEAK BASE", "#dc2626")

    # Cross-engine
    in_c = tk in c_tickers; in_d = tk in d_tickers
    if in_c and in_d: s["cross"] = ("ALL 3", "#b45309")
    elif in_c: s["cross"] = ("+VALUE", "#4338ca")
    elif in_d: s["cross"] = ("+COMPOUNDER", "#4338ca")

    # Risk-Reward (stop at -15% from peak/current, target = 52W high)
    peak = max(ltp, _sf(stock.get("peak")) or 0)
    stop = round(peak * 0.85)
    target = h52 or ltp
    rr, rr_txt, rr_c = _risk_reward(ltp, stop, target)
    if rr and rr_txt: s["rr"] = (f"R:R {rr_txt}", rr_c)

    # Sector
    sp, sl, sc = _sector_weight(tk, stock.get("sector"), all_pos)
    if sl != "CLEAR" and sl != "UNKNOWN": s["sector_risk"] = (f"SEC {sp}% {sl}", sc)

    return s

def rules_engine_c(stock, ea_score, vol_data, all_pos, b_tickers, d_tickers):
    """Compute all Layer 1-3 signals for an Engine C stock."""
    s = {}
    tk = stock.get("ticker","")
    pe = _sf(stock.get("pe")); roe = _sf(stock.get("roe")); pio = _sf(stock.get("piotroski"))
    vr = _sf(vol_data.get(tk,{}).get("vol_ratio",0)) if isinstance(vol_data.get(tk), dict) else 0
    dp = _sf(stock.get("delivery_pct")) or 0
    ltp = _sf(stock.get("ltp")) or 0
    h52 = _sf(stock.get("high_52w")); l52 = _sf(stock.get("low_52w"))

    # PE Depth
    if pe:
        if pe < 12: s["pe_depth"] = ("DEEP DISCOUNT", "#059669")
        elif pe < 18: s["pe_depth"] = ("SOLID VALUE", "#16a34a")
        elif pe < 23: s["pe_depth"] = ("MODERATE", "#d97706")
        else: s["pe_depth"] = ("NEAR CAP", "#dc2626")

    # Value Trap
    rq = _sf(stock.get("rev_qoq")); prom = _sf(stock.get("promoter"))
    if rq is not None and prom is not None:
        if rq > 0 and prom > 40: s["trap"] = ("CLEAN", "#16a34a")
        elif rq < -10 and prom < 40: s["trap"] = ("VALUE TRAP", "#dc2626")
        elif rq < -10 and prom > 40: s["trap"] = ("CONTRARIAN", "#d97706")
        elif rq > 0 and prom < 40: s["trap"] = ("PROM LOW", "#d97706")

    # Piotroski Depth
    if pio:
        if pio >= 9: s["pio_depth"] = ("PERFECT 9/9", "#059669")
        elif pio >= 8: s["pio_depth"] = ("STRONG 8/9", "#16a34a")
        elif pio >= 7: s["pio_depth"] = ("GOOD 7/9", "#2563eb")
        else: s["pio_depth"] = ("MIN 6/9", "#d97706")

    # Volume
    vl, vc = _volume_signal(vr, dp)
    s["volume"] = (vl, vc)

    # Growth Accel
    ga, gc = _growth_accel(stock.get("profit_growth"), stock.get("profit_growth_3yr"))
    if ga: s["growth"] = (ga, gc)

    # Rev-Profit
    rp, rc = _rev_profit_div(stock.get("rev_qoq"), stock.get("profit_growth"))
    if rp: s["rev_profit"] = (rp, rc)

    # Earnings Freshness
    el, ed, ec = _earnings_freshness(stock.get("result_date"))
    if el != "UNKNOWN": s["earnings"] = (f"{el} ({ed}d)", ec)

    # Prom-FII
    pf, pc = _prom_fii(stock.get("promoter"), stock.get("fii"))
    if pf: s["alignment"] = (pf, pc)

    # Cross-engine
    in_b = tk in b_tickers; in_d = tk in d_tickers
    if in_b and in_d: s["cross"] = ("ALL 3", "#b45309")
    elif in_b: s["cross"] = ("+MOMENTUM", "#3b82f6")
    elif in_d: s["cross"] = ("+COMPOUNDER", "#4338ca")

    # Risk-Reward (stop at -7%, target = PE 25 mapped price)
    stop = round(ltp * 0.93) if ltp else 0
    target_pe = 25
    target = round(ltp * (target_pe / pe)) if pe and pe > 0 and ltp else 0
    rr, rr_txt, rr_c = _risk_reward(ltp, stop, target)
    if rr and rr_txt: s["rr"] = (f"R:R {rr_txt}", rr_c)

    # Sector
    sp, sl, sc = _sector_weight(tk, stock.get("sector"), all_pos)
    if sl != "CLEAR" and sl != "UNKNOWN": s["sector_risk"] = (f"SEC {sp}% {sl}", sc)

    return s

def rules_engine_d(stock, ea_score, vol_data, all_pos, b_tickers, c_tickers):
    """Compute all Layer 1-3 signals for an Engine D stock."""
    s = {}
    tk = stock.get("ticker","")
    pg = _sf(stock.get("profit_growth")); rq = _sf(stock.get("rev_qoq")); peg = _sf(stock.get("peg"))
    de = _sf(stock.get("de")); prom = _sf(stock.get("promoter")); mcap = _sf(stock.get("mcap"))
    vr = _sf(vol_data.get(tk,{}).get("vol_ratio",0)) if isinstance(vol_data.get(tk), dict) else 0
    dp = _sf(stock.get("delivery_pct")) or 0
    ltp = _sf(stock.get("ltp")) or 0
    h52 = _sf(stock.get("high_52w")); l52 = _sf(stock.get("low_52w"))

    # Growth Engine
    if pg is not None and rq is not None:
        if pg > 30 and rq > 0: s["growth_eng"] = ("ACCELERATING", "#059669")
        elif pg > 15 and rq > 0: s["growth_eng"] = ("STEADY", "#16a34a")
        elif pg > 15: s["growth_eng"] = ("MIXED", "#d97706")
        elif pg <= 0: s["growth_eng"] = ("NO GROWTH", "#dc2626")
        else: s["growth_eng"] = ("WEAK", "#d97706")

    # PEG
    if peg and peg > 0:
        if peg < 0.5: s["peg_val"] = ("PEG EXTREME", "#059669")
        elif peg < 0.8: s["peg_val"] = ("PEG UNDER", "#16a34a")
        elif peg <= 1.2: s["peg_val"] = ("PEG FAIR", "#2563eb")
        elif peg <= 1.5: s["peg_val"] = ("PEG FULL", "#d97706")
        else: s["peg_val"] = ("PEG EXPENSIVE", "#dc2626")

    # Kill Shots
    kills = 0
    if pg is not None and pg <= 0: kills += 1
    if de is not None and de > 1.5: kills += 1
    if prom is not None and prom < 40: kills += 1
    if rq is not None and rq < -10: kills += 1
    if kills == 0: s["killshot"] = ("NO KILLS", "#16a34a")
    elif kills == 1: s["killshot"] = ("1 KILL", "#d97706")
    else: s["killshot"] = (f"{kills} KILLS", "#dc2626")

    # Compounding Runway
    if mcap:
        if mcap < 10000: s["runway"] = ("SMALL CAP", "#7c3aed")
        elif mcap < 50000: s["runway"] = ("MID CAP", "#2563eb")
        else: s["runway"] = ("LARGE CAP", "#64748b")

    # Volume
    vl, vc = _volume_signal(vr, dp)
    s["volume"] = (vl, vc)

    # Growth Accel
    ga, gc = _growth_accel(stock.get("profit_growth"), stock.get("profit_growth_3yr"))
    if ga: s["growth_accel"] = (ga, gc)

    # Rev-Profit
    rp, rc = _rev_profit_div(rq, pg)
    if rp: s["rev_profit"] = (rp, rc)

    # Earnings Freshness
    el, ed, ec = _earnings_freshness(stock.get("result_date"))
    if el != "UNKNOWN": s["earnings"] = (f"{el} ({ed}d)", ec)

    # Prom-FII
    pf, pc = _prom_fii(prom, stock.get("fii"))
    if pf: s["alignment"] = (pf, pc)

    # Cross-engine
    in_b = tk in b_tickers; in_c = tk in c_tickers
    if in_b and in_c: s["cross"] = ("ALL 3", "#b45309")
    elif in_b: s["cross"] = ("+MOMENTUM", "#3b82f6")
    elif in_c: s["cross"] = ("+VALUE", "#4338ca")

    # Risk-Reward
    stop = round(ltp * 0.90) if ltp else 0
    target = round(ltp * (1 / peg)) if peg and peg > 0 and peg < 2 and ltp else (h52 or ltp)
    rr, rr_txt, rr_c = _risk_reward(ltp, stop, target)
    if rr and rr_txt: s["rr"] = (f"R:R {rr_txt}", rr_c)

    # Sector
    sp, sl, sc = _sector_weight(tk, stock.get("sector"), all_pos)
    if sl != "CLEAR" and sl != "UNKNOWN": s["sector_risk"] = (f"SEC {sp}% {sl}", sc)

    return s

def _engine_avg(all_wl, field):
    vals = [_sf(s.get(field)) for s in all_wl if _sf(s.get(field)) is not None and _sf(s.get(field)) != 0]
    return round(sum(vals)/len(vals),1) if vals else 0

def _vs_avg(val, avg):
    if not val or not avg or avg == 0: return ""
    r = val/avg
    if r >= 2: return f" ({r:.1f}x avg)"
    if r >= 1.3: return f" (above avg {avg:.0f})"
    if r <= 0.7: return f" (below avg {avg:.0f})"
    return ""

def render_signals_html(signals, engine="B", stock=None, all_wl=None, ea_score=None, all_pos=None):
    """GODMODE: Synthesize all data into contextual analysis paragraph."""
    if not stock: stock = {}
    if not all_wl: all_wl = []
    if not all_pos: all_pos = []

    nm = stock.get("name",""); tk = stock.get("ticker","")
    roe = _sf(stock.get("roe")); pe = _sf(stock.get("pe")); pio = _sf(stock.get("piotroski"))
    de = _sf(stock.get("de")); pg = _sf(stock.get("profit_growth")); pg3 = _sf(stock.get("profit_growth_3yr"))
    prom = _sf(stock.get("promoter")); fii = _sf(stock.get("fii")); inst = _sf(stock.get("inst"))
    rq = _sf(stock.get("rev_qoq")); peg = _sf(stock.get("peg")); mcap = _sf(stock.get("mcap"))
    dur = _sf(stock.get("durability")); mom = _sf(stock.get("momentum"))
    prev_m = _sf(stock.get("prev_momentum"))
    dp = _sf(stock.get("delivery_pct")) or 0
    ltp = _sf(stock.get("ltp")) or 0
    h52 = _sf(stock.get("high_52w")) or 0; l52 = _sf(stock.get("low_52w")) or 0
    w52 = round((ltp-l52)/(h52-l52)*100) if h52>l52 and ltp>0 else 50
    is_dbl = stock.get("is_double", False)
    sec = stock.get("sector","")

    # Engine averages
    avg_roe = _engine_avg(all_wl, "roe")
    avg_pe = _engine_avg(all_wl, "pe")
    avg_pg = _engine_avg(all_wl, "profit_growth")

    lines = []  # Analysis lines
    verdict = "STALK"
    vc = "#d97706"
    red_flags = []
    strengths = 0

    # ═══════════════════════════════════════════
    # ENGINE B — MOMENTUM ANALYSIS
    # ═══════════════════════════════════════════
    if engine == "B":
        vel = (mom - prev_m) if mom and prev_m is not None else 0

        # DVM is THE signal for momentum
        if dur and dur > 55 and mom and mom > 59:
            if dur > 75:
                lines.append(f"Durability {dur:.0f} is fortress-level — institutions deeply committed.")
                strengths += 2
            else:
                lines.append(f"DVM green (D:{dur:.0f} M:{mom:.0f}) — institutional buying active.")
                strengths += 1

            # Velocity adds urgency
            if vel >= 5:
                lines.append(f"Momentum accelerating (+{vel:.0f}/wk) — buying pressure increasing.")
                strengths += 1
            elif vel < -5:
                lines.append(f"⚠ Momentum decaying ({vel:.0f}/wk) despite green DVM. Early exit warning.")
                red_flags.append("velocity decay")
        elif dur and dur >= 45 and mom and mom >= 49:
            lines.append(f"DVM in grey zone (D:{dur:.0f} M:{mom:.0f}). Not investable yet — wait for green crossover above D:55/M:59.")
            verdict = "STALK"; vc = "#d97706"
        else:
            lines.append(f"DVM below threshold. No institutional interest. Skip.")
            verdict = "AVOID"; vc = "#dc2626"

        # Volume tells you if the move is real
        vr = signals.get("volume",("",""))[0]
        if "ACCUMULATION" in vr or "CONFIRMED" in vr:
            lines.append(f"Volume confirms — {'delivery '+str(dp)+'%' if dp>55 else 'above-average activity'}. Real buying, not speculation.")
            strengths += 1
        elif "SPECULATIVE" in vr:
            lines.append(f"⚠ High volume but low delivery ({dp:.0f}%). This is traders, not institutions.")
            red_flags.append("speculative volume")
        elif "NO INTEREST" in vr:
            lines.append(f"Volume dead. Momentum score may be stale — needs fresh confirmation.")

        # Fundamental floor check — BUT framed for momentum
        if roe and roe < 10 and pio and pio <= 6:
            lines.append(f"⚠ Weak fundamentals (ROE:{roe:.0f}%, Pio:{pio:.0f}). Momentum on shaky ground — if DVM turns, crash will be severe. Smaller position.")
            red_flags.append("weak fundamentals")
        elif roe and roe > 20 and pio and pio >= 7:
            lines.append(f"Strong fundamentals back the momentum (ROE:{roe:.0f}%{_vs_avg(roe,avg_roe)}, Pio:{pio:.0f}/9). If DVM stays green, this has legs.")
            strengths += 1

        # 52W context matters for momentum timing
        if w52 > 90:
            lines.append(f"At {w52}% of 52W range — near highs. If volume is thin, this is exhaustion, not breakout.")
            if not ("ACCUMULATION" in vr or "CONFIRMED" in vr):
                red_flags.append("near highs, thin volume")
        elif w52 < 30:
            lines.append(f"At {w52}% of 52W range — near lows. Unusual for a green DVM stock. Potential early accumulation.")

        # PG is bonus context for momentum
        if pg and pg > 50:
            lines.append(f"Profit growth +{pg:.0f}%{_vs_avg(pg,avg_pg)} gives fundamental tailwind to momentum.")

        # Cross-engine adds conviction
        cross = signals.get("cross")
        if cross and "ALL 3" in cross[0]:
            lines.append(f"Confirmed across all 3 engines — momentum + value + growth. Highest conviction.")
            strengths += 1
        elif cross:
            lines.append(f"Also in {cross[0].replace('+','')} screener — momentum has fundamental backing.")

        # VERDICT
        if "AVOID" not in verdict:
            if len(red_flags) >= 2: verdict, vc = "AVOID", "#dc2626"
            elif strengths >= 3 and not red_flags: verdict, vc = "ENTER", "#059669"
            elif strengths >= 2 and len(red_flags) <= 1: verdict, vc = "STALK", "#d97706"
            elif red_flags: verdict, vc = "STALK", "#d97706"

        # Risk-reward
        if ltp and h52:
            stop = round(max(ltp, h52) * 0.85)
            down = ltp - stop; up = h52 - ltp
            if down > 0 and up > 0:
                rr = round(up/down, 1)
                lines.append(f"Stop: ₹{stop:,} (-15%). Target: ₹{h52:,} (52W high). Risk:Reward 1:{rr}{'— favorable.' if rr>=2 else '— tight.' if rr>=1 else '— unfavorable. Most upside captured.'}")

    # ═══════════════════════════════════════════
    # ENGINE C — VALUE ANALYSIS
    # ═══════════════════════════════════════════
    elif engine == "C":
        # PE is THE signal for value
        if pe:
            room = round(((25-pe)/pe)*100) if pe < 25 else 0
            if pe < 12:
                lines.append(f"PE {pe:.0f} is a deep discount — {room}% expansion room to cap of 25. Market is sleeping on this.")
                strengths += 2
            elif pe < 18:
                lines.append(f"PE {pe:.0f}{' (vs avg '+str(avg_pe)+')' if avg_pe else ''} with {room}% room. Solid value — sweet spot for accumulation.")
                strengths += 1
            elif pe < 23:
                lines.append(f"PE {pe:.0f} — moderate value, {room}% room left. Enter only if quality is exceptional.")
            else:
                lines.append(f"PE {pe:.0f} — near the cap of 25. Minimal PE expansion upside remaining.")
                red_flags.append("PE near cap")

        # Quality is what separates value from trap
        quality_score = 0
        quality_parts = []
        if roe and roe > 20: quality_score += 2; quality_parts.append(f"ROE {roe:.0f}%{_vs_avg(roe,avg_roe)}")
        elif roe and roe > 15: quality_score += 1; quality_parts.append(f"ROE {roe:.0f}%")
        if pio and pio >= 8: quality_score += 2; quality_parts.append(f"Piotroski {pio:.0f}/9")
        elif pio and pio >= 7: quality_score += 1; quality_parts.append(f"Pio {pio:.0f}/9")
        if de is not None and de < 0.5: quality_score += 1; quality_parts.append(f"D/E {de:.1f}")
        if quality_score >= 4:
            lines.append(f"Exceptional quality: {', '.join(quality_parts)}. This is cheap AND strong — rare combination.")
            strengths += 2
        elif quality_score >= 2:
            lines.append(f"Good quality: {', '.join(quality_parts)}. Meets all thresholds.")
            strengths += 1

        # Value trap detection — THE critical safety check
        rev_ok = rq is None or rq > -10
        prom_ok = prom is None or prom > 40
        if not rev_ok and not prom_ok:
            lines.append(f"🚨 VALUE TRAP: Revenue declining ({rq:+.0f}% QoQ) AND promoter low ({prom:.0f}%). Cheap for a reason. Skip.")
            red_flags.append("value trap")
            verdict, vc = "AVOID", "#dc2626"
        elif not rev_ok:
            lines.append(f"⚠ Revenue declining ({rq:+.0f}% QoQ). Watch if this is seasonal or structural.")
            red_flags.append("revenue decline")
        elif not prom_ok:
            lines.append(f"⚠ Promoter at {prom:.0f}%. Low skin in the game — monitor for further selling.")

        # Growth acceleration
        if pg and pg3:
            if pg > pg3 * 1.5 and pg > 15:
                lines.append(f"Growth accelerating: YoY +{pg:.0f}% vs 3Yr +{pg3:.0f}%. Recent quarters outperforming history.")
                strengths += 1
            elif pg < pg3 * 0.5 and pg3 > 15:
                lines.append(f"⚠ Growth decelerating: YoY +{pg:.0f}% vs 3Yr +{pg3:.0f}%. Recent quarters weaker than history.")
                red_flags.append("growth slowing")
        elif pg and pg > 20:
            lines.append(f"Profit growth +{pg:.0f}%{_vs_avg(pg,avg_pg)}. Earnings momentum supports the value thesis.")
            strengths += 1

        # Double screener
        if is_dbl:
            lines.append(f"Passed BOTH 4-filter and 6-filter screener. Stricter quality filters (D/E<1, PG>15%) also confirm.")
            strengths += 1

        # Cross-engine
        cross = signals.get("cross")
        if cross and "ALL 3" in cross[0]:
            lines.append(f"All 3 engines confirm — value + momentum + growth. Highest conviction entry.")
            strengths += 1
        elif cross:
            lines.append(f"Also in {cross[0].replace('+','')} screener — multiple angles validate this stock.")

        # VERDICT
        if "AVOID" not in verdict:
            if strengths >= 4 and not red_flags: verdict, vc = "ENTER", "#059669"
            elif strengths >= 3 and len(red_flags) <= 1: verdict, vc = "ENTER", "#059669"
            elif strengths >= 2: verdict, vc = "STALK", "#d97706"
            elif red_flags: verdict, vc = "AVOID", "#dc2626"

        # Targets
        if pe and pe < 25 and ltp:
            t25 = round(ltp * (pe*1.3)/pe); t50 = round(ltp * (pe*1.5)/pe); t75 = round(ltp * (pe*1.8)/pe)
            stop = round(ltp * 0.93)
            lines.append(f"Stop: ₹{stop:,} (-7%). Targets: Book 25% at ₹{t25:,}, 50% at ₹{t50:,}, 75% at ₹{t75:,}.")

    # ═══════════════════════════════════════════
    # ENGINE D — COMPOUNDER ANALYSIS
    # ═══════════════════════════════════════════
    elif engine == "D":
        # Growth is THE thesis
        if pg and pg > 30 and rq and rq > 0:
            lines.append(f"Growth engine firing on all cylinders: profit +{pg:.0f}% YoY, revenue +{rq:.0f}% QoQ. Both top-line and bottom-line growing.")
            strengths += 2
        elif pg and pg > 15 and rq and rq > 0:
            lines.append(f"Steady growth: profit +{pg:.0f}% YoY with revenue +{rq:.0f}% QoQ. Compounder thesis intact.")
            strengths += 1
        elif pg and pg > 15 and (rq is None or rq <= 0):
            lines.append(f"⚠ Profit growing (+{pg:.0f}%) but revenue {'declining ('+str(rq)+' QoQ)' if rq and rq<0 else 'flat'}. Profits may be from cost cuts, not real growth.")
            red_flags.append("revenue disconnect")
        elif pg and pg <= 0:
            lines.append(f"🚨 Profit declining ({pg:+.0f}%). Compounder thesis broken. Do not enter.")
            red_flags.append("no growth")
            verdict, vc = "AVOID", "#dc2626"

        # PEG tells you if you're paying fair price for growth
        if peg and peg > 0:
            if peg < 0.5:
                lines.append(f"PEG {peg:.1f} — market is severely underpricing this growth. Extreme value relative to earnings trajectory.")
                strengths += 2
            elif peg < 0.8:
                lines.append(f"PEG {peg:.1f} — growth not fully priced in. Good entry window.")
                strengths += 1
            elif peg <= 1.2:
                lines.append(f"PEG {peg:.1f} — fairly valued for growth. Enter on dips only.")
            else:
                lines.append(f"PEG {peg:.1f} — paying premium for growth. Wait for correction or acceleration.")
                red_flags.append("expensive PEG")

        # Kill shots
        kills = []
        if pg is not None and pg <= 0: kills.append("growth failing")
        if de is not None and de > 1.5: kills.append("debt creeping")
        if prom is not None and prom < 35: kills.append("promoter disengaged")
        if rq is not None and rq < -15: kills.append("revenue collapsing")
        if kills:
            lines.append(f"⚠ Kill shots: {', '.join(kills)}. {'2+ disqualifiers — REJECT.' if len(kills)>=2 else 'Monitor closely.'}")
            if len(kills) >= 2: red_flags.append("multiple kills"); verdict, vc = "AVOID", "#dc2626"
        else:
            lines.append(f"No kill shots. Growth + debt + promoter all clean.")
            strengths += 1

        # Growth acceleration
        if pg and pg3:
            if pg > pg3 * 1.5:
                lines.append(f"Growth accelerating: recent +{pg:.0f}% vs 3Yr trend +{pg3:.0f}%. Compounding is intensifying.")
                strengths += 1
            elif pg < pg3 * 0.5 and pg3 > 15:
                lines.append(f"⚠ Growth decelerating: +{pg:.0f}% vs 3Yr +{pg3:.0f}%. Watch for further slowdown.")

        # MCap runway
        if mcap:
            if mcap < 10000:
                lines.append(f"Small cap (₹{mcap:,.0f}Cr) — maximum compounding runway. Can 5-10x if growth sustains.")
                strengths += 1
            elif mcap < 50000:
                lines.append(f"Mid cap (₹{mcap:,.0f}Cr) — still has 2-3x potential. Sweet spot for compounders.")

        # Quality
        if roe and roe > 25 and pio and pio >= 8:
            lines.append(f"Quality elite: ROE {roe:.0f}%{_vs_avg(roe,avg_roe)}, Pio {pio:.0f}/9, D/E {de if de is not None else 'N/A'}. Business machine.")
            strengths += 1

        # Double + Cross
        if is_dbl:
            lines.append(f"Double screener (PEG + PE filters both confirm). Higher conviction.")
            strengths += 1
        cross = signals.get("cross")
        if cross and "ALL 3" in cross[0]:
            lines.append(f"All 3 engines confirm. Momentum + value + growth aligned.")
            strengths += 1

        # VERDICT
        if "AVOID" not in verdict:
            if strengths >= 4 and not red_flags: verdict, vc = "ENTER", "#059669"
            elif strengths >= 3 and len(red_flags) <= 1: verdict, vc = "ENTER", "#059669"
            elif strengths >= 2: verdict, vc = "STALK", "#d97706"
            elif red_flags: verdict, vc = "AVOID", "#dc2626"

        # Target from PEG normalization
        if peg and peg > 0 and peg < 1.5 and ltp:
            target = round(ltp / peg) if peg < 1 else round(ltp * 1.5)
            stop = round(ltp * 0.90)
            rr = round((target-ltp)/(ltp-stop),1) if (ltp-stop) > 0 else 0
            lines.append(f"Stop: ₹{stop:,} (-10%). Target: ₹{target:,}. Risk:Reward 1:{rr}{'— favorable.' if rr>=2 else '.'}")

    # ═══════════════════════════════════════════
    # Sector concentration warning (all engines)
    # ═══════════════════════════════════════════
    sec_sig = signals.get("sector_risk")
    if sec_sig and "BLOCKED" in sec_sig[0]:
        lines.append(f"🚫 Sector {sec} already at 30%+ of portfolio. Cannot add — sell one from this sector first.")
        verdict, vc = "BLOCKED", "#dc2626"
    elif sec_sig and "NEAR CAP" in sec_sig[0]:
        lines.append(f"Sector {sec} near 30% cap. Room for this stock, but no more after.")

    # Earnings freshness
    earn_sig = signals.get("earnings")
    if earn_sig and ("STALE" in earn_sig[0] or "OVERDUE" in earn_sig[0]):
        lines.append(f"⚠ Results data is old ({earn_sig[0]}). Numbers may change significantly with next filing.")

    # Engine A gate check
    if ea_score and ea_score <= 30:
        lines.append(f"🚫 Engine A at {ea_score}/100 — FREEZE mode. No new buys regardless of stock quality.")
        verdict, vc = "FREEZE", "#dc2626"
    elif ea_score and ea_score <= 20:
        verdict, vc = "EXIT ALL", "#dc2626"

    # ═══════════════════════════════════════════
    # BUILD HTML
    # ═══════════════════════════════════════════
    bg = "#f0fdf4" if vc == "#059669" else ("#fffbeb" if vc == "#d97706" else "#fef2f2")

    # Cross-engine badge
    cross = signals.get("cross")
    cross_html = ""
    if cross:
        cross_html = f" {_pill(cross[0], cross[1])}"

    analysis_text = " ".join(lines[:6])  # Cap at 6 most important lines

    html = (
        f"<div style='margin:8px 0;padding:10px 14px;border-radius:10px;"
        f"background:{bg};border-left:4px solid {vc};'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;'>"
        f"<span style='font-size:14px;font-weight:800;color:{vc};letter-spacing:1px;'>{verdict}</span>"
        f"<span>{cross_html}</span></div>"
        f"<div style='font-size:11px;color:#334155;line-height:1.6;'>{analysis_text}</div>"
        f"</div>"
    )
    return html

# ============================================================
# AI NARRATIVE — Layer 4 (Claude Sonnet API, ~Rs 1-2/stock)
# ============================================================
def get_anthropic_key():
    try: return st.secrets["ANTHROPIC_API_KEY"]
    except: return None

def ai_narrative(stock, engine, signals, engine_a_score=None):
    """Call Claude Sonnet API for narrative analysis. Returns HTML or None."""
    api_key = get_anthropic_key()
    if not api_key: return None

    nm = stock.get("name","Unknown"); tk = stock.get("ticker","")
    sec = stock.get("sector","")

    # Build signal summary for AI
    sig_text = ", ".join(f"{k}: {v[0]}" for k, v in signals.items())

    # Build data summary
    data_lines = []
    for k in ["roe","pe","piotroski","de","profit_growth","profit_growth_3yr","rev_qoq",
              "promoter","fii","inst","peg","mcap","delivery_pct","durability","momentum"]:
        v = stock.get(k)
        if v is not None: data_lines.append(f"{k}: {v}")
    data_text = ", ".join(data_lines)

    h52 = stock.get("high_52w","?"); l52 = stock.get("low_52w","?")
    ltp = stock.get("ltp",0)

    engine_names = {"B":"Momentum Hunter","C":"Value Warriors","D":"Compounders"}
    eng_name = engine_names.get(engine, engine)

    prompt = f"""You are an expert Indian equity analyst. Analyze this stock for Engine {engine} ({eng_name}).

STOCK: {nm} ({tk}) | Sector: {sec} | CMP: Rs {ltp} | 52W: Rs {l52} - Rs {h52}
DATA: {data_text}
RULES ENGINE SIGNALS: {sig_text}
ENGINE A SCORE: {engine_a_score or 'N/A'}/100

Write a compact analysis in EXACTLY this format (no markdown, plain text):
BUSINESS: [1 line - what company does, competitive position]
BULL: [2-3 strongest buy arguments with specific numbers from data]
BEAR: [2-3 risks with specific numbers]
VERDICT: [BUY/ACCUMULATE/WATCH/AVOID] [1 line reason]
ACTION: [Exact next step - buy X shares at Rs Y, or watch for Z signal]

Keep total under 150 words. Be specific with numbers. No generic statements."""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-6-20250514",
                "max_tokens": 400,
                "messages": [{"role":"user","content":prompt}]
            },
            timeout=30
        )
        if resp.status_code != 200: return None
        data = resp.json()
        text = data.get("content",[{}])[0].get("text","")
        if not text: return None

        # Parse sections and render
        lines = text.strip().split("\n")
        html = "<div style='padding:10px 12px;background:#f8fafc;border-radius:8px;border-left:3px solid #2563eb;margin-top:6px;'>"
        for line in lines:
            line = line.strip()
            if not line: continue
            for prefix, color in [("BUSINESS:","#475569"),("BULL:","#059669"),("BEAR:","#dc2626"),("VERDICT:","#2563eb"),("ACTION:","#7c3aed")]:
                if line.upper().startswith(prefix.upper()):
                    content = line[len(prefix):].strip()
                    html += f"<div style='margin-bottom:4px;'><span style='font-size:9px;font-weight:700;color:{color};letter-spacing:.5px;'>{prefix[:-1]}</span> <span style='font-size:10px;color:#475569;'>{content}</span></div>"
                    break
        html += "</div>"
        return html
    except Exception as e:
        return None

