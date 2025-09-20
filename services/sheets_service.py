"""Google Sheets API 서비스"""
import json
import os

import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import SCOPES
from dotenv import load_dotenv

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


@st.cache_resource
def get_google_sheets_service():
    """Google Sheets 서비스 객체 반환"""
    google_service_account = os.environ.get("GOOGLE_SERVICE_ACCOUNT")
    service_account_info = None

    if google_service_account:
        try:
            service_account_info = json.loads(google_service_account)
        except json.JSONDecodeError:
            st.error("GOOGLE_SERVICE_ACCOUNT 환경변수 형식이 올바르지 않습니다.")
            return None
    else:
        try:
            with open("token.json", "r") as f:
                service_account_info = json.load(f)
        except FileNotFoundError:
            st.error("token.json 파일을 찾을 수 없고 GOOGLE_SERVICE_ACCOUNT 환경변수도 설정되지 않았습니다.")
            return None

    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=credentials)


@st.cache_data
def get_sheet_list(_service):
    """상담데이터 시트 목록을 조회합니다."""
    if not _service:
        return []

    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    if not spreadsheet_id:
        st.error("SPREADSHEET_ID 환경변수가 설정되지 않았습니다.")
        return []

    try:
        spreadsheet = _service.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()

        sheets = []
        for sheet in spreadsheet.get("sheets", []):
            title = sheet.get("properties", {}).get("title")
            if title and ("상담데이터" in title or "상담 데이터" in title):
                sheets.append(title)

        return sorted(sheets, reverse=True)

    except Exception as e:
        st.error(f"시트 목록 조회 실패: {str(e)}")
        return []

def load_sheet_data(sheet_name):
    """시트 데이터를 로드합니다."""
    service = get_google_sheets_service()
    if not service:
        return None

    try:
        
        spreadsheet_id = os.environ.get("SPREADSHEET_ID")
        if not spreadsheet_id:
            st.error("SPREADSHEET_ID가 .env 파일에 설정되지 않았습니다.")
            return None
            
        range_name = f"{sheet_name}!A:Z"
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, 
            range=range_name
        ).execute()

        values = result.get("values", [])
        if not values or len(values) < 2:
            st.error("시트에 충분한 데이터가 없습니다.")
            return None

        headers = values[0]
        data_rows = values[1:]

        # 행 길이 정규화
        for row in data_rows:
            while len(row) < len(headers):
                row.append("")
            if len(row) > len(headers):
                row[:] = row[:len(headers)]

        return pd.DataFrame(data_rows, columns=headers)

    except Exception as e:
        st.error(f"데이터 로드 실패: {str(e)}")
        return None