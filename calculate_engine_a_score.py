"""
calculate_engine_a_score.py - Engine A Market Strength Scoring Engine

Reads:
  - data/live_prices.csv       (today's Indian indices)
  - data/global_prices.csv     (today's global metrics)
  - data/historical_prices.csv (daily closes for DMA + directions)
  - manual_inputs.json         (PE, FII, DII, breadth, RBI, CPI, PMI, yield)

Writes:
  - data/engine_a_score.csv    (score + components + allocation)
  - data/score_history.csv     (append-only score history for charts)

Scoring logic mirrors Master_System_v2 Excel "Engine A Dashboard" sheet.
Every function cites the Excel cell whose formula it implements.
"""

import csv
import json
from pathlib import Path
from datetime import datetime, timedelta

print("=" * 50)
print("ENGINE A - SCORING ENGINE v1.1")
print("=" * 50)

# ============================================================
# STEP 1: LOAD ALL DATA SOURCES
# ============================================================

def load_live_prices():
    out = {}
    path = Path("data/live_prices.csv")
    if not path.exists():
        print("ERROR: data/live_prices.csv missing")
        return out
    with open(path, "r", newline="") as f:
        for row in csv.DictReader(f):
            if row["price"]:
                out[row["symbol"]] = float(row["price"])
    return out

def load_global_prices():
    out = {}
    path = Path("data/global_prices.csv")
    if not path.exists():
        print("ERROR: data/global_prices.csv missing")
        return out
    with open(path, "r", newline="") as f:
        for row in csv.DictReader(f):
            if row["price"]:
                out[row["symbol"]] = float(row["price"])
    return out

def load_history():
    out = {}
    path = Path("data/historical_prices.csv")
    if not path.exists():
        print("ERROR: data/historical_prices.csv missing")
        return out
    with open(path, "r", newline="") as f:
        for row in csv.DictReader(f):
            out.setdefault(row["symbol"], []).append((row["date"], float(row["close"])))
    for sym in out:
        out[sym].sort(key=lambda x: x[0])
    return out

def load_manual_inputs():
    result = {}

    # Source 1: data/manual_inputs.json (GitHub Pages flat format)
    # Keys: nifty_pe, fii, dii, breadth, yield_inverted, rbi_stance, cpi, pmi
    data_path = Path("data/manual_inputs.json")
    if data_path.exists():
        try:
            with open(data_path, "r") as f:
                flat = json.load(f)
            key_map = {
                "nifty_pe": "nifty_pe",
                "fii": "fii_30day_net_cr",
                "dii": "dii_30day_net_cr",
                "breadth": "breadth_pct_above_200dma",
                "yield_inverted": "yield_curve_inverted",
                "rbi_stance": "rbi_stance",
                "cpi": "cpi_pct",
                "pmi": "pmi_manufacturing",
            }
            # Also handle long keys already in data/ file
            long_keys = set(key_map.values())
            for k, raw in flat.items():
                if k.startswith("_"): continue
                v = raw.get("value") if isinstance(raw, dict) and "value" in raw else raw
                if v is None: continue
                if k in key_map:
                    result[key_map[k]] = v
                elif k in long_keys:
                    result[k] = v
            print(f"  Loaded {len(result)} fields from data/manual_inputs.json")
        except Exception as e:
            print(f"  WARN: data/manual_inputs.json read error: {e}")

    # Source 2: root manual_inputs.json (Streamlit nested format)
    # Keys: nifty_pe.value, fii_30day_net_cr.value, etc.
    root_path = Path("manual_inputs.json")
    if root_path.exists():
        try:
            with open(root_path, "r") as f:
                data = json.load(f)
            root_count = 0
            for key, obj in data.items():
                if key.startswith("_"):
                    continue
                val = obj.get("value") if isinstance(obj, dict) else obj
                if val is not None and key not in result:
                    result[key] = val
                    root_count += 1
            print(f"  Loaded {root_count} additional fields from manual_inputs.json")
        except Exception as e:
            print(f"  WARN: manual_inputs.json read error: {e}")

    if not result:
        print("ERROR: No manual inputs found in either file")
    return result

