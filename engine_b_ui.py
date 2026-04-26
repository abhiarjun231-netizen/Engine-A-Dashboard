"""
engine_b_ui.py - Engine B: The Momentum Hunter
"Follow the smart money. Exit before they do."
"""
import streamlit as st
import json
from datetime import datetime, date
from utils import (
    load_stocks_json, save_stocks_to_github, load_stock_prices,
    trigger_workflow, parse_trendlyne_csv, parse_trendlyne_text,
    load_screener_from_github, get_engine_a_score,
    fmt, fmt_pnl, fmt_pct, days_held,
    render_section_title, render_info_card, render_data_card,
    render_stat_row, render_hero_number, render_badge,
    render_stage_badge, render_engine_gate,
    calculate_trailing_stop_b, get_profit_stage_b,
)

MAX_POSITIONS = 10
MAX_PCT = 10

def conviction_b(stock, c_tickers=None, d_tickers=None):
    score = 0
    t = stock.get("ticker", "")
    d = float(stock.get("durability", 0) or 0)
    m = float(stock.get("momentum", 0) or 0)
    p = float(stock.get("piotroski", 0) or 0)
    if c_tickers and t in c_tickers: score += 3
    elif d_tickers and t in d_tickers: score += 3
    if d > 75: score += 2
    elif d > 65: score += 1
    if m > 70: score += 2
    elif m > 64: score += 1
    if p >= 8: score += 1
    score += 1
    return min(score, 10)

def dvm_status(d, m):
    dz = "GREEN" if d > 55 else ("GREY" if d >= 45 else "RED")
    mz = "GREEN" if m > 59 else ("GREY" if m >= 49 else "RED")
    dc = "#16a34a" if dz == "GREEN" else ("#d97706" if dz == "GREY" else "#dc2626")
    mc = "#16a34a" if mz == "GREEN" else ("#d97706" if mz == "GREY" else "#dc2626")
    if dz == "GREEN" and mz == "GREEN": act = "RIDE"
    elif dz == "GREEN" and mz == "GREY": act = "GUARD"
    elif dz == "GREY" and mz == "GREEN": act = "GUARD"
    elif dz == "RED" or mz == "RED": act = "EXIT"
    else: act = "EXIT"
    return dz, mz, dc, mc, act

