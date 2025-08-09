import base64
import io
import os
import os.path
from collections import Counter
from typing import Any, Dict, List

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from pydantic import BaseModel

# matplotlib 백엔드 설정
matplotlib.use("Agg")
# 한글 폰트 설정
try:
    # macOS
    plt.rcParams["font.family"] = "AppleGothic"
except:
    try:
        # Windows
        plt.rcParams["font.family"] = "Malgun Gothic"
    except:
        # Linux
        plt.rcParams["font.family"] = "DejaVu Sans"

plt.rcParams["axes.unicode_minus"] = False

load_dotenv()

app = FastAPI(title="Saladlab DOGE", version="1.0.0")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
if not SPREADSHEET_ID:
    raise ValueError("SPREADSHEET_ID 환경변수가 설정되지 않았습니다.")


class SheetAnalysisRequest(BaseModel):
    sheet_name: str


class SheetListResponse(BaseModel):
    sheets: List[Dict[str, Any]]


class TagAnalysisResponse(BaseModel):
    tag_counts: Dict[str, int]
    category_counts: Dict[str, Dict[str, int]]
    new_sheet_name: str
    success: bool


class ChartRequest(BaseModel):
    sheet_name: str
    chart_start_row: int = 1  # 차트 시작 행
    chart_width: int = 1050  # 차트 너비(px)
    chart_height: int = 500  # 차트 높이(px)
    charts_per_row: int = 1  # 한 행에 1개씩 배치


class ChartResponse(BaseModel):
    charts: Dict[str, str]  # category_name: base64_encoded_image
    success: bool


class SheetsChartResponse(BaseModel):
    chart_ids: List[int]  # Google Sheets chart IDs
    sheet_name: str
    success: bool


def get_google_sheets_service():
    """Google Sheets API 서비스 객체를 반환합니다."""
    if not os.path.exists("token.json"):
        raise FileNotFoundError("token.json 파일을 찾을 수 없습니다.")

    creds = Credentials.from_service_account_file("token.json", scopes=SCOPES)
    service = build("sheets", "v4", credentials=creds)
    return service


@app.get("/")
async def root():
    return {"message": "Google Sheets Analyzer API"}


@app.get("/sheets", response_model=SheetListResponse)
async def get_all_sheets():
    """스프레드시트의 모든 시트 목록을 조회합니다."""
    try:
        service = get_google_sheets_service()
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()

        sheets = []
        for sheet in spreadsheet.get("sheets", []):
            sheet_properties = sheet.get("properties", {})
            sheets.append(
                {
                    "sheet_id": sheet_properties.get("sheetId"),
                    "title": sheet_properties.get("title"),
                    "index": sheet_properties.get("index"),
                    "sheet_type": sheet_properties.get("sheetType", "GRID"),
                    "grid_properties": sheet_properties.get("gridProperties", {}),
                }
            )

        return SheetListResponse(sheets=sheets)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시트 목록 조회 실패: {str(e)}")


def parse_tags(tag_string: str) -> List[str]:
    """태그 문자열을 파싱하여 개별 태그 리스트로 반환합니다."""
    if not tag_string or pd.isna(tag_string):
        return []

    tags = [tag.strip() for tag in str(tag_string).split(",")]
    return [tag for tag in tags if tag]


def analyze_tags(df: pd.DataFrame, tag_column: str = "tags") -> Dict[str, int]:
    """태그 열을 분석하여 각 태그별 개수를 반환합니다."""
    if tag_column not in df.columns:
        raise ValueError(f"'{tag_column}' 열을 찾을 수 없습니다.")

    all_tags = []
    for tag_string in df[tag_column]:
        tags = parse_tags(tag_string)
        all_tags.extend(tags)

    tag_counts = Counter(all_tags)
    return dict(tag_counts)


