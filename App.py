import streamlit as st
import yfinance as yf
import datetime

st.set_page_config(page_title="Engine A Dashboard", layout="wide")

st.title("ENGINE A — LIVE DASHBOARD")
st.caption("Last refreshed: " + str(datetime.datetime.now().strftime("%d %b %Y %H:%M")))

# ===== AUTO-FETCH DATA =====
@st.cache_data(ttl=3600)
def fetch_data():
    nifty_1y = yf.download('^NSEI', period='1y', progress=False)
    nifty_price = float(nifty_1y['Close'].iloc[-1])
    dma200 = float(nifty_1y['Close'].rolling(200).mean().iloc[-1])
    pct_dma = round((nifty_price - dma200) / dma200 * 100, 1)
    
    dma_lw = float(nifty_1y['Close'].rolling(200).mean().iloc[-6])
    if dma200 > dma_lw * 1.001: dma_dir = "Rising"
    elif dma200 < dma_lw * 0.999: dma_dir = "Falling"
    else: dma_dir = "Flat"
    
    def gd(ticker):
        h = yf.download(ticker, period='2mo', progress=False)
        cur = float(h['Close'].iloc[-1])
        old = float(h['Close'].iloc[0])
        chg = round((cur-old)/old*100, 1)
        if chg > 2: d = "Rising"
        elif chg < -2: d = "Falling"
        else: d = "Stable"
        return cur, d, chg
    
    us10y, us10y_dir, _ = gd('^TNX')
    dxy, _, _ = gd('DX-Y.NYB')
    gvix, _, _ = gd('^VIX')
    inr, _, inr_chg = gd('USDINR=X')
    brent, crude_dir, _ = gd('BZ=F')
    
    if inr_chg > 2: inr_dir = "Weakening"
    elif inr_chg < -2: inr_dir = "Strengthening"
    else: inr_dir = "Stable"
    
    return {
        'nifty_price': nifty_price, 'dma200': dma200, 'pct_dma': pct_dma,
        'dma_dir': dma_dir, 'us10y': us10y, 'us10y_dir': us10y_dir,
        'dxy': dxy, 'gvix': gvix, 'inr': inr, 'inr_dir': inr_dir,
        'brent': brent, 'crude_dir': crude_dir
    }

with st.spinner("Fetching live data..."):
    d = fetch_data()

# ===== SIDEBAR — MANUAL INPUTS =====
st.sidebar.header("MANUAL INPUTS")
st.sidebar.caption("Update these every Sunday")
nifty_pe = st.sidebar.number_input("Nifty PE", value=20.5, step=0.1)
breadth = st.sidebar.number_input("Breadth % (Nifty500 > 200DMA)", value=20.0, step=1.0)
india_vix = st.sidebar.number_input("India VIX", value=24.0, step=0.1)
fii_30d = st.sidebar.number_input("FII 30D Net (Rs Cr)", value=-100000, step=1000)
dii_30d = st.sidebar.number_input("DII 30D Net (Rs Cr)", value=130000, step=1000)
rbi_stance = st.sidebar.selectbox("RBI Stance", ["Accommodative-Cutting","Accommodative-Paused","Neutral","Tightening-Paused","Tightening-Hiking"], index=2)
cpi = st.sidebar.number_input("CPI %", value=3.21, step=0.1)
pmi = st.sidebar.number_input("PMI", value=53.8, step=0.1)
yc_inv = st.sidebar.selectbox("Yield Curve Inverted?", ["No","Yes"], index=0)
last_score = st.sidebar.number_input("Last Week Score", value=34, step=1)

# ===== SCORING =====
if nifty_pe < 18: val_score = 15
elif nifty_pe < 20: val_score = 12
elif nifty_pe < 22: val_score = 9
elif nifty_pe < 24: val_score = 4
elif nifty_pe < 26: val_score = 2
else: val_score = 0

pct_dma = d['pct_dma']
dma_dir = d['dma_dir']
if pct_dma > 10: trend_score = 15 if dma_dir == "Rising" else 13
elif pct_dma > 5: trend_score = 13 if dma_dir == "Rising" else 11
elif pct_dma > 0: trend_score = 10 if dma_dir == "Rising" else 7
elif pct_dma > -5: trend_score = 5
elif pct_dma > -10: trend_score = 3
else: trend_score = 0

