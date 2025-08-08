# utils/google_sheet.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import os, json

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

def _get_creds():
    # 1) Streamlit Secrets 우선
    if "gcp_service_account" in st.secrets:
        info = dict(st.secrets["gcp_service_account"])
        # (triple-quoted라면 아래 replace 불필요하지만, 안전하게 유지)
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        return ServiceAccountCredentials.from_json_keyfile_dict(info, SCOPE)

    # 2) (옵션) 환경변수로 JSON 문자열을 넣어둔 경우
    env_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
    if env_json:
        info = json.loads(env_json)
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        return ServiceAccountCredentials.from_json_keyfile_dict(info, SCOPE)

    raise RuntimeError(
        "GCP 자격증명이 없습니다. Streamlit Secrets의 [gcp_service_account]에 키를 넣거나 "
        "환경변수 GCP_SERVICE_ACCOUNT_JSON을 설정하세요."
    )

def get_google_sheet(sheet_name: str):
    creds = _get_creds()
    client = gspread.authorize(creds)
    return client.open(sheet_name).sheet1  # 첫 번째 시트

def append_row_to_sheet(sheet_name: str, row_data: list):
    sheet = get_google_sheet(sheet_name)
    sheet.append_row(row_data)
