"""
test_angel.py — Engine A Live Data Fetcher v3
Uses hardcoded symbol tokens for reliability.
Adding a new data point = add one line to KNOWN_TOKENS + SYMBOLS.
"""

import os
import csv
import pyotp
from datetime import datetime
from pathlib import Path
from SmartApi import SmartConnect

print("=" * 50)
print("ENGINE A — LIVE DATA FETCHER v3")
print("=" * 50)

# ---------- SYMBOLS TO FETCH ----------
# Format: "display name": (exchange, tradingsymbol, symboltoken)
SYMBOLS = {
    "Nifty 50":   ("NSE", "Nifty 50",  "99926000"),
    "India VIX":  ("NSE", "India VIX", "99919000"),
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

# ---------- LOGIN ----------
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

# ---------- FETCH HELPER ----------
def fetch_ltp(name, exchange, tradingsymbol, token):
    """Fetch last traded price for one symbol."""
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

# ---------- FETCH ALL SYMBOLS ----------
print("\n--- Fetching data ---")
results = []
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

for name, (exchange, tradingsymbol, token) in SYMBOLS.items():
    price, status = fetch_ltp(name, exchange, tradingsymbol, token)
    results.append({
        "timestamp": timestamp,
        "symbol": name,
        "price": price if price else "",
        "status": status,
        "token": token
    })

# ---------- SAVE TO CSV ----------
Path("data").mkdir(exist_ok=True)
csv_path = "data/live_prices.csv"

with open(csv_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["timestamp", "symbol", "price", "status", "token"])
    writer.writeheader()
    writer.writerows(results)

print(f"\n✅ Saved {len(results)} rows to {csv_path}")
print("=" * 50)
print("✅ FETCHER RUN COMPLETE")
print("=" * 50)
