# utils/google_sheet.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

def _get_creds():
    info = dict(st.secrets["gcp_service_account"])
    if "private_key" in info and "\\n" in info["private_key"]:
        info["private_key"] = info["private_key"].replace("\\n", "\n")
    return ServiceAccountCredentials.from_json_keyfile_dict(info, SCOPE)

def get_google_sheet():
    creds = _get_creds()
    client = gspread.authorize(creds)

    # ✅ id 우선, 없으면 url 사용
    gs_conf = st.secrets.get("google_sheet", {})
    sheet_id = gs_conf.get("id")
    sheet_url = gs_conf.get("url")

    if sheet_id:
        return client.open_by_key(sheet_id).sheet1
    if sheet_url:
        return client.open_by_url(sheet_url).sheet1

    raise RuntimeError("Secrets에 [google_sheet.id] 또는 [google_sheet.url]을 설정하세요.")

def append_row_to_sheet(_unused, row_data):
    sheet = get_google_sheet()
    sheet.append_row(row_data)