print("\n--- LOADING DATA ---")
live = load_live_prices()
glob = load_global_prices()
hist = load_history()
manual = load_manual_inputs()
print(f"Live prices:    {len(live)} symbols")
print(f"Global prices:  {len(glob)} symbols")
print(f"History:        {sum(len(v) for v in hist.values())} rows across {len(hist)} symbols")
print(f"Manual inputs:  {len(manual)} fields")

# ============================================================
# STEP 2: COMPUTE DERIVED VALUES FROM HISTORY
# ============================================================

def compute_sma(series, window):
    if len(series) < window:
        return None
    closes = [c for _, c in series[-window:]]
    return sum(closes) / window

def compute_sma_at(series, window, offset_from_end):
    if len(series) < window + offset_from_end:
        return None
    end_idx = len(series) - offset_from_end
    closes = [c for _, c in series[end_idx - window:end_idx]]
    return sum(closes) / window

def get_price_n_bars_ago(series, n_bars):
    if len(series) <= n_bars:
        return None
    return series[-1 - n_bars][1]

def classify_direction(current, past, flat_threshold_pct=0.5):
    if current is None or past is None or past == 0:
        return "Stable"
    change_pct = (current - past) / past * 100
    if change_pct > flat_threshold_pct:
        return "Rising"
    if change_pct < -flat_threshold_pct:
        return "Falling"
    return "Stable"

def classify_dma_direction(current_dma, last_week_dma):
    if current_dma is None or last_week_dma is None:
        return "Flat"
    if current_dma > last_week_dma:
        return "Rising"
    if current_dma < last_week_dma:
        return "Falling"
    return "Flat"

def classify_inr_direction(current, past):
    if current is None or past is None or past == 0:
        return "Stable"
    change_pct = (current - past) / past * 100
    if change_pct < -0.5:
        return "Strengthening"
    if change_pct > 0.5:
        return "Weakening"
    return "Stable"

print("\n--- COMPUTING DERIVED VALUES ---")

nifty_series = hist.get("Nifty 50", [])
nifty_200dma = compute_sma(nifty_series, 200)
nifty_200dma_lastwk = compute_sma_at(nifty_series, 200, 5)
dma_direction = classify_dma_direction(nifty_200dma, nifty_200dma_lastwk)
nifty_close = live.get("Nifty 50")

pct_vs_dma = None
if nifty_close is not None and nifty_200dma is not None and nifty_200dma > 0:
    pct_vs_dma = round((nifty_close - nifty_200dma) / nifty_200dma * 100, 1)

print(f"Nifty close:          {nifty_close}")
print(f"Nifty 200-DMA:        {nifty_200dma:.2f}" if nifty_200dma else "Nifty 200-DMA: NOT ENOUGH DATA")
print(f"200-DMA last week:    {nifty_200dma_lastwk:.2f}" if nifty_200dma_lastwk else "200-DMA last week: NOT ENOUGH DATA")
print(f"DMA direction:        {dma_direction}")
print(f"% vs 200-DMA:         {pct_vs_dma}")

us10y_series   = hist.get("US 10Y Yield", [])
inr_series     = hist.get("INR/USD", [])
crude_series   = hist.get("Brent Crude", [])

us10y_today    = live.get("US 10Y Yield") or glob.get("US 10Y Yield")
inr_today      = live.get("INR/USD")       or glob.get("INR/USD")
crude_today    = live.get("Brent Crude")   or glob.get("Brent Crude")

us10y_4wk      = get_price_n_bars_ago(us10y_series, 20)
inr_4wk        = get_price_n_bars_ago(inr_series, 20)
crude_4wk      = get_price_n_bars_ago(crude_series, 20)