def categorize_tags_advanced(tag_counts: Dict[str, int]) -> Dict[str, Dict[str, int]]:
    """태그를 대분류, 중분류에 따라 세분화하여 분류합니다."""
    categories = {
        "리뷰_상담태그": {},
        "리뷰_도입_상담태그": {},
        "업셀_상담태그": {},
        "업셀_도입_상담태그": {},
        "푸시_상담태그": {},
        "푸시_도입_상담태그": {},
        "기타": {},
    }

    for tag, count in tag_counts.items():
        if "/" not in tag:
            categories["기타"][tag] = count
            continue

        parts = tag.split("/")
        if len(parts) < 2:
            categories["기타"][tag] = count
            continue

        first_category = parts[0]
        second_category = parts[1]
        is_intro = "도입문의" in second_category

        if first_category == "리뷰":
            key = "리뷰_도입_상담태그" if is_intro else "리뷰_상담태그"
        elif first_category == "업셀":
            key = "업셀_도입_상담태그" if is_intro else "업셀_상담태그"
        elif first_category == "푸시":
            key = "푸시_도입_상담태그" if is_intro else "푸시_상담태그"
        else:
            key = "기타"

        categories[key][tag] = count

    return categories


@app.post("/analyze", response_model=TagAnalysisResponse)
async def analyze_sheet_and_create_summary(request: SheetAnalysisRequest):
    """특정 시트의 태그를 분석하고 새로운 정리 시트를 생성합니다."""
    try:
        service = get_google_sheets_service()
        sheet_name = request.sheet_name

        # 1. 기존 시트에서 데이터 읽기
        range_name = f"{sheet_name}!A:Z"
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range=range_name)
            .execute()
        )

        values = result.get("values", [])
        if not values or len(values) < 2:
            raise HTTPException(
                status_code=404, detail="시트에 충분한 데이터가 없습니다."
            )

        # 2. DataFrame으로 변환
        headers = values[0]
        data_rows = values[1:]

        for i, row in enumerate(data_rows):
            while len(row) < len(headers):
                row.append("")

        df = pd.DataFrame(data_rows, columns=headers)

        # 3. 태그 분석
        tag_counts = analyze_tags(df, "tags")
        category_counts = categorize_tags_advanced(tag_counts)

        # 4. 새로운 시트 생성 (기존 시트가 있으면 삭제)
        new_sheet_name = f"[beta]{sheet_name}_분석"

        # 기존 시트 확인 및 삭제
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        existing_sheet_id = None
        for sheet in spreadsheet.get("sheets", []):
            if sheet["properties"]["title"] == new_sheet_name:
                existing_sheet_id = sheet["properties"]["sheetId"]
                break

        requests = []
        if existing_sheet_id:
            requests.append({"deleteSheet": {"sheetId": existing_sheet_id}})

        requests.append(
            {
                "addSheet": {
                    "properties": {
                        "title": new_sheet_name,
                        "gridProperties": {
                            "rowCount": 1000,
                            "columnCount": 50,  # S열 이후 차트를 위해 50열로 확장
                        },
                    }
                }
            }
        )

        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID, body={"requests": requests}
        ).execute()

        # 5. 새로 생성된 시트의 ID 가져오기
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        new_sheet_id = None
        for sheet in spreadsheet.get("sheets", []):
            if sheet["properties"]["title"] == new_sheet_name:
                new_sheet_id = sheet["properties"]["sheetId"]
                break

        # 6. 6개 테이블 데이터 준비 및 생성
        categories = [
            (category_counts.get("리뷰_상담태그", {}), "리뷰 상담태그", 0),
            (category_counts.get("리뷰_도입_상담태그", {}), "리뷰 도입 상담태그", 3),
            (category_counts.get("업셀_상담태그", {}), "업셀 상담태그", 6),
            (category_counts.get("업셀_도입_상담태그", {}), "업셀 도입 상담태그", 9),
            (category_counts.get("푸시_상담태그", {}), "푸시 상담태그", 12),
            (category_counts.get("푸시_도입_상담태그", {}), "푸시 도입 상담태그", 15),
        ]

        # 최대 행 수 계산
        max_rows = max([len(tags) + 4 for tags, _, _ in categories if tags] + [10])
        sheet_data = [[""] * 18 for _ in range(max_rows)]

        # 각 카테고리별 테이블 생성
        for tags, title, start_col in categories:
            if not tags:
                continue

            # 테이블 데이터 생성
            table_data = [[title, "개수"]]
            sorted_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)
            for tag, count in sorted_tags:
                table_data.append([tag, count])
            table_data.append(["", ""])  # 빈 행 추가
            table_data.append(["소계", sum(tags.values())])

            # sheet_data에 데이터 복사
            for i, row in enumerate(table_data):
                if i < len(sheet_data):
                    sheet_data[i][start_col] = row[0]
                    sheet_data[i][start_col + 1] = row[1]

        # 7. 데이터를 시트에 입력
        range_name = f"{new_sheet_name}!A1:R{max_rows}"
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption="RAW",
            body={"values": sheet_data},
        ).execute()

        # 8. 테이블 생성
        table_requests = []
        for tags, title, start_col in categories:
            if not tags:
                continue

            table_requests.append(
                {
                    "addTable": {
                        "table": {
                            "range": {
                                "sheetId": new_sheet_id,
                                "startRowIndex": 0,
                                "endRowIndex": len(tags) + 1,
                                "startColumnIndex": start_col,
                                "endColumnIndex": start_col + 2,
                            }
                        }
                    }
                }
            )

        if table_requests:
            service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID, body={"requests": table_requests}
            ).execute()

        # 9. 소계 행 서식 적용
        format_requests = []
        for tags, title, start_col in categories:
            if not tags:
                continue

            subtotal_row = len(tags) + 1
            format_requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": new_sheet_id,
                            "startRowIndex": subtotal_row,
                            "endRowIndex": subtotal_row + 1,
                            "startColumnIndex": start_col,
                            "endColumnIndex": start_col + 2,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "textFormat": {"bold": True},
                                "backgroundColor": {
                                    "red": 0.9,
                                    "green": 0.9,
                                    "blue": 0.9,
                                },
                            }
                        },
                        "fields": "userEnteredFormat.textFormat.bold,userEnteredFormat.backgroundColor",
                    }
                }
            )

        if format_requests:
            service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID, body={"requests": format_requests}
            ).execute()

        return TagAnalysisResponse(
            tag_counts=tag_counts,
            category_counts=category_counts,
            new_sheet_name=new_sheet_name,
            success=True,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 실패: {str(e)}")


def create_bar_chart(data: Dict[str, int], title: str) -> str:
    """막대 그래프를 생성하고 base64 인코딩된 이미지를 반환합니다."""
    if not data:
        return ""

    # 데이터 정렬 (내림차순)
    sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)
    tags = [item[0] for item in sorted_data]
    counts = [item[1] for item in sorted_data]

    # 카테고리별 색상 설정
    if "리뷰" in title:
        color = "#4285F4"  # Google Blue
        edge_color = "#1a73e8"
    elif "업셀" in title:
        color = "#34A853"  # Google Green
        edge_color = "#137333"
    elif "푸시" in title:
        color = "#EA4335"  # Google Red
        edge_color = "#d33b2c"
    else:
        color = "#9AA0A6"  # Google Grey
        edge_color = "#5f6368"

    # 그래프 생성
    plt.figure(figsize=(12, 8))
    bars = plt.bar(
        range(len(tags)), counts, color=color, edgecolor=edge_color, alpha=0.8
    )

    # 그래프 설정
    plt.title(title, fontsize=16, fontweight="bold", pad=20)
    plt.xlabel("태그", fontsize=12)
    plt.ylabel("개수", fontsize=12)

    # x축 레이블 설정 (회전)
    plt.xticks(range(len(tags)), tags, rotation=45, ha="right")

    # 값 표시
    for bar, count in zip(bars, counts):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.1,
            str(count),
            ha="center",
            va="bottom",
            fontweight="bold",
        )

    plt.tight_layout()

    # 이미지를 base64로 인코딩
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    plt.close()

    return image_base64


