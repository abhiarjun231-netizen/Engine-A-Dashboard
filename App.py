import streamlit as st
import yfinance as yf
from nsepython import nse_get_index_quote
from datetime import datetime

st.set_page_config(page_title="Engine A Dashboard", layout="wide")
st.title("📊 Engine A — Market Strength Dashboard")
st.caption(f"Last refresh: {datetime.now().strftime('%d %b %Y, %H:%M:%S')}")

def to_float(v):
    try:
        return float(str(v).replace(",", "").strip())
    except:
        return None

@st.cache_data(ttl=300)
def get_nse(index):
    try:
        d = nse_get_index_quote(index)
        return d
    except Exception as e:
        return {"error": str(e)}

@st.cache_data(ttl=600)
def get_yf_price(ticker):
    try:
        h = yf.download(ticker, period="5d", progress=False, auto_adjust=True)
        if h.empty:
            return None
        close = h["Close"]
        if hasattr(close, "columns"):
            close = close.iloc[:, 0]
        return float(close.dropna().iloc[-1])
    except:
        return None

@st.cache_data(ttl=3600)
def get_dma():
    try:
        h = yf.download("^NSEI", period="320d", progress=False, auto_adjust=True)
        close = h["Close"]
        if hasattr(close, "columns"):
            close = close.iloc[:, 0]
        dma = close.rolling(200).mean().dropna()
        return float(dma.iloc[-1]), float(dma.iloc[-6])
    except:
        return None, None

nifty_raw = get_nse("NIFTY 50")
vix_raw = get_nse("INDIA VIX")

nifty_price = to_float(nifty_raw.get("last")) if "error" not in nifty_raw else get_yf_price("^NSEI")
nifty_pe = to_float(nifty_raw.get("pe")) if "error" not in nifty_raw else None
adv = to_float(nifty_raw.get("advances")) if "error" not in nifty_raw else None
dec = to_float(nifty_raw.get("declines")) if "error" not in nifty_raw else None
vix = to_float(vix_raw.get("last")) if "error" not in vix_raw else None

us10y = get_yf_price("^TNX")
dxy = get_yf_price("DX-Y.NYB")
gvix = get_yf_price("^VIX")
inr = get_yf_price("INR=X")
brent = get_yf_price("BZ=F")
dma_now, dma_prev = get_dma()

st.header("🟢 Live Auto-Fetched Data")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Nifty 50", f"{nifty_price:,.2f}" if nifty_price else "N/A")
c2.metric("Nifty PE", f"{nifty_pe:.2f}" if nifty_pe else "N/A")
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
else:
    c10.metric("% vs 200DMA", "N/A")
if dma_now and dma_prev:
    c11.metric("DMA Direction", "Rising ↑" if dma_now > dma_prev else "Falling ↓")
else:
    c11.metric("DMA Direction", "N/A")
if adv and dec:
    breadth = adv / max(adv + dec, 1) * 100
    c12.metric("Nifty50 A/D", f"{breadth:.0f}%")
else:
    c12.metric("Nifty50 A/D", "N/A")

st.header("✍️ Manual Inputs")
m1, m2, m3 = st.columns(3)
rbi = m1.selectbox("RBI Stance", ["Accommodative-Cutting", "Accommodative-Paused", "Neutral", "Tightening-Paused", "Tightening-Hiking"])
cpi = m2.number_input("CPI %", value=5.0, step=0.1)
pmi = m3.number_input("PMI", value=55.0, step=0.5)

st.info("⚙️ Scoring engine + allocation logic coming in next update.")