def show_engine_b():
    data = load_stocks_json()
    prices = load_stock_prices()
    sd = get_engine_a_score()
    ea = int(sd["raw_score"]) if sd else None
    pos = data.get("engine_b", [])
    wl = data.get("engine_b_watchlist", [])
    closed = data.get("engine_b_closed", [])
    cap = float(data.get("_capital", 100000))
    eq_pct = int(sd.get("equity_pct", 55)) if sd else 55
    b_cap = cap * eq_pct / 100 * 30 / 100

    # HEADER
    st.markdown(
        "<div style='text-align:center;margin-bottom:4px;'>"
        "<div style='font-size:11px;color:#94a3b8;text-transform:uppercase;"
        "letter-spacing:2px;font-weight:600;'>Engine B</div>"
        "<div style='font-size:20px;font-weight:800;color:#1e293b;"
        "font-family:DM Sans,sans-serif;'>The Momentum Hunter</div>"
        "<div style='font-size:11px;color:#94a3b8;font-style:italic;'>"
        "Follow the smart money. Exit before they do.</div></div>",
        unsafe_allow_html=True)

    render_engine_gate(ea)

    if st.button("Refresh Data", type="primary", use_container_width=True, key="ref_b"):
        with st.spinner("Fetching..."):
            ok, msg = trigger_workflow()
        st.success(msg) if ok else st.error(msg)

    # SUMMARY
    render_section_title("Portfolio Summary")
    ti = sum(float(s.get("entry",0))*int(s.get("qty",0)) for s in pos)
    tc = sum(prices.get(s.get("ticker",""),float(s.get("entry",0)))*int(s.get("qty",0)) for s in pos)
    tp = tc - ti
    ps, pc = fmt_pnl(tp)
    pp, _ = fmt_pct((tp/ti*100) if ti>0 else 0)
    c1,c2,c3 = st.columns(3)
    with c1: render_hero_number("Budget", f"₹{b_cap:,.0f}", "#2563eb")
    with c2: render_hero_number("Deployed", f"₹{ti:,.0f}", "#1e293b", f"{len(pos)}/{MAX_POSITIONS}")
    with c3: render_hero_number("P&L", f"₹{ps}", pc, pp)

    # POSITIONS
    render_section_title(f"Active Positions ({len(pos)})")
    if not pos:
        render_info_card("No positions. Upload DVM screener CSV to scout stocks.")
    else:
        for i, p in enumerate(pos):
            tk = p.get("ticker",""); nm = p.get("name",tk)
            en = float(p.get("entry",0)); qt = int(p.get("qty",0))
            bd = p.get("buy_date",""); pk = float(p.get("peak",en))
            dr = float(p.get("durability",0) or 0); mo = float(p.get("momentum",0) or 0)
            pm = float(p.get("prev_momentum",mo) or mo)
            cp = prices.get(tk, en)
            if cp > pk: pk = cp; data["engine_b"][i]["peak"] = pk
            pnl = (cp-en)*qt; pnlp = ((cp-en)/en*100) if en>0 else 0
            hd = days_held(bd); stg = get_profit_stage_b(pnlp)
            stp = calculate_trailing_stop_b(en, pk, pnlp)
            sd2 = ((cp-stp)/cp*100) if cp>0 else 0
            dz,mz,dc2,mc2,act = dvm_status(dr, mo)
            vel = mo - pm
            vc = "#16a34a" if vel>0 else ("#dc2626" if vel<-5 else "#d97706")
            ps2,pc2 = fmt_pnl(pnl); pp2,_ = fmt_pct(pnlp)
            bc = "#16a34a" if act=="RIDE" else ("#d97706" if act=="GUARD" else "#dc2626")
            st.markdown(
                f"<div class='data-card' style='border-left:4px solid {bc};'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>"
                f"<div style='font-weight:700;color:#1e293b;font-size:14px;'>{nm}</div>"
                f"<div>{render_stage_badge(stg)}</div></div>"
                f"<div style='display:flex;justify-content:space-between;margin-bottom:6px;'>"
                f"<div style='font-size:12px;color:#64748b;'>₹{en:,.0f} → ₹{cp:,.0f}</div>"
                f"<div style='font-size:13px;font-weight:700;color:{pc2};'>{pp2} (₹{ps2})</div></div>"
                f"<div style='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px;font-size:10px;color:#94a3b8;'>"
                f"<span>Qty: {qt}</span><span>Days: {hd}</span>"
                f"<span>Stop: ₹{stp:,.0f} ({sd2:.1f}%)</span><span>Peak: ₹{pk:,.0f}</span></div>"
                f"<div style='display:flex;gap:12px;font-size:11px;'>"
                f"<span>D: <b style='color:{dc2}'>{dr:.0f}</b></span>"
                f"<span>M: <b style='color:{mc2}'>{mo:.0f}</b></span>"
                f"<span>Vel: <b style='color:{vc}'>{vel:+.0f}</b></span>"
                f"<span>{render_stage_badge(act)}</span></div></div>",
                unsafe_allow_html=True)

            with st.expander(f"Sell {nm}", expanded=False):
                er = ["DVM Decay","Velocity Crash","Hard Stop","Engine A Gate","Manual","Profit Taking"]
                r = st.selectbox("Reason", er, key=f"sr_b_{i}")
                if st.button(f"Confirm Sell", type="primary", use_container_width=True, key=f"sb_{i}"):
                    data["engine_b_closed"].append({
                        "name":nm,"ticker":tk,"entry":en,"exit_price":cp,"qty":qt,
                        "pnl":round(pnl,2),"pnl_pct":round(pnlp,1),"buy_date":bd,
                        "exit_date":date.today().strftime("%Y-%m-%d"),"days_held":hd,"exit_reason":r})
                    data["engine_b"].pop(i)
                    ok,msg = save_stocks_to_github(data, f"Sell {nm} Engine B")
                    if ok: st.success(f"Sold {nm}"); st.rerun()
                    else: st.error(msg)

    # POSITION SIZER
    render_section_title("Position Sizer")
    with st.expander("Calculate", expanded=False):
        av = b_cap - ti; mx = b_cap * MAX_PCT / 100
        st.markdown(f"**Available:** ₹{av:,.0f} | **Max/stock:** ₹{mx:,.0f}")
        pr = st.number_input("Price ₹", value=100.0, key="ps_b", min_value=1.0, format="%.2f")
        if pr>0:
            mq = int(min(av,mx)/pr)
            st.markdown(f"**Suggested:** {mq} shares = ₹{mq*pr:,.0f}")

    # WATCHLIST
    render_section_title("Screener Watchlist")
    st.caption("Trendlyne: Durability > 55 AND Momentum > 59")
    st.markdown(
        "<div style='font-size:12px;color:#64748b;line-height:1.6;'>"
        "Upload DVM screener CSV (name starting with <code>Mom</code>) "
        "to GitHub → <code>data</code> folder → press Load</div>",
        unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        load_gh = st.button("Load from GitHub", type="primary", use_container_width=True, key="ghb_b")
    with c2:
        show_paste = st.button("Paste CSV Instead", use_container_width=True, key="paste_toggle_b")
    if load_gh:
        with st.spinner("Fetching from GitHub..."):
            stks, err = load_screener_from_github("Mom")
            if err:
                st.error(err)
            elif stks:
                for s in stks: s["upload_date"] = date.today().strftime("%Y-%m-%d")
                st.session_state["_pending_b"] = stks
    if show_paste or st.session_state.get("_show_paste_b"):
        st.session_state["_show_paste_b"] = True
        txt = st.text_area("Paste CSV content", height=120, key="ptxt_b", placeholder="Paste CSV text here...")
        if txt and txt.strip():
            stks, err = parse_trendlyne_text(txt)
            if err: st.error(err)
            elif stks:
                for s in stks: s["upload_date"] = date.today().strftime("%Y-%m-%d")
                st.session_state["_pending_b"] = stks
    pending = st.session_state.get("_pending_b")
    if pending:
        st.success(f"Found {len(pending)} stocks — press Save to confirm")
        if st.button("Save Watchlist", type="primary", use_container_width=True, key="swl_b"):
            data["engine_b_watchlist"] = pending
            data["_b_watchlist_date"] = date.today().strftime("%Y-%m-%d")
            ok,msg = save_stocks_to_github(data, "Update Engine B watchlist")
            if ok:
                st.session_state.pop("_pending_b", None)
                st.success("Saved!"); trigger_workflow(); st.rerun()
            else: st.error(msg)

    if wl:
        wd = data.get("_b_watchlist_date","")
        st.markdown(f"<div style='font-size:11px;color:#94a3b8;margin-bottom:8px;'>"
                   f"Uploaded: {wd} · {len(wl)} stocks</div>", unsafe_allow_html=True)
        ct = set(s.get("ticker","") for s in data.get("engine_c",[])+data.get("engine_c_watchlist",[]))
        dt = set(s.get("ticker","") for s in data.get("engine_d",[])+data.get("engine_d_watchlist",[]))
        ht = set(s.get("ticker","") for s in pos)
        for j,s in enumerate(wl):
            nm=s.get("name",""); tk=s.get("ticker",""); lp=s.get("ltp",0) or 0
            cp2=prices.get(tk,lp); opp=((cp2-lp)/lp*100) if lp>0 and cp2>0 else 0
            os2,oc=fmt_pct(opp); cv=conviction_b(s,ct,dt)
            vd="STRIKE NOW" if cv>=7 else ("STALK MORE" if cv>=4 else "WEAK")
            cc="#16a34a" if cv>=7 else ("#2563eb" if cv>=4 else "#94a3b8")
            ah = tk in ht
            st.markdown(
                f"<div class='data-card'>"
                f"<div style='display:flex;justify-content:space-between;margin-bottom:6px;'>"
                f"<div style='font-weight:700;color:#1e293b;font-size:13px;'>{nm}</div>"
                f"<div style='font-size:12px;font-weight:700;color:{cc};'>Conv: {cv}/10</div></div>"
                f"<div style='display:flex;gap:8px;flex-wrap:wrap;font-size:11px;color:#64748b;margin-bottom:4px;'>"
                f"<span>₹{cp2:,.0f}</span><span style='color:{oc}'>{os2}</span>"
                f"<span>ROE:{fmt(s.get('roe'),0)}</span><span>PE:{fmt(s.get('pe'),0)}</span>"
                f"<span>Pio:{fmt(s.get('piotroski'),0)}</span></div>"
                f"<div>{render_stage_badge(vd)}"
                f"{'  '+render_badge('HELD','#94a3b8') if ah else ''}</div></div>",
                unsafe_allow_html=True)
            if not ah and ea and ea>30 and len(pos)<MAX_POSITIONS:
                with st.expander(f"Buy {nm}", expanded=False):
                    d_in=st.number_input("Durability",value=0.0,key=f"db_{j}",max_value=100.0)
                    m_in=st.number_input("Momentum",value=0.0,key=f"mb_{j}",max_value=100.0)
                    if d_in<=55 or m_in<=59: st.warning("Below entry threshold.")
                    bp=st.number_input("Price ₹",value=float(cp2),key=f"bp_b_{j}",format="%.2f")
                    mx2=min(b_cap-ti, b_cap*MAX_PCT/100)
                    sq=int(mx2/bp) if bp>0 else 0
                    bq=st.number_input("Qty",value=max(sq,1),min_value=1,key=f"bq_b_{j}")
                    st.markdown(f"**₹{bp*bq:,.0f}**")
                    if st.button(f"Confirm Buy",type="primary",use_container_width=True,key=f"cb_{j}"):
                        data["engine_b"].append({
                            "name":nm,"ticker":tk,"entry":bp,"qty":bq,
                            "buy_date":date.today().strftime("%Y-%m-%d"),"peak":bp,
                            "durability":d_in,"momentum":m_in,"prev_momentum":m_in,
                            "conviction":cv,"sector":s.get("sector","")})
                        ok,msg=save_stocks_to_github(data,f"Buy {nm} Engine B")
                        if ok: st.success(f"Bought {nm}"); trigger_workflow(); st.rerun()
                        else: st.error(msg)
        if st.button("Clear Watchlist", key="cwl_b"):
            data["engine_b_watchlist"]=[]; data["_b_watchlist_date"]=""
            ok,msg=save_stocks_to_github(data,"Clear Engine B watchlist")
            if ok: st.success("Cleared"); st.rerun()
    else:
        render_info_card("No watchlist. Upload DVM screener CSV to start.")

    # UPDATE DVM
    if pos:
        render_section_title("Update DVM Scores")
        with st.expander("Update D & M Scores", expanded=False):
            st.caption("From Trendlyne stock pages")
            ch=False
            for i,p in enumerate(pos):
                nm=p.get("name",""); cd=float(p.get("durability",0) or 0); cm=float(p.get("momentum",0) or 0)
                st.markdown(f"**{nm}** (D={cd:.0f}, M={cm:.0f})")
                c1,c2=st.columns(2)
                with c1: nd=st.number_input("D",value=cd,key=f"ud_{i}",max_value=100.0)
                with c2: nm2=st.number_input("M",value=cm,key=f"um_{i}",max_value=100.0)
                if nd!=cd or nm2!=cm:
                    data["engine_b"][i]["prev_momentum"]=cm
                    data["engine_b"][i]["durability"]=nd
                    data["engine_b"][i]["momentum"]=nm2; ch=True
            if ch and st.button("Save DVM",type="primary",use_container_width=True,key="sdvm"):
                ok,msg=save_stocks_to_github(data,"Update DVM scores")
                if ok: st.success("Updated!"); st.rerun()
                else: st.error(msg)

    # TRADE LOG
    render_section_title("Trade Log")
    if closed:
        ws=[t for t in closed if float(t.get("pnl",0))>0]
        ls=[t for t in closed if float(t.get("pnl",0))<=0]
        tr=sum(float(t.get("pnl",0)) for t in closed)
        ts2,tc2=fmt_pnl(tr); wr=(len(ws)/len(closed)*100) if closed else 0
        render_data_card(
            render_stat_row("Trades",str(len(closed)))+
            render_stat_row("Win/Loss",f"{len(ws)}/{len(ls)}")+
            render_stat_row("Win Rate",f"{wr:.0f}%","#16a34a" if wr>=50 else "#dc2626")+
            render_stat_row("Total P&L",f"₹{ts2}",tc2))
    else:
        render_info_card("No trades yet.")
