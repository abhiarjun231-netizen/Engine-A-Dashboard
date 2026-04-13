"""
test_angel.py — Baby step test: Can we talk to Angel One?
Goal: Login + fetch Nifty 50 live price. Nothing else.
"""

import os
import pyotp
from SmartApi import SmartConnect

print("=" * 50)
print("ANGEL ONE CONNECTION TEST")
print("=" * 50)

# Step 1: Read secrets from environment
client_id = os.environ.get("ANGEL_CLIENT_ID")
api_key = os.environ.get("ANGEL_API_KEY")
secret_key = os.environ.get("ANGEL_SECRET_KEY")
totp_secret = os.environ.get("ANGEL_TOTP_SECRET")
mpin = os.environ.get("ANGEL_MPIN")

# Step 2: Verify all secrets are present
if not all([client_id, api_key, secret_key, totp_secret, mpin]):
    print("❌ MISSING SECRETS — check GitHub Secrets")
    print(f"  Client ID present: {bool(client_id)}")
    print(f"  API Key present:   {bool(api_key)}")
    print(f"  Secret Key present:{bool(secret_key)}")
    print(f"  TOTP present:      {bool(totp_secret)}")
    print(f"  MPIN present:      {bool(mpin)}")
    exit(1)

print("✅ All 5 secrets loaded")

# Step 3: Generate current TOTP code
try:
    totp_code = pyotp.TOTP(totp_secret).now()
    print(f"✅ TOTP code generated: {totp_code}")
except Exception as e:
    print(f"❌ TOTP generation failed: {e}")
    exit(1)

# Step 4: Login to Angel One
try:
    smart = SmartConnect(api_key=api_key)
    session = smart.generateSession(client_id, mpin, totp_code)
    if session.get("status"):
        print("✅ Angel One login SUCCESS")
    else:
        print(f"❌ Login failed: {session.get('message')}")
        exit(1)
except Exception as e:
    print(f"❌ Login exception: {e}")
    exit(1)

# Step 5: Fetch Nifty 50 live price
try:
    # Nifty 50 token on NSE is 99926000
    ltp_data = smart.ltpData(
        exchange="NSE",
        tradingsymbol="Nifty 50",
        symboltoken="99926000"
    )
    if ltp_data.get("status"):
        price = ltp_data["data"]["ltp"]
        print(f"🎯 NIFTY 50 LIVE PRICE: ₹{price:,.2f}")
        print("=" * 50)
        print("✅ FULL TEST PASSED — Angel One is working!")
        print("=" * 50)
    else:
        print(f"❌ LTP fetch failed: {ltp_data.get('message')}")
        exit(1)
except Exception as e:
    print(f"❌ LTP fetch exception: {e}")
    exit(1)
