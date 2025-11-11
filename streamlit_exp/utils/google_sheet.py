from __future__ import annotations

import json
import os
from typing import Any, List, Optional

import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _creds_from_secrets() -> Optional[Credentials]:
    try:
        info = dict(st.secrets["gcp_service_account"])
    except Exception:
        return None
    pk = info.get("private_key")
    if isinstance(pk, str) and "\\n" in pk and "BEGIN PRIVATE KEY" in pk:
        info["private_key"] = pk.replace("\\n", "\n")
    return Credentials.from_service_account_info(info, scopes=SCOPES)


def _creds_from_file() -> Optional[Credentials]:
    # Local-dev fallback ONLY. Streamlit Cloud should use st.secrets.
    path = (
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        or os.getenv("GCP_CREDENTIALS_PATH")
        or os.getenv("SERVICE_ACCOUNT_JSON")
    )
    if not path or not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        info = json.load(f)
    pk = info.get("private_key")
    if isinstance(pk, str) and "\\n" in pk and "BEGIN PRIVATE KEY" in pk:
        info["private_key"] = pk.replace("\\n", "\n")
    return Credentials.from_service_account_info(info, scopes=SCOPES)


def _client() -> gspread.Client:
    creds = _creds_from_secrets() or _creds_from_file()
    if not creds:
        raise RuntimeError(
            "No Google credentials. On Streamlit Cloud, set `gcp_service_account` in Secrets. "
            "For local dev, set env GOOGLE_APPLICATION_CREDENTIALS_JSON / GCP_CREDENTIALS_PATH."
        )
    return gspread.authorize(creds)


def get_google_sheet():
    client = _client()
    gs_conf = getattr(st.secrets, "google_sheet", {}) or {}
    sheet_id = gs_conf.get("id") or os.getenv("GOOGLE_SHEET_ID")
    sheet_url = gs_conf.get("url") or os.getenv("GOOGLE_SHEET_URL")
    if sheet_id:
        return client.open_by_key(sheet_id)
    if sheet_url:
        return client.open_by_url(sheet_url)
    raise RuntimeError("Missing Google Sheet identifier. Set secrets [google_sheet] id/url.")


def append_row_to_sheet(row: List[Any], worksheet: str = "resp") -> None:
    sh = get_google_sheet()
    try:
        ws = sh.worksheet(worksheet)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.sheet1
    ws.append_row(row, value_input_option="RAW")
