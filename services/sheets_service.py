"""Google Sheets API 서비스"""

import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import SCOPES


@st.cache_resource
def get_google_sheets_service():
    """Google Sheets 서비스 객체를 반환합니다."""
    info = st.secrets["google_service_account"]
    service_account_info = dict(info)
    service_account_info["private_key"] = service_account_info["private_key"].replace("\\n", "\n")
    
    credentials = service_account.Credentials.from_service_account_info(service_account_info)
    return build("sheets", "v4", credentials=credentials)


@st.cache_data
def get_sheet_list(_service):
    """상담데이터 시트 목록을 조회합니다."""
    if not _service:
        return []

    try:
        spreadsheet = _service.spreadsheets().get(spreadsheetId=st.secrets["SPREADSHEET_ID"]).execute()
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
        range_name = f"{sheet_name}!A:Z"
        result = service.spreadsheets().values().get(
            spreadsheetId=st.secrets["SPREADSHEET_ID"], 
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