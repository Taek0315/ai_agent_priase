import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import json, os

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

def _get_creds():
    info = dict(st.secrets["gcp_service_account"])
    if "private_key" in info and "\\n" in info["private_key"]:
        info["private_key"] = info["private_key"].replace("\\n", "\n")
    return ServiceAccountCredentials.from_json_keyfile_dict(info, SCOPE)

def get_google_sheet(_unused_sheet_name: str = None):
    creds = _get_creds()
    client = gspread.authorize(creds)

    # ✅ ID 로 직접 열기 (제목 이슈 회피)
    sheet_id = st.secrets["google_sheet"]["id"]
    return client.open_by_url(st.secrets["google_sheet"]["url"]).sheet1
    # 또는 url로 저장했다면: return client.open_by_url(st.secrets["google_sheet"]["url"]).sheet1

def append_row_to_sheet(_unused_sheet_name: str, row_data: list):
    sheet = get_google_sheet()
    sheet.append_row(row_data)