@app.post("/charts", response_model=ChartResponse)
async def create_charts_for_analysis(request: ChartRequest):
    """분석된 데이터를 기반으로 6개의 막대 그래프를 생성합니다."""
    try:
        service = get_google_sheets_service()
        sheet_name = request.sheet_name

        # 1. 기존 시트에서 데이터 읽기
        range_name = f"{sheet_name}!A:Z"
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range=range_name)
            .execute()
        )

        values = result.get("values", [])
        if not values or len(values) < 2:
            raise HTTPException(
                status_code=404, detail="시트에 충분한 데이터가 없습니다."
            )

        # 2. DataFrame으로 변환
        headers = values[0]
        data_rows = values[1:]

        for i, row in enumerate(data_rows):
            while len(row) < len(headers):
                row.append("")

        df = pd.DataFrame(data_rows, columns=headers)

        # 3. 태그 분석
        tag_counts = analyze_tags(df, "tags")
        category_counts = categorize_tags_advanced(tag_counts)

        # 4. 6개 카테고리에 대한 그래프 생성
        charts = {}
        categories = [
            ("리뷰_상담태그", "리뷰 상담태그"),
            ("리뷰_도입_상담태그", "리뷰 도입 상담태그"),
            ("업셀_상담태그", "업셀 상담태그"),
            ("업셀_도입_상담태그", "업셀 도입 상담태그"),
            ("푸시_상담태그", "푸시 상담태그"),
            ("푸시_도입_상담태그", "푸시 도입 상담태그"),
        ]

        for category_key, category_title in categories:
            category_data = category_counts.get(category_key, {})
            if category_data:  # 데이터가 있는 경우만 그래프 생성
                chart_base64 = create_bar_chart(category_data, category_title)
                charts[category_key] = chart_base64

        return ChartResponse(charts=charts, success=True)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"그래프 생성 실패: {str(e)}")