us10y_dir      = classify_direction(us10y_today, us10y_4wk)
inr_dir        = classify_inr_direction(inr_today, inr_4wk)
crude_dir      = classify_direction(crude_today, crude_4wk)

print(f"US10Y: {us10y_today} (4wk ago {us10y_4wk}) -> {us10y_dir}")
print(f"INR:   {inr_today} (4wk ago {inr_4wk}) -> {inr_dir}")
print(f"Crude: {crude_today} (4wk ago {crude_4wk}) -> {crude_dir}")

# ============================================================
# STEP 3: COMPONENT SCORING FUNCTIONS
# ============================================================

def score_valuation(pe):
    if pe is None: return 0
    if pe < 18: return 15
    if pe < 20: return 12
    if pe < 22: return 9
    if pe < 24: return 4
    if pe < 26: return 2
    return 0

def score_trend(pct_vs_dma, dma_dir):
    if pct_vs_dma is None: return 0
    if pct_vs_dma > 10:
        return 15 if dma_dir == "Rising" else 13
    if pct_vs_dma > 5:
        return 13 if dma_dir == "Rising" else 11
    if pct_vs_dma > 0:
        return 10 if dma_dir == "Rising" else 7
    if pct_vs_dma > -5:
        return 5
    if pct_vs_dma > -10:
        return 3
    return 0

def score_breadth(pct):
    if pct is None: return 0
    if pct > 70: return 12
    if pct > 60: return 10
    if pct > 50: return 8
    if pct > 40: return 6
    if pct > 30: return 4
    if pct > 20: return 2
    return 0

def score_volatility(vix):
    if vix is None: return 0
    if vix < 12: return 10
    if vix < 15: return 8
    if vix < 18: return 6
    if vix < 22: return 4
    if vix < 30: return 2
    return 0

def score_flows(fii, dii):
    if fii is None or dii is None: return 0
    if   fii >  5000:  f = 6
    elif fii >     0:  f = 5
    elif fii > -5000:  f = 4
    elif fii > -10000: f = 2
    elif fii > -20000: f = 1
    else:              f = 0
    if   dii > 15000: d = 6
    elif dii > 10000: d = 5
    elif dii >  5000: d = 4
    elif dii >     0: d = 3
    elif dii > -5000: d = 1
    else:             d = 0
    return min(12, f + d)

def score_macro(rbi, cpi, pmi, yield_inverted):
    rbi_map = {
        "Accommodative-Cutting": 4,
        "Accommodative-Paused": 3,
        "Neutral": 2,
        "Tightening-Paused": 1,
        "Tightening-Hiking": 0,
    }
    r = rbi_map.get(rbi, 0)
    if   cpi is None:  c = 0
    elif cpi < 4.5:    c = 4
    elif cpi < 5.7:    c = 3
    elif cpi < 7:      c = 2
    elif cpi < 8.5:    c = 1
    else:              c = 0
    if   pmi is None:  p = 0
    elif pmi > 55:     p = 4
    elif pmi > 52:     p = 3
    elif pmi > 50:     p = 2
    elif pmi > 48:     p = 1
    else:              p = 0
    y = 2 if yield_inverted == "Yes" else 0
    return max(0, r + c + p - y)

def score_global(us10y, us10y_dir, dxy, gvix, inr_dir):
    if us10y is None:
        u = 0
    elif us10y_dir == "Falling" and us10y < 4: u = 3
    elif us10y_dir == "Falling" and us10y >= 4: u = 2
    elif us10y_dir == "Stable":                 u = 2
    elif us10y_dir == "Rising"  and us10y < 5:  u = 1
    else:                                        u = 0
    if   dxy is None: d = 0
    elif dxy < 82:    d = 3
    elif dxy < 92:    d = 3
    elif dxy < 100:   d = 2
    elif dxy < 106:   d = 1
    else:             d = 0
    if   gvix is None: g = 0
    elif gvix < 15:    g = 3
    elif gvix < 20:    g = 2
    elif gvix < 25:    g = 2
    elif gvix < 30:    g = 1
    else:              g = 0
    if   inr_dir == "Strengthening": i = 3
    elif inr_dir == "Stable":        i = 2
    elif inr_dir == "Weakening":     i = 1
    else:                            i = 0
    return min(12, u + d + g + i)