if breadth > 70: br_score = 12
elif breadth > 60: br_score = 10
elif breadth > 50: br_score = 8
elif breadth > 40: br_score = 6
elif breadth > 30: br_score = 4
elif breadth > 20: br_score = 2
else: br_score = 0

if india_vix < 12: vix_score = 10
elif india_vix < 15: vix_score = 8
elif india_vix < 18: vix_score = 6
elif india_vix < 22: vix_score = 4
elif india_vix < 30: vix_score = 2
else: vix_score = 0

if fii_30d > 5000: fii_s = 6
elif fii_30d > 0: fii_s = 5
elif fii_30d > -5000: fii_s = 4
elif fii_30d > -10000: fii_s = 2
elif fii_30d > -20000: fii_s = 1
else: fii_s = 0
if dii_30d > 15000: dii_s = 6
elif dii_30d > 10000: dii_s = 5
elif dii_30d > 5000: dii_s = 4
elif dii_30d > 0: dii_s = 3
elif dii_30d > -5000: dii_s = 1
else: dii_s = 0
flow_score = min(12, fii_s + dii_s)

rbi_map = {"Accommodative-Cutting":4,"Accommodative-Paused":3,"Neutral":2,"Tightening-Paused":1,"Tightening-Hiking":0}
rbi_s = rbi_map.get(rbi_stance, 0)
if cpi < 4.5: cpi_s = 4
elif cpi < 5.7: cpi_s = 3
elif cpi < 7: cpi_s = 2
elif cpi < 8.5: cpi_s = 1
else: cpi_s = 0
if pmi > 55: pmi_s = 4
elif pmi > 52: pmi_s = 3
elif pmi > 50: pmi_s = 2
elif pmi > 48: pmi_s = 1
else: pmi_s = 0
yc_p = 2 if yc_inv == "Yes" else 0
macro_score = max(0, rbi_s + cpi_s + pmi_s - yc_p)

us10y = d['us10y']; us10y_dir = d['us10y_dir']
dxy = d['dxy']; gvix = d['gvix']; inr_dir = d['inr_dir']
brent = d['brent']; crude_dir = d['crude_dir']

if us10y_dir == "Falling" and us10y < 4: us_s = 3
elif us10y_dir == "Falling": us_s = 2
elif us10y_dir == "Stable": us_s = 2
elif us10y < 5: us_s = 1
else: us_s = 0
if dxy < 92: dx_s = 3
elif dxy < 100: dx_s = 2
elif dxy < 106: dx_s = 1
else: dx_s = 0
if gvix < 15: gv_s = 3
elif gvix < 20: gv_s = 2
elif gvix < 25: gv_s = 2
elif gvix < 30: gv_s = 1
else: gv_s = 0
if inr_dir == "Strengthening": ir_s = 3
elif inr_dir == "Stable": ir_s = 2
elif inr_dir == "Weakening": ir_s = 1
else: ir_s = 0
global_score = min(12, us_s + dx_s + gv_s + ir_s)

if brent < 50: crude_score = 12
elif brent < 60: crude_score = 10
elif brent < 70: crude_score = 8
elif brent < 80: crude_score = 6
elif brent < 90: crude_score = 4
elif brent < 100: crude_score = 2
else: crude_score = 0

raw_score = val_score + trend_score + br_score + vix_score + flow_score + macro_score + global_score + crude_score
smoothed = round((raw_score + last_score) / 2) if last_score else raw_score

red_flag = trend_score <= 3 and vix_score <= 2 and (flow_score <= 3 or fii_30d < -15000)
pe_bubble = nifty_pe > 26

if smoothed <= 20: eq, gold = 10, 25
elif smoothed <= 30: eq, gold = 25, 25
elif smoothed <= 40: eq, gold = 40, 20
elif smoothed <= 52: eq, gold = 55, 15
elif smoothed <= 62: eq, gold = 70, 10
else: eq, gold = 85, 5
if red_flag: eq = min(eq, 25); gold = 25
if pe_bubble: eq = min(eq, 70)
debt = 100 - eq - gold

