"""
test_angel.py - Engine A Live Data Fetcher v11
NEW in v11: Fetches live prices for watchlist stocks (engine_b_watchlist + engine_c_watchlist).
v10: Updates peak prices in engine_b_stocks.json for trailing stop tracking.
v9: Fetches LTP even on weekends/holidays (last traded price).
Only skips historical store on non-market days.
"""
import os
import csv
import sys
import json
import time
import pyotp
import yfinance as yf
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from SmartApi import SmartConnect

print("=" * 50)
print("ENGINE A - LIVE DATA FETCHER v11")
print("=" * 50)

# ============================================================
# TRADING DAY CHECK
# ============================================================
NSE_HOLIDAYS_2026 = {
    "2026-01-26", "2026-02-17", "2026-03-03", "2026-03-20",
    "2026-04-03", "2026-04-14", "2026-05-01", "2026-05-27",
    "2026-08-15", "2026-08-26", "2026-10-02", "2026-10-21",
    "2026-11-04", "2026-12-25",
}

today = datetime.now()
today_str = today.strftime("%Y-%m-%d")
weekday = today.weekday()

print(f"Today: {today_str} ({today.strftime('%A')})")

is_market_day = True

if weekday == 5:
    print("Saturday - market closed. Will fetch LTP only (no history).")
    is_market_day = False

if today_str in NSE_HOLIDAYS_2026 and weekday != 6:
    print("NSE Holiday - will fetch LTP only (no history).")
    is_market_day = False

print(f"Market day: {is_market_day} - proceeding with fetch")

# ============================================================
# INDIAN SYMBOLS (Angel One - indices)
# ============================================================
SYMBOLS = {
    "Nifty 50":         ("NSE", "Nifty 50",         "99926000"),
    "India VIX":        ("NSE", "India VIX",        "99926017"),
    "Nifty 500":        ("NSE", "Nifty 500",        "99926004"),
    "Nifty Midcap 100": ("NSE", "Nifty Midcap 100", "99926011"),
    "Nifty Midcap 50":  ("NSE", "Nifty Midcap 50",  "99926014"),
}

# ============================================================
# GLOBAL SYMBOLS (yfinance)
# ============================================================
GLOBAL_SYMBOLS = {
    "US 10Y Yield": "^TNX",
    "DXY":          "DX-Y.NYB",
    "Global VIX":   "^VIX",
    "INR/USD":      "INR=X",
    "Brent Crude":  "BZ=F",
}

# ============================================================
# HISTORY CONFIG
# ============================================================
HISTORY_FILE = "data/historical_prices.csv"
BOOTSTRAP_DAYS = 300

# ============================================================
# ENGINE B STOCK LIST
# ============================================================
ENGINE_B_FILE = "data/engine_b_stocks.json"

def load_engine_b_stocks():
    if not Path(ENGINE_B_FILE).exists():
        print("No engine_b_stocks.json found - skipping stock fetch")
        return None
    with open(ENGINE_B_FILE, "r") as f:
        return json.load(f)

