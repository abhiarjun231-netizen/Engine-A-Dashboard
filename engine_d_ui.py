"""
engine_d_ui.py - Engine D: The Compounders
"Find businesses that print money. Hold them forever."
Screener 3 (PEG+YoY) + Screener 4 (PE+3Yr)
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
    calculate_trailing_stop_d, get_profit_stage_d,
    mcap_tag, render_mini_bar, render_52w_position,
    sector_summary, render_check, peg_reading, compound_stars,
    smart_signal_d,
    ai_analyst,
    render_earnings_info, earnings_alert,
    load_stock_analysis, render_volume_badge,
)

MAX_POSITIONS = 15
MAX_PCT = 10

def dna_score(stock, is_double=False):
    score = 0
    p = float(stock.get("piotroski",0) or 0)
    roe = float(stock.get("roe",0) or 0)
    de = float(stock.get("de",99) or 99)
    pg = float(stock.get("profit_growth",0) or 0)
    peg = float(stock.get("peg",99) or 99)
    mcap = float(stock.get("mcap",0) or 0)
    # Earnings (max 6)
    if pg > 30: score += 3
    elif pg > 15: score += 2
    # Quality (max 6)
    if p >= 9: score += 3
    elif p >= 8: score += 2
    if roe > 25: score += 2
    if de < 0.3: score += 2
    elif de < 0.5: score += 1
    # Growth (max 4)
    if peg < 0.8: score += 2
    elif peg < 1.2: score += 1
    if is_double: score += 2
    # Market (max 4)
    if mcap > 10000: score += 1
    if 0 < mcap < 50000: score += 1
    return min(score, 20)

def show_engine_d():
    data = load_stocks_json()
    prices = load_stock_prices()
    analysis = load_stock_analysis()
    sd = get_engine_a_score()
    ea = int(sd["raw_score"]) if sd else None
    pos = data.get("engine_d", []) + data.get("compounders", []);
    data["engine_d"] = pos  # normalize for indexing
    wl = data.get("engine_d_watchlist", [])
    closed = data.get("engine_d_closed", [])
    cap = float(data.get("_capital", data.get("capital", 100000)))
    eq_pct = int(sd.get("equity_pct", 55)) if sd else 55
    d_cap = round(cap * eq_pct / 100 * 40 / 100, 2)

    # HEADER
    st.markdown(
        "<div style='text-align:center;margin-bottom:4px;'>"
        "<div style='font-size:11px;color:#94a3b8;text-transform:uppercase;"
        "letter-spacing:2px;font-weight:600;'>Engine D</div>"
        "<div style='font-size:20px;font-weight:800;color:#1e293b;"
        "font-family:DM Sans,sans-serif;'>The Compounders</div>"
        "<div style='font-size:11px;color:#94a3b8;font-style:italic;'>"
        "Find businesses that print money. Hold them forever.</div></div>",
        unsafe_allow_html=True)

    render_engine_gate(ea)

    if st.button("Refresh Data", type="primary", use_container_width=True, key="ref_d"):
        with st.spinner("Fetching..."):
            ok, msg = trigger_workflow()
        st.success(msg) if ok else st.error(msg)

    # SUMMARY
    render_section_title("Portfolio Summary")
    ti = round(sum(float(s.get("entry", s.get("buy_price", 0)))*int(s.get("qty",0)) for s in pos), 2)
    tc = sum(prices.get(s.get("ticker",""),float(s.get("entry", s.get("buy_price", 0))))*int(s.get("qty",0)) for s in pos)
    tp = tc - ti
    ps, pc = fmt_pnl(tp)
    pp, _ = fmt_pct((tp/ti*100) if ti>0 else 0)
    c1,c2,c3 = st.columns(3)
    with c1: render_hero_number("Budget", f"₹{d_cap:,.0f}", "#2563eb")
    with c2: render_hero_number("Deployed", f"₹{ti:,.0f}", "#1e293b", f"{len(pos)}/{MAX_POSITIONS}")
    with c3: render_hero_number("P&L", f"₹{ps}", pc, pp)

    # POSITIONS
    render_section_title(f"Active Positions ({len(pos)})")
    if not pos:
        render_info_card("No positions. Upload Screener 3/4 CSVs to identify compounders.")
    else:
        for i, p in enumerate(pos):
            tk = p.get("ticker",""); nm = p.get("name",tk)
            en = float(p.get("entry", p.get("buy_price", 0))); qt = int(p.get("qty",0))
            bd = p.get("buy_date",""); pk = float(p.get("peak",en))
            dns = int(p.get("dna_score",0) or 0)
            is_imm = p.get("is_immortal", False)
            is_leg = p.get("is_legendary", False)

            cp = prices.get(tk, en)
            if cp > pk: pk = cp; data["engine_d"][i]["peak"] = pk
            pnl = (cp-en)*qt; pnlp = ((cp-en)/en*100) if en>0 else 0
            hd = days_held(bd)

            stg = get_profit_stage_d(pnlp, hd, is_imm, is_leg)
            stp = calculate_trailing_stop_d(en, pk, pnlp, is_imm)
            sd2 = ((cp-stp)/cp*100) if cp>0 else 0

            # Incubation check
            in_incubation = hd <= 90
            incub_days_left = max(0, 90 - hd)

            # LTCG eligibility
            is_ltcg = hd >= 365
            tax_badge = "LTCG" if is_ltcg else "STCG"
            tax_color = "#16a34a" if is_ltcg else "#d97706"

            # Tax-aware harvest signals
            harvest_signal = ""
            if is_ltcg:
                if pnlp >= 150: harvest_signal = "BOOK 10% MORE"
                elif pnlp >= 100: harvest_signal = "BOOK 20% MORE"
                elif pnlp >= 50: harvest_signal = "BOOK 20%"

            # Check IMMORTAL eligibility
            can_immortal = hd >= 365 and pnlp >= 30 and not is_imm
            can_legendary = hd >= 730 and pnlp >= 100 and is_imm and not is_leg

            ps2,pc2 = fmt_pnl(pnl); pp2,_ = fmt_pct(pnlp)

            # Border color
            if is_leg: bc = "#f59e0b"
            elif is_imm: bc = "#fbbf24"
            elif in_incubation: bc = "#818cf8"
            elif pnlp >= 0: bc = "#16a34a"
            else: bc = "#dc2626"

            # Build card
            card_top = (
                f"<div class='data-card' style='border-left:4px solid {bc};'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>"
                f"<div style='font-weight:700;color:#1e293b;font-size:14px;'>{nm}</div>"
                f"<div>{render_stage_badge(stg)}</div></div>"
            )

            if in_incubation:
                card_top += (
                    f"<div style='background:#e0e7ff;border-radius:8px;padding:10px;margin-bottom:8px;"
                    f"text-align:center;font-size:12px;color:#4338ca;font-weight:600;'>"
                    f"INCUBATION — {incub_days_left} days remaining. Short-term price is noise."
                    f"</div>"
                )

            card_body = (
                f"<div style='display:flex;justify-content:space-between;margin-bottom:6px;'>"
                f"<div style='font-size:12px;color:#64748b;'>₹{en:,.0f} → ₹{cp:,.0f}</div>"
                f"<div style='font-size:13px;font-weight:700;color:{pc2};'>{pp2} (₹{ps2})</div></div>"
                f"<div style='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px;font-size:10px;color:#94a3b8;'>"
                f"<span>Qty: {qt}</span><span>Days: {hd}</span>"
                f"<span>Stop: ₹{stp:,.0f} ({sd2:.1f}%)</span>"
                f"<span>DNA: {dns}/20</span>"
                f"<span style='color:{tax_color};font-weight:600;'>{tax_badge}</span></div>"
            )

            if harvest_signal:
                card_body += (
                    f"<div style='margin-top:4px;'>"
                    f"{render_badge(harvest_signal, '#d1fae5', '#059669')}</div>"
                )

            card_html = card_top + card_body + "</div>"
            st.markdown(card_html, unsafe_allow_html=True)

            with st.expander(f"Manage {nm}", expanded=False):
                # IMMORTAL / LEGENDARY promotion
                if can_immortal:
                    st.markdown("**Eligible for IMMORTAL status** (12mo+, 4Q growth, +30%)")
                    if st.button(f"Promote to IMMORTAL", key=f"imm_{i}"):
                        data["engine_d"][i]["is_immortal"] = True
                        ok,msg = save_stocks_to_github(data, f"{nm} promoted to IMMORTAL")
                        if ok: st.success(f"{nm} is now IMMORTAL!"); st.rerun()

                if can_legendary:
                    st.markdown("**Eligible for LEGENDARY status** (24mo+, 8Q growth, +100%)")
                    if st.button(f"Promote to LEGENDARY", key=f"leg_{i}"):
                        data["engine_d"][i]["is_legendary"] = True
                        ok,msg = save_stocks_to_github(data, f"{nm} promoted to LEGENDARY")
                        if ok: st.success(f"{nm} is now LEGENDARY!"); st.rerun()

                # INTENSIFY (add to position)
                if hd >= 180 and pnlp > 0 and not in_incubation:
                    st.markdown("**INTENSIFY eligible** — Business proving itself. Add to position?")
                    add_qty = st.number_input("Add shares", value=0, min_value=0, key=f"aq_{i}")
                    add_price = st.number_input("At price ₹", value=float(cp), key=f"ap_{i}", format="%.2f")
                    if add_qty > 0 and st.button(f"Add {add_qty} shares", key=f"add_{i}"):
                        old_cost = en * qt
                        add_cost = add_price * add_qty
                        new_qty = qt + add_qty
                        new_avg = (old_cost + add_cost) / new_qty
                        data["engine_d"][i]["entry"] = round(new_avg, 2)
                        data["engine_d"][i]["qty"] = new_qty
                        ok,msg = save_stocks_to_github(data, f"Intensify {nm} +{add_qty}")
                        if ok: st.success(f"Added {add_qty} at ₹{add_price:,.0f}. New avg: ₹{new_avg:,.0f}"); st.rerun()

                # Sell
                if not in_incubation or pnlp <= -10:
                    er = ["Fundamental Break (Piotroski)","Fundamental Break (ROE)",
                          "D/E Breach","Growth Stalled (ETS=0 2Q)","Trailing Stop",
                          "Tax-Aware Harvest","Engine A Gate","Manual"]
                    r = st.selectbox("Exit reason", er, key=f"sr_d_{i}")
                    pct_sell = st.selectbox("% to sell", [100, 75, 50, 25, 20, 10], key=f"pct_d_{i}")
                    sell_qty = max(1, int(qt * pct_sell / 100))
                    sell_pnl = (cp - en) * sell_qty
                    sp_s, sp_c = fmt_pnl(sell_pnl)
                    st.markdown(f"Selling {sell_qty} of {qt} shares. P&L: <span style='color:{sp_c}'>₹{sp_s}</span>",
                               unsafe_allow_html=True)

                    if st.button(f"Confirm Sell", type="primary", use_container_width=True, key=f"sd_{i}"):
                        data["engine_d_closed"].append({
                            "name":nm,"ticker":tk,"entry":en,"exit_price":cp,
                            "qty":sell_qty,"pnl":round(sell_pnl,2),
                            "pnl_pct":round(pnlp,1),"buy_date":bd,
                            "exit_date":date.today().strftime("%Y-%m-%d"),
                            "days_held":hd,"exit_reason":r,
                            "partial": pct_sell < 100,
                            "tax_type":"LTCG" if is_ltcg else "STCG"})
                        if sell_qty >= qt:
                            data["engine_d"].pop(i)
                        else:
                            data["engine_d"][i]["qty"] = qt - sell_qty
                        ok,msg = save_stocks_to_github(data, f"Sell {sell_qty} {nm} Engine D")
                        if ok: st.success(f"Sold {sell_qty} {nm}"); st.rerun()
                        else: st.error(msg)
                elif in_incubation:
                    st.info(f"Sell disabled during incubation ({incub_days_left} days left). "
                           f"Hard stop at ₹{stp:,.0f} still active.")

    # POSITION SIZER
    render_section_title("Position Sizer")
    with st.expander("Calculate", expanded=False):
        av = round(d_cap - ti, 2); mx = round(d_cap * MAX_PCT / 100, 2)
        st.markdown(
            f"<div style='font-size:13px;color:#1e293b;font-weight:600;margin-bottom:8px;'>"
            f"Available: <span style='color:#059669;'>₹{av:,.0f}</span> | "
            f"Max/stock: <span style='color:#2563eb;'>₹{mx:,.0f}</span></div>",
            unsafe_allow_html=True)
        pr = st.number_input("Price ₹", value=100.0, key="ps_d", min_value=1.0, format="%.2f")
        if pr>0:
            mq = int(min(av,mx)/pr)
            st.markdown(
                f"<div style='font-size:14px;color:#1e293b;font-weight:700;margin-top:8px;'>"
                f"Suggested: <span style='color:#059669;'>{mq} shares</span> = "
                f"<span style='color:#2563eb;'>₹{mq*pr:,.0f}</span></div>",
                unsafe_allow_html=True)

    # WATCHLIST
    render_section_title("Screener Watchlist")
    st.caption("S3: ROE>15, PEG<=1.5, >200DMA, Pio>6, D/E<1, PG YoY>15%")
    st.caption("S4: ROE>15, PE<25, >200DMA, Pio>6, D/E<1, PG 3Yr>15%")
    st.markdown(
        "<div style='font-size:12px;color:#64748b;line-height:1.6;'>"
        "Upload CSVs (names starting with <code>D1</code> + <code>D2</code>) "
        "to GitHub → <code>data</code> folder → press Load</div>",
        unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        load_gh = st.button("Load from GitHub", type="primary", use_container_width=True, key="ghb_d")
    with c2:
        show_paste = st.button("Paste CSV Instead", use_container_width=True, key="paste_toggle_d")

    def _process_d(all_stocks, s3_tickers, s4_tickers):
        seen = {}
        for s in all_stocks:
            tk = s.get("ticker","")
            if tk in seen:
                seen[tk]["screener"] = "DOUBLE"
            else:
                is_dbl = tk in s3_tickers and tk in s4_tickers
                if is_dbl: s["screener"] = "DOUBLE"
                seen[tk] = s
        deduped = list(seen.values())
        for s in deduped:
            s["upload_date"] = date.today().strftime("%Y-%m-%d")
            s["is_double"] = s.get("screener") == "DOUBLE"
            s["dns"] = dna_score(s, s.get("is_double", False))
        deduped.sort(key=lambda x: x.get("dns",0), reverse=True)
        return deduped

    if load_gh:
        with st.spinner("Fetching from GitHub..."):
            all_stocks = []; s3_tickers = set(); s4_tickers = set()
            st1, err1 = load_screener_from_github("D1")
            if err1: st.warning(f"Screener 3: {err1}")
            elif st1:
                s3_tickers = set(s.get("ticker","") for s in st1)
                for s in st1: s["screener"] = "S3"
                all_stocks.extend(st1)
            st2, err2 = load_screener_from_github("D2")
            if err2: st.warning(f"Screener 4: {err2}")
            elif st2:
                s4_tickers = set(s.get("ticker","") for s in st2)
                for s in st2: s["screener"] = "S4"
                all_stocks.extend(st2)
            if all_stocks:
                st.session_state["_pending_d"] = _process_d(all_stocks, s3_tickers, s4_tickers)

    if show_paste or st.session_state.get("_show_paste_d"):
        st.session_state["_show_paste_d"] = True
        txt1 = st.text_area("Screener 3 CSV text", height=100, key="ptxt_d1", placeholder="Paste Screener 3 CSV here...")
        txt2 = st.text_area("Screener 4 CSV text", height=100, key="ptxt_d2", placeholder="Paste Screener 4 CSV here...")
        all_stocks = []; s3_tickers = set(); s4_tickers = set()
        if txt1 and txt1.strip():
            st1, err = parse_trendlyne_text(txt1)
            if err: st.error(err)
            else:
                s3_tickers = set(s.get("ticker","") for s in st1)
                for s in st1: s["screener"] = "S3"
                all_stocks.extend(st1)
        if txt2 and txt2.strip():
            st2, err = parse_trendlyne_text(txt2)
            if err: st.error(err)
            else:
                s4_tickers = set(s.get("ticker","") for s in st2)
                for s in st2: s["screener"] = "S4"
                all_stocks.extend(st2)
        if all_stocks:
            st.session_state["_pending_d"] = _process_d(all_stocks, s3_tickers, s4_tickers)

    pending = st.session_state.get("_pending_d")
    if pending:
        doubles = sum(1 for s in pending if s.get("is_double"))
        st.success(f"Found {len(pending)} stocks ({doubles} doubles) — press Save to confirm")
        if st.button("Save Watchlist", type="primary", use_container_width=True, key="swl_d"):
            data["engine_d_watchlist"] = pending
            data["_d_watchlist_date"] = date.today().strftime("%Y-%m-%d")
            ok,msg = save_stocks_to_github(data, "Update Engine D watchlist")
            if ok:
                st.session_state.pop("_pending_d", None)
                st.success("Saved!"); trigger_workflow(); st.rerun()
            else: st.error(msg)

    if wl:
        wd = data.get("_d_watchlist_date","")
        doubles = sum(1 for s in wl if s.get("is_double"))
        ht = set(s.get("ticker","") for s in pos)

        # INTELLIGENCE SUMMARY
        elites = [s for s in wl if s.get("dns",0)>=16]
        strongs = [s for s in wl if 11<=s.get("dns",0)<16]
        potentials = [s for s in wl if s.get("dns",0)<11]
        low_peg = sum(1 for s in wl if s.get("peg") is not None and s.get("peg",99)<=0.5)

        st.markdown(
            "<div class='data-card' style='border-left:4px solid #059669;padding:16px 18px;'>"
            "<div style='font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:2px;"
            "font-weight:700;margin-bottom:10px;'>COMPOUNDER INTELLIGENCE</div>"
            f"<div style='display:flex;gap:12px;margin-bottom:10px;'>"
            f"<div style='text-align:center;flex:1;'><div style='font-size:20px;font-weight:800;"
            f"color:#059669;'>{len(elites)}</div><div style='font-size:10px;color:#94a3b8;'>ELITE</div></div>"
            f"<div style='text-align:center;flex:1;'><div style='font-size:20px;font-weight:800;"
            f"color:#2563eb;'>{len(strongs)}</div><div style='font-size:10px;color:#94a3b8;'>STRONG</div></div>"
            f"<div style='text-align:center;flex:1;'><div style='font-size:20px;font-weight:800;"
            f"color:#4338ca;'>{doubles}</div><div style='font-size:10px;color:#94a3b8;'>DOUBLES</div></div>"
            f"<div style='text-align:center;flex:1;'><div style='font-size:20px;font-weight:800;"
            f"color:#1e293b;'>{len(wl)}</div><div style='font-size:10px;color:#94a3b8;'>TOTAL</div></div>"
            f"</div>"
            f"<div style='font-size:11px;color:#64748b;margin-bottom:6px;'>"
            f"<b style='color:#16a34a;'>{low_peg} stocks</b> with PEG ≤ 0.5 (extreme value)</div>"
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
            dns2=s.get("dns",0)
            scr=s.get("screener","S3")
            vd="ELITE" if dns2>=16 else ("STRONG" if dns2>=11 else ("POTENTIAL" if dns2>=7 else "WEAK"))
            vc="#16a34a" if dns2>=16 else ("#2563eb" if dns2>=11 else ("#d97706" if dns2>=7 else "#94a3b8"))
            ah = tk in ht
            mc_label, mc_color = mcap_tag(s.get("mcap"))
            pg = s.get("profit_growth"); peg_val = s.get("peg")
            peg_txt, peg_col = peg_reading(peg_val)
            de_val = s.get("de")
            # Kill Shot checks
            growth_ok = pg is None or pg > 0
            debt_ok = de_val is None or de_val < 1.5
            kill_html = (
                f"<div style='display:flex;gap:10px;font-size:10px;margin-top:4px;'>"
                f"<span>{render_check('Growth', growth_ok)}</span>"
                f"<span>{render_check('Debt', debt_ok)}</span>"
                f"<span style='color:{peg_col};font-weight:600;'>PEG: {peg_txt}</span>"
                f"</div>"
            )

            card_html = (
                f"<div class='data-card' style='border-left:4px solid {vc};'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'>"
                f"<div style='font-weight:700;color:#1e293b;font-size:14px;'>{nm}</div>"
                f"<div style='font-size:13px;font-weight:800;color:{vc};'>DNA: {dns2}/20</div></div>"
                f"<div style='text-align:right;margin-bottom:6px;'>{compound_stars(dns2)}</div>"
                f"<div style='display:flex;justify-content:space-between;margin-bottom:6px;'>"
                f"<div style='font-size:12px;color:#64748b;'>₹{cp2:,.0f}"
                f"<span style='color:{oc};margin-left:6px;'>{os2}</span></div>"
                f"<div style='font-size:11px;display:flex;align-items:center;gap:4px;'>{'<span style=\"color:#475569;font-weight:600;\">₹'+fmt(s.get('mcap'),0)+'Cr</span>' if s.get('mcap') else ''} {render_stage_badge(mc_label)}</div></div>"
                f"<div style='display:flex;gap:6px;flex-wrap:wrap;font-size:11px;color:#64748b;margin-bottom:4px;'>"
                f"<span>ROE:{fmt(s.get('roe'),0)}</span><span>PE:{fmt(s.get('pe'),0)}</span>"
                f"<span>Pio:{fmt(s.get('piotroski'),0)}</span>"
                f"<span>D/E:{fmt(s.get('de'),1)}</span>"
                f"<span>PEG:{fmt(peg_val,1)}</span>"
                f" {render_volume_badge(analysis.get(tk,{}).get('vol_ratio'), s.get('delivery_pct'))}</div>"
                f"<div style='display:flex;gap:6px;flex-wrap:wrap;font-size:11px;color:#64748b;margin-bottom:4px;'>"
                f"{'<span style=\"color:#16a34a;font-weight:600;\">PG:+'+fmt(pg,0)+'%</span>' if pg and pg>0 else ('<span style=\"color:#dc2626;\">PG:'+fmt(pg,0)+'%</span>' if pg else '')}"
                f"{'<span>Prom:'+fmt(s.get('promoter'),0)+'%</span>' if s.get('promoter') else ''}"
                f"{'<span>FII:'+fmt(s.get('fii'),1)+'%</span>' if s.get('fii') else ''}"
                f"{'<span style=\"color:#16a34a;\">Rev:+'+fmt(s.get('rev_qoq'),0)+'%</span>' if s.get('rev_qoq') and s.get('rev_qoq')>0 else ('<span style=\"color:#dc2626;\">Rev:'+fmt(s.get('rev_qoq'),0)+'%</span>' if s.get('rev_qoq') and s.get('rev_qoq')<0 else '')}"
                f"</div>"
                f"{render_52w_position(cp2, s.get('low_52w'), s.get('high_52w'))}"
                f"{kill_html}"
                f"<div style='margin-top:4px;'>"
                f"{render_badge('DOUBLE','#e0e7ff','#4338ca') if s.get('is_double') else render_badge(scr,'#f1f5f9','#64748b')}"
                f" {render_stage_badge(vd)}"
                f"{'  '+render_badge('HELD','#94a3b8') if ah else ''}</div>"
                f"{smart_signal_d(s, dns2)}"
                f"{render_earnings_info(s)}</div>"
            )
            st.markdown(card_html, unsafe_allow_html=True)
            with st.expander(f"AI Analysis · {nm}", expanded=False):
                _, _, ai_html = ai_analyst(s, engine="D", engine_score=ea, held=ah)
                st.markdown(ai_html, unsafe_allow_html=True)
            if not ah and ea and ea>30 and len(pos)<MAX_POSITIONS:
                with st.expander(f"Buy {nm}", expanded=False):
                    bp=st.number_input("Price ₹",value=float(cp2),key=f"bp_d_{j}",format="%.2f")
                    mx2=round(min(d_cap-ti, d_cap*MAX_PCT/100), 2)
                    if dns2>=16: sz=10
                    elif dns2>=11: sz=7
                    else: sz=4
                    mx3=min(mx2, d_cap*sz/100)
                    sq=int(mx3/bp) if bp>0 else 0
                    bq=st.number_input("Qty",value=max(sq,1),min_value=1,key=f"bq_d_{j}")
                    st.markdown(f"**₹{bp*bq:,.0f}** ({sz}% sizing for DNA {dns2})")
                    if st.button(f"Confirm Buy",type="primary",use_container_width=True,key=f"cb_d_{j}"):
                        data["engine_d"].append({
                            "name":nm,"ticker":tk,"entry":bp,"qty":bq,
                            "buy_date":date.today().strftime("%Y-%m-%d"),"peak":bp,
                            "dna_score":dns2,"is_double":s.get("is_double",False),
                            "is_immortal":False,"is_legendary":False,
                            "sector":s.get("sector","")})
                        ok,msg=save_stocks_to_github(data,f"Buy {nm} Engine D")
                        if ok: st.success(f"Bought {nm}"); trigger_workflow(); st.rerun()
                        else: st.error(msg)
        if st.button("Clear Watchlist", key="cwl_d"):
            data["engine_d_watchlist"]=[]; data["_d_watchlist_date"]=""
            ok,msg=save_stocks_to_github(data,"Clear Engine D watchlist")
            if ok: st.success("Cleared"); st.rerun()
    else:
        render_info_card("No watchlist. Upload Screener 3/4 CSVs to identify compounders.")

    # TRADE LOG
    render_section_title("Trade Log")
    if closed:
        ws=[t for t in closed if float(t.get("pnl",0))>0]
        ls=[t for t in closed if float(t.get("pnl",0))<=0]
        tr=sum(float(t.get("pnl",0)) for t in closed)
        ts2,tc2=fmt_pnl(tr); wr=(len(ws)/len(closed)*100) if closed else 0
        ltcg_trades = sum(1 for t in closed if t.get("tax_type")=="LTCG")
        partials = sum(1 for t in closed if t.get("partial"))
        render_data_card(
            render_stat_row("Total Trades",str(len(closed)))+
            render_stat_row("Win/Loss",f"{len(ws)}/{len(ls)}")+
            render_stat_row("Win Rate",f"{wr:.0f}%","#16a34a" if wr>=50 else "#dc2626")+
            render_stat_row("Total P&L",f"₹{ts2}",tc2)+
            render_stat_row("LTCG Trades",str(ltcg_trades),"#16a34a")+
            render_stat_row("Partial Bookings",str(partials)))
    else:
        render_info_card("No trades yet. Compounders take time.")
