"""
engine_e_ui.py - Engine E: The Fortress
"Capital preservation and hedge"
Debt Duration Management + Gold Signals
"""
import streamlit as st
from utils import (
    get_engine_a_score, load_stocks_json,
    render_section_title, render_info_card, render_data_card,
    render_stat_row, render_hero_number, render_badge,
)

def show_engine_e():
    sd = get_engine_a_score()
    data = load_stocks_json()
    cap = float(data.get("_capital", data.get("capital", 100000)))

    if not sd:
        render_info_card("No Engine A score available. Run the workflow first.")
        return

    ea = int(sd["raw_score"])
    debt_pct = int(sd.get("debt_pct", 30))
    gold_pct = int(sd.get("gold_pct", 15))
    dur_signal = sd.get("duration_signal", "MEDIUM DURATION")
    gold_signal = sd.get("gold_signal", "HOLD")

    debt_amount = round(cap * debt_pct / 100)
    gold_amount = round(cap * gold_pct / 100)

    # HEADER
    st.markdown(
        "<div style='text-align:center;margin-bottom:4px;'>"
        "<div style='font-size:11px;color:#94a3b8;text-transform:uppercase;"
        "letter-spacing:2px;font-weight:600;'>Engine E</div>"
        "<div style='font-size:20px;font-weight:800;color:#1e293b;"
        "font-family:DM Sans,sans-serif;'>The Fortress</div>"
        "<div style='font-size:11px;color:#94a3b8;font-style:italic;'>"
        "Capital preservation and hedge.</div></div>",
        unsafe_allow_html=True)

    # ALLOCATION SUMMARY
    render_section_title("Allocation")
    c1, c2 = st.columns(2)
    with c1:
        render_hero_number("Debt", f"₹{debt_amount:,}", "#2563eb", f"{debt_pct}% of capital")
    with c2:
        render_hero_number("Gold", f"₹{gold_amount:,}", "#d97706", f"{gold_pct}% of capital")

    # ============================================================
    # DEBT DURATION
    # ============================================================
    render_section_title("Debt Duration Signal")

    dur_color = "#16a34a" if "LONG" in dur_signal else ("#2563eb" if "MEDIUM" in dur_signal else "#d97706")
    dur_emoji = "&#128994;" if "LONG" in dur_signal else ("&#128309;" if "MEDIUM" in dur_signal else "&#128992;")

    st.markdown(
        f"<div class='data-card' style='text-align:center;padding:24px;'>"
        f"<div style='font-size:28px;margin-bottom:8px;'>{dur_emoji}</div>"
        f"<div style='font-size:22px;font-weight:800;color:{dur_color};"
        f"font-family:DM Sans,sans-serif;letter-spacing:1px;'>{dur_signal}</div>"
        f"</div>",
        unsafe_allow_html=True)

    # Duration rules
    dur_rules = (
        render_stat_row("Accommodative + No Inversion", "LONG DURATION", "#16a34a") +
        render_stat_row("Neutral", "MEDIUM DURATION", "#2563eb") +
        render_stat_row("Tightening / Inversion", "SHORT / CASH", "#d97706")
    )
    render_data_card(dur_rules)

    # Instrument recommendations
    render_section_title("Recommended Instruments")
    if "LONG" in dur_signal:
        inst_html = (
            render_stat_row("Primary", "Gilt Mutual Funds") +
            render_stat_row("Alternative", "Long-term G-Sec Bonds") +
            render_stat_row("Example", "SBI Magnum Gilt / ICICI Gilt") +
            render_stat_row("Duration", "10+ years maturity")
        )
    elif "MEDIUM" in dur_signal:
        inst_html = (
            render_stat_row("Primary", "Corporate Bond Funds") +
            render_stat_row("Alternative", "Banking & PSU Debt Funds") +
            render_stat_row("Example", "HDFC Corporate Bond / Axis Banking") +
            render_stat_row("Duration", "3-5 years maturity")
        )
    else:
        inst_html = (
            render_stat_row("Primary", "Liquid Funds") +
            render_stat_row("Alternative", "Money Market / Overnight Funds") +
            render_stat_row("Example", "Parag Parikh Liquid / PPFAS Liquid") +
            render_stat_row("Duration", "< 91 days maturity")
        )
    render_data_card(inst_html)

    # ============================================================
    # GOLD SIGNAL
    # ============================================================
    render_section_title("Gold Signal")

    gold_color = "#16a34a" if gold_signal == "ACCUMULATE" else ("#dc2626" if gold_signal == "TRIM" else "#d97706")
    gold_emoji = "&#129351;" if gold_signal == "ACCUMULATE" else ("&#128200;" if gold_signal == "TRIM" else "&#128993;")

    st.markdown(
        f"<div class='data-card' style='text-align:center;padding:24px;'>"
        f"<div style='font-size:28px;margin-bottom:8px;'>{gold_emoji}</div>"
        f"<div style='font-size:22px;font-weight:800;color:{gold_color};"
        f"font-family:DM Sans,sans-serif;letter-spacing:1px;'>{gold_signal}</div>"
        f"</div>",
        unsafe_allow_html=True)

    # Gold rules
    gold_rules = (
        render_stat_row("GVIX > 25 OR Crude > 100 OR INR weak", "ACCUMULATE", "#16a34a") +
        render_stat_row("GVIX < 15 AND Crude < 60", "TRIM", "#dc2626") +
        render_stat_row("Everything else", "HOLD", "#d97706")
    )
    render_data_card(gold_rules)

    # Gold instruments
    render_section_title("Gold Instruments")
    gold_inst = (
        render_stat_row("ETF", "GOLDBEES (NSE)") +
        render_stat_row("Sovereign", "Sovereign Gold Bond (RBI)") +
        render_stat_row("Fund", "SBI Gold Fund / HDFC Gold Fund") +
        render_stat_row("Advantage", "SGB: 2.5% annual interest + tax-free on maturity")
    )
    render_data_card(gold_inst)

    # ============================================================
    # SUMMARY TABLE
    # ============================================================
    render_section_title("Quick Reference")
    ref_html = (
        render_stat_row("Engine A Score", f"{ea}/100") +
        render_stat_row("Debt Allocation", f"₹{debt_amount:,} ({debt_pct}%)") +
        render_stat_row("Debt Duration", dur_signal, dur_color) +
        render_stat_row("Gold Allocation", f"₹{gold_amount:,} ({gold_pct}%)") +
        render_stat_row("Gold Signal", gold_signal, gold_color) +
        render_stat_row("Total Fortress", f"₹{debt_amount + gold_amount:,}")
    )
    render_data_card(ref_html)