def score_crude(brent):
    if brent is None: return 0
    if brent < 50:  return 12
    if brent < 60:  return 10
    if brent < 70:  return 8
    if brent < 80:  return 6
    if brent < 90:  return 4
    if brent < 100: return 2
    return 0

# ============================================================
# STEP 3B: COMPUTE ALL 8 COMPONENT SCORES
# ============================================================

print("\n--- COMPONENT SCORES ---")

s_val   = score_valuation(manual.get("nifty_pe"))
s_trend = score_trend(pct_vs_dma, dma_direction)
s_brd   = score_breadth(manual.get("breadth_pct_above_200dma"))
s_vol   = score_volatility(live.get("India VIX"))
s_flow  = score_flows(manual.get("fii_30day_net_cr"), manual.get("dii_30day_net_cr"))
s_mac   = score_macro(manual.get("rbi_stance"), manual.get("cpi_pct"),
                      manual.get("pmi_manufacturing"), manual.get("yield_curve_inverted"))
s_glob  = score_global(us10y_today, us10y_dir,
                       glob.get("DXY"), glob.get("Global VIX"), inr_dir)
s_crd   = score_crude(crude_today)

print(f"1. Valuation:  {s_val:>5} / 15")
print(f"2. Trend:      {s_trend:>5} / 15")
print(f"3. Breadth:    {s_brd:>5} / 12")
print(f"4. Volatility: {s_vol:>5} / 10")
print(f"5. Flows:      {s_flow:>5} / 12")
print(f"6. Macro:      {s_mac:>5} / 12")
print(f"7. Global:     {s_glob:>5} / 12")
print(f"8. Crude:      {s_crd:>5} / 12")

raw_score = s_val + s_trend + s_brd + s_vol + s_flow + s_mac + s_glob + s_crd
print(f"\nRAW SCORE: {raw_score} / 100")

# ============================================================
# STEP 4: SAFETY OVERRIDES
# ============================================================

fii_val = manual.get("fii_30day_net_cr") or 0
red_flag = (s_trend <= 3 and s_vol <= 2 and (s_flow <= 3 or fii_val < -15000))

pe_val = manual.get("nifty_pe") or 0
pe_bubble = pe_val > 26

print(f"\nRed Flag:   {'YES - equity capped 25%' if red_flag else 'NO'}")
print(f"PE Bubble:  {'YES - equity capped 70%' if pe_bubble else 'NO'}")

smoothed = raw_score
if   smoothed <= 20: condition = "TERRIBLE"
elif smoothed <= 30: condition = "WEAK"
elif smoothed <= 40: condition = "BELOW AVG"
elif smoothed <= 52: condition = "NEUTRAL"
elif smoothed <= 62: condition = "GOOD"
else:                condition = "EXCELLENT"

print(f"\nMarket Condition: {condition}")

# ============================================================
# STEP 5: ALLOCATION
# ============================================================

if   smoothed <= 20: base_eq = 10
elif smoothed <= 30: base_eq = 25
elif smoothed <= 40: base_eq = 40
elif smoothed <= 52: base_eq = 55
elif smoothed <= 62: base_eq = 70
else:                base_eq = 85

equity_pct = base_eq
if red_flag:
    equity_pct = min(25, equity_pct)
if pe_bubble:
    equity_pct = min(70, equity_pct)

if   smoothed <= 20: eng_b_of_eq = 30
elif smoothed <= 30: eng_b_of_eq = 35
elif smoothed <= 40: eng_b_of_eq = 40
elif smoothed <= 52: eng_b_of_eq = 45
else:                eng_b_of_eq = 50

