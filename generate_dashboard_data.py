"""
generate_dashboard_data.py v2
Fixes: delivery% bug, price reading from multiple sources
Adds: sector concentration, overlap map, velocity, earnings, intelligence summaries
"""

import json, csv, os, glob
from datetime import datetime, timedelta

DATA_DIR = "data"
DOCS_DIR = "docs"
SCORE_FILE = os.path.join(DATA_DIR, "engine_a_score.csv")
STOCKS_FILE = os.path.join(DATA_DIR, "engine_b_stocks.json")
OUTPUT_FILE = os.path.join(DOCS_DIR, "data.json")

ALLOC_BANDS = [(20,10,65,25),(30,25,50,25),(40,40,40,20),(52,55,30,15),(62,70,20,10),(999,85,10,5)]

def get_allocation(score):
    for cap,eq,debt,gold in ALLOC_BANDS:
        if score <= cap: return {"equity":eq,"debt":debt,"gold":gold}
    return {"equity":85,"debt":10,"gold":5}

def find_col(headers, patterns, exclude=None):
    h_lower = [h.lower().strip() for h in headers]
    ex = exclude or []
    for pat in patterns:
        for i,h in enumerate(h_lower):
            if pat.lower() in h:
                if any(e.lower() in h for e in ex): continue
                return i
    return -1

def safe_float(val, default=0):
    if val is None: return default
    try:
        v = str(val).strip().replace(",","").replace("%","")
        if v=="" or v.lower() in ("nan","none","-","n/a","inf","-inf"): return default
        f = float(v)
        if abs(f) > 1e8: return default
        return f
    except: return default

def safe_str(val, default=""):
    if val is None: return default
    s = str(val).strip()
    return default if s.lower() in ("nan","none","") else s

def read_engine_a():
    result = {"score":0,"prevScore":0,"components":[],"history":[],"capital":500000}
    if not os.path.exists(SCORE_FILE):
        print(f"[WARN] {SCORE_FILE} not found"); return result
    try:
        with open(SCORE_FILE,"r") as f: rows = list(csv.DictReader(f))
        if not rows: return result
        headers = {k.lower().strip():k for k in rows[0].keys()}
        scores = []
        for row in rows:
            for key in ["raw_score","score","total_score"]:
                if key in headers:
                    val = safe_float(row.get(headers[key],0))
                    if val > 0: scores.append(val); break
        if scores:
            result["score"] = int(scores[-1])
            result["prevScore"] = int(scores[-2]) if len(scores)>1 else int(scores[-1])
            result["history"] = [int(s) for s in scores[-12:]]
        latest = rows[-1]
        for sk,(dn,mx) in {"valuation":("Valuation",15),"trend":("Trend",15),"breadth":("Breadth",12),
            "volatility":("Volatility",10),"flow":("Flows",12),"macro":("Macro",12),
            "global":("Global",12),"crude":("Crude",12)}.items():
            found = False
            for cn,ok in headers.items():
                if sk in cn:
                    result["components"].append({"name":dn,"score":min(int(safe_float(latest.get(ok,0))),mx),"max":mx})
                    found = True; break
            if not found: result["components"].append({"name":dn,"score":0,"max":mx})
    except Exception as e: print(f"[ERROR] Engine A: {e}")
    return result

def find_csv_file(prefix):
    if not os.path.exists(DATA_DIR): return None
    files = [f for f in os.listdir(DATA_DIR) if f.upper().startswith(prefix.upper()) and f.lower().endswith(".csv")]
    if not files: return None
    files.sort(key=lambda x: os.path.getmtime(os.path.join(DATA_DIR,x)), reverse=True)
    return os.path.join(DATA_DIR, files[0])

