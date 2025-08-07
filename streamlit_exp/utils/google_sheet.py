# utils/google_sheet.py

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# 인증 및 시트 연결 함수
def get_google_sheet(sheet_name):
    # 현재 디렉토리 기준 JSON 경로 설정
    JSON_PATH = os.path.join(os.path.dirname(__file__), "..", "ai-agent-priase-a24b2b876831.json")

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_PATH, scope)
    client = gspread.authorize(creds)

    sheet = client.open(sheet_name).sheet1  # 첫 번째 시트 사용
    return sheet

# 데이터 한 줄 추가 함수
def append_row_to_sheet(sheet_name, row_data):
    sheet = get_google_sheet(sheet_name)
    sheet.append_row(row_data)
