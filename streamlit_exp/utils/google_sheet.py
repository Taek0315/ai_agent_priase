from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import gspread
from google.oauth2.service_account import Credentials
from gspread.utils import rowcol_to_a1

from .persistence import get_cfg

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _service_account_info() -> Optional[Dict[str, Any]]:
    try:
        cfg = get_cfg()
    except RuntimeError:
        cfg = {}
    info = dict(cfg.get("service_account") or {})
    if info:
        return info
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
    sheet_id = gs_conf.get("spreadsheet_id") or os.getenv("GOOGLE_SHEET_ID")
    sheet_url = gs_conf.get("spreadsheet_url") or os.getenv("GOOGLE_SHEET_URL")
    if sheet_id:
        return client.open_by_key(sheet_id)
    if sheet_url:
        return client.open_by_url(sheet_url)
    raise RuntimeError("Missing Google Sheet identifier. Set secrets [sheets] spreadsheet_id or spreadsheet_url.")


def append_row_to_sheet(
    row: List[Any], worksheet: str = "resp", header: Optional[List[Any]] = None
) -> None:
    sh = get_google_sheet()
    try:
        ws = sh.worksheet(worksheet)
    except gspread.exceptions.WorksheetNotFound:
        target_cols = len(header) if header else max(1, len(row))
        target_rows = max(2, len(row) + 1)
        ws = sh.add_worksheet(title=worksheet, rows=target_rows, cols=target_cols)
    if header:
        expected_cols = len(header)
        if ws.col_count < expected_cols:
            ws.resize(rows=ws.row_count, cols=expected_cols)
        existing_header = ws.row_values(1)
        normalized_existing = existing_header + [""] * (expected_cols - len(existing_header))
        if normalized_existing[:expected_cols] != list(header):
            header_range = f"A1:{rowcol_to_a1(1, expected_cols)}"
            ws.update(header_range, [list(header)])
    ws.append_row(row, value_input_option="RAW")


def _sheet_config() -> Dict[str, Any]:
    try:
        return get_cfg()
    except RuntimeError:
        return {}
