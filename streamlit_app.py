import os
from collections import Counter

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# 환경 설정
load_dotenv()
plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False

# 상수
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")


@st.cache_resource
def get_google_sheets_service():
    """Google Sheets API 서비스 객체를 반환합니다."""
    if not os.path.exists("token.json"):
        st.error("token.json 파일을 찾을 수 없습니다.")
        return None

    creds = Credentials.from_service_account_file("token.json", scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


@st.cache_data
def get_sheet_list():
    """상담데이터 시트 목록만 조회합니다."""
    service = get_google_sheets_service()
    if not service:
        return []

    try:
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = []
        for sheet in spreadsheet.get("sheets", []):
            title = sheet.get("properties", {}).get("title")
            if title and ("상담데이터" in title or "상담 데이터" in title):
                sheets.append(title)
        return sorted(sheets, reverse=True)  # 최신 날짜 순으로 정렬
    except Exception as e:
        st.error(f"시트 목록 조회 실패: {str(e)}")
        return []


def parse_tags(tag_string):
    """태그 문자열을 파싱하여 개별 태그 리스트로 반환합니다."""
    if not tag_string or pd.isna(tag_string):
        return []
    return [tag.strip() for tag in str(tag_string).split(",") if tag.strip()]


def analyze_tags(df, tag_column="tags"):
    """태그 열을 분석하여 각 태그별 개수를 반환합니다."""
    if tag_column not in df.columns:
        st.error(f"'{tag_column}' 열을 찾을 수 없습니다.")
        return {}

    all_tags = []
    for tag_string in df[tag_column]:
        all_tags.extend(parse_tags(tag_string))

    return dict(Counter(all_tags))


def categorize_tags_advanced(tag_counts):
    """태그를 대분류, 중분류에 따라 세분화하여 분류합니다."""
    categories = {
        "리뷰_상담태그": {},
        "리뷰_요청사항_상담태그": {},
        "리뷰_도입_상담태그": {},
        ##
        "업셀_상담태그": {},
        "업셀_요청사항_상담태그": {},
        "업셀_도입_상담태그": {},
        ##
        "푸시_상담태그": {},
        "푸시_요청사항_상담태그": {},
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
        is_request = "요청사항" in second_category

        if first_category == "리뷰":
            if is_request:
                key = "리뷰_요청사항_상담태그"
            elif is_intro:
                key = "리뷰_도입_상담태그"
            else:
                key = "리뷰_상담태그"

        elif first_category == "업셀":
            if is_request:
                key = "업셀_요청사항_상담태그"
            elif is_intro:
                key = "업셀_도입_상담태그"
            else:
                key = "업셀_상담태그"

        elif first_category == "푸시":
            if is_request:
                key = "푸시_요청사항_상담태그"
            elif is_intro:
                key = "푸시_도입_상담태그"
            else:
                key = "푸시_상담태그"

        else:
            key = "기타_요청사항" if is_request else "기타"

        categories[key][tag] = count

    return categories


def load_sheet_data(sheet_name):
    """시트 데이터를 로드합니다."""
    service = get_google_sheets_service()
    if not service:
        return None

    try:
        range_name = f"{sheet_name}!A:Z"
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range=range_name)
            .execute()
        )

        values = result.get("values", [])
        if not values or len(values) < 2:
            st.error("시트에 충분한 데이터가 없습니다.")
            return None

        headers = values[0]
        data_rows = values[1:]

        # 모든 행의 길이를 헤더와 맞춤
        for row in data_rows:
            while len(row) < len(headers):
                row.append("")
            # 헤더보다 긴 행은 자름
            if len(row) > len(headers):
                row[:] = row[: len(headers)]

        return pd.DataFrame(data_rows, columns=headers)

    except Exception as e:
        st.error(f"데이터 로드 실패: {str(e)}")
        return None


def clean_tag_name(tag):
    """태그에서 대분류 부분을 제거합니다."""
    if "/" in tag:
        parts = tag.split("/")
        # 대분류 제거
        remaining = "/".join(parts[1:])
        # 도입문의/요청사항 중분류도 제거
        if remaining.startswith("도입문의/"):
            remaining = remaining.replace("도입문의/", "")
        if remaining.startswith("요청사항/"):
            remaining = remaining.replace("요청사항/", "")
        return remaining
    return tag


