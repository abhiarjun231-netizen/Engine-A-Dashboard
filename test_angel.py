"""
test_angel.py — Engine A Live Data Fetcher v5
Fetches Indian indices (Angel One) + Global data (yfinance).
"""

import os
import csv
import pyotp
import yfinance as yf
from datetime import datetime
from pathlib import Path
from SmartApi import SmartConnect

print("=" * 50)
print("ENGINE A — LIVE DATA FETCHER v5")
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
# Format: "display name": "yahoo_ticker"
GLOBAL_SYMBOLS = {
    "US 10Y Yield":  "^TNX",
    "DXY":           "DX-Y.NYB",
    "Global VIX":    "^VIX",
    "INR/USD":       "INR=X",
    "Brent Crude":   "BZ=F",
}

# ---------- LOAD SECRETS ----------
client_id = os.environ.get("ANGEL_CLIENT_ID")
api_key = os.environ.get("ANGEL_API_KEY")
totp_secret = os.environ.get("ANGEL_TOTP_SECRET")
mpin = os.environ.get("ANGEL_MPIN")

if not all([client_id, api_key, totp_secret, mpin]):
    print("❌ Missing secrets")
    exit(1)
print("✅ Secrets loaded")

# ---------- LOGIN TO ANGEL ONE ----------
try:
    totp_code = pyotp.TOTP(totp_secret).now()
    smart = SmartConnect(api_key=api_key)
    session = smart.generateSession(client_id, mpin, totp_code)
    if not session.get("status"):
        print(f"❌ Login failed: {session.get('message')}")
        exit(1)
    print("✅ Angel One login SUCCESS")
except Exception as e:
    print(f"❌ Login exception: {e}")
    exit(1)

# ---------- FETCH HELPER (Angel One) ----------
def fetch_ltp(name, exchange, tradingsymbol, token):
    try:
        data = smart.ltpData(
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            symboltoken=token
        )
        if data.get("status"):
            price = data["data"]["ltp"]
            print(f"  ✅ {name}: ₹{price:,.2f}")
            return price, "OK"
        else:
            print(f"  ❌ {name}: {data.get('message')}")
            return None, "ERROR"
    except Exception as e:
        print(f"  ❌ {name}: exception {e}")
        return None, "EXCEPTION"

# ---------- FETCH HELPER (yfinance) ----------
def fetch_yfinance(name, ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="2d")
        if hist.empty:
            print(f"  ❌ {name}: no data")
            return None, "NO_DATA"
        price = float(hist["Close"].iloc[-1])
        print(f"  ✅ {name}: {price:,.2f}")
        return price, "OK"
    except Exception as e:
        print(f"  ❌ {name}: exception {e}")
        return None, "EXCEPTION"

# ---------- FETCH INDIAN SYMBOLS ----------
print(f"\n--- Fetching {len(SYMBOLS)} Indian symbols ---")
indian_results = []
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

for name, (exchange, tradingsymbol, token) in SYMBOLS.items():
    price, status = fetch_ltp(name, exchange, tradingsymbol, token)
    indian_results.append({
        "timestamp": timestamp,
        "symbol": name,
        "price": price if price else "",
        "status": status,
        "source": "AngelOne",
    })

# ---------- FETCH GLOBAL SYMBOLS ----------
print(f"\n--- Fetching {len(GLOBAL_SYMBOLS)} Global symbols ---")
global_results = []

for name, ticker in GLOBAL_SYMBOLS.items():
    price, status = fetch_yfinance(name, ticker)
    global_results.append({
        "timestamp": timestamp,
        "symbol": name,
        "price": price if price else "",
        "status": status,
        "source": "yfinance",
        "ticker": ticker,
    })

# ---------- SAVE INDIAN CSV ----------
Path("data").mkdir(exist_ok=True)
indian_csv = "data/live_prices.csv"
with open(indian_csv, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["timestamp", "symbol", "price", "status", "source"])
    writer.writeheader()
    writer.writerows(indian_results)

# ---------- SAVE GLOBAL CSV ----------
global_csv = "data/global_prices.csv"
with open(global_csv, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["timestamp", "symbol", "price", "status", "source", "ticker"])
    writer.writeheader()
    writer.writerows(global_results)

# ---------- SUMMARY ----------
indian_ok = sum(1 for r in indian_results if r["status"] == "OK")
global_ok = sum(1 for r in global_results if r["status"] == "OK")

print(f"\n✅ Indian: {indian_ok}/{len(indian_results)} → {indian_csv}")
print(f"✅ Global: {global_ok}/{len(global_results)} → {global_csv}")
print("=" * 50)
print("✅ FETCHER RUN COMPLETE")
print("=" * 50)