def save_engine_b_stocks(data):
    with open(ENGINE_B_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def resolve_tokens(stock_data):
    cache = stock_data.get("_token_cache", {})
    # Collect tickers from positions AND watchlists
    all_stocks = (stock_data.get("engine_b", []) +
                  stock_data.get("engine_c", []) +
                  stock_data.get("engine_b_watchlist", []) +
                  stock_data.get("engine_c_watchlist", []))
    
    need_tokens = []
    for s in all_stocks:
        ticker = s.get("ticker", "")
        if ticker and ticker not in cache:
            need_tokens.append(ticker)
    
    # Deduplicate
    need_tokens = list(set(need_tokens))
    
    if not need_tokens:
        print("All tokens cached - no master download needed")
        return cache
    
    print(f"Need tokens for: {need_tokens}")
    print("Downloading Angel One instrument master...")
    
    try:
        url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        response = urllib.request.urlopen(url, timeout=60)
        master = json.loads(response.read().decode())
        print(f"Downloaded {len(master)} instruments")
        
        for ticker in need_tokens:
            found = False
            for item in master:
                if (item.get("exch_seg") == "NSE" and 
                    item.get("symbol") == ticker + "-EQ"):
                    cache[ticker] = {
                        "token": item["token"],
                        "symbol": item["symbol"],
                        "name": item.get("name", ""),
                    }
                    print(f"  {ticker}: token={item['token']}")
                    found = True
                    break
            if not found:
                for item in master:
                    if (item.get("exch_seg") == "NSE" and
                        item.get("symbol") == ticker):
                        cache[ticker] = {
                            "token": item["token"],
                            "symbol": item["symbol"],
                            "name": item.get("name", ""),
                        }
                        print(f"  {ticker}: token={item['token']}")
                        found = True
                        break
            if not found:
                print(f"  {ticker}: NOT FOUND in master")
        
        stock_data["_token_cache"] = cache
        stock_data["_last_token_update"] = today_str
        save_engine_b_stocks(stock_data)
        print("Token cache updated and saved")
        
    except Exception as e:
        print(f"Master download failed: {e}")
    
    return cache

# ============================================================
# LOAD SECRETS
# ============================================================
client_id   = os.environ.get("ANGEL_CLIENT_ID")
api_key     = os.environ.get("ANGEL_API_KEY")
totp_secret = os.environ.get("ANGEL_TOTP_SECRET")
mpin        = os.environ.get("ANGEL_MPIN")

if not all([client_id, api_key, totp_secret, mpin]):
    print("Missing secrets")
    exit(1)
print("Secrets loaded")

# ============================================================
# LOGIN TO ANGEL ONE
# ============================================================
try:
    totp_code = pyotp.TOTP(totp_secret).now()
    smart = SmartConnect(api_key=api_key)
    session = smart.generateSession(client_id, mpin, totp_code)
    if not session.get("status"):
        print(f"Login failed: {session.get('message')}")
        exit(1)
    print("Angel One login SUCCESS")
except Exception as e:
    print(f"Login exception: {e}")
    exit(1)

# ============================================================
# PART 1: LIVE LTP FETCH (indices)
# ============================================================

def fetch_ltp(name, exchange, tradingsymbol, token):
    try:
        data = smart.ltpData(exchange=exchange,
                             tradingsymbol=tradingsymbol,
                             symboltoken=token)
        if data.get("status"):
            price = data["data"]["ltp"]
            print(f"  {name}: Rs.{price:,.2f}")
            return price, "OK"
        return None, "ERROR"
    except Exception as e:
        return None, "EXCEPTION"

def fetch_yfinance_ltp(name, ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="2d")
        if hist.empty:
            return None, "NO_DATA"
        price = float(hist["Close"].iloc[-1])
        print(f"  {name}: {price:,.2f}")
        return price, "OK"
    except Exception as e:
        return None, "EXCEPTION"

print("\n--- LIVE LTP FETCH (Indices) ---")
indian_results = []
global_results = []
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

for name, (exchange, tradingsymbol, token) in SYMBOLS.items():
    price, status = fetch_ltp(name, exchange, tradingsymbol, token)
    indian_results.append({"timestamp": timestamp, "symbol": name,
                           "price": price if price else "",
                           "status": status, "source": "AngelOne"})

for name, ticker in GLOBAL_SYMBOLS.items():
    price, status = fetch_yfinance_ltp(name, ticker)
    global_results.append({"timestamp": timestamp, "symbol": name,
                           "price": price if price else "",
                           "status": status, "source": "yfinance",
                           "ticker": ticker})

Path("data").mkdir(exist_ok=True)

with open("data/live_prices.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["timestamp", "symbol", "price", "status", "source"])
    writer.writeheader()
    writer.writerows(indian_results)

with open("data/global_prices.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["timestamp", "symbol", "price", "status", "source", "ticker"])
    writer.writeheader()
    writer.writerows(global_results)

print("Live LTP fetch complete")

# ============================================================
# PART 2: ENGINE B/C STOCK PRICES (positions + watchlists)
# ============================================================

print("\n--- ENGINE B/C STOCK PRICES ---")

stock_data = load_engine_b_stocks()

if stock_data:
    token_cache = resolve_tokens(stock_data)
    
    # Collect ALL unique tickers: positions + watchlists
    all_tickers_seen = set()
    all_stocks_to_fetch = []
    
    # Positions first (engine_b + engine_c)
    for s in stock_data.get("engine_b", []) + stock_data.get("engine_c", []):
        ticker = s.get("ticker", "")
        if ticker and ticker not in all_tickers_seen:
            all_tickers_seen.add(ticker)
            all_stocks_to_fetch.append(s)
    
    # Watchlist stocks (only if not already fetching via positions)
    for s in stock_data.get("engine_b_watchlist", []) + stock_data.get("engine_c_watchlist", []):
        ticker = s.get("ticker", "")
        action = s.get("action", "")
        if ticker and ticker not in all_tickers_seen and action != "AVOID":
            all_tickers_seen.add(ticker)
            all_stocks_to_fetch.append(s)
    
    print(f"Fetching prices for {len(all_stocks_to_fetch)} unique stocks "
          f"(positions + watchlists)")
    
    stock_results = []
    
    for s in all_stocks_to_fetch:
        ticker = s.get("ticker", "")
        stock_name = s.get("stock", ticker)
        cached = token_cache.get(ticker, {})
        token = cached.get("token")
        symbol = cached.get("symbol", ticker)
        
        if not token:
            print(f"  {stock_name}: no token - skipping")
            stock_results.append({
                "timestamp": timestamp, "stock": stock_name,
                "ticker": ticker, "price": "", "status": "NO_TOKEN",
                "entry": s.get("entry", ""), "qty": s.get("qty", ""),
            })
            continue
        
        price, status = fetch_ltp(stock_name, "NSE", symbol, token)
        stock_results.append({
            "timestamp": timestamp, "stock": stock_name,
            "ticker": ticker, "price": price if price else "",
            "status": status, "entry": s.get("entry", ""),
            "qty": s.get("qty", ""),
        })
        time.sleep(0.3)
    
    with open("data/engine_b_prices.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "timestamp", "stock", "ticker", "price", "status", "entry", "qty"
        ])
        writer.writeheader()
        writer.writerows(stock_results)
    
    print(f"Stock prices saved: {len(stock_results)} stocks")

    # ----------------------------------------------------------
    # PEAK PRICE TRACKER (v10)
    # Updates peak in engine_b_stocks.json for trailing stop calc
    # ----------------------------------------------------------
    print("\n--- PEAK PRICE TRACKER ---")
    peaks_updated = 0

    # Build a price lookup from fetched results
    price_lookup = {}
    for r in stock_results:
        if r["price"] != "" and r["price"] is not None:
            try:
                price_lookup[r["ticker"]] = float(r["price"])
            except:
                pass

    # Update peaks for engine_b positions
    for s in stock_data.get("engine_b", []):
        ticker = s.get("ticker", "")
        current = price_lookup.get(ticker)
        if current is None:
            continue
        old_peak = float(s.get("peak", s.get("entry", 0)))
        if current > old_peak:
            s["peak"] = round(current, 2)
            trail_stop = round(current * 0.93, 2)
            print(f"  {s.get('stock', ticker)}: peak {old_peak} -> {current} (trail stop: {trail_stop})")
            peaks_updated += 1
        else:
            trail_stop = round(old_peak * 0.93, 2)
            print(f"  {s.get('stock', ticker)}: peak {old_peak} unchanged (trail stop: {trail_stop})")

    # Update peaks for engine_c positions (same logic)
    for s in stock_data.get("engine_c", []):
        ticker = s.get("ticker", "")
        current = price_lookup.get(ticker)
        if current is None:
            continue
        old_peak = float(s.get("peak", s.get("entry", 0)))
        if current > old_peak:
            s["peak"] = round(current, 2)
            print(f"  {s.get('stock', ticker)}: peak {old_peak} -> {current}")
            peaks_updated += 1

    if peaks_updated > 0:
        save_engine_b_stocks(stock_data)
        print(f"Peaks updated: {peaks_updated} stocks")
    else:
        print("No peaks updated (all at or below stored peak)")

else:
    print("No Engine B stocks configured")

# ============================================================
# PART 2.5: STOCK ANALYSIS (Volume, 52W High/Low, 60D/90D Trends)
# Fetches 365 days of candle data per stock for analysis
# ============================================================

ANALYSIS_FILE = "data/stock_analysis.csv"

if stock_data and token_cache:
    print("\n--- STOCK ANALYSIS (Volume, 52W, Trends) ---")

    # Collect all unique tickers from positions + watchlists
    analysis_tickers = set()
    ticker_to_name = {}
    for s in (stock_data.get("engine_b", []) + stock_data.get("engine_c", []) +
              stock_data.get("engine_b_watchlist", []) + stock_data.get("engine_c_watchlist", [])):
        ticker = s.get("ticker", "")
        if ticker and s.get("action", "") != "AVOID":
            analysis_tickers.add(ticker)
            ticker_to_name[ticker] = s.get("stock", ticker)

    print(f"Analyzing {len(analysis_tickers)} unique stocks...")

    from_date_analysis = today - timedelta(days=365)
    analysis_results = []

    for ticker in sorted(analysis_tickers):
        cached = token_cache.get(ticker, {})
        a_token = cached.get("token")
        a_symbol = cached.get("symbol", ticker)

        if not a_token:
            print(f"  {ticker}: no token - skipping analysis")
            continue

        try:
            params = {
                "exchange": "NSE",
                "symboltoken": a_token,
                "interval": "ONE_DAY",
                "fromdate": from_date_analysis.strftime("%Y-%m-%d 09:15"),
                "todate": today.strftime("%Y-%m-%d 15:30"),
            }
            resp = smart.getCandleData(params)

            if not resp or not resp.get("status"):
                print(f"  {ticker}: candle API failed")
                continue

            candles = resp.get("data") or []
            if len(candles) < 20:
                print(f"  {ticker}: only {len(candles)} candles - insufficient")
                continue

            # Extract closes and volumes
            closes = [float(c[4]) for c in candles]
            volumes = [float(c[5]) for c in candles]

            current_price = closes[-1]

            # Volume ratio (today vs 20-day average)
            vol_20d_avg = sum(volumes[-20:]) / 20
            vol_today = volumes[-1]
            vol_ratio = round(vol_today / vol_20d_avg, 2) if vol_20d_avg > 0 else 0

            # 52W high/low
            high_52w = max(closes)
            low_52w = min(closes)
            range_52w = high_52w - low_52w
            pct_52w = round((current_price - low_52w) / range_52w * 100, 1) if range_52w > 0 else 50

            # 60-day change
            if len(closes) >= 60:
                close_60d = closes[-60]
                change_60d = round((current_price - close_60d) / close_60d * 100, 2)
            else:
                change_60d = 0

            # 90-day change
            if len(closes) >= 90:
                close_90d = closes[-90]
                change_90d = round((current_price - close_90d) / close_90d * 100, 2)
            else:
                change_90d = 0

            analysis_results.append({
                "ticker": ticker,
                "stock": ticker_to_name.get(ticker, ticker),
                "vol_ratio": vol_ratio,
                "high_52w": round(high_52w, 2),
                "low_52w": round(low_52w, 2),
                "pct_52w": pct_52w,
                "change_60d": change_60d,
                "change_90d": change_90d,
                "candles": len(candles),
            })

            print(f"  {ticker}: Vol {vol_ratio}x | 52W {pct_52w}% | 60D {change_60d:+.1f}% | 90D {change_90d:+.1f}%")
            time.sleep(0.5)

        except Exception as e:
            print(f"  {ticker}: analysis error - {e}")

    # Save analysis
    if analysis_results:
        with open(ANALYSIS_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "ticker", "stock", "vol_ratio", "high_52w", "low_52w",
                "pct_52w", "change_60d", "change_90d", "candles"
            ])
            writer.writeheader()
            writer.writerows(analysis_results)
        print(f"Analysis saved: {len(analysis_results)} stocks")
    else:
        print("No analysis data to save")

else:
    if not stock_data:
        pass  # Already printed above

# ============================================================
# PART 3: HISTORICAL PRICE STORE (skip on non-market days)
# ============================================================

if not is_market_day:
    print("\nSkipping historical store (not a market day)")
    print("=" * 50)
    print("FETCHER RUN COMPLETE")
    print("=" * 50)
    sys.exit(0)

print("\n--- HISTORICAL PRICE STORE ---")

existing_history = []
existing_keys = set()
latest_date_per_symbol = {}

if Path(HISTORY_FILE).exists():
    with open(HISTORY_FILE, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing_history.append(row)
            existing_keys.add((row["symbol"], row["date"]))
            cur = latest_date_per_symbol.get(row["symbol"])
            if cur is None or row["date"] > cur:
                latest_date_per_symbol[row["symbol"]] = row["date"]
    print(f"Existing history: {len(existing_history)} rows, {len(latest_date_per_symbol)} symbols")
else:
    print("No existing history - will bootstrap 300 days")

today_date = datetime.now().date()
default_from = today_date - timedelta(days=BOOTSTRAP_DAYS)

def get_fetch_from(symbol_name):
    latest = latest_date_per_symbol.get(symbol_name)
    if latest is None:
        return default_from
    try:
        latest_dt = datetime.strptime(latest, "%Y-%m-%d").date()
        return latest_dt + timedelta(days=1)
    except Exception:
        return default_from

def fetch_angel_history(name, exchange, token, from_date, to_date):
    try:
        params = {
            "exchange": exchange,
            "symboltoken": token,
            "interval": "ONE_DAY",
            "fromdate": from_date.strftime("%Y-%m-%d 09:15"),
            "todate":   to_date.strftime("%Y-%m-%d 15:30"),
        }
        resp = smart.getCandleData(params)
        if not resp or not resp.get("status"):
            print(f"  {name}: API status FAIL")
            return []
        data = resp.get("data") or []
        rows = []
        for candle in data:
            dt_str = str(candle[0])
            date_only = dt_str[:10]
            close_val = float(candle[4])
            rows.append({"date": date_only, "symbol": name,
                         "close": close_val, "source": "AngelOne"})
        print(f"  {name}: {len(rows)} candles")
        return rows
    except Exception as e:
        print(f"  {name}: EXCEPTION - {e}")
        return []

def fetch_yfinance_history(name, ticker, from_date, to_date):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(start=from_date.strftime("%Y-%m-%d"),
                         end=(to_date + timedelta(days=1)).strftime("%Y-%m-%d"))
        if hist.empty:
            print(f"  {name}: no data")
            return []
        rows = []
        for idx, row in hist.iterrows():
            date_only = idx.strftime("%Y-%m-%d")
            close_val = float(row["Close"])
            rows.append({"date": date_only, "symbol": name,
                         "close": close_val, "source": "yfinance"})
        print(f"  {name}: {len(rows)} candles")
        return rows
    except Exception as e:
        print(f"  {name}: EXCEPTION - {e}")
        return []

new_rows = []

print("\nIndian indices history:")
for name, (exchange, tradingsymbol, token) in SYMBOLS.items():
    from_date = get_fetch_from(name)
    if from_date > today_date:
        print(f"  {name}: up to date")
        continue
    rows = fetch_angel_history(name, exchange, token, from_date, today_date)
    new_rows.extend(rows)
    time.sleep(0.4)

print("\nGlobal symbols history:")
for name, ticker in GLOBAL_SYMBOLS.items():
    from_date = get_fetch_from(name)
    if from_date > today_date:
        print(f"  {name}: up to date")
        continue
    rows = fetch_yfinance_history(name, ticker, from_date, today_date)
    new_rows.extend(rows)

merged = list(existing_history)
added = 0
for row in new_rows:
    key = (row["symbol"], row["date"])
    if key not in existing_keys:
        merged.append(row)
        existing_keys.add(key)
        added += 1

merged.sort(key=lambda r: (r["symbol"], r["date"]))

with open(HISTORY_FILE, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["date", "symbol", "close", "source"])
    writer.writeheader()
    writer.writerows(merged)

print(f"\nHistory store: {len(merged)} total rows ({added} new)")
print("=" * 50)
print("FETCHER RUN COMPLETE")
print("=" * 50)
