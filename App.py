import streamlit as st
import yfinance as yf
import datetime, requests, re, json, os

st.set_page_config(page_title="Investment Dashboard", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""<style>
.stApp{background-color:#0a0e1a;color:#e2e8f0}
.block-container{padding-top:1rem;padding-bottom:2rem}
h1,h2,h3{color:#f1f5f9!important;font-weight:700}
.metric-card{background:#131826;padding:20px;border-radius:12px;border:1px solid #1e293b;margin-bottom:12px}
.score-card{background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 50%,#a855f7 100%);color:white;padding:28px;border-radius:16px;text-align:center;box-shadow:0 10px 25px rgba(79,70,229,0.4)}
.score-number{font-size:72px;font-weight:800;line-height:1;margin:8px 0;color:white!important}
.score-label{font-size:13px;opacity:0.95;text-transform:uppercase;letter-spacing:2px;color:white!important}
.badge-green{background:rgba(16,185,129,0.15);color:#10b981;padding:6px 16px;border-radius:999px;font-size:12px;font-weight:700;display:inline-block;border:1px solid rgba(16,185,129,0.3)}
.badge-yellow{background:rgba(245,158,11,0.15);color:#f59e0b;padding:6px 16px;border-radius:999px;font-size:12px;font-weight:700;display:inline-block;border:1px solid rgba(245,158,11,0.3)}
.badge-red{background:rgba(239,68,68,0.15);color:#ef4444;padding:6px 16px;border-radius:999px;font-size:12px;font-weight:700;display:inline-block;border:1px solid rgba(239,68,68,0.3)}
.stock-row{background:#131826;padding:16px 18px;border-radius:10px;border-left:4px solid #4f46e5;margin-bottom:10px}
.stock-row-safe{border-left-color:#10b981}
.stock-row-warn{border-left-color:#f59e0b}
.stock-row-danger{border-left-color:#ef4444}
.section-header{font-size:18px;font-weight:700;color:#f1f5f9!important;margin:28px 0 14px 0;padding-bottom:10px;border-bottom:1px solid #1e293b}
.stMetric{background:#131826!important;padding:18px!important;border-radius:10px!important;border:1px solid #1e293b!important}
.stMetric label{color:#94a3b8!important}
.stMetric [data-testid="stMetricValue"]{color:#f1f5f9!important}
[data-testid="stSidebar"]{background-color:#0f1420!important}
[data-testid="stSidebar"] *{color:#cbd5e1!important}
.stNumberInput input,.stSelectbox > div{background-color:#1e293b!important;color:#f1f5f9!important;border:1px solid #334155!important}
.stLinkButton > a{background:#131826!important;color:#818cf8!important;border:1px solid #334155!important;border-radius:8px!important;font-weight:600!important;padding:10px 14px!important}
</style>""", unsafe_allow_html=True)

SCORE_FILE = "last_score.json"

def load_last_score():
    try:
        if os.path.exists(SCORE_FILE):
            with open(SCORE_FILE, 'r') as f:
                return json.load(f).get('score', 34)
    except: pass
    return 34

def save_score(score):
    try:
        with open(SCORE_FILE, 'w') as f:
            json.dump({'score': score, 'date': str(datetime.datetime.now())}, f)
    except: pass

@st.cache_data(ttl=3600)
def fetch_nifty_pe():
    try:
        r = requests.get('https://www.nifty-pe-ratio.com/', headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if r.status_code == 200:
            for pat in [r'P/?E[\s:]*(\d{2}\.\d{1,2})', r'>(\d{2}\.\d{1,2})<']:
                m = re.search(pat, r.text, re.IGNORECASE)
                if m:
                    v = float(m.group(1))
                    if 15 < v < 35: return round(v, 2)
    except: pass
    return 0

@st.cache_data(ttl=1800)
def fetch_holdings():
    h = {
        'NATIONALUM.NS': {'name':'National Aluminium','qty':12,'entry':400,'stop':372,'engine':'B'},
        'INDUSTOWER.NS': {'name':'Indus Towers','qty':11,'entry':441,'stop':410,'engine':'B'},
        'ENGINERSIN.NS': {'name':'Engineers India','qty':24,'entry':206,'stop':191,'engine':'B'},
        'TORNTPOWER.NS': {'name':'Torrent Power','qty':3,'entry':1448,'stop':1347,'engine':'B'},
        'HINDZINC.NS': {'name':'Hindustan Zinc','qty':8,'entry':559,'stop':520,'engine':'B'},
        'GOLDBEES.NS': {'name':'Gold BeES','qty':121,'entry':124.39,'stop':0,'engine':'E'},
        'LIQUIDBEES.NS': {'name':'Liquid BeES','qty':31,'entry':999.99,'stop':0,'engine':'C'},
    }
    for t, i in h.items():
        i['current'] = i['entry']
        try:
            df = yf.download(t, period='5d', progress=False, auto_adjust=True)
            if len(df) > 0:
                cc = [c for c in df.columns if 'Close' in str(c)]
                if cc:
                    lp = df[cc[0]].dropna()
                    if len(lp) > 0: i['current'] = round(float(lp.iloc[-1]), 2)
        except: pass
        i['pnl'] = round((i['current'] - i['entry']) * i['qty'], 2)
        i['pnl_pct'] = round((i['current'] - i['entry']) / i['entry'] * 100, 2) if i['entry'] > 0 else 0
        if i['engine'] == 'B':
            if i['current'] <= i['stop']: i['status']='EXIT'; i['action']='SELL - Stop hit'
            elif i['pnl_pct'] <= -5: i['status']='WARN'; i['action']='Watch closely'
            elif i['pnl_pct'] >= 25: i['status']='PROFIT'; i['action']='Move stop +12%'
            elif i['pnl_pct'] >= 15: i['status']='PROFIT'; i['action']='Move stop +5%'
            elif i['pnl_pct'] >= 8: i['status']='PROFIT'; i['action']='Move stop to entry'
            else: i['status']='OK'; i['action']='Hold'
        else: i['status']='OK'; i['action']='Long-term hold'
    h['BHARATBOND'] = {'name':'Bharat Bond ETF Apr30','qty':19,'entry':1562.18,'stop':0,'current':1562.18,'engine':'D','pnl':0,'pnl_pct':0,'status':'OK','action':'Long-term hold'}
    return h

@st.cache_data(ttl=3600)
def fetch_data():
    d = {}
    tk = {'nifty':'^NSEI','us10y':'^TNX','dxy':'DX-Y.NYB','gvix':'^VIX','inr':'USDINR=X','brent':'BZ=F','indiavix':'^INDIAVIX'}
    for n, t in tk.items():
        try:
            h = yf.download(t, period='1y', progress=False)
            if len(h) == 0: continue
            cc = [c for c in h.columns if 'Close' in str(c)][0]
            p = h[cc].dropna()
            if len(p) < 5: continue
            cur = float(p.iloc[-1])
            if n == 'nifty' and len(p) >= 200:
                sma = p.rolling(200).mean()
                dma = float(sma.iloc[-1])
                dlw = float(sma.iloc[-6]) if len(sma) > 6 else dma
                d['nifty_price'] = cur; d['dma200'] = dma
                d['pct_dma'] = round((cur - dma) / dma * 100, 1)
                d['dma_dir'] = "Rising" if dma > dlw * 1.001 else ("Falling" if dma < dlw * 0.999 else "Flat")
                continue
            if n == 'indiavix': d['india_vix_auto'] = round(cur, 1); continue
            old = float(p.iloc[-22]) if len(p) > 22 else float(p.iloc[0])
            chg = round((cur - old) / old * 100, 1)
            if n == 'inr': d['inr'] = cur; d['inr_dir'] = "Weakening" if chg > 2 else ("Strengthening" if chg < -2 else "Stable")
            elif n == 'us10y': d['us10y'] = cur; d['us10y_dir'] = "Rising" if chg > 2 else ("Falling" if chg < -2 else "Stable")
            elif n == 'brent': d['brent'] = cur; d['crude_dir'] = "Rising" if chg > 2 else ("Falling" if chg < -2 else "Stable")
            elif n == 'dxy': d['dxy'] = cur
            elif n == 'gvix': d['gvix'] = cur
        except: continue
    d['nifty_pe_auto'] = fetch_nifty_pe()
    df = {'nifty_price':22000,'dma200':25000,'pct_dma':-10,'dma_dir':'Falling','us10y':4.3,'us10y_dir':'Stable','dxy':100,'gvix':24,'inr':92,'inr_dir':'Weakening','brent':109,'crude_dir':'Rising','india_vix_auto':0,'nifty_pe_auto':0}
    for k, v in df.items():
        if k not in d: d[k] = v
    return d

st.markdown("# 🎯 Investment Dashboard")
st.markdown(f"<p style='color:#64748b;font-size:14px;margin-top:-10px;'>Live • {datetime.datetime.now().strftime('%d %b %Y, %H:%M')}</p>", unsafe_allow_html=True)

with st.spinner("Loading..."):
    d = fetch_data()
    holdings = fetch_holdings()

st.sidebar.header("📝 Manual Inputs")
nifty_pe = st.sidebar.number_input("Nifty PE", value=d['nifty_pe_auto'] if d['nifty_pe_auto'] > 0 else 20.5, step=0.1)
india_vix = st.sidebar.number_input("India VIX", value=d['india_vix_auto'] if d['india_vix_auto'] > 0 else 19.7, step=0.1)
breadth = st.sidebar.number_input("Breadth %", value=29.0, step=1.0)
fii_30d = st.sidebar.number_input("FII 30D", value=-138643, step=1000)
dii_30d = st.sidebar.number_input("DII 30D", value=144790, step=1000)
rbi_stance = st.sidebar.selectbox("RBI Stance", ["Accommodative-Cutting","Accommodative-Paused","Neutral","Tightening-Paused","Tightening-Hiking"], index=2)
cpi = st.sidebar.number_input("CPI %", value=3.21, step=0.1)
pmi = st.sidebar.number_input("PMI", value=53.8, step=0.1)
yc_inv = st.sidebar.selectbox("Yield Inverted?", ["No","Yes"])
last_score = st.sidebar.number_input("Last Week Score", value=load_last_score(), step=1)

if nifty_pe < 18: vs = 15
elif nifty_pe < 20: vs = 12
elif nifty_pe < 22: vs = 9
elif nifty_pe < 24: vs = 4
elif nifty_pe < 26: vs = 2
else: vs = 0
val_score = vs

pd_v = d['pct_dma']; dd = d['dma_dir']
if pd_v > 10: ts = 15 if dd == "Rising" else 13
elif pd_v > 5: ts = 13 if dd == "Rising" else 11
elif pd_v > 0: ts = 10 if dd == "Rising" else 7
elif pd_v > -5: ts = 5
elif pd_v > -10: ts = 3
else: ts = 0
trend_score = ts

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

us10y = d['us10y']; us10y_dir = d['us10y_dir']; dxy = d['dxy']; gvix = d['gvix']; inr_dir = d['inr_dir']; brent = d['brent']
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
save_score(raw_score)
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

if rbi_stance in ["Accommodative-Cutting","Accommodative-Paused"] and yc_inv == "No": duration = "LONG DURATION"
elif rbi_stance == "Neutral": duration = "MEDIUM DURATION"
else: duration = "SHORT / CASH"

if gvix > 25 or brent > 100 or inr_dir == "Weakening": gold_signal = "ACCUMULATE"
elif gvix < 15 and brent < 60: gold_signal = "TRIM"
else: gold_signal = "HOLD"

c1, c2 = st.columns([1, 2])
with c1:
    st.markdown(f"<div class='score-card'><div class='score-label'>Engine A Score</div><div class='score-number'>{smoothed}</div><div class='score-label'>out of 100</div><div style='margin-top:12px;font-size:18px;font-weight:600;color:white;'>{condition}</div></div>", unsafe_allow_html=True)
with c2:
    fb = "badge-red" if red_flag else "badge-green"
    ft = "🚨 RED FLAG" if red_flag else "✅ ALL CLEAR"
    pc = "#10b981" if d['pct_dma'] > 0 else "#ef4444"
    st.markdown(f"<div class='metric-card'><div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;'><span style='color:#94a3b8;font-size:13px;'>MARKET STATUS</span><span class='{fb}'>{ft}</span></div><div style='display:grid;grid-template-columns:1fr 1fr;gap:14px;'><div><div style='color:#94a3b8;font-size:12px;'>Nifty 50</div><div style='font-size:22px;font-weight:700;color:#f1f5f9;'>{round(d['nifty_price']):,}</div></div><div><div style='color:#94a3b8;font-size:12px;'>vs 200 DMA</div><div style='font-size:22px;font-weight:700;color:{pc};'>{d['pct_dma']}%</div></div><div><div style='color:#94a3b8;font-size:12px;'>India VIX</div><div style='font-size:22px;font-weight:700;color:#f1f5f9;'>{india_vix}</div></div><div><div style='color:#94a3b8;font-size:12px;'>Brent</div><div style='font-size:22px;font-weight:700;color:#f1f5f9;'>${round(d['brent'])}</div></div></div></div>", unsafe_allow_html=True)

st.markdown("<div class='section-header'>💼 Asset Allocation</div>", unsafe_allow_html=True)
a1, a2, a3, a4 = st.columns(4)
with a1: st.metric("Equity", f"{eq}%", f"B:{round(eq*b_pct/100)}% C:{round(eq*c_pct/100)}%")
with a2: st.metric("Debt", f"{debt}%", duration)
with a3: st.metric("Gold", f"{gold}%", gold_signal)
with a4: st.metric("B:C Split", f"{b_pct}:{c_pct}")

ti = sum(s['entry'] * s['qty'] for s in holdings.values())
tc = sum(s['current'] * s['qty'] for s in holdings.values())
tp = tc - ti
tpp = (tp / ti) * 100 if ti > 0 else 0

st.markdown("<div class='section-header'>📊 Total Portfolio</div>", unsafe_allow_html=True)
po1, po2, po3 = st.columns(3)
with po1: st.metric("Invested", f"₹{ti:,.0f}")
with po2: st.metric("Current", f"₹{tc:,.0f}", f"₹{tp:+,.0f}")
with po3: st.metric("P&L %", f"{tpp:+.2f}%")

def render(title, ef):
    st.markdown(f"<div class='section-header'>{title}</div>", unsafe_allow_html=True)
    for t, s in holdings.items():
        if s['engine'] != ef: continue
        sc = {'EXIT':'stock-row-danger','WARN':'stock-row-warn','PROFIT':'stock-row-safe'}.get(s['status'], 'stock-row')
        bc = {'EXIT':'badge-red','WARN':'badge-yellow','PROFIT':'badge-green'}.get(s['status'], 'badge-green')
        pc = "#10b981" if s['pnl_pct'] >= 0 else "#ef4444"
        st_txt = f" • Stop: ₹{s['stop']}" if s['stop'] > 0 else ""
        st.markdown(f"<div class='stock-row {sc}'><div style='display:flex;justify-content:space-between;align-items:center;'><div><div style='font-weight:600;font-size:15px;color:#f1f5f9;'>{s['name']}</div><div style='font-size:12px;color:#94a3b8;margin-top:2px;'>Qty: {s['qty']} • Entry: ₹{s['entry']}{st_txt}</div></div><div style='text-align:right;'><div style='font-weight:700;font-size:16px;color:#f1f5f9;'>₹{s['current']}</div><div style='font-size:13px;font-weight:600;color:{pc};'>{s['pnl_pct']:+.2f}% (₹{s['pnl']:+,.0f})</div></div></div><div style='display:flex;justify-content:space-between;align-items:center;margin-top:8px;'><span class='{bc}'>{s['status']}</span><span style='font-size:12px;color:#94a3b8;'>{s['action']}</span></div></div>", unsafe_allow_html=True)

render("📈 Engine B - Trading", "B")
render("💎 Engine C - Compounders", "C")
render("🏛️ Engine D - Debt", "D")
render("🥇 Engine E - Gold", "E")

st.markdown("<div class='section-header'>📊 Component Scores</div>", unsafe_allow_html=True)
sd = {"Valuation":(val_score,15),"Trend":(trend_score,15),"Breadth":(br_score,12),"Volatility":(vix_score,10),"Flows":(flow_score,12),"Macro":(macro_score,12),"Global":(global_score,12),"Crude":(crude_score,12)}
sc1, sc2, sc3, sc4 = st.columns(4)
cl = [sc1, sc2, sc3, sc4]
for i, (n, (s, m)) in enumerate(sd.items()):
    with cl[i % 4]:
        p = s / m * 100
        co = "#10b981" if p > 60 else ("#f59e0b" if p > 30 else "#ef4444")
        st.markdown(f"<div class='metric-card' style='padding:14px;'><div style='font-size:12px;color:#94a3b8;'>{n}</div><div style='font-size:22px;font-weight:700;color:{co};margin-top:4px;'>{s}/{m}</div><div style='height:4px;background:#1e293b;border-radius:2px;margin-top:6px;'><div style='height:100%;width:{p}%;background:{co};border-radius:2px;'></div></div></div>", unsafe_allow_html=True)

st.markdown("<div class='section-header'>🔗 Quick Sources</div>", unsafe_allow_html=True)
q1, q2, q3 = st.columns(3)
with q1: st.link_button("📊 Breadth", "https://trendlyne.com/fundamentals/stock-screener/797020/nifty-500-above-200-sma/index/NIFTY500/nifty-500/", use_container_width=True)
with q2: st.link_button("💰 FII/DII", "https://trendlyne.com/macro-data/fii-dii/latest/cash-pastmonth/", use_container_width=True)
with q3: st.link_button("🏛️ RBI", "https://www.rbi.org.in/scripts/Annualpolicy.aspx", use_container_width=True)

st.markdown(f"<div style='text-align:center;color:#64748b;font-size:12px;padding:20px;'>Built by Abhishek • v4 Pro Dark • {datetime.datetime.now().strftime('%H:%M')}</div>", unsafe_allow_html=True)
