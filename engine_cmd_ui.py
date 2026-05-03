"""
engine_cmd_ui.py - Command Center
"The war room. One screen to rule all engines."
Cross-engine Power Picks, capital deployment, sector map.
"""
import streamlit as st
from datetime import date
from utils import (
    load_stocks_json, load_stock_prices, get_engine_a_score,
    fmt, fmt_pnl, fmt_pct,
    render_section_title, render_info_card, render_data_card,
    render_stat_row, render_hero_number, render_badge,
    render_stage_badge, sector_summary,
    mcap_tag, smart_signal_b, smart_signal_c, smart_signal_d,
    ai_analyst, refresh_prices_yfinance,
)

def show_command_center():
    data = load_stocks_json()
    prices = load_stock_prices()
    ea_data = get_engine_a_score()
    ea = int(ea_data.get("raw_score", 0)) if ea_data else None

    # REFRESH BUTTON
    if st.button("Refresh Live Prices", type="primary", use_container_width=True, key="refresh_cmd"):
        with st.spinner("Fetching live prices from NSE..."):
            live, err = refresh_prices_yfinance(data)
            if err:
                st.warning(f"Refresh error: {err}")
            elif live:
                prices.update(live)
                st.session_state["_live_prices"] = live
                st.success(f"Updated {len(live)} stock prices")
    if st.session_state.get("_live_prices"):
        prices.update(st.session_state["_live_prices"])

    # Load all watchlists
    b_wl = data.get("engine_b_watchlist", [])
    c_wl = data.get("engine_c_watchlist", [])
    d_wl = data.get("engine_d_watchlist", [])

    # Load all positions
    b_pos = data.get("engine_b", []) + data.get("momentum", [])
    c_pos = data.get("engine_c", []) + data.get("value", [])
    d_pos = data.get("engine_d", []) + data.get("compounders", [])

    # Ticker sets
    b_tickers = {s.get("ticker",""): s for s in b_wl}
    c_tickers = {s.get("ticker",""): s for s in c_wl}
    d_tickers = {s.get("ticker",""): s for s in d_wl}
    held_tickers = set(
        s.get("ticker","") for s in b_pos + c_pos + d_pos
    )

    # ============================================================
    # SYSTEM STATUS
    # ============================================================
    render_section_title("System Status")
    ea_color = "#16a34a" if ea and ea > 52 else ("#2563eb" if ea and ea > 30 else ("#d97706" if ea and ea > 20 else "#dc2626"))
    ea_label = "FULL DEPLOY" if ea and ea > 62 else ("ACTIVE" if ea and ea > 30 else ("FREEZE" if ea and ea > 20 else "EXIT ALL"))

    total_pos = len(b_pos) + len(c_pos) + len(d_pos)
    total_wl = len(b_wl) + len(c_wl) + len(d_wl)
    capital = data.get("_capital", data.get("capital", 100000))

    st.markdown(
        f"<div class='data-card' style='border-left:4px solid {ea_color};padding:16px 18px;'>"
        f"<div style='display:flex;gap:16px;margin-bottom:12px;'>"
        f"<div style='text-align:center;flex:1;'>"
        f"<div style='font-size:28px;font-weight:800;color:{ea_color};'>{ea or '—'}</div>"
        f"<div style='font-size:10px;color:#94a3b8;'>ENGINE A</div>"
        f"<div style='font-size:11px;font-weight:700;color:{ea_color};'>{ea_label}</div></div>"
        f"<div style='text-align:center;flex:1;'>"
        f"<div style='font-size:28px;font-weight:800;color:#1e293b;'>{total_pos}</div>"
        f"<div style='font-size:10px;color:#94a3b8;'>POSITIONS</div></div>"
        f"<div style='text-align:center;flex:1;'>"
        f"<div style='font-size:28px;font-weight:800;color:#1e293b;'>{total_wl}</div>"
        f"<div style='font-size:10px;color:#94a3b8;'>WATCHLIST</div></div>"
        f"<div style='text-align:center;flex:1;'>"
        f"<div style='font-size:28px;font-weight:800;color:#1e293b;'>₹{capital/1000:.0f}K</div>"
        f"<div style='font-size:10px;color:#94a3b8;'>CAPITAL</div></div>"
        f"</div></div>",
        unsafe_allow_html=True)

    # ============================================================
    # POWER PICKS - stocks in multiple engines
    # ============================================================
    render_section_title("Power Picks")
    st.markdown(
        "<div style='font-size:11px;color:#64748b;margin-bottom:12px;'>"
        "Stocks appearing in multiple engines — highest conviction signals</div>",
        unsafe_allow_html=True)

    # Find all unique tickers across all watchlists
    all_tickers = set(list(b_tickers.keys()) + list(c_tickers.keys()) + list(d_tickers.keys()))
    all_tickers.discard("")

    power_picks = []
    for tk in all_tickers:
        in_b = tk in b_tickers
        in_c = tk in c_tickers
        in_d = tk in d_tickers
        engine_count = sum([in_b, in_c, in_d])
        if engine_count < 2:
            continue

        # Get best data available
        stock = b_tickers.get(tk) or c_tickers.get(tk) or d_tickers.get(tk)
        name = stock.get("name", tk)

        # Calculate Power Score (max 45)
        conv = 0
        vds = 0
        dns = 0
        if in_b:
            bs = b_tickers[tk]
            d_val = float(bs.get("durability", 0) or 0)
            m_val = float(bs.get("momentum", 0) or 0)
            conv = min(int((d_val + m_val) / 20), 10)
        if in_c:
            vds = c_tickers[tk].get("vds", 0) or 0
        if in_d:
            dns = d_tickers[tk].get("dns", 0) or 0

        power_score = conv + vds + dns
        ltp = stock.get("ltp", 0) or 0
        cp = prices.get(tk, ltp)

        power_picks.append({
            "ticker": tk, "name": name, "in_b": in_b, "in_c": in_c, "in_d": in_d,
            "engines": engine_count, "conv": conv, "vds": vds, "dns": dns,
            "power": power_score, "price": cp, "ltp": ltp,
            "pe": stock.get("pe"), "roe": stock.get("roe"),
            "piotroski": stock.get("piotroski"), "de": stock.get("de"),
            "peg": stock.get("peg"), "mcap": stock.get("mcap"),
            "sector": stock.get("sector", ""),
            "held": tk in held_tickers,
        })

    # Sort: 3-engine first, then by power score
    power_picks.sort(key=lambda x: (x["engines"], x["power"]), reverse=True)

    if power_picks:
        # Summary
        triple = [p for p in power_picks if p["engines"] == 3]
        double = [p for p in power_picks if p["engines"] == 2]

        st.markdown(
            f"<div class='data-card' style='border-left:4px solid #b45309;padding:16px 18px;'>"
            f"<div style='display:flex;gap:16px;margin-bottom:10px;'>"
            f"<div style='text-align:center;flex:1;'>"
            f"<div style='font-size:24px;font-weight:800;color:#b45309;'>{len(triple)}</div>"
            f"<div style='font-size:10px;color:#94a3b8;'>ALL 3 ENGINES</div></div>"
            f"<div style='text-align:center;flex:1;'>"
            f"<div style='font-size:24px;font-weight:800;color:#4338ca;'>{len(double)}</div>"
            f"<div style='font-size:10px;color:#94a3b8;'>2 ENGINES</div></div>"
            f"<div style='text-align:center;flex:1;'>"
            f"<div style='font-size:24px;font-weight:800;color:#1e293b;'>{len(power_picks)}</div>"
            f"<div style='font-size:10px;color:#94a3b8;'>TOTAL OVERLAPS</div></div>"
            f"</div></div>",
            unsafe_allow_html=True)

        # Power Pick Cards
        for p in power_picks:
            eng_count = p["engines"]
            border_color = "#b45309" if eng_count == 3 else "#4338ca"
            eng_label = "ALL 3 ENGINES" if eng_count == 3 else "2 ENGINES"
            eng_bg = "#fef3c7" if eng_count == 3 else "#e0e7ff"
            eng_tc = "#b45309" if eng_count == 3 else "#4338ca"

            # Which engines
            engines_in = []
            if p["in_b"]: engines_in.append(f"<span style='color:#3b82f6;font-weight:700;'>MOM:{p['conv']}</span>")
            if p["in_c"]: engines_in.append(f"<span style='color:#2563eb;font-weight:700;'>VAL:{p['vds']}</span>")
            if p["in_d"]: engines_in.append(f"<span style='color:#059669;font-weight:700;'>CMP:{p['dns']}</span>")
            engines_html = " · ".join(engines_in)

            mc_label, mc_color = mcap_tag(p.get("mcap"))
            opp = ((p["price"] - p["ltp"]) / p["ltp"] * 100) if p["ltp"] > 0 and p["price"] > 0 else 0
            os2, oc = fmt_pct(opp)

            # Power bar (max ~35 realistic)
            bar_pct = min(p["power"] / 35 * 100, 100)
            bar_color = "#059669" if p["power"] >= 25 else ("#2563eb" if p["power"] >= 15 else "#d97706")

            card_html = (
                f"<div class='data-card' style='border-left:4px solid {border_color};'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'>"
                f"<div style='font-weight:800;color:#1e293b;font-size:15px;'>{p['name']}</div>"
                f"<div style='font-size:14px;font-weight:800;color:{bar_color};'>PWR: {p['power']}</div></div>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;'>"
                f"<div style='font-size:12px;color:#64748b;'>₹{p['price']:,.0f}"
                f"<span style='color:{oc};margin-left:6px;'>{os2}</span></div>"
                f"<div style='display:flex;align-items:center;gap:4px;flex-wrap:wrap;'>{render_badge(eng_label, eng_bg, eng_tc)}"
                f" {'<span style=\"color:#475569;font-size:11px;font-weight:600;\">₹'+fmt(p.get('mcap'),0)+'Cr</span>' if p.get('mcap') else ''}"
                f" {render_stage_badge(mc_label)}</div></div>"
                f"<div style='margin-bottom:6px;'>"
                f"<div style='height:6px;background:#e2e8f0;border-radius:3px;'>"
                f"<div style='width:{bar_pct:.0f}%;height:100%;background:{bar_color};"
                f"border-radius:3px;'></div></div>"
                f"<div style='display:flex;justify-content:space-between;font-size:10px;color:#94a3b8;margin-top:2px;'>"
                f"<span>{engines_html}</span>"
                f"<span>Power Score</span></div></div>"
                f"<div style='display:flex;gap:6px;flex-wrap:wrap;font-size:10px;color:#94a3b8;margin-bottom:4px;'>"
                f"<span>ROE:{fmt(p.get('roe'),0)}</span>"
                f"<span>PE:{fmt(p.get('pe'),0)}</span>"
                f"<span>Pio:{fmt(p.get('piotroski'),0)}</span>"
                f"<span>D/E:{fmt(p.get('de'),1)}</span>"
                f"{'<span>PEG:'+fmt(p.get('peg'),1)+'</span>' if p.get('peg') else ''}"
                f"</div>"
            )
            if p["held"]:
                card_html += f"<div style='margin-top:2px;'>{render_badge('HELD','#94a3b8')}</div>"
            # AI ANALYST
            best_stock = d_tickers.get(p["ticker"]) or c_tickers.get(p["ticker"]) or b_tickers.get(p["ticker"]) or {}
            best_engine = "D" if p["in_d"] else ("C" if p["in_c"] else "B")
            v, vc2, ai_html = ai_analyst(best_stock, engine=best_engine, engine_score=ea, held=p["held"])
            card_html += ai_html
            card_html += "</div>"
            st.markdown(card_html, unsafe_allow_html=True)
    else:
        render_info_card("No multi-engine overlaps found. Upload watchlists to all 3 engines first.")

    # ============================================================
    # SECTOR CONCENTRATION — ALL ENGINES
    # ============================================================
    render_section_title("Sector Map — All Engines")
    all_stocks = b_wl + c_wl + d_wl
    if all_stocks:
        st.markdown(
            f"<div class='data-card'>{sector_summary(all_stocks)}</div>",
            unsafe_allow_html=True)
    else:
        render_info_card("No watchlist data.")

    # ============================================================
    # ENGINE HEALTH
    # ============================================================
    render_section_title("Engine Health")
    engines = [
        ("B · Momentum", len(b_wl), len(b_pos), 10, "#3b82f6"),
        ("C · Value", len(c_wl), len(c_pos), 15, "#2563eb"),
        ("D · Compounder", len(d_wl), len(d_pos), 15, "#059669"),
    ]
    for name, wl_count, pos_count, max_pos, color in engines:
        fill = (pos_count / max_pos * 100) if max_pos > 0 else 0
        st.markdown(
            f"<div class='data-card' style='padding:12px 18px;'>"
            f"<div style='display:flex;justify-content:space-between;margin-bottom:6px;'>"
            f"<span style='font-weight:700;color:#1e293b;font-size:12px;'>{name}</span>"
            f"<span style='font-size:11px;color:#64748b;'>{pos_count}/{max_pos} positions · {wl_count} watchlist</span></div>"
            f"<div style='height:6px;background:#e2e8f0;border-radius:3px;'>"
            f"<div style='width:{fill:.0f}%;height:100%;background:{color};border-radius:3px;'>"
            f"</div></div></div>",
            unsafe_allow_html=True)