def read_csv_stocks(filepath):
    stocks = []
    if not filepath or not os.path.exists(filepath): return stocks
    try:
        with open(filepath,"r",encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            headers = [h.strip() for h in next(reader,[])]
            col = {}
            col["name"] = find_col(headers,["stock","company","name"])
            col["ticker"] = find_col(headers,["nse code","nse symbol","ticker","symbol"])
            col["price"] = find_col(headers,["ltp","price","cmp","close","last","current price"])
            col["mcap"] = find_col(headers,["market cap","mcap","m.cap","m cap"])
            col["roe"] = find_col(headers,["roe ann","roe annual","roe %","roe"])
            col["pe"] = find_col(headers,["pe ttm","pe ratio","p/e"])
            col["pio"] = find_col(headers,["piotroski","pio"])
            col["de"] = find_col(headers,["debt to total equity","debt to equity","d/e","debt equity","de ratio"])
            col["pg"] = find_col(headers,["net profit ann","profit growth annual","profit ann  yoy","profit growth yoy","pat growth"],["3y","3 y","qoq"])
            col["pg_3yr"] = find_col(headers,["net profit 3y","profit growth 3yr","profit 3y","pg 3yr"])
            col["prom"] = find_col(headers,["promoter hold","promoter %","promoter"])
            col["fii"] = find_col(headers,["fii hold","fii %","fii"])
            col["inst"] = find_col(headers,["institutional","inst hold","inst %","dii"])
            col["dvm_d"] = find_col(headers,["durability score","trendlyne durability","durability"],["momentum"])
            col["dvm_m"] = find_col(headers,["momentum score","trendlyne momentum"],["durability"])
            col["peg"] = find_col(headers,["peg ttm","peg ratio","peg"])
            col["rev_qoq"] = find_col(headers,["revenue qoq","rev qoq","revenue growth qoq"])
            # Delivery%: "Delivery% Vol  Avg Month" — search for "delivery% vol" (the % distinguishes from volume)
            col["delivery"] = find_col(headers,["delivery% vol  avg month","delivery% vol avg month","delivery% vol  avg","delivery% vol avg","delivery % avg","delivery avg month"],["qty","quantity"])
            col["sector"] = find_col(headers,["sector","industry"])
            col["w52_high"] = find_col(headers,["1y high","52 week high","52w high","52wk high","high 52"])
            col["w52_low"] = find_col(headers,["1y low","52 week low","52w low","52wk low","low 52"])
            col["results"] = find_col(headers,["latest financial result","financial result","result date","results date","next result","earnings"])

            # Debug column matching
            for k,v in col.items():
                matched = headers[v] if v>=0 else "NOT FOUND"
                if v<0: print(f"  [{os.path.basename(filepath)}] ⚠️ {k}: {matched}")
            found_count = sum(1 for v in col.values() if v>=0)
            print(f"  [{os.path.basename(filepath)}] Matched {found_count}/{len(col)} columns. "
                  f"price={headers[col['price']] if col['price']>=0 else 'MISSING'}, "
                  f"delivery={headers[col['delivery']] if col['delivery']>=0 else 'MISSING'}")

            for row in reader:
                if len(row)<3: continue
                def gf(k,d=0):
                    i=col.get(k,-1)
                    return safe_float(row[i],d) if 0<=i<len(row) else d
                def gs(k,d=""):
                    i=col.get(k,-1)
                    return safe_str(row[i],d) if 0<=i<len(row) else d

                ticker = gs("ticker") or gs("name")
                if not ticker or ticker.lower() in ("nan","","none"): continue
                ticker = ticker.replace(".NS","").replace(".BO","").replace(" ","").upper().strip()
                if not ticker or ticker=="NAN": continue

                price=gf("price"); mcap=gf("mcap"); w52h=gf("w52_high"); w52l=gf("w52_low")
                w52_pos = 50
                if w52h>w52l and w52h>0 and price>0:
                    w52_pos = max(0,min(100,int(((price-w52l)/(w52h-w52l))*100)))

                badge = "LARGE" if mcap>=50000 else "MID" if mcap>=5000 else "SMALL"
                delivery = gf("delivery")
                if delivery>100 or delivery<0: delivery=0

                stocks.append({
                    "ticker":ticker,"price":round(price,2),"change":0,"mcap":round(mcap,0),
                    "badge":badge,"roe":round(gf("roe"),1),"pe":round(gf("pe"),1),
                    "pio":int(gf("pio")),"de":round(gf("de"),2),"pg":round(gf("pg"),1),
                    "pg_3yr":round(gf("pg_3yr"),1),"prom":round(gf("prom"),1),
                    "fii":round(gf("fii"),1),"inst":round(gf("inst"),1),
                    "dvm_d":int(gf("dvm_d")),"dvm_m":int(gf("dvm_m")),
                    "peg":round(gf("peg"),2),"rev_qoq":round(gf("rev_qoq"),1),
                    "delivery":round(delivery,1),"sector":gs("sector","—"),
                    "w52_pos":w52_pos,"earnings":gs("results","—"),
                })
    except Exception as e:
        print(f"[ERROR] CSV {filepath}: {e}")
        import traceback; traceback.print_exc()
    return stocks

def read_live_prices():
    prices = {}
    # JSON files
    for pat in ["stock_prices*.json","live_prices*.json","prices*.json"]:
        for pf in glob.glob(os.path.join(DATA_DIR,pat)):
            try:
                with open(pf,"r") as f: d=json.load(f)
                if isinstance(d,dict):
                    for k,v in d.items():
                        t=k.replace(".NS","").replace(".BO","").upper().strip()
                        if isinstance(v,dict): prices[t]=v
                        elif isinstance(v,(int,float)): prices[t]={"price":v,"change":0}
            except: pass

    # CSV files from test_angel.py — engine_b_prices.csv has LTP, stock_analysis.csv has vol_ratio
    for pat in ["engine_b_prices*.csv","engine_*_prices*.csv","stock_analysis*.csv","stock_data*.csv","angel_*.csv"]:
        for pf in glob.glob(os.path.join(DATA_DIR,pat)):
            try:
                with open(pf,"r",encoding="utf-8-sig") as f:
                    for row in csv.DictReader(f):
                        ticker=""
                        for key in ["ticker","symbol","stock","name","tradingsymbol"]:
                            for k,v in row.items():
                                if k.lower().strip()==key: ticker=safe_str(v); break
                            if ticker: break
                        if not ticker: continue
                        ticker=ticker.replace(".NS","").replace(".BO","").replace("-EQ","").upper().strip()
                        if not ticker or ticker=="NAN": continue
                        price=0
                        for key in ["ltp","last_price","price","close","cmp"]:
                            for k,v in row.items():
                                if k.lower().strip()==key: price=safe_float(v); break
                            if price>0: break
                        change=0
                        for k,v in row.items():
                            if "change" in k.lower(): change=safe_float(v); break
                        vol_ratio=0
                        for k,v in row.items():
                            if "vol_ratio" in k.lower().replace(" ",""): vol_ratio=safe_float(v); break
                        if price>0:
                            prices[ticker]={"price":price,"change":round(change,2),"vol_ratio":round(vol_ratio,2)}
            except: pass

    # engine_b_stocks.json
    if os.path.exists(STOCKS_FILE):
        try:
            with open(STOCKS_FILE,"r") as f: d=json.load(f)
            if isinstance(d,dict):
                for ek in ["momentum","value","compounders","positions","watchlist"]:
                    if ek in d and isinstance(d[ek],list):
                        for item in d[ek]:
                            if isinstance(item,dict):
                                t=item.get("ticker",item.get("symbol","")).replace(".NS","").replace(".BO","").upper().strip()
                                p=safe_float(item.get("current_price",item.get("ltp",item.get("price",0))))
                                if t and p>0: prices[t]={"price":p,"change":safe_float(item.get("change",0)),"vol_ratio":safe_float(item.get("vol_ratio",0))}
        except: pass

    print(f"[OK] Prices: {len(prices)} tickers")

    # Merge vol_ratio from stock_analysis.csv separately (different structure)
    sa_file=os.path.join(DATA_DIR,"stock_analysis.csv")
    if os.path.exists(sa_file):
        try:
            with open(sa_file,"r",encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    t=safe_str(row.get("ticker","")).replace(".NS","").replace(".BO","").upper().strip()
                    if not t or t=="NAN": continue
                    vr=safe_float(row.get("vol_ratio",0))
                    if t in prices:
                        if vr>0: prices[t]["vol_ratio"]=round(vr,2)
                    else:
                        prices[t]={"price":0,"change":0,"vol_ratio":round(vr,2)}
            print(f"[OK] Vol ratios merged from stock_analysis.csv")
        except Exception as e:
            print(f"[WARN] stock_analysis.csv: {e}")

    return prices

# ── Scoring ──
def calc_conviction(s,vc,dc):
    sc=0; t=s["ticker"]
    if t in vc or t in dc: sc+=3
    if s["dvm_d"]>75: sc+=2
    if s["dvm_m"]>70: sc+=2
    if s["pio"]>=7: sc+=1
    if s["delivery"]>50: sc+=1
    sc+=1
    return min(sc,10)

def calc_vds(s,dbl=False):
    sc=0
    if s["pio"]>=9: sc+=3
    elif s["pio"]>=8: sc+=2
    elif s["pio"]>=7: sc+=1
    if s["roe"]>25: sc+=2
    elif s["roe"]>20: sc+=1
    if s["pe"]>0:
        if s["pe"]<12: sc+=3
        elif s["pe"]<18: sc+=2
        elif s["pe"]<25: sc+=1
    if dbl: sc+=2
    if s["pg"]>30: sc+=1
    if s["de"]<0.5: sc+=1
    return min(sc,15)

def calc_dna(s,dbl=False):
    sc=0
    if s["pg"]>30: sc+=3
    elif s["pg"]>15: sc+=2
    if s["rev_qoq"]>0: sc+=1
    if s["pio"]>=9: sc+=3
    elif s["pio"]>=8: sc+=2
    if s["roe"]>25: sc+=2
    if s["de"]<0.3: sc+=2
    elif s["de"]<0.5: sc+=1
    if s["peg"]>0:
        if s["peg"]<0.8: sc+=2
        elif s["peg"]<1.2: sc+=1
    if dbl: sc+=2
    if s["mcap"]>10000: sc+=1
    if s["mcap"]<50000: sc+=1
    return min(sc,20)

def calc_ai(s,ea_score):
    sc=0; pe=s.get("pe",0); peg=s.get("peg",0)
    if pe>0:
        if pe<12: sc+=5
        elif pe<18: sc+=4
        elif pe<25: sc+=3
        elif pe<35: sc+=1
    if peg>0:
        if peg<0.8: sc+=4
        elif peg<1.2: sc+=3
        elif peg<1.5: sc+=1
    if s.get("roe",0)>25: sc+=3
    elif s.get("roe",0)>15: sc+=2
    if s.get("pio",0)>=8: sc+=2
    elif s.get("pio",0)>=7: sc+=1
    if s.get("de",99)<0.5: sc+=1
    pg=s.get("pg",0)
    if pg>30: sc+=3
    elif pg>15: sc+=2
    elif pg>0: sc+=1
    rq=s.get("rev_qoq",0)
    if rq>10: sc+=2
    elif rq>0: sc+=1
    d=s.get("dvm_d",0); m=s.get("dvm_m",0)
    if d>55 and m>59: sc+=3
    elif d>45 and m>49: sc+=1
    if m>70: sc+=2
    if s.get("prom",0)>60: sc+=2
    elif s.get("prom",0)>50: sc+=1
    if s.get("fii",0)>15: sc+=1
    if s.get("inst",0)>15: sc+=1
    w=s.get("w52_pos",50)
    if 40<=w<=80: sc+=2
    elif 20<=w<=90: sc+=1
    if w>60: sc+=1
    if ea_score>62: sc+=5
    elif ea_score>52: sc+=3
    elif ea_score>40: sc+=1
    elif ea_score<=30: sc-=3
    return max(min(sc,40),-5)

def verdict(ai):
    if ai>=25: return "STRONG BUY"
    if ai>=18: return "BUY"
    if ai>=12: return "ACCUMULATE"
    if ai>=6: return "WAIT"
    if ai>=0: return "AVOID"
    return "DANGER"

def signal(s,eng):
    p=[]
    if eng=="momentum":
        if s.get("dvm_d",0)>70: p.append("DVM fortress")
        if s.get("dvm_m",0)>65: p.append("momentum surge")
        if s.get("vol_ratio",0)>=2: p.append("Volume unusual")
        if s.get("delivery",0)>=60: p.append("institutional accumulation")
        if s.get("dvm_d",0)<45 or s.get("dvm_m",0)<49: p.append("DVM RED — EXIT signal")
        if not p: p.append("Momentum steady")
    elif eng=="value":
        if s.get("pe",99)<12: p.append("PE extreme discount")
        elif s.get("pe",99)<18: p.append("Attractive PE")
        if s.get("delivery",0)>=60: p.append("high delivery confirms buying")
        if s.get("roe",0)>25: p.append("exceptional ROE")
        if s.get("rev_qoq",0)<-10: p.append("revenue declining — watch")
        if not p: p.append("Value opportunity")
    elif eng=="compounder":
        if s.get("peg",99)<0.8: p.append(f"PEG {s.get('peg',0)} extreme undervalue")
        if s.get("pg",0)>30: p.append("strong profit growth")
        if s.get("delivery",0)>=65: p.append(f"delivery {s.get('delivery',0)}% accumulation")
        if s.get("pio",0)>=9: p.append("perfect Piotroski")
        if s.get("pg",0)<=0: p.append("growth stalling — kill shot watch")
        if not p: p.append("Compounding candidate")
    return ". ".join(p)+"."

def sector_conc(stocks):
    sc={}
    for s in stocks:
        sec=s.get("sector","—")
        if sec and sec!="—": sc[sec]=sc.get(sec,0)+1
    total=max(len(stocks),1)
    return [{"name":k,"count":v,"pct":round(v/total*100,1),"overweight":v/total>=0.3}
            for k,v in sorted(sc.items(),key=lambda x:-x[1])]

# ── MAIN ──
def build():
    print("="*50+"\nGENERATING DASHBOARD v2\n"+"="*50)

    ea = read_engine_a()
    score = ea["score"]
    alloc = get_allocation(score)
    ea["allocation"] = alloc
    print(f"[OK] Engine A: {score}, Equity {alloc['equity']}%")

    mom = read_csv_stocks(find_csv_file("Mom"))
    c1 = read_csv_stocks(find_csv_file("C1"))
    c2 = read_csv_stocks(find_csv_file("C2"))
    d1 = read_csv_stocks(find_csv_file("D1"))
    d2 = read_csv_stocks(find_csv_file("D2"))
    print(f"[OK] CSVs: Mom={len(mom)} C1={len(c1)} C2={len(c2)} D1={len(d1)} D2={len(d2)}")

    vt=set(s["ticker"] for s in c1+c2)
    ct=set(s["ticker"] for s in d1+d2)
    mt=set(s["ticker"] for s in mom)

    prices = read_live_prices()

    def ap(s):
        t=s["ticker"]
        if t in prices:
            lp=prices[t]
            if isinstance(lp,dict):
                if lp.get("price",0)>0: s["price"]=round(lp["price"],2)
                s["change"]=round(lp.get("change",0),2)
                if lp.get("vol_ratio",0)>0: s["vol_ratio"]=round(lp["vol_ratio"],2)
        return s

    def gm(t,s1,n1,s2,n2):
        i1=t in s1; i2=t in s2
        if i1 and i2: return "ALL 3"
        if i1: return f"+{n1}"
        if i2: return f"+{n2}"
        return ""

    # Momentum
    momentum=[]
    for s in mom:
        t=s["ticker"]; multi=gm(t,vt,"VALUE",ct,"COMPOUNDER")
        conv=calc_conviction(s,vt,ct)
        if s["dvm_d"]<45 or s["dvm_m"]<49: stage="EXIT"
        elif s["dvm_d"]<55 or s["dvm_m"]<59: stage="GUARD"
        elif conv>=7: stage="STRIKE"
        elif conv>=4: stage="STALK"
        else: stage="WEAK"
        ai=calc_ai(s,score)
        if multi=="ALL 3": ai+=5
        elif multi: ai+=3
        s=ap(s)
        vv=5 if s["dvm_m"]>65 else 2 if s["dvm_m"]>59 else -2 if s["dvm_m"]>49 else -8
        vl="ACCELERATING" if vv>=5 else "COOLING" if vv<0 and vv>-5 else "CRASHING" if vv<=-5 else "STEADY"
        momentum.append({**s,"multi":multi,"stage":stage,"conviction":conv,
            "ai_score":min(ai,40),"verdict":verdict(ai),"signal":signal(s,"momentum"),
            "velocity":f"{'+' if vv>=0 else ''}{vv}","vel_label":vl})
    momentum.sort(key=lambda x:x["ai_score"],reverse=True)
    print(f"[OK] Momentum: {len(momentum)}")

    # Value
    vm={}
    for s in c1+c2:
        t=s["ticker"]
        if t not in vm: vm[t]={**s,"double_screener":False}
        else: vm[t]["double_screener"]=True
    value=[]
    for t,s in vm.items():
        multi=gm(t,mt,"MOMENTUM",ct,"COMPOUNDER")
        vds=calc_vds(s,s["double_screener"])
        ai=calc_ai(s,score)
        if multi=="ALL 3": ai+=5
        elif multi: ai+=3
        cpe=s.get("pe",0)
        s=ap(s)
        value.append({**s,"multi":multi,"vds":vds,"ai_score":min(ai,40),"verdict":verdict(ai),
            "signal":signal(s,"value"),
            "trap":{"rev":s.get("rev_qoq",0)>=-10,"prom":s.get("prom",0)>0},
            "pe_room":{"current":round(cpe,1),"p25":round(cpe*1.3,1) if cpe>0 else 0,
                       "p50":round(cpe*1.5,1) if cpe>0 else 0,"p75":round(cpe*1.8,1) if cpe>0 else 0}})
    value.sort(key=lambda x:x["ai_score"],reverse=True)
    print(f"[OK] Value: {len(value)}")

    # Compounders
    cm={}
    for s in d1+d2:
        t=s["ticker"]
        if t not in cm: cm[t]={**s,"double_screener":False}
        else: cm[t]["double_screener"]=True
    compounders=[]
    for t,s in cm.items():
        multi=gm(t,mt,"MOMENTUM",vt,"VALUE")
        dna=calc_dna(s,s["double_screener"])
        stars=5 if dna>=16 else 4 if dna>=13 else 3 if dna>=10 else 2 if dna>=7 else 1
        ai=calc_ai(s,score)
        if multi=="ALL 3": ai+=5
        elif multi: ai+=3
        peg=s.get("peg",0)
        pl="EXTREME" if 0<peg<0.8 else "UNDER" if peg<1.2 else "FAIR" if peg<=1.5 else "EXPENSIVE" if peg>0 else "FAIR"
        ets=2
        if s.get("pg",0)>25 and s.get("rev_qoq",0)>10: ets=4
        elif s.get("pg",0)>15 and s.get("rev_qoq",0)>0: ets=3
        elif s.get("pg",0)<=0: ets=1
        if s.get("pg",0)<-10: ets=0
        s=ap(s)
        compounders.append({**s,"multi":multi,"dna":dna,"stars":stars,
            "ai_score":min(ai,40),"verdict":verdict(ai),"signal":signal(s,"compounder"),
            "killshot":{"growth":s.get("pg",0)>0,"debt":s.get("de",99)<1.0},
            "peg_label":pl,"stage":"IDENTIFY","ets":ets})
    compounders.sort(key=lambda x:x["ai_score"],reverse=True)
    print(f"[OK] Compounders: {len(compounders)}")

    # Intelligence
    all3=mt&vt&ct; mv=(mt&vt)-all3; mc=(mt&ct)-all3; vc=(vt&ct)-all3
    intelligence={
        "momentum":{"strike":len([s for s in momentum if s["stage"]=="STRIKE"]),
            "stalk":len([s for s in momentum if s["stage"]=="STALK"]),
            "guard":len([s for s in momentum if s["stage"]=="GUARD"]),
            "weak":len([s for s in momentum if s["stage"]=="WEAK"]),
            "exit":len([s for s in momentum if s["stage"]=="EXIT"]),
            "strong_buy":len([s for s in momentum if s["verdict"]=="STRONG BUY"]),
            "avg_d":round(sum(s["dvm_d"] for s in momentum)/max(len(momentum),1),1),
            "avg_m":round(sum(s["dvm_m"] for s in momentum)/max(len(momentum),1),1),
            "sectors":sector_conc(momentum)},
        "value":{"deep":len([s for s in value if s["vds"]>=12]),
            "solid":len([s for s in value if 8<=s["vds"]<12]),
            "moderate":len([s for s in value if s["vds"]<8]),
            "strong_buy":len([s for s in value if s["verdict"]=="STRONG BUY"]),
            "traps":len([s for s in value if not s["trap"]["rev"] or not s["trap"]["prom"]]),
            "avg_pe":round(sum(s["pe"] for s in value if s["pe"]>0)/max(len([s for s in value if s["pe"]>0]),1),1),
            "sectors":sector_conc(value)},
        "compounder":{"elite":len([s for s in compounders if s["dna"]>=16]),
            "strong":len([s for s in compounders if 11<=s["dna"]<16]),
            "potential":len([s for s in compounders if s["dna"]<11]),
            "strong_buy":len([s for s in compounders if s["verdict"]=="STRONG BUY"]),
            "kills":len([s for s in compounders if not s["killshot"]["growth"] or not s["killshot"]["debt"]]),
            "avg_peg":round(sum(s["peg"] for s in compounders if s["peg"]>0)/max(len([s for s in compounders if s["peg"]>0]),1),2),
            "sectors":sector_conc(compounders)},
        "overlap":{"all3":sorted(list(all3)),"mom_val":sorted(list(mv)),
            "mom_comp":sorted(list(mc)),"val_comp":sorted(list(vc)),
            "only_mom":len(mt-vt-ct),"only_val":len(vt-mt-ct),"only_comp":len(ct-mt-vt)},
    }

    # Earnings
    seen=set(); earnings=[]
    for s in momentum+value+compounders:
        if s.get("earnings","—") not in ("—","","nan") and s["ticker"] not in seen:
            seen.add(s["ticker"]); earnings.append({"ticker":s["ticker"],"date":s["earnings"],"verdict":s["verdict"]})

    # Command
    all_stocks=momentum+value+compounders
    pp=[]
    for t in all3:
        m=next((s for s in all_stocks if s["ticker"]==t),None)
        if m: pp.append({"ticker":t,"ai_score":m["ai_score"],"verdict":m["verdict"],"price":m["price"]})
    pp.sort(key=lambda x:x["ai_score"],reverse=True)

    def eh(st):
        if not st: return 0
        return min(int((sum(s["ai_score"] for s in st)/len(st)/40)*100),100)

    command={"powerPicks":[p["ticker"] for p in pp[:10]],"all3Count":len(all3),
        "dualCount":len(mv)+len(mc)+len(vc),"totalPositions":len(set(s["ticker"] for s in all_stocks)),
        "engineHealth":{"b":eh(momentum),"c":eh(value),"d":eh(compounders),"e":90}}

    # Fortress
    fort={"rbi":"Neutral","duration":"MEDIUM","instrument":"Corporate Bond Funds",
        "gold_signal":"HOLD","gvix":0,"crude":0,"inr":0,
        "debt_alloc":int(ea["capital"]*alloc["debt"]/100),
        "gold_alloc":int(ea["capital"]*alloc["gold"]/100),
        "bharatbond":{"name":"BHARATBOND-APR30","nav":0,"ytm":0},
        "goldbees":{"name":"GOLDBEES","price":0,"change":0}}
    for mf in ["manual_inputs.json","engine_a_inputs.json"]:
        fp=os.path.join(DATA_DIR,mf)
        if os.path.exists(fp):
            try:
                with open(fp,"r") as f: macro=json.load(f)
                fort["gvix"]=safe_float(macro.get("gvix",macro.get("india_vix",0)))
                fort["crude"]=safe_float(macro.get("crude",macro.get("brent_crude",0)))
                fort["inr"]=safe_float(macro.get("inr",macro.get("inr_usd",macro.get("usdinr",0))))
                rbi=macro.get("rbi_stance",macro.get("rbi",""))
                if rbi:
                    fort["rbi"]=rbi
                    if "accom" in rbi.lower(): fort["duration"]="LONG"
                    elif "tight" in rbi.lower(): fort["duration"]="SHORT"
                gvix=fort["gvix"]; crude=fort["crude"]
                if gvix>25 or crude>100: fort["gold_signal"]="ACCUMULATE"
                elif gvix<15 and crude<60: fort["gold_signal"]="TRIM"
                print(f"[OK] Macro: VIX={fort['gvix']} Crude={fort['crude']}"); break
            except: pass

    # Read live_prices.csv + global_prices.csv (written by test_angel.py)
    lp_file=os.path.join(DATA_DIR,"live_prices.csv")
    if os.path.exists(lp_file):
        try:
            with open(lp_file,"r") as f:
                for row in csv.DictReader(f):
                    sym=row.get("symbol","").lower()
                    p=safe_float(row.get("price",0))
                    if "vix" in sym and p>0: fort["gvix"]=round(p,1)
            print(f"[OK] India VIX from live_prices.csv: {fort['gvix']}")
        except: pass

    gp_file=os.path.join(DATA_DIR,"global_prices.csv")
    if os.path.exists(gp_file):
        try:
            with open(gp_file,"r") as f:
                for row in csv.DictReader(f):
                    sym=row.get("symbol","").lower()
                    p=safe_float(row.get("price",0))
                    if "brent" in sym or "crude" in sym:
                        if p>0: fort["crude"]=round(p,1)
                    elif "inr" in sym:
                        if p>0: fort["inr"]=round(p,2)
            # Recalculate gold signal with fresh data
            if fort["gvix"]>25 or fort["crude"]>100: fort["gold_signal"]="ACCUMULATE"
            elif fort["gvix"]<15 and fort["crude"]<60: fort["gold_signal"]="TRIM"
            print(f"[OK] Global: Crude={fort['crude']} INR={fort['inr']}")
        except: pass

    now=datetime.now().strftime("%d %b %Y, %I:%M %p")

    # ── Indian Markets (from live_prices.csv) ──
    indian_markets = {}
    lp2 = os.path.join(DATA_DIR,"live_prices.csv")
    if os.path.exists(lp2):
        try:
            with open(lp2,"r",encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    sym = row.get("symbol","").strip()
                    p = safe_float(row.get("price",0))
                    if p > 0:
                        indian_markets[sym] = round(p,2)
        except: pass
    print(f"[OK] Indian Markets: {len(indian_markets)} indices")

    # ── Global Markets (from global_prices.csv) ──
    global_markets = {}
    gp2 = os.path.join(DATA_DIR,"global_prices.csv")
    if os.path.exists(gp2):
        try:
            with open(gp2,"r",encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    sym = row.get("symbol","").strip()
                    p = safe_float(row.get("price",0))
                    if p > 0:
                        global_markets[sym] = round(p,2)
        except: pass
    print(f"[OK] Global Markets: {len(global_markets)} items")

    # ── Manual Inputs ──
    manual_inputs = {}
    mi_file = os.path.join(DATA_DIR,"manual_inputs.json")
    if os.path.exists(mi_file):
        try:
            with open(mi_file,"r") as f: manual_inputs = json.load(f)
            print(f"[OK] Manual inputs loaded: {list(manual_inputs.keys())}")
        except: pass

    # ── P&L from positions ──
    pnl = {"total_invested":0,"current_value":0,"pnl":0,"pnl_pct":0,
           "cash_available":0,"positions":0,
           "b_deployed":0,"b_budget":0,"c_deployed":0,"c_budget":0,
           "d_deployed":0,"d_budget":0}
    positions_display = {"momentum":[],"value":[],"compounders":[]}
    tax = {"stcg_rate":20,"ltcg_rate":12.5,"ltcg_exemption":125000,
           "stcg_count":0,"ltcg_count":0,"unrealized_stcg":0,"unrealized_ltcg":0}
    if os.path.exists(STOCKS_FILE):
        try:
            with open(STOCKS_FILE,"r") as f: pos_data = json.load(f)
            # Read capital from positions file (saved by dashboard)
            if "capital" in pos_data:
                ea["capital"] = int(safe_float(pos_data["capital"]))
            elif "_capital" in pos_data:
                ea["capital"] = int(safe_float(pos_data["_capital"]))
            cap = ea.get("capital",500000)
            eq_amt = cap * alloc["equity"] / 100
            pnl["b_budget"] = round(eq_amt * 0.3, 2)
            pnl["c_budget"] = round(eq_amt * 0.3, 2)
            pnl["d_budget"] = round(eq_amt * 0.4, 2)

            total_inv = 0; total_cur = 0; pos_count = 0
            now_dt = datetime.now()
            ltcg_cutoff = now_dt - timedelta(days=365)
            stcg_gain = 0; ltcg_gain = 0; stcg_cnt = 0; ltcg_cnt = 0

            for eng_key in ["momentum","value","compounders","positions"]:
                if eng_key not in pos_data: continue
                positions_list = pos_data[eng_key]
                if not isinstance(positions_list, list): continue
                for p in positions_list:
                    if not isinstance(p, dict): continue
                    qty = safe_float(p.get("qty", p.get("quantity", 1)))
                    buy = safe_float(p.get("buy_price", p.get("entry_price", p.get("avg_price", 0))))
                    cur = safe_float(p.get("current_price", p.get("ltp", p.get("price", 0))))
                    t = p.get("ticker", p.get("symbol", "")).replace(".NS","").replace(".BO","").upper().strip()

                    # Try to get current price from live prices
                    if cur == 0 and t in prices:
                        cur = safe_float(prices[t].get("price", 0))

                    if buy > 0 and qty > 0:
                        inv = buy * qty
                        val = cur * qty if cur > 0 else inv
                        total_inv += inv
                        total_cur += val
                        pos_count += 1
                        gain = round(val - inv, 2)
                        gain_pct = round(((val - inv) / inv * 100) if inv > 0 else 0, 2)

                        # STCG vs LTCG
                        buy_date_str = p.get("buy_date","")
                        is_ltcg = False
                        if buy_date_str:
                            try:
                                bd = datetime.strptime(str(buy_date_str).strip()[:10], "%Y-%m-%d")
                                if bd < ltcg_cutoff: is_ltcg = True
                            except: pass
                        if is_ltcg:
                            ltcg_gain += gain; ltcg_cnt += 1
                        else:
                            stcg_gain += gain; stcg_cnt += 1

                        # Track per-engine deployment
                        eng = p.get("engine","").lower()
                        disp_eng = eng_key
                        if eng_key == "momentum" or eng in ("b","momentum"):
                            pnl["b_deployed"] += round(inv, 2); disp_eng = "momentum"
                        elif eng_key == "value" or eng in ("c","value"):
                            pnl["c_deployed"] += round(inv, 2); disp_eng = "value"
                        elif eng_key == "compounders" or eng in ("d","compounder","compounders"):
                            pnl["d_deployed"] += round(inv, 2); disp_eng = "compounders"

                        # Collect for display
                        if disp_eng in positions_display:
                            positions_display[disp_eng].append({
                                "ticker":t,"qty":int(qty),"buy_price":round(buy,2),
                                "current_price":round(cur,2),"pnl":gain,"pnl_pct":gain_pct,
                                "buy_date":buy_date_str,"is_ltcg":is_ltcg
                            })

            pnl["total_invested"] = round(total_inv, 2)
            pnl["current_value"] = round(total_cur, 2)
            pnl["pnl"] = round(total_cur - total_inv, 2)
            pnl["pnl_pct"] = round(((total_cur - total_inv) / total_inv * 100) if total_inv > 0 else 0, 2)
            pnl["cash_available"] = round(cap - total_inv, 2)
            pnl["positions"] = pos_count
            tax["stcg_count"] = stcg_cnt; tax["ltcg_count"] = ltcg_cnt
            tax["unrealized_stcg"] = round(stcg_gain, 2); tax["unrealized_ltcg"] = round(ltcg_gain, 2)
            print(f"[OK] P&L: Invested={pnl['total_invested']} Current={pnl['current_value']} P&L={pnl['pnl']}")
            print(f"[OK] Tax: STCG={stcg_cnt} pos +{stcg_gain} | LTCG={ltcg_cnt} pos +{ltcg_gain}")
            print(f"[OK] Positions: B={len(positions_display['momentum'])} C={len(positions_display['value'])} D={len(positions_display['compounders'])}")
        except Exception as e:
            print(f"[WARN] P&L calc: {e}")

    # ── Red Flag & PE Bubble checks ──
    nifty_pe = safe_float(manual_inputs.get("nifty_pe", 0))
    red_flag = False
    pe_bubble = False

    # Red Flag: Trend<=3 AND Vol<=2 AND (Flows<=3 OR FII<-15000)
    comps = {c["name"]:c["score"] for c in ea.get("components",[])}
    trend_score = comps.get("Trend",0)
    vol_score = comps.get("Volatility",0)
    flow_score = comps.get("Flows",0)
    fii_val = safe_float(manual_inputs.get("fii", manual_inputs.get("fii_30d",0)))
    if trend_score <= 3 and vol_score <= 2 and (flow_score <= 3 or fii_val < -15000):
        red_flag = True

    # PE Bubble: Nifty PE > 26
    if nifty_pe > 26:
        pe_bubble = True

    safety = {"red_flag": red_flag, "pe_bubble": pe_bubble, "nifty_pe": nifty_pe}

    dashboard={"engineA":ea,"momentum":momentum[:30],"value":value[:30],"compounders":compounders[:30],
        "fortress":fort,"command":command,"intelligence":intelligence,
        "upcomingEarnings":earnings[:20],
        "indianMarkets":indian_markets,"globalMarkets":global_markets,
        "manualInputs":manual_inputs,"pnl":pnl,"safety":safety,
        "positions":positions_display,"tax":tax,
        "lastUpdate":now,"version":"3.1"}

    os.makedirs(DOCS_DIR,exist_ok=True)
    with open(OUTPUT_FILE,"w") as f: json.dump(dashboard,f,indent=2)

    print(f"\n{'='*50}\nDASHBOARD v2 DONE\n{'='*50}")
    print(f"  Mom={len(momentum)} Val={len(value)} Comp={len(compounders)}")
    print(f"  ALL 3: {len(all3)} — {sorted(all3)}")
    print(f"  Earnings: {len(earnings)}")
    print(f"  Output: {OUTPUT_FILE} | {now}")

if __name__=="__main__": build()
