import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import json, os

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

def _get_creds():
    # ✅ Streamlit Secrets에서 서비스계정 정보 읽기
    if "gcp_service_account" in st.secrets:
        info = dict(st.secrets["gcp_service_account"])
        # Secrets에 "\n"로 저장했을 때 실제 줄바꿈으로 치환
        if "private_key" in info and "\\n" in info["private_key"]:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        return ServiceAccountCredentials.from_json_keyfile_dict(info, SCOPE)

    # (옵션) 환경변수로 JSON 통째로 넣은 경우
    env_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
    if env_json:
        info = json.loads(env_json)
        if "private_key" in info and "\\n" in info["private_key"]:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        return ServiceAccountCredentials.from_json_keyfile_dict(info, SCOPE)

    raise RuntimeError("GCP 자격증명을 찾을 수 없습니다. Secrets의 [gcp_service_account]를 확인하세요.")

def get_google_sheet(sheet_name: str):
    creds = _get_creds()
    client = gspread.authorize(creds)
    return client.open(sheet_name).sheet1  # 첫 번째 시트

def append_row_to_sheet(sheet_name: str, row_data: list):
    sheet = get_google_sheet(sheet_name)
    sheet.append_row(row_data)
