from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _service_account_info() -> Optional[Dict[str, Any]]:
    try:
        info = dict(st.secrets["gcp_service_account"])
        if info:
            return info
    except Exception:
        pass
    env_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if env_json:
        try:
            return json.loads(env_json)
        except json.JSONDecodeError:
            raise RuntimeError("Invalid JSON in GOOGLE_APPLICATION_CREDENTIALS_JSON.")
    return None


def _client() -> gspread.Client:
    info = _service_account_info()
    if not info:
        raise RuntimeError(
            "No Google credentials. On Streamlit Cloud, set `gcp_service_account` in Secrets. "
            "For local dev, set env GOOGLE_APPLICATION_CREDENTIALS_JSON with the full JSON."
        )
    pk = info.get("private_key")
    if isinstance(pk, str) and "\\n" in pk and "BEGIN PRIVATE KEY" in pk:
        info["private_key"] = pk.replace("\\n", "\n")
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def get_google_sheet():
    client = _client()
    gs_conf = _sheet_config()
    sheet_id = (
        gs_conf.get("spreadsheet_id")
        or gs_conf.get("id")
        or os.getenv("GOOGLE_SHEET_ID")
    )
    sheet_url = (
        gs_conf.get("spreadsheet_url")
        or gs_conf.get("url")
        or os.getenv("GOOGLE_SHEET_URL")
    )
    if sheet_id:
        return client.open_by_key(sheet_id)
    if sheet_url:
        return client.open_by_url(sheet_url)
    raise RuntimeError("Missing Google Sheet identifier. Set secrets [sheets] spreadsheet_id or spreadsheet_url.")


def append_row_to_sheet(row: List[Any], worksheet: str = "resp") -> None:
    sh = get_google_sheet()
    try:
        ws = sh.worksheet(worksheet)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.sheet1
    ws.append_row(row, value_input_option="RAW")


def _sheet_config() -> Dict[str, Any]:
    try:
        config = dict(st.secrets["sheets"])
        if config:
            return config
    except Exception:
        pass
    try:
        legacy = dict(getattr(st.secrets, "google_sheet", {}) or {})
    except Exception:
        legacy = {}
    return legacy
