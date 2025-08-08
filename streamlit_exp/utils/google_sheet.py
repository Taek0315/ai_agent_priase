from __future__ import annotations

import re
from typing import Optional

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError, WorksheetNotFound

# 권장 스코프
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def _build_credentials() -> Credentials:
    """Streamlit secrets의 gcp_service_account로부터 Credentials 생성."""
    info = dict(st.secrets["gcp_service_account"])
    pk = info.get("private_key", "")
    # \n 이스케이프가 들어온 경우 실제 개행으로 교체 (삼중따옴표면 영향 없음)
    if isinstance(pk, str) and "\\n" in pk and "-----BEGIN PRIVATE KEY-----" in pk:
        info["private_key"] = pk.replace("\\n", "\n")
    return Credentials.from_service_account_info(info, scopes=SCOPES)

@st.cache_resource(show_spinner=False)
def _get_client() -> gspread.Client:
    """gspread 클라이언트 캐싱."""
    creds = _build_credentials()
    return gspread.authorize(creds)

def _extract_id_from_url(url: str) -> Optional[str]:
    m = re.search(r"/d/([a-zA-Z0-9-_]+)/", url)
    return m.group(1) if m else None

def _open_spreadsheet() -> gspread.Spreadsheet:
    """secrets의 id 우선, 없으면 url로 스프레드시트 오픈."""
    gs_conf = st.secrets.get("google_sheet", {})
    sheet_id = gs_conf.get("id")
    sheet_url = gs_conf.get("url")
    client = _get_client()

    if sheet_id:
        return client.open_by_key(sheet_id)
    if sheet_url:
        sid = _extract_id_from_url(sheet_url)
        return client.open_by_key(sid) if sid else client.open_by_url(sheet_url)

    raise RuntimeError("Secrets에 [google_sheet.id] 또는 [google_sheet.url]을 설정하세요.")

def get_google_sheet(worksheet: str | int | None = None) -> gspread.Worksheet:
    """
    워크시트 핸들 반환.
    - None  -> secrets의 [google_sheet.worksheet] 또는 'resp'
    - str   -> 해당 이름 워크시트
    - int   -> 0-based 인덱스
    """
    sh = _open_spreadsheet()
    if worksheet is None:
        worksheet = st.secrets.get("google_sheet", {}).get("worksheet", "resp")
    if isinstance(worksheet, str):
        try:
            return sh.worksheet(worksheet)
        except WorksheetNotFound:
            return sh.sheet1
    if isinstance(worksheet, int):
        return sh.get_worksheet(worksheet)
    raise ValueError("worksheet는 None, str, int 중 하나여야 합니다.")

def append_row_to_sheet(row: list, worksheet: str | int | None = None) -> None:
    """한 행 추가 (RAW 입력)."""
    ws = get_google_sheet(worksheet)
    try:
        ws.append_row(row, value_input_option="RAW")
    except APIError as e:
        raise RuntimeError(f"행 추가 중 오류가 발생했습니다: {e}") from e
