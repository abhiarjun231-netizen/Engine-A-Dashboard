import streamlit as st
import yfinance as yf
import datetime

st.set_page_config(page_title="Engine A Dashboard", layout="wide")

st.title("ENGINE A — LIVE DASHBOARD")
st.caption("Last refreshed: " + str(datetime.datetime.now().strftime("%d %b %Y %H:%M")))

@st.cache_data(ttl=3600)
def fetch_data():
    data = {}
    tickers = {
        'nifty': '^NSEI', 'us10y': '^TNX', 'dxy': 'DX-Y.NYB',
        'gvix': '^VIX', 'inr': 'USDINR=X', 'brent': 'BZ=F'
    }
    
    for name, ticker in tickers.items():
        try:
            h = yf.download(ticker, period='1y', progress=False)
            if len(h) == 0:
                continue
            cols = h.columns
            close_col = [c for c in cols if 'Close' in str(c)][0]
            prices = h[close_col].dropna()
            
            if len(prices) < 10:
                continue
            
            cur = float(prices.iloc[-1])
            
            if name == 'nifty' and len(prices) >= 200:
                sma = prices.rolling(200).mean()
                dma200 = float(sma.iloc[-1])
                dma_lw = float(sma.iloc[-6]) if len(sma) > 6 else dma200
                data['nifty_price'] = cur
                data['dma200'] = dma200
                data['pct_dma'] = round((cur - dma200) / dma200 * 100, 1)
                if dma200 > dma_lw * 1.001: data['dma_dir'] = "Rising"
                elif dma200 < dma_lw * 0.999: data['dma_dir'] = "Falling"
                else: data['dma_dir'] = "Flat"
            
            old = float(prices.iloc[0]) if name != 'nifty' else float(prices.iloc[-22])
            chg = round((cur - old) / old * 100, 1)
            
            if name == 'inr':
                data['inr'] = cur
                if chg > 2: data['inr_dir'] = "Weakening"
                elif chg < -2: data['inr_dir'] = "Strengthening"
                else: data['inr_dir'] = "Stable"
            elif name == 'us10y':
                data['us10y'] = cur
                if chg > 2: data['us10y_dir'] = "Rising"
                elif chg < -2: data['us10y_dir'] = "Falling"
                else: data['us10y_dir'] = "Stable"
            elif name == 'brent':
                data['brent'] = cur
                if chg > 2: data['crude_dir'] = "Rising"
                elif chg < -2: data['crude_dir'] = "Falling"
                else: data['crude_dir'] = "Stable"
            elif name == 'dxy':
                data['dxy'] = cur
            elif name == 'gvix':
                data['gvix'] = cur
        except:
            continue
    
    defaults = {'nifty_price':22000,'dma200':25000,'pct_dma':-10,'dma_dir':'Falling',
                'us10y':4.3,'us10y_dir':'Stable','dxy':100,'gvix':24,
                'inr':92,'inr_dir':'Weakening','brent':109,'crude_dir':'Rising'}
    for k,v in defaults.items():
        if k not in data:
            data[k] = v
    return data

with st.spinner("Fetching live data..."):
    d = fetch_data()

st.sidebar.header("MANUAL INPUTS")
st.sidebar.caption("Update every Sunday")
nifty_pe = st.sidebar.number_input("Nifty PE", value=20.5, step=0.1)
breadth = st.sidebar.number_input("Breadth %", value=20.0, step=1.0)
india_vix = st.sidebar.number_input("India VIX", value=24.0, step=0.1)
fii_30d = st.sidebar.number_input("FII 30D (Cr)", value=-100000, step=1000)
dii_30d = st.sidebar.number_input("DII 30D (Cr)", value=130000, step=1000)
rbi_stance = st.sidebar.selectbox("RBI Stance", ["Accommodative-Cutting","Accommodative-Paused","Neutral","Tightening-Paused","Tightening-Hiking"], index=2)
cpi = st.sidebar.number_input("CPI %", value=3.21, step=0.1)
pmi = st.sidebar.number_input("PMI", value=53.8, step=0.1)
yc_inv = st.sidebar.selectbox("Yield Curve Inverted?", ["No","Yes"])
last_score = st.sidebar.number_input("Last Week Score", value=34, step=1)

if nifty_pe < 18: val_score = 15
elif nifty_pe < 20: val_score = 12
elif nifty_pe < 22: val_score = 9
elif nifty_pe < 24: val_score = 4
elif nifty_pe < 26: val_score = 2
else: val_score = 0

pct_dma = d['pct_dma']; dma_dir = d['dma_dir']
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

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("ENGINE A SCORE", str(smoothed) + "/100", "Raw: " + str(raw_score))
with col2:
    st.metric("CONDITION", condition)
with col3:
    st.metric("RED FLAG", "YES" if red_flag else "No")

st.divider()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("EQUITY", str(eq) + "%", "B:" + str(round(eq*b_pct/100)) + "% C:" + str(round(eq*c_pct/100)) + "%")
with col2:
    st.metric("DEBT", str(debt) + "%", duration)
with col3:
    st.metric("GOLD", str(gold) + "%", gold_signal)
with col4:
    st.metric("B:C SPLIT", str(b_pct) + ":" + str(c_pct))

st.divider()
st.subheader("Component Scores")

scores = {"Valuation": (val_score, 15), "Trend": (trend_score, 15),
          "Breadth": (br_score, 12), "Volatility": (vix_score, 10),
          "Flows": (flow_score, 12), "Macro": (macro_score, 12),
          "Global": (global_score, 12), "Crude": (crude_score, 12)}

cols = st.columns(4)
for i, (name, (score, mx)) in enumerate(scores.items()):
    with cols[i % 4]:
        pct = score / mx * 100
        icon = "🟢" if pct > 60 else ("🟡" if pct > 30 else "🔴")
        st.metric(icon + " " + name, str(score) + "/" + str(mx))

st.divider()
st.subheader("Live Market Data")

col1, col2 = st.columns(2)
with col1:
    st.markdown("**INDIA**")
    st.write("Nifty: **" + str(round(d['nifty_price'])) + "** (" + str(d['pct_dma']) + "% vs 200DMA)")
    st.write("200 DMA: " + str(round(d['dma200'])) + " (" + d['dma_dir'] + ")")
    st.write("Nifty PE: " + str(nifty_pe))
    st.write("India VIX: " + str(india_vix))
    st.write("Breadth: " + str(breadth) + "%")
    st.write("FII 30D: " + str(fii_30d) + " Cr")
    st.write("DII 30D: " + str(dii_30d) + " Cr")

with col2:
    st.markdown("**GLOBAL**")
    st.write("US 10Y: **" + str(round(d['us10y'],2)) + "%** (" + d['us10y_dir'] + ")")
    st.write("DXY: " + str(round(d['dxy'],1)))
    st.write("Global VIX: " + str(round(d['gvix'],1)))
    st.write("INR/USD: " + str(round(d['inr'],2)) + " (" + d['inr_dir'] + ")")
    st.write("Brent: $" + str(round(d['brent'],1)) + " (" + d['crude_dir'] + ")")
    st.write("RBI: " + rbi_stance)
    st.write("CPI: " + str(cpi) + "% | PMI: " + str(pmi))

st.divider()
st.caption("Built by Abhishek | Engine A v2 | Auto-fetches 10 inputs, 7 manual")
