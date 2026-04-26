"""
App.py - Investment Dashboard v5.0
5-Engine System · Premium White Theme · Safe Imports
"""
import streamlit as st

st.set_page_config(page_title="Investment Dashboard", layout="wide", initial_sidebar_state="collapsed")

# --- PREMIUM WHITE THEME CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
    .stApp { background-color: #f8fafc; font-family: 'DM Sans', sans-serif; }
    [data-testid="stHeader"] { background-color: #f8fafc; }
    [data-testid="stToolbar"] { display: none; }
    footer { display: none; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px; background-color: #ffffff; border-radius: 14px; padding: 5px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px; color: #94a3b8; font-weight: 600; font-size: 13px;
        padding: 8px 12px; font-family: 'DM Sans', sans-serif; transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1e293b; color: #ffffff;
        box-shadow: 0 2px 8px rgba(30,41,59,0.25);
    }
    .score-card {
        background: #ffffff; border-radius: 20px; padding: 36px 20px;
        border: 1px solid #e2e8f0; text-align: center; margin-bottom: 16px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.04);
    }
    .score-title {
        font-size: 12px; font-weight: 700; color: #94a3b8; text-transform: uppercase;
        letter-spacing: 2px; margin-bottom: 8px; font-family: 'DM Sans', sans-serif;
    }
    .score-number {
        font-size: 76px; font-weight: 800; line-height: 1; margin: 12px 0;
        font-family: 'DM Sans', sans-serif;
    }
    .score-denominator { font-size: 18px; color: #94a3b8; margin-bottom: 10px; font-weight: 500; }
    .score-condition {
        font-size: 20px; font-weight: 700; letter-spacing: 4px;
        text-transform: uppercase; margin-bottom: 10px;
    }
    .score-timestamp { font-size: 12px; color: #94a3b8; font-weight: 500; }
    .section-title {
        font-size: 12px; font-weight: 700; color: #94a3b8; text-transform: uppercase;
        letter-spacing: 2px; margin: 28px 0 14px 0; font-family: 'DM Sans', sans-serif;
    }
    .alloc-tile {
        background: #ffffff; border-radius: 16px; padding: 20px 10px;
        border: 1px solid #e2e8f0; text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03); transition: transform 0.15s ease;
    }
    .alloc-tile:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.07); }
    .alloc-label {
        font-size: 11px; color: #94a3b8; text-transform: uppercase;
        letter-spacing: 1.5px; margin-bottom: 6px; font-weight: 600;
    }
    .alloc-pct { font-size: 30px; font-weight: 800; font-family: 'DM Sans', sans-serif; }
    .alloc-sub { font-size: 11px; color: #94a3b8; margin-top: 6px; line-height: 1.5; font-weight: 500; }
    .safety-row { display: flex; gap: 12px; margin: 16px 0; }
    .safety-badge {
        flex: 1; background: #ffffff; border-radius: 14px; padding: 14px;
        border: 1px solid #e2e8f0; text-align: center; box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }
    .safety-badge .label {
        font-size: 10px; color: #94a3b8; text-transform: uppercase;
        letter-spacing: 1.5px; margin-bottom: 6px; font-weight: 600;
    }
    .safety-badge .value.ok { color: #10b981; font-weight: 700; font-size: 14px; }
    .safety-badge .value.bad { color: #ef4444; font-weight: 700; font-size: 14px; }
    .data-card {
        background: #ffffff; border-radius: 16px; padding: 8px 18px;
        border: 1px solid #e2e8f0; margin-bottom: 14px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }
    .data-row {
        display: flex; align-items: center; justify-content: space-between;
        padding: 10px 0; border-bottom: 1px solid #f1f5f9;
    }
    .data-row:last-child { border-bottom: none; }
    .data-label { color: #64748b; font-size: 13px; font-weight: 500; }
    .data-value { color: #1e293b; font-weight: 700; font-size: 13px; font-family: 'DM Sans', sans-serif; }
    .input-card-label { color: #1e293b; font-weight: 600; font-size: 14px; margin-top: 14px; }
    .input-card-current { color: #94a3b8; font-size: 12px; margin-bottom: 4px; font-weight: 500; }
    div[data-testid="stExpander"] {
        background-color: #ffffff; border: 1px solid #e2e8f0;
        border-radius: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }
    div[data-testid="stExpander"] summary { font-weight: 600; color: #1e293b; }
    .stButton > button {
        background: linear-gradient(135deg, #f8fafc, #ffffff); color: #1e293b;
        border: 1px solid #e2e8f0; border-radius: 12px; font-weight: 600;
        font-size: 14px; padding: 10px 20px; font-family: 'DM Sans', sans-serif;
        transition: all 0.2s ease; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .stButton > button:hover {
        background: #ffffff; border-color: #cbd5e1;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08); transform: translateY(-1px);
    }
    .stButton > button:active { transform: translateY(0px); }
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #3b82f6, #2563eb); color: #ffffff;
        border: none; box-shadow: 0 4px 14px rgba(59,130,246,0.35);
    }
    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="stBaseButton-primary"]:hover {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        box-shadow: 0 6px 20px rgba(59,130,246,0.45); transform: translateY(-1px);
    }
    [data-testid="stHorizontalBlock"] { gap: 10px; }
    input[type="number"] {
        background: #f8fafc !important; border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important; color: #1e293b !important;
    }
    div[data-baseweb="select"] > div {
        background: #f8fafc !important; border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
    }
    div[data-testid="stAlert"] { border-radius: 12px; font-family: 'DM Sans', sans-serif; }
</style>
""", unsafe_allow_html=True)

# --- SAFE IMPORTS ---
from engine_a_ui import show_engine_a

try:
    from engine_b_ui import show_engine_b
    engine_b_ok = True
except Exception as e:
    engine_b_ok = False
    engine_b_error = str(e)

try:
    from engine_c_ui import show_engine_c
    engine_c_ok = True
except Exception as e:
    engine_c_ok = False
    engine_c_error = str(e)

try:
    from engine_d_ui import show_engine_d
    engine_d_ok = True
except Exception as e:
    engine_d_ok = False
    engine_d_error = str(e)

try:
    from engine_e_ui import show_engine_e
    engine_e_ok = True
except Exception as e:
    engine_e_ok = False
    engine_e_error = str(e)

# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Director", "Momentum", "Value", "Compounder", "Fortress"
])

with tab1:
    show_engine_a()

with tab2:
    if engine_b_ok:
        show_engine_b()
    else:
        st.error(f"Engine B failed to load: {engine_b_error}")

with tab3:
    if engine_c_ok:
        show_engine_c()
    else:
        st.error(f"Engine C failed to load: {engine_c_error}")

with tab4:
    if engine_d_ok:
        show_engine_d()
    else:
        st.error(f"Engine D failed to load: {engine_d_error}")

with tab5:
    if engine_e_ok:
        show_engine_e()
    else:
        st.error(f"Engine E failed to load: {engine_e_error}")

# --- FOOTER ---
st.markdown(
    "<div style='text-align:center;color:#94a3b8;font-size:11px;"
    "margin-top:40px;padding:16px;letter-spacing:1.5px;font-weight:500;"
    "font-family:DM Sans,sans-serif;'>"
    "INVESTMENT DASHBOARD V5.0 · 5-ENGINE SYSTEM · EMOTION-FREE SYSTEMATIC INVESTING"
    "</div>",
    unsafe_allow_html=True
)
