import streamlit as st
import yfinance as yf
from nsepython import nse_get_index_quote
from datetime import datetime

st.set_page_config(page_title="Engine A Dashboard", layout="wide")
st.title("📊 Engine A — Market Strength Dashboard")
st.caption(f"Last refresh: {datetime.now().strftime('%d %b %Y, %H:%M:%S')}")

@st.cache_data(ttl=300)
def get_nse_nifty():
    try:
        d = nse_get_index_quote("NIFTY 50")
        return {
            "price": float(d.get("last", 0)),
            "pe": float(d.get("pe", 0)),
            "advances": int(d.get("advances", 0)),
            "declines": int(d.get("declines", 0)),
        }
    except Exception as e:
        return {"error": str(e)}

@st.cache_data(ttl=300)
def get_india_vix():
    try:
        d = nse_get_index_quote("INDIA VIX")
        return float(d.get("last", 0))
    except:
        return None

@st.cache_data(ttl=600)
def get_yf(ticker):
    try:
        h = yf.Ticker(ticker).history(period="1d")
        return float(h["Close"].iloc[-1]) if not h.empty else None
    except:
        return None

@st.cache_data(ttl=3600)
def get_dma():
    try:
        h = yf.download("^NSEI", period="300d", progress=False)
        dma = h["Close"].rolling(200).mean()
        return float(dma.iloc[-1]), float(dma.iloc[-6])
    except:
        return None, None

nifty = get_nse_nifty()
vix = get_india_vix()
us10y = get_yf("^TNX")
dxy = get_yf("DX-Y.NYB")
gvix = get_yf("^VIX")
inr = get_yf("INR=X")
brent = get_yf("BZ=F")
dma_now, dma_prev = get_dma()

st.header("🟢 Live Auto-Fetched Data")

if "error" in nifty:
    st.warning(f"NSE direct failed, using fallback. ({nifty['error'][:50]})")
    nifty_price = get_yf("^NSEI")
    nifty_pe = None
else:
    nifty_price = nifty["price"]
    nifty_pe = nifty["pe"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Nifty 50", f"{nifty_price:,.2f}" if nifty_price else "N/A")
c2.metric("Nifty PE", f"{nifty_pe:.2f}" if nifty_pe else "Manual")
c3.metric("India VIX", f"{vix:.2f}" if vix else "N/A")
c4.metric("200 DMA", f"{dma_now:,.2f}" if dma_now else "N/A")

c5, c6, c7, c8 = st.columns(4)
c5.metric("US 10Y", f"{us10y:.2f}%" if us10y else "N/A")
c6.metric("DXY", f"{dxy:.2f}" if dxy else "N/A")
c7.metric("Global VIX", f"{gvix:.2f}" if gvix else "N/A")
c8.metric("INR/USD", f"{inr:.2f}" if inr else "N/A")

c9, c10, c11, c12 = st.columns(4)
c9.metric("Brent", f"${brent:.2f}" if brent else "N/A")
if nifty_price and dma_now:
    pct = (nifty_price - dma_now) / dma_now * 100
    c10.metric("% vs 200DMA", f"{pct:+.2f}%")
if dma_now and dma_prev:
    c11.metric("DMA Direction", "Rising ↑" if dma_now > dma_prev else "Falling ↓")
if "error" not in nifty:
    breadth = nifty["advances"] / max(nifty["advances"] + nifty["declines"], 1) * 100
    c12.metric("Nifty50 A/D", f"{breadth:.0f}%")

st.header("✍️ Manual Inputs")
m1, m2, m3 = st.columns(3)
rbi = m1.selectbox("RBI Stance", ["Accommodative-Cutting", "Accommodative-Paused", "Neutral", "Tightening-Paused", "Tightening-Hiking"])
cpi = m2.number_input("CPI %", value=5.0, step=0.1)
pmi = m3.number_input("PMI", value=55.0, step=0.5)

st.info("⚙️ Scoring engine + allocation logic coming in next update.")
