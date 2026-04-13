"""
test_angel.py — Engine A Live Data Fetcher v2
Uses Angel One searchScrip() to auto-resolve symbol tokens.
Adding a new data point = add one line to SYMBOLS dict.
"""

import os
import csv
import pyotp
from datetime import datetime
from pathlib import Path
from SmartApi import SmartConnect

print("=" * 50)
print("ENGINE A — LIVE DATA FETCHER v2")
print("=" * 50)

# ---------- SYMBOLS TO FETCH ----------
# Format: "display name": (exchange, search_query)
# search_query is what Angel One's searchScrip will match
SYMBOLS = {
    "Nifty 50":   ("NSE", "Nifty 50"),
    "India VIX":  ("NSE", "India VIX"),
}

# Hardcoded fallbacks for symbols where searchScrip is unreliable
# (Angel One's search API sometimes returns derivatives instead of spot index)
KNOWN_TOKENS = {
    "Nifty 50": "99926000",  # Verified working
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

# ---------- TOKEN RESOLVER ----------
def resolve_token(name, exchange, search_query):
    """Find the correct symboltoken for a given name."""
    # Use hardcoded token if we have one
    if name in KNOWN_TOKENS:
        print(f"  🔑 {name}: using known token {KNOWN_TOKENS[name]}")
        return KNOWN_TOKENS[name]
    # Otherwise search Angel One
    try:
        result = smart.searchScrip(exchange=exchange, searchtext=search_query)
        if result.get("status") and result.get("data"):
            matches = result["data"]
            print(f"  🔎 {name}: found {len(matches)} match(es)")
            for m in matches[:5]:
                print(f"      → {m.get('tradingsymbol')} | token={m.get('symboltoken')}")
            # Return first match's token
            return matches[0].get("symboltoken")
        else:
            print(f"  ❌ {name}: searchScrip returned nothing")
            return None
    except Exception as e:
        print(f"  ❌ {name}: searchScrip exception {e}")
        return None

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
print("\n--- Resolving tokens ---")
results = []
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

for name, (exchange, search_query) in SYMBOLS.items():
    token = resolve_token(name, exchange, search_query)
    if token:
        price, status = fetch_ltp(name, exchange, search_query, token)
    else:
        price, status = None, "NO_TOKEN"
    results.append({
        "timestamp": timestamp,
        "symbol": name,
        "price": price if price else "",
        "status": status,
        "token_used": token if token else ""
    })

# ---------- SAVE TO CSV ----------
Path("data").mkdir(exist_ok=True)
csv_path = "data/live_prices.csv"

with open(csv_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["timestamp", "symbol", "price", "status", "token_used"])
    writer.writeheader()
    writer.writerows(results)

print(f"\n✅ Saved {len(results)} rows to {csv_path}")
print("=" * 50)
print("✅ FETCHER RUN COMPLETE")
print("=" * 50)
