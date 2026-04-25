"""
engine_c_ui.py - Engine C: Long-Term Compounders
REBUILT from scratch — Session 7
"""
import streamlit as st
import pandas as pd
import json
import base64
import requests
import io
from pathlib import Path

# ============================================================
# CONSTANTS
# ============================================================
SCORE_FILE = Path("data/engine_a_score.csv")
PRICES_FILE = Path("data/engine_b_prices.csv")
STOCKS_FILE = Path("data/engine_b_stocks.json")
REPO_OWNER = "abhiarjun231-netizen"
REPO_NAME = "Engine-A-Dashboard"
STOCKS_PATH = "data/engine_b_stocks.json"

# ============================================================
# GITHUB API HELPERS
# ============================================================
def get_github_token():
    return st.secrets.get("GITHUB_TOKEN", "")

def get_file_from_github(token):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{STOCKS_PATH}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content), data["sha"]
    return None, None

def save_file_to_github(token, new_content, sha, message):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{STOCKS_PATH}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    encoded = base64.b64encode(json.dumps(new_content, indent=2).encode("utf-8")).decode("utf-8")
    body = {"message": message, "content": encoded, "sha": sha}
    resp = requests.put(url, headers=headers, json=body)
    return resp.status_code in [200, 201]

def trigger_workflow(token):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/test.yml/dispatches"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    resp = requests.post(url, headers=headers, json={"ref": "main"})
    return resp.status_code == 204

# ============================================================
# MAIN DISPLAY FUNCTION
# ============================================================
def show_engine_c():
    st.markdown(
        "<div style='background:#1e293b;border-radius:12px;padding:24px 16px;"
        "border:1px solid #334155;text-align:center;margin-bottom:16px;'>"
        "<div style='font-size:18px;font-weight:700;color:#e2e8f0;margin-bottom:8px;'>"
        "Engine C — Rebuilding</div>"
        "<div style='font-size:13px;color:#64748b;'>"
        "Fresh start. New features coming step by step.</div>"
        "</div>",
        unsafe_allow_html=True
    )
