"""
engine_c_ui.py - Engine C: The Value Warriors
"Buy what the market ignores. Sell when the market wakes up."
Screener 1 (4-filter) + Screener 2 (6-filter)
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
    calculate_trailing_stop_c, get_profit_stage_c,
    mcap_tag, render_mini_bar, render_52w_position,
    sector_summary, render_check,
    smart_signal_c,
    ai_analyst,
    render_earnings_info, earnings_alert,
)

MAX_POSITIONS = 15
MAX_PCT = 10

def value_depth_score(stock, is_double=False):
    score = 0
    p = float(stock.get("piotroski",0) or 0)
    roe = float(stock.get("roe",0) or 0)
    pe = float(stock.get("pe",999) or 999)
    de = float(stock.get("de",99) or 99)
    pg = float(stock.get("profit_growth",0) or 0)
    # Quality (max 6)
    if p >= 9: score += 3
    elif p >= 8: score += 2
    elif p >= 7: score += 1
    if roe > 25: score += 2
    elif roe > 20: score += 1
    # Value (max 5)
    if pe < 12: score += 3
    elif pe < 18: score += 2
    elif pe < 25: score += 1
    if is_double: score += 2
    # Trend (max 4)
    if pg and pg > 30: score += 1
    if de < 0.5: score += 1
    return min(score, 15)

def pe_expansion_pct(entry_pe, current_pe):
    if not entry_pe or entry_pe <= 0 or not current_pe: return 0
    return ((current_pe - entry_pe) / entry_pe) * 100

def show_engine_c():
    data = load_stocks_json()
    prices = load_stock_prices()
    sd = get_engine_a_score()
    ea = int(sd["raw_score"]) if sd else None
    pos = data.get("engine_c", [])
    wl = data.get("engine_c_watchlist", [])
    closed = data.get("engine_c_closed", [])
    cap = float(data.get("_capital", 100000))
    eq_pct = int(sd.get("equity_pct", 55)) if sd else 55
    c_cap = cap * eq_pct / 100 * 30 / 100

    # HEADER
    st.markdown(
        "<div style='text-align:center;margin-bottom:4px;'>"
        "<div style='font-size:11px;color:#94a3b8;text-transform:uppercase;"
        "letter-spacing:2px;font-weight:600;'>Engine C</div>"
        "<div style='font-size:20px;font-weight:800;color:#1e293b;"
        "font-family:DM Sans,sans-serif;'>The Value Warriors</div>"
        "<div style='font-size:11px;color:#94a3b8;font-style:italic;'>"
        "Buy what the market ignores. Sell when the market wakes up.</div></div>",
        unsafe_allow_html=True)

    render_engine_gate(ea)

    if st.button("Refresh Data", type="primary", use_container_width=True, key="ref_c"):
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
    with c1: render_hero_number("Budget", f"₹{c_cap:,.0f}", "#2563eb")
    with c2: render_hero_number("Deployed", f"₹{ti:,.0f}", "#1e293b", f"{len(pos)}/{MAX_POSITIONS}")
    with c3: render_hero_number("P&L", f"₹{ps}", pc, pp)

    # POSITIONS
    render_section_title(f"Active Positions ({len(pos)})")
    if not pos:
        render_info_card("No positions. Upload Screener 1/2 CSVs to discover stocks.")
    else:
        for i, p in enumerate(pos):
            tk = p.get("ticker",""); nm = p.get("name",tk)
            en = float(p.get("entry",0)); qt = int(p.get("qty",0))
            bd = p.get("buy_date",""); pk = float(p.get("peak",en))
            entry_pe = float(p.get("entry_pe",0) or 0)
            cur_pe = float(p.get("current_pe", entry_pe) or entry_pe)
            vds = int(p.get("value_depth_score",0) or 0)

            cp = prices.get(tk, en)
            if cp > pk: pk = cp; data["engine_c"][i]["peak"] = pk
            pnl = (cp-en)*qt; pnlp = ((cp-en)/en*100) if en>0 else 0
            hd = days_held(bd)
            stg = get_profit_stage_c(pnlp)
            stp = calculate_trailing_stop_c(en, pk, pnlp)
            sd2 = ((cp-stp)/cp*100) if cp>0 else 0

            # PE expansion
            pe_exp = pe_expansion_pct(entry_pe, cur_pe)
            pe_signal = ""
            if pe_exp >= 80: pe_signal = "FULL HARVEST"
            elif pe_exp >= 50: pe_signal = "MEDIUM HARVEST"
            elif pe_exp >= 30: pe_signal = "LIGHT HARVEST"

            # Time decay
            time_flag = ""
            if hd >= 365 and pnlp < 10: time_flag = "TIME DECAY"
            elif hd >= 270 and pnlp < 5: time_flag = "TIME DECAY"
            elif hd >= 180 and pnlp < 5: time_flag = "REASSESS"

            ps2,pc2 = fmt_pnl(pnl); pp2,_ = fmt_pct(pnlp)
            bc = "#dc2626" if time_flag == "TIME DECAY" else ("#d97706" if time_flag else "#16a34a")

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
                f"<span>Stop: ₹{stp:,.0f} ({sd2:.1f}%)</span>"
                f"<span>VDS: {vds}/15</span></div>"
                f"<div style='display:flex;gap:8px;font-size:11px;flex-wrap:wrap;'>"
                f"<span>PE: {entry_pe:.0f} → {cur_pe:.0f} ({pe_exp:+.0f}%)</span>"
                f"{'  '+render_stage_badge(pe_signal) if pe_signal else ''}"
                f"{'  '+render_badge(time_flag,'#fecaca','#dc2626') if time_flag else ''}"
                f"</div></div>",
                unsafe_allow_html=True)

            with st.expander(f"Manage {nm}", expanded=False):
                # Update PE
                new_pe = st.number_input("Current PE", value=cur_pe, key=f"pe_c_{i}", format="%.1f")
                if new_pe != cur_pe:
                    data["engine_c"][i]["current_pe"] = new_pe
                # Sell
                er = ["Fundamental Break","Trailing Stop","PE Expansion Harvest",
                      "Time Decay","Engine A Gate","30-Day Clock","Manual"]
                r = st.selectbox("Exit reason", er, key=f"sr_c_{i}")
                if st.button(f"Sell {nm}", type="primary", use_container_width=True, key=f"sc_{i}"):
                    data["engine_c_closed"].append({
                        "name":nm,"ticker":tk,"entry":en,"exit_price":cp,"qty":qt,
                        "pnl":round(pnl,2),"pnl_pct":round(pnlp,1),"buy_date":bd,
                        "exit_date":date.today().strftime("%Y-%m-%d"),"days_held":hd,
                        "exit_reason":r,"entry_pe":entry_pe,"exit_pe":cur_pe,
                        "pe_expansion":round(pe_exp,1)})
                    data["engine_c"].pop(i)
                    ok,msg = save_stocks_to_github(data, f"Sell {nm} Engine C")
                    if ok: st.success(f"Sold {nm}"); st.rerun()
                    else: st.error(msg)

    # POSITION SIZER
    render_section_title("Position Sizer")
    with st.expander("Calculate", expanded=False):
        av = c_cap - ti; mx = c_cap * MAX_PCT / 100
        st.markdown(
            f"<div style='font-size:13px;color:#1e293b;font-weight:600;margin-bottom:8px;'>"
            f"Available: <span style='color:#059669;'>₹{av:,.0f}</span> | "
            f"Max/stock: <span style='color:#2563eb;'>₹{mx:,.0f}</span></div>",
            unsafe_allow_html=True)
        pr = st.number_input("Price ₹", value=100.0, key="ps_c", min_value=1.0, format="%.2f")
        if pr>0:
            mq = int(min(av,mx)/pr)
            st.markdown(
                f"<div style='font-size:14px;color:#1e293b;font-weight:700;margin-top:8px;'>"
                f"Suggested: <span style='color:#059669;'>{mq} shares</span> = "
                f"<span style='color:#2563eb;'>₹{mq*pr:,.0f}</span></div>",
                unsafe_allow_html=True)

    # WATCHLIST
    render_section_title("Screener Watchlist")
    st.caption("S1: ROE>15, PE<25, >200DMA, Pio>6 · S2: + D/E<1, PG>15%")
    st.markdown(
        "<div style='font-size:12px;color:#64748b;line-height:1.6;'>"
        "Upload CSVs (names starting with <code>C1</code> + <code>C2</code>) "
        "to GitHub → <code>data</code> folder → press Load</div>",
        unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        load_gh = st.button("Load from GitHub", type="primary", use_container_width=True, key="ghb_c")
    with c2:
        show_paste = st.button("Paste CSV Instead", use_container_width=True, key="paste_toggle_c")

    def _process_c(all_stocks, s1_tickers, s2_tickers):
        seen = {}
        for s in all_stocks:
            tk = s.get("ticker","")
            if tk in seen:
                seen[tk]["screener"] = "DOUBLE"
            else:
                is_dbl = tk in s1_tickers and tk in s2_tickers
                if is_dbl: s["screener"] = "DOUBLE"
                seen[tk] = s
        deduped = list(seen.values())
        for s in deduped:
            s["upload_date"] = date.today().strftime("%Y-%m-%d")
            s["is_double"] = s.get("screener") == "DOUBLE"
            s["vds"] = value_depth_score(s, s.get("is_double", False))
        deduped.sort(key=lambda x: x.get("vds",0), reverse=True)
        return deduped

    if load_gh:
        with st.spinner("Fetching from GitHub..."):
            all_stocks = []; s1_tickers = set(); s2_tickers = set()
            st1, err1 = load_screener_from_github("C1")
            if err1: st.warning(f"Screener 1: {err1}")
            elif st1:
                s1_tickers = set(s.get("ticker","") for s in st1)
                for s in st1: s["screener"] = "S1"
                all_stocks.extend(st1)
            st2, err2 = load_screener_from_github("C2")
            if err2: st.warning(f"Screener 2: {err2}")
            elif st2:
                s2_tickers = set(s.get("ticker","") for s in st2)
                for s in st2: s["screener"] = "S2"
                all_stocks.extend(st2)
            if all_stocks:
                st.session_state["_pending_c"] = _process_c(all_stocks, s1_tickers, s2_tickers)

    if show_paste or st.session_state.get("_show_paste_c"):
        st.session_state["_show_paste_c"] = True
        txt1 = st.text_area("Screener 1 CSV text", height=100, key="ptxt_c1", placeholder="Paste Screener 1 CSV here...")
        txt2 = st.text_area("Screener 2 CSV text", height=100, key="ptxt_c2", placeholder="Paste Screener 2 CSV here...")
        all_stocks = []; s1_tickers = set(); s2_tickers = set()
        if txt1 and txt1.strip():
            st1, err = parse_trendlyne_text(txt1)
            if err: st.error(err)
            else:
                s1_tickers = set(s.get("ticker","") for s in st1)
                for s in st1: s["screener"] = "S1"
                all_stocks.extend(st1)
        if txt2 and txt2.strip():
            st2, err = parse_trendlyne_text(txt2)
            if err: st.error(err)
            else:
                s2_tickers = set(s.get("ticker","") for s in st2)
                for s in st2: s["screener"] = "S2"
                all_stocks.extend(st2)
        if all_stocks:
            st.session_state["_pending_c"] = _process_c(all_stocks, s1_tickers, s2_tickers)

    pending = st.session_state.get("_pending_c")
    if pending:
        doubles = sum(1 for s in pending if s.get("is_double"))
        st.success(f"Found {len(pending)} stocks ({doubles} doubles) — press Save to confirm")
        if st.button("Save Watchlist", type="primary", use_container_width=True, key="swl_c"):
            data["engine_c_watchlist"] = pending
            data["_c_watchlist_date"] = date.today().strftime("%Y-%m-%d")
            ok,msg = save_stocks_to_github(data, "Update Engine C watchlist")
            if ok:
                st.session_state.pop("_pending_c", None)
                st.success("Saved!"); trigger_workflow(); st.rerun()
            else: st.error(msg)

    if wl:
        wd = data.get("_c_watchlist_date","")
        doubles = sum(1 for s in wl if s.get("is_double"))
        ht = set(s.get("ticker","") for s in pos)

        # INTELLIGENCE SUMMARY
        gems = [s for s in wl if s.get("vds",0)>=12]
        solids = [s for s in wl if 8<=s.get("vds",0)<12]
        mods = [s for s in wl if s.get("vds",0)<8]
        traps = sum(1 for s in wl if (s.get("rev_qoq") is not None and s.get("rev_qoq",0)<-10))

        st.markdown(
            "<div class='data-card' style='border-left:4px solid #2563eb;padding:16px 18px;'>"
            "<div style='font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:2px;"
            "font-weight:700;margin-bottom:10px;'>VALUE INTELLIGENCE</div>"
            f"<div style='display:flex;gap:12px;margin-bottom:10px;'>"
            f"<div style='text-align:center;flex:1;'><div style='font-size:20px;font-weight:800;"
            f"color:#059669;'>{len(gems)}</div><div style='font-size:10px;color:#94a3b8;'>GEMS</div></div>"
            f"<div style='text-align:center;flex:1;'><div style='font-size:20px;font-weight:800;"
            f"color:#2563eb;'>{len(solids)}</div><div style='font-size:10px;color:#94a3b8;'>SOLID</div></div>"
            f"<div style='text-align:center;flex:1;'><div style='font-size:20px;font-weight:800;"
            f"color:#4338ca;'>{doubles}</div><div style='font-size:10px;color:#94a3b8;'>DOUBLES</div></div>"
            f"<div style='text-align:center;flex:1;'><div style='font-size:20px;font-weight:800;"
            f"color:#1e293b;'>{len(wl)}</div><div style='font-size:10px;color:#94a3b8;'>TOTAL</div></div>"
            f"</div>"
            f"{'<div style=\"font-size:11px;color:#dc2626;margin-bottom:6px;\">⚠ '+str(traps)+' stocks with revenue decline — check value traps</div>' if traps else ''}"
            f"{earnings_alert(wl)}"
            f"<div style='margin-top:8px;'>{sector_summary(wl)}</div>"
            f"<div style='font-size:10px;color:#94a3b8;margin-top:6px;'>Uploaded: {wd}</div>"
            "</div>",
            unsafe_allow_html=True)

        # STOCK CARDS
        for j,s in enumerate(wl):
            nm=s.get("name",""); tk=s.get("ticker",""); lp=s.get("ltp",0) or 0
            cp2=prices.get(tk,lp); opp=((cp2-lp)/lp*100) if lp>0 and cp2>0 else 0
            os2,oc=fmt_pct(opp)
            vds=s.get("vds",0)
            scr=s.get("screener","S1")
            vd="DEEP VALUE GEM" if vds>=12 else ("SOLID VALUE" if vds>=8 else ("MODERATE VALUE" if vds>=5 else "THIN VALUE"))
            vc="#16a34a" if vds>=12 else ("#2563eb" if vds>=8 else ("#d97706" if vds>=5 else "#94a3b8"))
            ah = tk in ht
            mc_label, mc_color = mcap_tag(s.get("mcap"))
            pg = s.get("profit_growth"); rq = s.get("rev_qoq")
            prom = s.get("promoter")
            # Value Trap checks
            rev_ok = rq is None or rq > -10
            prom_ok = prom is None or prom > 0
            trap_html = (
                f"<div style='display:flex;gap:10px;font-size:10px;margin-top:4px;'>"
                f"<span>{render_check('Revenue', rev_ok)}</span>"
                f"<span>{render_check('Promoter', prom_ok)}</span>"
                f"</div>"
            )

            card_html = (
                f"<div class='data-card' style='border-left:4px solid {vc};'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;'>"
                f"<div style='font-weight:700;color:#1e293b;font-size:14px;'>{nm}</div>"
                f"<div style='font-size:13px;font-weight:800;color:{vc};'>VDS: {vds}/15</div></div>"
                f"<div style='display:flex;justify-content:space-between;margin-bottom:6px;'>"
                f"<div style='font-size:12px;color:#64748b;'>₹{cp2:,.0f}"
                f"<span style='color:{oc};margin-left:6px;'>{os2}</span></div>"
                f"<div style='font-size:11px;display:flex;align-items:center;gap:4px;'>{'<span style=\"color:#475569;font-weight:600;\">₹'+fmt(s.get('mcap'),0)+'Cr</span>' if s.get('mcap') else ''} {render_stage_badge(mc_label)}</div></div>"
                f"<div style='display:flex;gap:6px;flex-wrap:wrap;font-size:11px;color:#64748b;margin-bottom:4px;'>"
                f"<span>ROE:{fmt(s.get('roe'),0)}</span><span>PE:{fmt(s.get('pe'),0)}</span>"
                f"<span>Pio:{fmt(s.get('piotroski'),0)}</span>"
                f"<span>D/E:{fmt(s.get('de'),1)}</span></div>"
            )
            # PE Expansion Room
            pe_val = s.get("pe")
            pe_room_html = ""
            if pe_val and pe_val > 0:
                pe_ceiling = 25
                room_pct = ((pe_ceiling - pe_val) / pe_val) * 100
                if room_pct > 0:
                    # Ladder milestones
                    pe_30 = pe_val * 1.30
                    pe_50 = pe_val * 1.50
                    pe_80 = pe_val * 1.80
                    bar_fill = min(max((pe_val / pe_ceiling) * 100, 5), 100)
                    bar_color = "#16a34a" if pe_val < 15 else ("#2563eb" if pe_val < 20 else "#d97706")
                    pe_room_html = (
                        f"<div style='margin-bottom:6px;'>"
                        f"<div style='display:flex;justify-content:space-between;font-size:10px;color:#94a3b8;'>"
                        f"<span>PE: {pe_val:.0f}</span>"
                        f"<span style='color:{bar_color};font-weight:700;'>Room: +{room_pct:.0f}%</span>"
                        f"<span>Cap: {pe_ceiling}</span></div>"
                        f"<div style='height:4px;background:#e2e8f0;border-radius:2px;margin-top:2px;'>"
                        f"<div style='width:{bar_fill:.0f}%;height:100%;background:{bar_color};border-radius:2px;'>"
                        f"</div></div>"
                        f"<div style='display:flex;justify-content:space-between;font-size:9px;color:#cbd5e1;margin-top:2px;'>"
                        f"<span>Book 25%→{pe_30:.0f}</span>"
                        f"<span>Book 50%→{pe_50:.0f}</span>"
                        f"<span>Book 75%→{pe_80:.0f}</span></div>"
                        f"</div>"
                    )
                else:
                    pe_room_html = (
                        f"<div style='font-size:10px;color:#dc2626;margin-bottom:6px;font-weight:600;'>"
                        f"⚠ PE at {pe_val:.0f} — already above cap. Limited upside.</div>"
                    )

            card_html = (
                f"<div class='data-card' style='border-left:4px solid {vc};'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;'>"
                f"<div style='font-weight:700;color:#1e293b;font-size:14px;'>{nm}</div>"
                f"<div style='font-size:13px;font-weight:800;color:{vc};'>VDS: {vds}/15</div></div>"
                f"<div style='display:flex;justify-content:space-between;margin-bottom:6px;'>"
                f"<div style='font-size:12px;color:#64748b;'>₹{cp2:,.0f}"
                f"<span style='color:{oc};margin-left:6px;'>{os2}</span></div>"
                f"<div style='font-size:11px;display:flex;align-items:center;gap:4px;'>{'<span style=\"color:#475569;font-weight:600;\">₹'+fmt(s.get('mcap'),0)+'Cr</span>' if s.get('mcap') else ''} {render_stage_badge(mc_label)}</div></div>"
                f"<div style='display:flex;gap:6px;flex-wrap:wrap;font-size:11px;color:#64748b;margin-bottom:4px;'>"
                f"<span>ROE:{fmt(s.get('roe'),0)}</span><span>PE:{fmt(s.get('pe'),0)}</span>"
                f"<span>Pio:{fmt(s.get('piotroski'),0)}</span>"
                f"<span>D/E:{fmt(s.get('de'),1)}</span></div>"
                f"{pe_room_html}"
                f"<div style='display:flex;gap:6px;flex-wrap:wrap;font-size:11px;color:#64748b;margin-bottom:4px;'>"
                f"{'<span style=\"color:#16a34a;\">PG:+'+fmt(pg,0)+'%</span>' if pg and pg>0 else ('<span style=\"color:#dc2626;\">PG:'+fmt(pg,0)+'%</span>' if pg else '')}"
                f"{'<span>Prom:'+fmt(prom,1)+'%</span>' if prom else ''}"
                f"{'<span>FII:'+fmt(s.get('fii'),1)+'%</span>' if s.get('fii') else ''}"
                f"{'<span>Inst:'+fmt(s.get('inst'),1)+'%</span>' if s.get('inst') else ''}"
                f"{'<span style=\"color:#16a34a;\">Rev:+'+fmt(rq,0)+'%</span>' if rq and rq>0 else ('<span style=\"color:#dc2626;\">Rev:'+fmt(rq,0)+'%</span>' if rq else '')}"
                f"</div>"
                f"{render_52w_position(cp2, s.get('low_52w'), s.get('high_52w'))}"
                f"{trap_html}"
                f"<div style='margin-top:4px;'>"
                f"{render_badge('DOUBLE','#e0e7ff','#4338ca') if s.get('is_double') else render_badge(scr,'#f1f5f9','#64748b')}"
                f" {render_stage_badge(vd)}"
                f"{'  '+render_badge('HELD','#94a3b8') if ah else ''}</div>"
                f"{smart_signal_c(s, vds)}"
                f"{render_earnings_info(s)}</div>"
            )
            st.markdown(card_html, unsafe_allow_html=True)
            with st.expander(f"AI Analysis · {nm}", expanded=False):
                _, _, ai_html = ai_analyst(s, engine="C", engine_score=ea, held=ah)
                st.markdown(ai_html, unsafe_allow_html=True)
            if not ah and ea and ea>30 and len(pos)<MAX_POSITIONS:
                with st.expander(f"Buy {nm}", expanded=False):
                    pe_in=st.number_input("Current PE",value=float(s.get("pe",0) or 0),key=f"pe_cb_{j}",format="%.1f")
                    bp=st.number_input("Price ₹",value=float(cp2),key=f"bp_c_{j}",format="%.2f")
                    mx2=min(c_cap-ti, c_cap*MAX_PCT/100)
                    # Size by VDS
                    if vds>=12: sz_pct=10
                    elif vds>=8: sz_pct=7
                    else: sz_pct=4
                    mx3=min(mx2, c_cap*sz_pct/100)
                    sq=int(mx3/bp) if bp>0 else 0
                    bq=st.number_input("Qty",value=max(sq,1),min_value=1,key=f"bq_c_{j}")
                    st.markdown(f"**₹{bp*bq:,.0f}** ({sz_pct}% sizing for VDS {vds})")
                    if st.button(f"Confirm Buy",type="primary",use_container_width=True,key=f"cb_c_{j}"):
                        data["engine_c"].append({
                            "name":nm,"ticker":tk,"entry":bp,"qty":bq,
                            "buy_date":date.today().strftime("%Y-%m-%d"),"peak":bp,
                            "entry_pe":pe_in,"current_pe":pe_in,
                            "value_depth_score":vds,"is_double":s.get("is_double",False),
                            "sector":s.get("sector","")})
                        ok,msg=save_stocks_to_github(data,f"Buy {nm} Engine C")
                        if ok: st.success(f"Bought {nm}"); trigger_workflow(); st.rerun()
                        else: st.error(msg)
        if st.button("Clear Watchlist", key="cwl_c"):
            data["engine_c_watchlist"]=[]; data["_c_watchlist_date"]=""
            ok,msg=save_stocks_to_github(data,"Clear Engine C watchlist")
            if ok: st.success("Cleared"); st.rerun()
    else:
        render_info_card("No watchlist. Upload Screener 1/2 CSVs to discover.")

    # TRADE LOG
    render_section_title("Trade Log")
    if closed:
        ws=[t for t in closed if float(t.get("pnl",0))>0]
        ls=[t for t in closed if float(t.get("pnl",0))<=0]
        tr=sum(float(t.get("pnl",0)) for t in closed)
        ts2,tc2=fmt_pnl(tr); wr=(len(ws)/len(closed)*100) if closed else 0
        avg_pe_exp = sum(float(t.get("pe_expansion",0)) for t in closed)/len(closed) if closed else 0
        render_data_card(
            render_stat_row("Trades",str(len(closed)))+
            render_stat_row("Win/Loss",f"{len(ws)}/{len(ls)}")+
            render_stat_row("Win Rate",f"{wr:.0f}%","#16a34a" if wr>=50 else "#dc2626")+
            render_stat_row("Total P&L",f"₹{ts2}",tc2)+
            render_stat_row("Avg PE Expansion",f"{avg_pe_exp:.0f}%"))
    else:
        render_info_card("No trades yet.")