def create_chart(data, title):
    """차트를 생성합니다."""
    if not data:
        return None

    fig, ax = plt.subplots(figsize=(12, 8))
    # 개수 기준으로 내림차순 정렬
    sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)
    clean_tags = [clean_tag_name(tag) for tag, count in sorted_items]
    counts = [count for tag, count in sorted_items]

    bars = ax.bar(range(len(clean_tags)), counts)
    ax.set_xlabel("태그", fontsize=10)
    ax.set_ylabel("개수", fontsize=10)
    ax.set_title(title, fontsize=12)
    ax.set_xticks(range(len(clean_tags)))
    ax.set_xticklabels(clean_tags, rotation=45, ha="right", fontsize=8)

    # 막대 위에 숫자 표시
    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.1,
            str(count),
            ha="center",
            va="bottom",
            fontsize=9,
        )

    plt.tight_layout()
    return fig

def highlight_top5_per_column(df):
    def high_top5(s):
        # 숫자 상위 5개 추출
        top5 = s.nlargest(5).sort_values(ascending=False)
        result = []
        # 불투명도 단계 (큰 값일수록 진하게)
        opacities = [0.9, 0.7, 0.5, 0.3, 0.1]
        for v in s:
            if v in top5.values:
                # 순서에 맞는 불투명도 가져오기
                idx = top5.values.tolist().index(v)
                opacity = opacities[idx]
                result.append(f'background-color: rgba(255, 255, 0, {opacity})')
            else:
                result.append('')
        return result

    # "태그" 열 제외하고 숫자 컬럼만 스타일 적용
    numeric_cols = df.select_dtypes(include='number').columns
    return df.style.apply(high_top5, subset=numeric_cols)