@app.post("/sheets-charts", response_model=SheetsChartResponse)
async def create_sheets_charts(request: ChartRequest):
    """분석된 데이터를 기반으로 Google Sheets에 직접 차트를 생성합니다."""
    try:
        service = get_google_sheets_service()
        sheet_name = request.sheet_name

        # 1. 기존 시트에서 데이터 읽기
        range_name = f"{sheet_name}!A:Z"
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range=range_name)
            .execute()
        )

        values = result.get("values", [])
        if not values or len(values) < 2:
            raise HTTPException(
                status_code=404, detail="시트에 충분한 데이터가 없습니다."
            )

        # 2. DataFrame으로 변환
        headers = values[0]
        data_rows = values[1:]

        for i, row in enumerate(data_rows):
            while len(row) < len(headers):
                row.append("")

        df = pd.DataFrame(data_rows, columns=headers)

        # 3. 태그 분석
        tag_counts = analyze_tags(df, "tags")
        category_counts = categorize_tags_advanced(tag_counts)

        # 4. 정리 시트 찾기
        summary_sheet_name = f"[beta]{sheet_name}_분석"
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        summary_sheet_id = None

        for sheet in spreadsheet.get("sheets", []):
            if sheet["properties"]["title"] == summary_sheet_name:
                summary_sheet_id = sheet["properties"]["sheetId"]
                break

        if not summary_sheet_id:
            raise HTTPException(
                status_code=404,
                detail=f"정리 시트 '{summary_sheet_name}'를 찾을 수 없습니다. 먼저 /analyze API를 실행하세요.",
            )

        # 5. 시트 열 수 확장 (S열 이후 차트 배치를 위해)
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                "requests": [
                    {
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId": summary_sheet_id,
                                "gridProperties": {"columnCount": 50},
                            },
                            "fields": "gridProperties.columnCount",
                        }
                    }
                ]
            },
        ).execute()

        # 6. 차트 생성 요청 준비
        chart_requests = []
        chart_start_row = request.chart_start_row

        categories = [
            (category_counts.get("리뷰_상담태그", {}), "리뷰 상담태그", 0),
            (category_counts.get("리뷰_도입_상담태그", {}), "리뷰 도입 상담태그", 3),
            (category_counts.get("업셀_상담태그", {}), "업셀 상담태그", 6),
            (category_counts.get("업셀_도입_상담태그", {}), "업셀 도입 상담태그", 9),
            (category_counts.get("푸시_상담태그", {}), "푸시 상담태그", 12),
            (category_counts.get("푸시_도입_상담태그", {}), "푸시 도입 상담태그", 15),
        ]

        for i, (tags, title, start_col) in enumerate(categories):
            if not tags:
                continue

            # 카테고리별 색상 설정
            if "리뷰" in title:
                color = {"red": 0.26, "green": 0.52, "blue": 0.96}  # Google Blue
            elif "업셀" in title:
                color = {"red": 0.20, "green": 0.66, "blue": 0.33}  # Google Green
            elif "푸시" in title:
                color = {"red": 0.92, "green": 0.26, "blue": 0.21}  # Google Red
            else:
                color = {"red": 0.60, "green": 0.63, "blue": 0.65}  # Google Grey

            # 차트 생성 요청
            chart_requests.append(
                {
                    "addChart": {
                        "chart": {
                            "spec": {
                                "title": title,
                                "basicChart": {
                                    "chartType": "COLUMN",
                                    "legendPosition": "BOTTOM_LEGEND",
                                    "axis": [
                                        {"position": "BOTTOM_AXIS", "title": "태그"},
                                        {"position": "LEFT_AXIS", "title": "개수"},
                                    ],
                                    "domains": [
                                        {
                                            "domain": {
                                                "sourceRange": {
                                                    "sources": [
                                                        {
                                                            "sheetId": summary_sheet_id,
                                                            "startRowIndex": 1,
                                                            "endRowIndex": len(tags)
                                                            + 1,
                                                            "startColumnIndex": start_col,
                                                            "endColumnIndex": start_col
                                                            + 1,
                                                        }
                                                    ]
                                                }
                                            }
                                        }
                                    ],
                                    "series": [
                                        {
                                            "series": {
                                                "sourceRange": {
                                                    "sources": [
                                                        {
                                                            "sheetId": summary_sheet_id,
                                                            "startRowIndex": 1,
                                                            "endRowIndex": len(tags)
                                                            + 1,
                                                            "startColumnIndex": start_col
                                                            + 1,
                                                            "endColumnIndex": start_col
                                                            + 2,
                                                        }
                                                    ]
                                                }
                                            },
                                            "color": color,
                                        }
                                    ],
                                },
                            },
                            "position": {
                                "overlayPosition": {
                                    "anchorCell": {
                                        "sheetId": summary_sheet_id,
                                        "rowIndex": chart_start_row
                                        - 1
                                        + i * 15,  # 15행 간격으로 세로 배치
                                        "columnIndex": 18,  # S열(18)부터 시작
                                    },
                                    "widthPixels": request.chart_width,
                                    "heightPixels": request.chart_height,
                                }
                            },
                        }
                    }
                }
            )

        # 6. 차트 생성 실행
        if chart_requests:
            response = (
                service.spreadsheets()
                .batchUpdate(
                    spreadsheetId=SPREADSHEET_ID, body={"requests": chart_requests}
                )
                .execute()
            )

            # 생성된 차트 ID 추출
            chart_ids = []
            for reply in response.get("replies", []):
                if "addChart" in reply:
                    chart_ids.append(reply["addChart"]["chart"]["chartId"])

            return SheetsChartResponse(
                chart_ids=chart_ids, sheet_name=summary_sheet_name, success=True
            )
        else:
            return SheetsChartResponse(
                chart_ids=[], sheet_name=summary_sheet_name, success=True
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Google Sheets 차트 생성 실패: {str(e)}"
        )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Google Sheets Analyzer API is running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