engine_b_pct = round(equity_pct * eng_b_of_eq / 100)
engine_c_pct = equity_pct - engine_b_pct

if red_flag:
    gold_pct = 25
elif smoothed <= 20: gold_pct = 25
elif smoothed <= 30: gold_pct = 25
elif smoothed <= 40: gold_pct = 20
elif smoothed <= 52: gold_pct = 15
elif smoothed <= 62: gold_pct = 10
else:                gold_pct = 5

debt_pct = 100 - equity_pct - gold_pct

rbi_val = manual.get("rbi_stance", "")
yield_inv = manual.get("yield_curve_inverted", "No")
if rbi_val in ("Accommodative-Cutting", "Accommodative-Paused") and yield_inv == "No":
    duration = "LONG DURATION"
elif rbi_val == "Neutral":
    duration = "MEDIUM DURATION"
else:
    duration = "SHORT/CASH"

gvix_val  = glob.get("Global VIX") or 0
brent_val = crude_today or 0
if gvix_val > 25 or brent_val > 100 or inr_dir == "Weakening":
    gold_signal = "ACCUMULATE"
elif gvix_val < 15 and brent_val < 60:
    gold_signal = "TRIM"
else:
    gold_signal = "HOLD"

print("\n--- ALLOCATION ---")
print(f"Equity: {equity_pct}%  (Engine B: {engine_b_pct}% | Engine C: {engine_c_pct}%)")
print(f"Debt:   {debt_pct}%  ({duration})")
print(f"Gold:   {gold_pct}%  ({gold_signal})")
print(f"Total:  {equity_pct + debt_pct + gold_pct}%")

# ============================================================
# STEP 6: WRITE OUTPUT (latest score)
# ============================================================

out_row = {
    "timestamp":               datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "raw_score":               raw_score,
    "smoothed_score":          smoothed,
    "market_condition":        condition,
    "score_valuation":         s_val,
    "score_trend":             s_trend,
    "score_breadth":           s_brd,
    "score_volatility":        s_vol,
    "score_flows":             s_flow,
    "score_macro":             s_mac,
    "score_global":            s_glob,
    "score_crude":             s_crd,
    "red_flag":                "YES" if red_flag else "NO",
    "pe_bubble":               "YES" if pe_bubble else "NO",
    "equity_pct":              equity_pct,
    "engine_b_pct":            engine_b_pct,
    "engine_c_pct":            engine_c_pct,
    "debt_pct":                debt_pct,
    "gold_pct":                gold_pct,
    "duration_signal":         duration,
    "gold_signal":             gold_signal,
    "nifty_close":             nifty_close,
    "nifty_200dma":            round(nifty_200dma, 2) if nifty_200dma else "",
    "pct_vs_dma":              pct_vs_dma,
    "dma_direction":           dma_direction,
}

Path("data").mkdir(exist_ok=True)
with open("data/engine_a_score.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(out_row.keys()))
    writer.writeheader()
    writer.writerow(out_row)

print("\nWritten to data/engine_a_score.csv")

# ============================================================
# STEP 7: APPEND TO SCORE HISTORY (NEW in v1.1)
# ============================================================

HISTORY_FILE = "data/score_history.csv"
history_path = Path(HISTORY_FILE)
write_header = not history_path.exists()

history_row = {
    "date": datetime.now().strftime("%Y-%m-%d"),
    "score": raw_score,
    "condition": condition,
    "equity_pct": equity_pct,
    "debt_pct": debt_pct,
    "gold_pct": gold_pct,
    "nifty": nifty_close or "",
    "vix": live.get("India VIX", ""),
    "red_flag": "YES" if red_flag else "NO",
}

with open(HISTORY_FILE, "a", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(history_row.keys()))
    if write_header:
        writer.writeheader()
    writer.writerow(history_row)

print(f"Score appended to {HISTORY_FILE}")

print("\n" + "=" * 50)
print(f"ENGINE A SCORE: {raw_score} / 100 — {condition}")
print("=" * 50)
