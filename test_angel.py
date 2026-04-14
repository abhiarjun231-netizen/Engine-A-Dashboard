"""
test_angel.py - Engine A Live Data Fetcher v6
NEW in v6: Unified historical price store (data/historical_prices.csv).
- Bootstraps 300 days of daily closes on first run.
- Incremental updates on every run after.
- Single source of truth for 200-DMA, 4-week directions, future indicators.
- Long format: date, symbol, close, source - easy to scale to Engine B/C.
"""
import os
import csv
import time
import pyotp
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path
from SmartApi import SmartConnect

print("=" * 50)
print("ENGINE A - LIVE DATA FETCHER v6")
print("=" * 50)

# ---------- INDIAN SYMBOLS (Angel One) ----------
SYMBOLS = {
    "Nifty 50":         ("NSE", "Nifty 50",         "99926000"),
    "India VIX":        ("NSE", "India VIX",        "99926017"),
    "Nifty 500":        ("NSE", "Nifty 500",        "99926004"),
    "Nifty Midcap 100": ("NSE", "Nifty Midcap 100", "99926011"),
    "Nifty Midcap 50":  ("NSE", "Nifty Midcap 50",  "99926014"),
}

# ---------- GLOBAL SYMBOLS (yfinance) ----------
GLOBAL_SYMBOLS = {
    "US 10Y Yield": "^TNX",
    "DXY":          "DX-Y.NYB",
    "Global VIX":   "^VIX",
    "INR/USD":      "INR=X",
    "Brent Crude":  "BZ=F",
}

# ---------- HISTORY CONFIG ----------
HISTORY_FILE = "data/historical_prices.csv"
BOOTSTRAP_DAYS = 300

# ---------- LOAD SECRETS ----------
client_id   = os.environ.get("ANGEL_CLIENT_ID")
api_key     = os.environ.get("ANGEL_API_KEY")
totp_secret = os.environ.get("ANGEL_TOTP_SECRET")
mpin        = os.environ.get("ANGEL_MPIN")

if not all([client_id, api_key, totp_secret, mpin]):
    print("Missing secrets")
    exit(1)
print("Secrets loaded")

# ---------- LOGIN TO ANGEL ONE ----------
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
# PART 1: LIVE LTP FETCH (unchanged from v5)
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

print("\n--- LIVE LTP FETCH ---")
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
# PART 2: HISTORICAL PRICE STORE (NEW in v6)
# ============================================================

print("\n--- HISTORICAL PRICE STORE ---")

# Step 1: Read existing history (if any)
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

# Step 2: Determine fetch start date per symbol
today = datetime.now().date()
default_from = today - timedelta(days=BOOTSTRAP_DAYS)

def get_fetch_from(symbol_name):
    latest = latest_date_per_symbol.get(symbol_name)
    if latest is None:
        return default_from
    try:
        latest_dt = datetime.strptime(latest, "%Y-%m-%d").date()
        return latest_dt + timedelta(days=1)
    except Exception:
        return default_from

# Step 3: Angel One historical fetcher
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

# Step 4: yfinance historical fetcher
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

# Step 5: Fetch history for all symbols
new_rows = []

print("\nIndian indices history:")
for name, (exchange, tradingsymbol, token) in SYMBOLS.items():
    from_date = get_fetch_from(name)
    if from_date > today:
        print(f"  {name}: up to date")
        continue
    rows = fetch_angel_history(name, exchange, token, from_date, today)
    new_rows.extend(rows)
    time.sleep(0.4)  # respect Angel One rate limit (3 req/sec)

print("\nGlobal symbols history:")
for name, ticker in GLOBAL_SYMBOLS.items():
    from_date = get_fetch_from(name)
    if from_date > today:
        print(f"  {name}: up to date")
        continue
    rows = fetch_yfinance_history(name, ticker, from_date, today)
    new_rows.extend(rows)

# Step 6: Merge with existing, dedupe, sort, save
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
