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
        "_capital": 100000, "_token_cache": {},
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
            elif "roce" in cl:
                col_map["roce"] = c

        stocks = []
        for _, row in df.iterrows():
            stock = {}
            stock["name"] = str(row.get(col_map.get("stock", ""), "")).strip()
            stock["ticker"] = str(row.get(col_map.get("ticker", ""), "")).strip()

            if not stock["name"] or not stock["ticker"]:
                continue

            for key in ["roe", "pe", "piotroski", "ltp", "mcap", "de", "peg", "profit_growth", "rev_qoq", "sma200", "durability", "momentum", "promoter", "fii", "dii", "high_52w", "low_52w", "roce"]:
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
