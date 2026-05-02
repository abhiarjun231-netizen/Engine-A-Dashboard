"""
generate_dashboard_data.py
Reads Engine A score, Trendlyne CSVs, stock positions, and Angel One data
to generate docs/data.json for the GitHub Pages dashboard.

Run by GitHub Actions cron after test_angel.py completes.
"""

import json
import csv
import os
from datetime import datetime

# ── Paths ──
DATA_DIR = "data"
DOCS_DIR = "docs"
SCORE_FILE = os.path.join(DATA_DIR, "engine_a_score.csv")
STOCKS_FILE = os.path.join(DATA_DIR, "engine_b_stocks.json")
OUTPUT_FILE = os.path.join(DOCS_DIR, "data.json")

# CSV prefix mapping
CSV_MAP = {
    "Mom": "momentum",
    "C1": "value_s1",
    "C2": "value_s2",
    "D1": "compounder_s3",
    "D2": "compounder_s4",
}

# ── Allocation bands (Engine A) ──
ALLOC_BANDS = [
    (20, 10, 65, 25),
    (30, 25, 50, 25),
    (40, 40, 40, 20),
    (52, 55, 30, 15),
    (62, 70, 20, 10),
    (999, 85, 10, 5),
]


def get_allocation(score):
    for cap, eq, debt, gold in ALLOC_BANDS:
        if score <= cap:
            return {"equity": eq, "debt": debt, "gold": gold}
    return {"equity": 85, "debt": 10, "gold": 5}


# ── Column matching helpers ──
def find_col(headers, patterns):
    """Find a column by checking multiple possible names."""
    h_lower = [h.lower().strip() for h in headers]
    for pat in patterns:
        for i, h in enumerate(h_lower):
            if pat.lower() in h:
                return i
    return -1


def safe_float(val, default=0):
    """Convert value to float, return default if fails."""
    if val is None:
        return default
    try:
        v = str(val).strip().replace(",", "").replace("%", "")
        if v == "" or v.lower() in ("nan", "none", "-", "n/a"):
            return default
        return float(v)
    except (ValueError, TypeError):
        return default


def safe_str(val, default=""):
    if val is None:
        return default
    s = str(val).strip()
    return default if s.lower() in ("nan", "none", "") else s