# Streamlit 앱
def main():
    st.set_page_config(
        page_title="Google Sheets 태그 분석기", page_icon="📊", layout="wide"
    )

    st.title("📊 Google Sheets 태그 분석기")
    st.markdown("---")

    # 환경 변수 확인
    if not SPREADSHEET_ID:
        st.error("SPREADSHEET_ID 환경변수가 설정되지 않았습니다.")
        return

    # 사이드바
    st.sidebar.header("설정")

    # 시트 목록 가져오기
    sheets = get_sheet_list()
    if not sheets:
        st.error("시트 목록을 가져올 수 없습니다.")
        return

    # 분석 모드 선택
    analysis_mode = st.sidebar.radio("분석 모드", ["단일 분석", "다중 비교"])

    if analysis_mode == "단일 분석":
        selected_sheet = st.sidebar.selectbox("분석할 시트 선택", sheets)
        if st.sidebar.button("분석 시작"):
            st.session_state.analyze = True
            st.session_state.compare = False
            st.session_state.selected_sheet = selected_sheet
    else:
        selected_sheets = st.sidebar.multiselect(
            "비교할 시트 선택 (2개 이상)",
            sheets,
            default=sheets[:2] if len(sheets) >= 2 else sheets,
        )
        if len(selected_sheets) >= 2 and st.sidebar.button("비교 분석 시작"):
            st.session_state.analyze = False
            st.session_state.compare = True
            st.session_state.selected_sheets = selected_sheets
        elif len(selected_sheets) < 2:
            st.sidebar.warning("비교하려면 2개 이상의 시트를 선택하세요.")

    # 메인 컨텐츠
    if hasattr(st.session_state, "compare") and st.session_state.compare:
        # 다중 비교 분석
        with st.spinner(
            f"{len(st.session_state.selected_sheets)}개 시트를 비교 분석 중입니다..."
        ):
            # 모든 시트 데이터 로드
            sheet_data = {}
            tag_counts_all = {}
            category_counts_all = {}

            for sheet in st.session_state.selected_sheets:
                df = load_sheet_data(sheet)
                if df is not None:
                    sheet_data[sheet] = df
                    tag_counts_all[sheet] = analyze_tags(df)
                    category_counts_all[sheet] = categorize_tags_advanced(
                        tag_counts_all[sheet]
                    )

            if len(sheet_data) >= 2:
                st.success(f"{len(sheet_data)}개 시트 비교 분석 완료!")

                # 비교 통계
                st.subheader("📊 다중 비교 통계")
                cols = st.columns(len(sheet_data))
                sheet_list = list(tag_counts_all.items())
                for i, (sheet, tag_counts) in enumerate(sheet_list):
                    current_total = sum(tag_counts.values())

                    # 전월 대비 변화량 계산
                    delta = None
                    if i > 0:
                        prev_total = sum(sheet_list[i - 1][1].values())
                        delta = current_total - prev_total

                    with cols[i]:
                        with st.container():
                            color = "#6c757d" if delta is None else (
                                "#28a745" if delta > 0 else "#dc3545" if delta < 0 else "#6c757d")
                            st.markdown(
                                f"""
                                <div style="
                                    background-color: #f0f2f6;
                                    padding: 0.5rem;
                                    border-radius: 0.3rem;
                                    border-left: 3px solid {color};
                                    margin-bottom: 0.5rem;
                                ">
                                    <p style="margin: 0; font-size: 0.8rem; color: #666;">{sheet}</p>
                                    <p style="margin: 0.2rem 0 0 0; font-size: 1.2rem; font-weight: bold; color: #262730;">{current_total}개</p>
                                    {f'<p style="margin: 0.1rem 0 0 0; font-size: 0.75rem; color: {color};">{delta:+d}개</p>' if delta is not None else '<p style="margin: 0.1rem 0 0 0; font-size: 0.75rem;">&nbsp;</p>'}
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                # 카테고리별 비교
                categories = [
                    ("리뷰_상담태그", "리뷰 상담태그"),
                    ("리뷰_요청사항_상담태그", "리뷰 요청사항 상담태그"),
                    ("리뷰_도입_상담태그", "리뷰 도입 상담태그"),
                    ##
                    ("업셀_상담태그", "업셀 상담태그"),
                    ("업셀_요청사항_상담태그", "업셀 요청사항 상담태그"),
                    ("업셀_도입_상담태그", "업셀 도입 상담태그"),
                    ##
                    ("푸시_상담태그", "푸시 상담태그"),
                    ("푸시_요청사항_상담태그", "푸시 요청사항 상담태그"),
                    ("푸시_도입_상담태그", "푸시 도입 상담태그"),
                ]

                for key, title in categories:
                    # 모든 시트에서 해당 카테고리 데이터 수집
                    category_data = {}
                    all_tags = set()

                    for sheet in st.session_state.selected_sheets:
                        if sheet in category_counts_all:
                            data = category_counts_all[sheet].get(key, {})
                            category_data[sheet] = data
                            all_tags.update(data.keys())

                    if all_tags:
                        st.write(f"### {title} 비교")

                        # 각 시트별 통계 표시
                        stats_cols = st.columns(len(st.session_state.selected_sheets))
                        for i, sheet in enumerate(st.session_state.selected_sheets):
                            sheet_data_for_category = category_data.get(sheet, {})
                            current_count = sum(sheet_data_for_category.values())

                            # 전월 대비 변화량 계산
                            delta = None
                            if i > 0:  # 첫 번째 시트가 아닌 경우
                                prev_sheet = st.session_state.selected_sheets[i - 1]
                                prev_data = category_data.get(prev_sheet, {})
                                prev_count = sum(prev_data.values())
                                if prev_count > 0:
                                    delta = current_count - prev_count

                            with stats_cols[i]:
                                with st.container():
                                    color = "#6c757d" if delta is None else (
                                        "#28a745" if delta > 0 else "#dc3545" if delta < 0 else "#6c757d")

                                    st.markdown(
                                        f"""
                                        <div style="
                                            background-color: #f8f9fa;
                                            padding: 0.4rem;
                                            border-radius: 0.3rem;
                                            border-left: 3px solid {color};
                                            margin-bottom: 0.3rem;
                                        ">
                                            <p style="margin: 0; font-size: 0.75rem; color: #666;">{sheet}</p>
                                            <p style="margin: 0.1rem 0 0 0; font-size: 1rem; font-weight: bold; color: #262730;">{current_count}개</p>
                                            {f'<p style="margin: 0.1rem 0 0 0; font-size: 0.7rem; color: {color};">{delta:+d}개</p>' if delta is not None else '<p style="margin: 0.1rem 0 0 0; font-size: 0.7rem;">&nbsp;</p>'}
                                        </div>
                                        """,
                                        unsafe_allow_html=True,
                                    )

                        comparison_data = []
                        for tag in all_tags:
                            row = {"태그": clean_tag_name(tag)}
                            counts = []
                            for sheet in st.session_state.selected_sheets:
                                count = category_data.get(sheet, {}).get(tag, 0)
                                row[sheet] = count
                                counts.append(count)
                            # 변화량 계산 (최대값 - 최소값)
                            row["변화량"] = max(counts) - min(counts) if counts else 0
                            comparison_data.append(row)

                        df_comparison = pd.DataFrame(comparison_data)
                        # 변화량 기준으로 정렬
                        df_comparison = df_comparison.sort_values(
                            "변화량", ascending=False
                        )

                        # 변화량 열 숨기고 표시
                        display_df = df_comparison.drop("변화량", axis=1).reset_index(
                            drop=True
                        )

                        styled_df = highlight_top5_per_column(display_df)
                        st.dataframe(styled_df, use_container_width=True, hide_index=True)

    elif hasattr(st.session_state, "analyze") and st.session_state.analyze:
        with st.spinner("데이터를 분석 중입니다..."):
            df = load_sheet_data(st.session_state.selected_sheet)

            if df is not None:
                st.success(
                    f"'{st.session_state.selected_sheet}' 시트 데이터를 성공적으로 로드했습니다!"
                )

                # 태그 분석
                tag_counts = analyze_tags(df)
                category_counts = categorize_tags_advanced(tag_counts)

                # 전체 태그 통계
                st.subheader("📈 전체 태그 통계")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("총 태그 종류", len(tag_counts))
                with col2:
                    st.metric("총 상담 수", sum(tag_counts.values()))

                # 카테고리별 분석
                st.subheader("📊 카테고리별 분석")

                categories = [
                    ("리뷰_상담태그", "리뷰 상담태그"),
                    ("리뷰_요청사항_상담태그", "리뷰 요청사항 상담태그"),
                    ("리뷰_도입_상담태그", "리뷰 도입 상담태그"),
                    ##
                    ("업셀_상담태그", "업셀 상담태그"),
                    ("업셀_요청사항_상담태그", "업셀 요청사항 상담태그"),
                    ("업셀_도입_상담태그", "업셀 도입 상담태그"),
                    ##
                    ("푸시_상담태그", "푸시 상담태그"),
                    ("푸시_요청사항_상담태그", "푸시 요청사항 상담태그"),
                    ("푸시_도입_상담태그", "푸시 도입 상담태그"),
                ]

                for key, title in categories:
                    data = category_counts.get(key, {})
                    if data:
                        st.write(f"### {title}")

                        col1, col2 = st.columns([1, 2])

                        with col1:
                            # 테이블 표시 (대분류 제거)
                            st.markdown(f"· 태그 종류: {len(data)}개  \n· 총 개수: {sum(data.values())}개")

                            clean_data = [
                                (clean_tag_name(tag), count)
                                for tag, count in data.items()
                            ]
                            df_category = (
                                pd.DataFrame(clean_data, columns=["태그", "개수"])
                                .sort_values("개수", ascending=False)
                                .reset_index(drop=True)
                            )
                            st.dataframe(
                                df_category, use_container_width=True, hide_index=True
                            )

                        with col2:
                            # 차트 표시
                            chart_data = data
                            if key == "리뷰_상담태그":
                                chart_data = dict(
                                    sorted(
                                        data.items(),
                                        key=lambda x: int(x[1]),
                                        reverse=True,
                                    )[:50]
                                )

                            fig = create_chart(chart_data, title)

                            if fig:
                                st.pyplot(fig)
                                plt.close(fig)

                # 기타 태그
                other_data = category_counts.get("기타", {})
                if other_data:
                    st.write("### 기타 태그")
                    clean_other_data = [
                        (clean_tag_name(tag), count)
                        for tag, count in other_data.items()
                    ]
                    df_other = (
                        pd.DataFrame(clean_other_data, columns=["태그", "개수"])
                        .sort_values("개수", ascending=False)
                        .reset_index(drop=True)
                    )
                    st.dataframe(df_other, use_container_width=True, hide_index=True)
                    st.write(
                        f"**태그 종류: {len(other_data)}개 | 총 개수: {sum(other_data.values())}개**"
                    )

    else:
        st.info("👈 사이드바에서 분석 모드를 선택하고 버튼을 클릭하세요.")


if __name__ == "__main__":
    main()