if smoothed <= 20: b_pct, c_pct = 30, 70
elif smoothed <= 30: b_pct, c_pct = 35, 65
elif smoothed <= 40: b_pct, c_pct = 40, 60
elif smoothed <= 52: b_pct, c_pct = 45, 55
else: b_pct, c_pct = 50, 50

if smoothed <= 20: condition = "TERRIBLE"
elif smoothed <= 30: condition = "WEAK"
elif smoothed <= 40: condition = "BELOW AVG"
elif smoothed <= 52: condition = "NEUTRAL"
elif smoothed <= 62: condition = "GOOD"
else: condition = "EXCELLENT"

if rbi_stance in ["Accommodative-Cutting","Accommodative-Paused"] and yc_inv == "No":
    duration = "LONG DURATION"
elif rbi_stance == "Neutral": duration = "MEDIUM DURATION"
else: duration = "SHORT / CASH"

if gvix > 25 or brent > 100 or inr_dir == "Weakening": gold_signal = "ACCUMULATE"
elif gvix < 15 and brent < 60: gold_signal = "TRIM"
else: gold_signal = "HOLD"

# ===== DISPLAY =====
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("ENGINE A SCORE", f"{smoothed}/100", f"Raw: {raw_score}")
with col2:
    st.metric("CONDITION", condition)
with col3:
    rf_text = "YES" if red_flag else "No"
    st.metric("RED FLAG", rf_text)

st.divider()

col1, col2, col3, col4 = st.columns(4)
with col1:
    eq_color = "inverse" if eq <= 25 else "normal"
    st.metric("EQUITY", f"{eq}%", f"B:{round(eq*b_pct/100)}% C:{round(eq*c_pct/100)}%")
with col2:
    st.metric("DEBT", f"{debt}%", duration)
with col3:
    st.metric("GOLD", f"{gold}%", gold_signal)
with col4:
    st.metric("B:C SPLIT", f"{b_pct}:{c_pct}")

st.divider()
st.subheader("Component Scores")

scores = {
    "Valuation": (val_score, 15),
    "Trend": (trend_score, 15),
    "Breadth": (br_score, 12),
    "Volatility": (vix_score, 10),
    "Flows": (flow_score, 12),
    "Macro": (macro_score, 12),
    "Global": (global_score, 12),
    "Crude": (crude_score, 12),
}

cols = st.columns(4)
for i, (name, (score, mx)) in enumerate(scores.items()):
    with cols[i % 4]:
        pct = score / mx * 100
        color = "🟢" if pct > 60 else ("🟡" if pct > 30 else "🔴")
        st.metric(f"{color} {name}", f"{score}/{mx}")

st.divider()
st.subheader("Live Market Data")

col1, col2 = st.columns(2)
with col1:
    st.markdown("**INDIA**")
    st.write(f"Nifty: **{round(d['nifty_price'])}** ({d['pct_dma']}% vs 200DMA)")
    st.write(f"200 DMA: {round(d['dma200'])} ({d['dma_dir']})")
    st.write(f"Nifty PE: {nifty_pe}")
    st.write(f"India VIX: {india_vix}")
    st.write(f"Breadth: {breadth}%")
    st.write(f"FII 30D: {fii_30d:,} Cr")
    st.write(f"DII 30D: {dii_30d:,} Cr")

with col2:
    st.markdown("**GLOBAL**")
    st.write(f"US 10Y: **{round(d['us10y'],2)}%** ({d['us10y_dir']})")
    st.write(f"DXY: {round(d['dxy'],1)}")
    st.write(f"Global VIX: {round(d['gvix'],1)}")
    st.write(f"INR/USD: {round(d['inr'],2)} ({d['inr_dir']})")
    st.write(f"Brent: ${round(d['brent'],1)} ({d['crude_dir']})")
    st.write(f"RBI: {rbi_stance}")
    st.write(f"CPI: {cpi}% | PMI: {pmi}")

st.divider()
st.caption("Built by Abhishek | Engine A v2 | Auto-fetches 10 inputs, 7 manual")