# ── Read Engine A Score ──
def read_engine_a():
    result = {
        "score": 0,
        "prevScore": 0,
        "components": [],
        "history": [],
        "capital": 500000,
    }

    if not os.path.exists(SCORE_FILE):
        print(f"[WARN] {SCORE_FILE} not found, using defaults")
        return result

    try:
        with open(SCORE_FILE, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            return result

        # Get headers (lowercase for matching)
        headers = {k.lower().strip(): k for k in rows[0].keys()}

        # Read score history
        scores = []
        for row in rows:
            for key in ["raw_score", "score", "total_score"]:
                if key in headers:
                    val = safe_float(row.get(headers[key], 0))
                    if val > 0:
                        scores.append(val)
                        break

        if scores:
            result["score"] = int(scores[-1])
            result["prevScore"] = int(scores[-2]) if len(scores) > 1 else int(scores[-1])
            result["history"] = [int(s) for s in scores[-12:]]  # Last 12 weeks

        # Read components from latest row
        latest = rows[-1]
        comp_names = [
            ("valuation", "Valuation", 15),
            ("trend", "Trend", 15),
            ("breadth", "Breadth", 12),
            ("volatility", "Volatility", 10),
            ("flow", "Flows", 12),
            ("macro", "Macro", 12),
            ("global", "Global", 12),
            ("crude", "Crude", 12),
        ]

        for search_key, display_name, max_val in comp_names:
            for col_name, orig_key in headers.items():
                if search_key in col_name and "score" not in col_name:
                    val = safe_float(latest.get(orig_key, 0))
                    result["components"].append({
                        "name": display_name,
                        "score": min(int(val), max_val),
                        "max": max_val
                    })
                    break
            else:
                result["components"].append({
                    "name": display_name, "score": 0, "max": max_val
                })

    except Exception as e:
        print(f"[ERROR] Reading Engine A: {e}")

    return result


# ── Read CSVs ──
def find_csv(prefix):
    """Find latest CSV with given prefix in data/ folder."""
    if not os.path.exists(DATA_DIR):
        return None
    files = [f for f in os.listdir(DATA_DIR) if f.startswith(prefix) and f.endswith(".csv")]
    if not files:
        return None
    files.sort(key=lambda x: os.path.getmtime(os.path.join(DATA_DIR, x)), reverse=True)
    return os.path.join(DATA_DIR, files[0])


def read_csv_stocks(filepath):
    """Read a Trendlyne CSV and extract stock data."""
    stocks = []
    if not filepath or not os.path.exists(filepath):
        return stocks

    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            headers_raw = next(reader, [])
            headers = [h.strip() for h in headers_raw]

            # Find column indices
            col = {}
            col["name"] = find_col(headers, ["company", "name", "stock"])
            col["ticker"] = find_col(headers, ["ticker", "symbol", "nse code", "nse symbol"])
            col["price"] = find_col(headers, ["price", "cmp", "close", "last", "current price"])
            col["mcap"] = find_col(headers, ["market cap", "mcap", "m.cap", "m cap"])
            col["roe"] = find_col(headers, ["roe annual", "roe %", "roe"])
            col["pe"] = find_col(headers, ["pe ttm", "pe ratio", "p/e"])
            col["pio"] = find_col(headers, ["piotroski", "pio"])
            col["de"] = find_col(headers, ["debt to equity", "d/e", "debt equity", "de ratio"])
            col["pg"] = find_col(headers, ["profit growth", "profit growth annual", "pat growth"])
            col["prom"] = find_col(headers, ["promoter hold", "promoter %", "promoter"])
            col["fii"] = find_col(headers, ["fii hold", "fii %", "fii"])
            col["inst"] = find_col(headers, ["institutional", "inst hold", "inst %", "dii"])
            col["dvm_d"] = find_col(headers, ["durability", "dvm durability", "trendlyne durability"])
            col["dvm_m"] = find_col(headers, ["momentum score", "dvm momentum", "trendlyne momentum"])
            col["peg"] = find_col(headers, ["peg ttm", "peg ratio", "peg"])
            col["rev_qoq"] = find_col(headers, ["revenue qoq", "rev qoq", "revenue growth qoq"])
            col["delivery"] = find_col(headers, ["delivery", "delivery %", "delivery avg"])
            col["sector"] = find_col(headers, ["sector", "industry"])
            col["w52_high"] = find_col(headers, ["52 week high", "52w high", "52wk high", "high 52"])
            col["w52_low"] = find_col(headers, ["52 week low", "52w low", "52wk low", "low 52"])
            col["pg_3yr"] = find_col(headers, ["profit growth 3yr", "pg 3yr", "profit growth 3 yr"])

            for row in reader:
                if len(row) < 3:
                    continue

                def get(key, default=0):
                    idx = col.get(key, -1)
                    if idx < 0 or idx >= len(row):
                        return default
                    return safe_float(row[idx], default) if isinstance(default, (int, float)) else safe_str(row[idx], default)

                ticker = ""
                if col["ticker"] >= 0 and col["ticker"] < len(row):
                    ticker = safe_str(row[col["ticker"]])
                if not ticker and col["name"] >= 0 and col["name"] < len(row):
                    ticker = safe_str(row[col["name"]])

                if not ticker or ticker.lower() in ("nan", "", "none"):
                    continue

                price = get("price", 0)
                mcap = get("mcap", 0)
                w52h = get("w52_high", 0)
                w52l = get("w52_low", 0)

                # 52W position
                w52_pos = 50
                if w52h > w52l and w52h > 0 and price > 0:
                    w52_pos = int(((price - w52l) / (w52h - w52l)) * 100)
                    w52_pos = max(0, min(100, w52_pos))

                # MCap badge
                badge = "SMALL"
                if mcap >= 50000:
                    badge = "LARGE"
                elif mcap >= 5000:
                    badge = "MID"

                stock = {
                    "ticker": ticker.replace(".NS", "").replace(".BO", "").upper().strip(),
                    "price": round(price, 2),
                    "change": 0,  # Updated by live price fetch
                    "mcap": round(mcap, 0),
                    "badge": badge,
                    "roe": round(get("roe"), 1),
                    "pe": round(get("pe"), 1),
                    "pio": int(get("pio")),
                    "de": round(get("de"), 2),
                    "pg": round(get("pg"), 1),
                    "prom": round(get("prom"), 1),
                    "fii": round(get("fii"), 1),
                    "inst": round(get("inst"), 1),
                    "dvm_d": int(get("dvm_d")),
                    "dvm_m": int(get("dvm_m")),
                    "peg": round(get("peg"), 2),
                    "rev_qoq": round(get("rev_qoq"), 1),
                    "delivery": round(get("delivery"), 1),
                    "sector": get("sector", "—") if isinstance("", str) else "—",
                    "w52_pos": w52_pos,
                    "pg_3yr": round(get("pg_3yr"), 1),
                }

                # Fix sector to be string
                if col["sector"] >= 0 and col["sector"] < len(row):
                    stock["sector"] = safe_str(row[col["sector"]], "—")

                stocks.append(stock)

    except Exception as e:
        print(f"[ERROR] Reading CSV {filepath}: {e}")

    return stocks


# ── Scoring Functions ──

def calc_conviction(stock, all_tickers_c, all_tickers_d):
    """Engine B conviction score (max 10)."""
    score = 0
    t = stock["ticker"]
    if t in all_tickers_c or t in all_tickers_d:
        score += 3  # Multi-engine
    if stock["dvm_d"] > 75:
        score += 2  # Durability fortress
    if stock["dvm_m"] > 70:
        score += 2  # Momentum surge
    if stock["pio"] >= 7:
        score += 1
    if stock["delivery"] > 50:
        score += 1
    score += 1  # Fresh qualifier (simplified)
    return min(score, 10)


def calc_vds(stock):
    """Value Depth Score (max 15)."""
    score = 0
    # Quality (max 6)
    if stock["pio"] >= 9: score += 3
    elif stock["pio"] >= 8: score += 2
    elif stock["pio"] >= 7: score += 1
    if stock["roe"] > 25: score += 2
    elif stock["roe"] > 20: score += 1
    # Value (max 5)
    if stock["pe"] > 0:
        if stock["pe"] < 12: score += 3
        elif stock["pe"] < 18: score += 2
        elif stock["pe"] < 25: score += 1
    # Trend (max 4)
    if stock["pg"] > 30: score += 1
    if stock["de"] < 0.5: score += 1
    return min(score, 15)


def calc_dna(stock):
    """Compounder DNA Score (max 20)."""
    score = 0
    # Earnings (max 6)
    if stock["pg"] > 30: score += 3
    elif stock["pg"] > 15: score += 2
    if stock["rev_qoq"] > 0: score += 1
    # Quality (max 6)
    if stock["pio"] >= 9: score += 3
    elif stock["pio"] >= 8: score += 2
    if stock["roe"] > 25: score += 2
    if stock["de"] < 0.3: score += 2
    elif stock["de"] < 0.5: score += 1
    # Growth (max 4)
    if stock["peg"] > 0:
        if stock["peg"] < 0.8: score += 2
        elif stock["peg"] < 1.2: score += 1
    # Market (max 4)
    if stock["mcap"] > 10000: score += 1
    if stock["mcap"] < 50000: score += 1
    return min(score, 20)


def calc_ai_score(stock, engine_a_score, engine_type="momentum"):
    """AI Analyst 8-dimension scoring (max 40)."""
    score = 0

    # 1. Valuation (max 9)
    pe = stock.get("pe", 0)
    peg = stock.get("peg", 0)
    if pe > 0:
        if pe < 12: score += 5
        elif pe < 18: score += 4
        elif pe < 25: score += 3
        elif pe < 35: score += 1
    if peg > 0:
        if peg < 0.8: score += 4
        elif peg < 1.2: score += 3
        elif peg < 1.5: score += 1

    # 2. Quality (max 6)
    if stock.get("roe", 0) > 25: score += 3
    elif stock.get("roe", 0) > 15: score += 2
    if stock.get("pio", 0) >= 8: score += 2
    elif stock.get("pio", 0) >= 7: score += 1
    if stock.get("de", 99) < 0.5: score += 1

    # 3. Growth (max 5)
    pg = stock.get("pg", 0)
    if pg > 30: score += 3
    elif pg > 15: score += 2
    elif pg > 0: score += 1
    rq = stock.get("rev_qoq", 0)
    if rq > 10: score += 2
    elif rq > 0: score += 1

    # 4. Momentum (max 5)
    d = stock.get("dvm_d", 0)
    m = stock.get("dvm_m", 0)
    if d > 55 and m > 59: score += 3
    elif d > 45 and m > 49: score += 1
    if m > 70: score += 2

    # 5. Ownership (max 4)
    if stock.get("prom", 0) > 60: score += 2
    elif stock.get("prom", 0) > 50: score += 1
    if stock.get("fii", 0) > 15: score += 1
    if stock.get("inst", 0) > 15: score += 1

    # 6. Technical (max 3)
    w52 = stock.get("w52_pos", 50)
    if 40 <= w52 <= 80: score += 2
    elif 20 <= w52 <= 90: score += 1
    if w52 > 60: score += 1

    # 7. Multi-engine (max 5) - handled by caller
    # 8. Engine A gate (max 5)
    if engine_a_score > 62: score += 5
    elif engine_a_score > 52: score += 3
    elif engine_a_score > 40: score += 1
    elif engine_a_score <= 30: score -= 3

    return max(min(score, 40), -5)


def get_verdict(ai_score):
    if ai_score >= 25: return "STRONG BUY"
    if ai_score >= 18: return "BUY"
    if ai_score >= 12: return "ACCUMULATE"
    if ai_score >= 6: return "WAIT"
    if ai_score >= 0: return "AVOID"
    return "DANGER"


def get_signal(stock, engine_type):
    """Generate smart signal text."""
    parts = []

    if engine_type == "momentum":
        if stock.get("dvm_d", 0) > 70:
            parts.append("DVM fortress")
        if stock.get("dvm_m", 0) > 65:
            parts.append("momentum surge")
        if stock.get("vol_ratio", 0) >= 2:
            parts.append("Volume unusual — something happening")
        if stock.get("delivery", 0) >= 60:
            parts.append("institutional accumulation confirmed")
        if not parts:
            parts.append("Momentum holding steady")

    elif engine_type == "value":
        if stock.get("pe", 99) < 12:
            parts.append("PE at extreme discount")
        elif stock.get("pe", 99) < 18:
            parts.append("Attractive PE valuation")
        if stock.get("delivery", 0) >= 60:
            parts.append("High delivery confirms buying")
        if stock.get("roe", 0) > 25:
            parts.append("Exceptional ROE")
        if not parts:
            parts.append("Value opportunity in watchlist")

    elif engine_type == "compounder":
        if stock.get("peg", 99) < 0.8:
            parts.append(f"PEG {stock.get('peg', 0)} = extreme undervalue")
        if stock.get("pg", 0) > 30:
            parts.append("Strong profit growth")
        if stock.get("delivery", 0) >= 65:
            parts.append(f"Delivery {stock.get('delivery', 0)}% = accumulation")
        if stock.get("pio", 0) >= 9:
            parts.append("Perfect Piotroski")
        if not parts:
            parts.append("Compounding candidate under review")

    return ". ".join(parts) + "."


# ── Read positions/watchlists ──
def read_positions():
    """Read engine_b_stocks.json for positions and watchlists."""
    data = {}
    if os.path.exists(STOCKS_FILE):
        try:
            with open(STOCKS_FILE, "r") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[WARN] Reading positions: {e}")
    return data


# ── Read live prices from Angel One output ──
def read_live_prices():
    """Read latest prices from Angel One data files."""
    prices = {}
    price_files = [
        os.path.join(DATA_DIR, "stock_prices.json"),
        os.path.join(DATA_DIR, "live_prices.json"),
    ]
    for pf in price_files:
        if os.path.exists(pf):
            try:
                with open(pf, "r") as f:
                    d = json.load(f)
                if isinstance(d, dict):
                    prices.update(d)
            except:
                pass
    return prices


# ── Build Dashboard Data ──
def build_dashboard():
    print("=" * 50)
    print("GENERATING DASHBOARD DATA")
    print("=" * 50)

    # 1. Engine A
    engine_a = read_engine_a()
    score = engine_a["score"]
    alloc = get_allocation(score)
    engine_a["allocation"] = alloc

    print(f"[OK] Engine A: Score {score}, Equity {alloc['equity']}%")

    # 2. Read all CSVs
    mom_stocks = read_csv_stocks(find_csv("Mom"))
    c1_stocks = read_csv_stocks(find_csv("C1"))
    c2_stocks = read_csv_stocks(find_csv("C2"))
    d1_stocks = read_csv_stocks(find_csv("D1"))
    d2_stocks = read_csv_stocks(find_csv("D2"))

    print(f"[OK] CSVs: Mom={len(mom_stocks)}, C1={len(c1_stocks)}, C2={len(c2_stocks)}, D1={len(d1_stocks)}, D2={len(d2_stocks)}")

    # 3. Build ticker sets for cross-engine detection
    val_tickers = set(s["ticker"] for s in c1_stocks + c2_stocks)
    comp_tickers = set(s["ticker"] for s in d1_stocks + d2_stocks)
    mom_tickers = set(s["ticker"] for s in mom_stocks)

    # 4. Read positions and live prices
    positions = read_positions()
    live_prices = read_live_prices()

    # 5. Process Momentum (Engine B)
    momentum = []
    for s in mom_stocks:
        t = s["ticker"]
        # Multi-engine detection
        multi = ""
        in_val = t in val_tickers
        in_comp = t in comp_tickers
        if in_val and in_comp: multi = "ALL 3"
        elif in_val: multi = "+VALUE"
        elif in_comp: multi = "+COMPOUNDER"

        # Conviction & lifecycle stage
        conv = calc_conviction(s, val_tickers, comp_tickers)
        stage = "SCOUT"
        if conv >= 7: stage = "STRIKE"
        elif conv >= 4: stage = "STALK"
        else: stage = "WEAK"

        # AI Score
        ai = calc_ai_score(s, score, "momentum")
        if multi == "ALL 3": ai += 5
        elif multi: ai += 3

        # Apply live price if available
        if t in live_prices:
            lp = live_prices[t]
            if isinstance(lp, dict):
                s["price"] = lp.get("price", s["price"])
                s["change"] = lp.get("change", 0)
                s["vol_ratio"] = lp.get("vol_ratio", 0)

        momentum.append({
            **s,
            "multi": multi,
            "stage": stage,
            "conviction": conv,
            "ai_score": min(ai, 40),
            "verdict": get_verdict(ai),
            "signal": get_signal(s, "momentum"),
            "velocity": "+0",
            "vel_label": "STEADY",
            "earnings": "—",
        })

    momentum.sort(key=lambda x: x["ai_score"], reverse=True)
    print(f"[OK] Momentum: {len(momentum)} stocks processed")

    # 6. Process Value (Engine C) — merge C1 + C2, deduplicate
    val_map = {}
    for s in c1_stocks + c2_stocks:
        t = s["ticker"]
        if t not in val_map:
            val_map[t] = {**s, "double_screener": False}
        else:
            val_map[t]["double_screener"] = True

    value = []
    for t, s in val_map.items():
        multi = ""
        in_mom = t in mom_tickers
        in_comp = t in comp_tickers
        if in_mom and in_comp: multi = "ALL 3"
        elif in_comp: multi = "+COMPOUNDER"
        elif in_mom: multi = "+MOMENTUM"

        vds = calc_vds(s)
        if s["double_screener"]:
            vds = min(vds + 2, 15)

        ai = calc_ai_score(s, score, "value")
        if multi == "ALL 3": ai += 5
        elif multi: ai += 3

        # Value trap detection
        trap_rev = s.get("rev_qoq", 0) >= -10
        trap_prom = s.get("prom", 0) >= 0  # Simplified — needs history

        # PE Expansion room
        current_pe = s.get("pe", 0)
        pe_room = {
            "current": round(current_pe, 1),
            "p25": round(current_pe * 1.3, 1),
            "p50": round(current_pe * 1.5, 1),
            "p75": round(current_pe * 1.8, 1),
        }

        if t in live_prices:
            lp = live_prices[t]
            if isinstance(lp, dict):
                s["price"] = lp.get("price", s["price"])
                s["change"] = lp.get("change", 0)

        value.append({
            **s,
            "multi": multi,
            "vds": vds,
            "ai_score": min(ai, 40),
            "verdict": get_verdict(ai),
            "signal": get_signal(s, "value"),
            "trap": {"rev": trap_rev, "prom": trap_prom},
            "pe_room": pe_room,
        })

    value.sort(key=lambda x: x["ai_score"], reverse=True)
    print(f"[OK] Value: {len(value)} stocks processed")

    # 7. Process Compounders (Engine D) — merge D1 + D2
    comp_map = {}
    for s in d1_stocks + d2_stocks:
        t = s["ticker"]
        if t not in comp_map:
            comp_map[t] = {**s, "double_screener": False}
        else:
            comp_map[t]["double_screener"] = True

    compounders = []
    for t, s in comp_map.items():
        multi = ""
        in_mom = t in mom_tickers
        in_val = t in val_tickers
        if in_mom and in_val: multi = "ALL 3"
        elif in_val: multi = "+VALUE"
        elif in_mom: multi = "+MOMENTUM"

        dna = calc_dna(s)
        if s["double_screener"]:
            dna = min(dna + 2, 20)

        # Stars
        stars = 1
        if dna >= 16: stars = 5
        elif dna >= 13: stars = 4
        elif dna >= 10: stars = 3
        elif dna >= 7: stars = 2

        ai = calc_ai_score(s, score, "compounder")
        if multi == "ALL 3": ai += 5
        elif multi: ai += 3

        # Kill shot checks (simplified)
        ks_growth = s.get("pg", 0) > 0
        ks_debt = s.get("de", 99) < 1.0

        # PEG interpretation
        peg = s.get("peg", 0)
        peg_label = "FAIR"
        if peg > 0:
            if peg < 0.8: peg_label = "EXTREME"
            elif peg < 1.2: peg_label = "UNDER"
            elif peg > 1.5: peg_label = "EXPENSIVE"

        if t in live_prices:
            lp = live_prices[t]
            if isinstance(lp, dict):
                s["price"] = lp.get("price", s["price"])
                s["change"] = lp.get("change", 0)

        compounders.append({
            **s,
            "multi": multi,
            "dna": dna,
            "stars": stars,
            "ai_score": min(ai, 40),
            "verdict": get_verdict(ai),
            "signal": get_signal(s, "compounder"),
            "killshot": {"growth": ks_growth, "debt": ks_debt},
            "peg_label": peg_label,
            "stage": "IDENTIFY",
            "ets": 2,
        })

    compounders.sort(key=lambda x: x["ai_score"], reverse=True)
    print(f"[OK] Compounders: {len(compounders)} stocks processed")

    # 8. Command Center
    all_tickers_all3 = mom_tickers & val_tickers & comp_tickers
    all_tickers_2 = (mom_tickers & val_tickers) | (mom_tickers & comp_tickers) | (val_tickers & comp_tickers)
    all_stocks = momentum + value + compounders

    power_picks = []
    for t in all_tickers_all3:
        match = next((s for s in all_stocks if s["ticker"] == t), None)
        if match:
            power_picks.append(match)
    power_picks.sort(key=lambda x: x["ai_score"], reverse=True)

    # Engine health (simplified)
    def engine_health(stocks):
        if not stocks:
            return 0
        avg_ai = sum(s["ai_score"] for s in stocks) / len(stocks)
        return min(int((avg_ai / 40) * 100), 100)

    command = {
        "powerPicks": [s["ticker"] for s in power_picks[:10]],
        "all3Count": len(all_tickers_all3),
        "dual_count": len(all_tickers_2 - all_tickers_all3),
        "totalPositions": len(momentum) + len(value) + len(compounders),
        "engineHealth": {
            "b": engine_health(momentum),
            "c": engine_health(value),
            "d": engine_health(compounders),
            "e": 90,  # Fortress is always healthy
        },
    }

    # 9. Fortress (static from Engine A)
    fortress = {
        "rbi": "Neutral",
        "duration": "MEDIUM",
        "instrument": "Corporate Bond Funds",
        "gold_signal": "HOLD",
        "gvix": 0,
        "crude": 0,
        "inr": 0,
        "debt_alloc": int(engine_a["capital"] * alloc["debt"] / 100),
        "gold_alloc": int(engine_a["capital"] * alloc["gold"] / 100),
        "bharatbond": {"name": "BHARATBOND-APR30", "nav": 0, "ytm": 0},
        "goldbees": {"name": "GOLDBEES", "price": 0, "change": 0},
    }

    # Try to read macro data
    macro_file = os.path.join(DATA_DIR, "engine_a_inputs.json")
    if os.path.exists(macro_file):
        try:
            with open(macro_file, "r") as f:
                macro = json.load(f)
            fortress["gvix"] = macro.get("gvix", 0)
            fortress["crude"] = macro.get("crude", 0)
            fortress["inr"] = macro.get("inr", 0)
        except:
            pass

    # 10. Assemble
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")

    dashboard = {
        "engineA": engine_a,
        "momentum": momentum[:25],  # Top 25
        "value": value[:25],
        "compounders": compounders[:25],
        "fortress": fortress,
        "command": command,
        "lastUpdate": now,
    }

    # Write JSON
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(dashboard, f, indent=2)

    print(f"\n[DONE] Dashboard data written to {OUTPUT_FILE}")
    print(f"  Momentum: {len(momentum)} | Value: {len(value)} | Compounders: {len(compounders)}")
    print(f"  Power Picks (ALL 3): {len(all_tickers_all3)}")
    print(f"  Last Update: {now}")


if __name__ == "__main__":
    build_dashboard()
