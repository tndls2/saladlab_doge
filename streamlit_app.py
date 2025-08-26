import streamlit as st

st.set_page_config(page_title="샐러드랩 상담데이터 분석", page_icon="🥗", layout="wide")
import platform
from collections import Counter

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

# 환경 설정
load_dotenv()


# 한글 폰트 설정 함수
def setup_korean_font():
    try:
        # 시스템별 한글 폰트 설정
        if platform.system() == "Darwin":  # macOS
            font_candidates = ["AppleGothic", "Apple SD Gothic Neo", "Noto Sans CJK KR"]
        elif platform.system() == "Windows":
            font_candidates = ["Malgun Gothic", "Microsoft YaHei", "Noto Sans CJK KR"]
        else:  # Linux (including Streamlit Cloud)
            font_candidates = ["NanumGothic", "Noto Sans CJK KR", "DejaVu Sans"]

        # 사용 가능한 폰트 찾기
        available_fonts = [f.name for f in fm.fontManager.ttflist]

        for font in font_candidates:
            if font in available_fonts:
                plt.rcParams["font.family"] = font
                plt.rcParams["axes.unicode_minus"] = False
                return font

        # 한글 폰트를 찾지 못한 경우 기본 설정
        plt.rcParams["font.family"] = "DejaVu Sans"
        plt.rcParams["axes.unicode_minus"] = False
        return "DejaVu Sans"

    except Exception as e:
        plt.rcParams["font.family"] = "DejaVu Sans"
        plt.rcParams["axes.unicode_minus"] = False
        return "DejaVu Sans"


# 폰트 설정 적용
used_font = setup_korean_font()

# 상수
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


@st.cache_resource
def get_google_sheets_service():
    info = st.secrets["google_service_account"]
    service_account_info = dict(info)
    service_account_info["private_key"] = service_account_info["private_key"].replace(
        "\\n", "\n"
    )
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info
    )
    service = build("sheets", "v4", credentials=credentials)
    return service


@st.cache_data
def get_sheet_list(_service):
    """상담데이터 시트 목록만 조회합니다."""
    if not _service:
        return []

    try:
        spreadsheet = (
            _service.spreadsheets()
            .get(spreadsheetId=st.secrets["SPREADSHEET_ID"])
            .execute()
        )
        sheets = []
        for sheet in spreadsheet.get("sheets", []):
            title = sheet.get("properties", {}).get("title")
            if title and ("상담데이터" in title or "상담 데이터" in title):
                sheets.append(title)
        return sorted(sheets, reverse=True)
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

    tag_counts = Counter()
    for tag_string in df[tag_column]:
        unique_tags = set(parse_tags(tag_string))
        for tag in unique_tags:
            tag_counts[tag] += 1

    return dict(tag_counts)


def analyze_company_stats(df, tag_column="tags", company_column="name"):
    """대분류별 업체 수를 계산합니다."""
    if tag_column not in df.columns or company_column not in df.columns:
        st.warning(f"컴럼을 찾을 수 없습니다: {tag_column}, {company_column}")
        st.write(f"사용 가능한 컴럼: {list(df.columns)}")
        return {"review": 0, "upsell": 0, "push": 0, "review_upsell": 0}

    # 대분류별 업체 집합 (중복 제거)
    review_companies = set()
    upsell_companies = set()
    push_companies = set()
    review_upsell_companies = set()
    upsell_push_companies = set()
    push_review_companies = set()
    review_upsell_push_companies = set()

    for idx, row in df.iterrows():
        if pd.isna(row[company_column]) or row[company_column] == "":
            continue

        company = str(row[company_column]).strip()
        tags = parse_tags(row[tag_column])

        is_review = False
        is_upsell = False
        is_push = False

        for tag in tags:
            if tag.startswith("리뷰"):
                is_review = True
            elif tag.startswith("업셀"):
                is_upsell = True
            elif tag.startswith("푸시"):
                is_push = True

        if is_review:
            review_companies.add(company)
        if is_upsell:
            upsell_companies.add(company)
        if is_push:
            push_companies.add(company)

        # 서로 다른 서비스의 태그가 모두 있는 경우
        if is_review and is_upsell:
            review_upsell_companies.add(company)
        if is_upsell and is_push:
            upsell_push_companies.add(company)
        if is_push and is_review:
            push_review_companies.add(company)
        if is_review and is_upsell and is_push:
            review_upsell_push_companies.add(company)

    return {
        "review": len(review_companies),
        "upsell": len(upsell_companies),
        "push": len(push_companies),
        "review_upsell": len(review_upsell_companies),
        "upsell_push": len(upsell_push_companies),
        "push_review": len(push_review_companies),
        "review_upsell_push": len(review_upsell_push_companies),
    }


def categorize_tags_advanced(tag_counts):
    """태그를 대분류, 중분류에 따라 세분화하여 분류합니다."""
    categories = {
        "리뷰_상담태그": {},
        "리뷰_요청사항_상담태그": {},
        "리뷰_도입문의_상담태그": {},
        "리뷰_기능문의_상담태그": {},
        ##
        "업셀_상담태그": {},
        "업셀_요청사항_상담태그": {},
        "업셀_도입문의_상담태그": {},
        "업셀_기능문의_상담태그": {},
        ##
        "푸시_상담태그": {},
        "푸시_요청사항_상담태그": {},
        "푸시_도입문의_상담태그": {},
        "푸시_기능문의_상담태그": {},
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
        third_category = parts[2] if len(parts) > 2 else ""

        is_intro = "도입문의" in second_category
        is_request = "요청사항" in second_category
        is_function = second_category == "기능문의" or third_category == "기능문의"

        if first_category in ["리뷰", "리뷰목록"]:
            categories["리뷰_상담태그"][tag] = count

            # 중분류에 따라 추가 분류
            if is_request:
                categories["리뷰_요청사항_상담태그"][tag] = count
            elif is_intro:
                categories["리뷰_도입문의_상담태그"][tag] = count
            elif is_function:
                categories["리뷰_기능문의_상담태그"][tag] = count

        elif first_category == "업셀":
            categories["업셀_상담태그"][tag] = count

            # 중분류에 따라 추가 분류
            if is_request:
                categories["업셀_요청사항_상담태그"][tag] = count
            elif is_intro:
                categories["업셀_도입문의_상담태그"][tag] = count
            elif is_function:
                categories["업셀_기능문의_상담태그"][tag] = count

        elif first_category == "푸시":
            categories["푸시_상담태그"][tag] = count

            # 중분류에 따라 추가 분류
            if is_request:
                categories["푸시_요청사항_상담태그"][tag] = count
            elif is_intro:
                categories["푸시_도입문의_상담태그"][tag] = count
            elif is_function:
                categories["푸시_기능문의_상담태그"][tag] = count

        else:
            categories["기타"][tag] = count

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
            .get(spreadsheetId=st.secrets["SPREADSHEET_ID"], range=range_name)
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
        if remaining.startswith("기능문의/"):
            remaining = remaining.replace("기능문의/", "")
        # 소분류에서 /기능문의 제거
        if remaining.endswith("/기능문의"):
            remaining = remaining.replace("/기능문의", "")
        return remaining
    return tag


def create_chart(data, title):
    """차트를 생성합니다."""
    if not data:
        return None

    fig, ax = plt.subplots(figsize=(12, 8))

    # 한글 레이블 설정
    ax.set_xlabel("태그", fontsize=10)
    ax.set_ylabel("개수", fontsize=10)
    ax.set_title(title, fontsize=12)

    # 개수 기준으로 내림차순 정렬
    sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)
    clean_tags = [clean_tag_name(tag) for tag, count in sorted_items]
    counts = [count for tag, count in sorted_items]

    bars = ax.bar(range(len(clean_tags)), counts)
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


def create_trend_chart(comparison_data, title, key):
    """다중 비교용 선 그래프를 생성합니다."""
    if not comparison_data:
        return None

    df = pd.DataFrame(comparison_data)

    # 시트 이름들 (월)
    sheet_columns = [col for col in df.columns if col not in ["태그", "변화량"]]

    # 리뷰 전체 태그와 리뷰 요청사항 태그의 경우 유의미한 태그만 필터링
    if key == "리뷰_상담태그":
        df["max_value"] = df[sheet_columns].max(axis=1)
        df = df[df["max_value"] >= 5].drop("max_value", axis=1)
    elif key == "리뷰_요청사항_상담태그":
        df["max_value"] = df[sheet_columns].max(axis=1)
        df = df[df["max_value"] >= 5].drop("max_value", axis=1)

    # 마지막 시트의 값 기준으로 정렬
    last_sheet = sheet_columns[-1]
    df = df.sort_values(last_sheet, ascending=False).head(15)

    if len(df) == 0:
        return None

    # 그래프 크기 축소
    fig, ax = plt.subplots(figsize=(10, 6))

    # 파란색 계열 음영 색상
    blue_shades = [
        "#E6F3FF",  # 매우 밝은 파란
        "#B3D9FF",  # 밝은 파란
        "#80BFFF",  # 연한 파란
        "#4DA6FF",  # 보통 파란
        "#1A8CFF",  # 진한 파란
        "#0066CC",  # 더 진한 파란
        "#004499",  # 매우 진한 파란
        "#002266",  # 가장 진한 파란
    ]

    if len(sheet_columns) <= len(blue_shades):
        # 시트 수에 맞게 색상 선택
        colors = blue_shades[: len(sheet_columns)]
    else:
        # 시트가 많을 때는 비례적으로 색상 생성
        colors = [
            blue_shades[int(i * (len(blue_shades) - 1) / (len(sheet_columns) - 1))]
            for i in range(len(sheet_columns))
        ]

    for i, sheet in enumerate(sheet_columns):
        values = df[sheet].values
        ax.plot(
            df["태그"],
            values,
            marker="o",
            linewidth=2.5,
            label=sheet,
            color=colors[i],
            markersize=6,
        )

    ax.set_xlabel("태그", fontsize=9)
    ax.set_ylabel("월별 개수", fontsize=9)
    ax.set_title(f"{title} - 태그별 월별 추이", fontsize=10)
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.xticks(rotation=90, ha="right", fontsize=7)
    plt.yticks(fontsize=8)
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
                result.append(f"background-color: rgba(255, 255, 0, {opacity})")
            else:
                result.append("")
        return result

    # "태그" 열 제외하고 숫자 컬럼만 스타일 적용
    numeric_cols = df.select_dtypes(include="number").columns
    return df.style.apply(high_top5, subset=numeric_cols)


# Streamlit 앱
def main():
    st.title("🥗 샐러드랩 상담데이터 분석")
    st.markdown("---")

    # 자동으로 시트 로드
    try:
        service = get_google_sheets_service()
        sheets = get_sheet_list(service)
        if not sheets:
            st.warning("상담데이터 시트를 찾을 수 없습니다.")
            return
    except Exception as e:
        st.error(f"❌ 시트 로드 실패: {e}")
        st.info("💡 Google Sheets API 연결을 확인해주세요.")
        return

    # 사이드바
    st.sidebar.header("설정")

    # 분석 모드 선택
    analysis_mode = st.sidebar.radio("분석 모드", ["단일 분석", "다중 비교"])

    if analysis_mode == "단일 분석":
        selected_sheet = st.sidebar.selectbox("분석할 시트 선택", sheets)
        if st.sidebar.button("분석 시작"):
            st.session_state.analyze = True
            st.session_state.compare = False
            st.session_state.selected_sheet = selected_sheet
            if "success_shown" in st.session_state:
                del st.session_state.success_shown
            st.rerun()
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
            if "success_shown" in st.session_state:
                del st.session_state.success_shown
            st.rerun()
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
            company_stats_all = {}

            for sheet in st.session_state.selected_sheets:
                df = load_sheet_data(sheet)
                if df is not None:
                    sheet_data[sheet] = df
                    tag_counts_all[sheet] = analyze_tags(df)
                    category_counts_all[sheet] = categorize_tags_advanced(
                        tag_counts_all[sheet]
                    )
                    company_stats_all[sheet] = analyze_company_stats(df)

            if len(sheet_data) >= 2:
                pass

                # 비교 통계
                st.subheader("📊 다중 비교 통계")
                cols = st.columns(len(sheet_data))
                sheet_list = list(tag_counts_all.items())
                for i, (sheet, tag_counts) in enumerate(sheet_list):
                    # ID 열이 있는 행 수로 상담 수 계산
                    sheet_df = sheet_data[sheet]
                    current_total = len(
                        sheet_df[sheet_df["id"].notna() & (sheet_df["id"] != "")]
                    )

                    # 전월 대비 변화량 계산
                    delta = None
                    if i > 0:
                        prev_sheet = sheet_list[i - 1][0]
                        prev_df = sheet_data[prev_sheet]
                        prev_total = len(
                            prev_df[prev_df["id"].notna() & (prev_df["id"] != "")]
                        )
                        delta = current_total - prev_total

                    with cols[i]:
                        with st.container():
                            color = (
                                "#6c757d"
                                if delta is None
                                else (
                                    "#28a745"
                                    if delta > 0
                                    else "#dc3545" if delta < 0 else "#6c757d"
                                )
                            )
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

                # 업체 통계 비교
                st.markdown("#### 상담 인입 업체 수 (중복 제거)")

                # 표 데이터 준비
                categories = [
                    "review",
                    "upsell",
                    "push",
                    "review_upsell",
                    "upsell_push",
                    "push_review",
                    "review_upsell_push",
                ]
                category_names = {
                    "review": "리뷰",
                    "upsell": "업셀",
                    "push": "푸시",
                    "review_upsell": "리뷰&업셀",
                    "upsell_push": "업셀&푸시",
                    "push_review": "푸시&리뷰",
                    "review_upsell_push": "리뷰&업셀&푸시",
                }

                # 각 카테고리별로 데이터 준비
                company_table_data = {}
                for category in categories:
                    category_values = []
                    for i, sheet in enumerate(st.session_state.selected_sheets):
                        current_stats = company_stats_all[sheet]
                        current_count = current_stats[category]

                        # 증감률 계산
                        change_text = ""
                        if i > 0:
                            prev_sheet = st.session_state.selected_sheets[i - 1]
                            prev_stats = company_stats_all[prev_sheet]
                            prev_count = prev_stats[category]
                            if prev_count > 0:
                                change_rate = (
                                    (current_count - prev_count) / prev_count
                                ) * 100
                                if change_rate != 0:
                                    change_text = f" ({change_rate:+.1f}%)"

                        category_values.append(f"{current_count}개{change_text}")

                    company_table_data[category_names[category]] = category_values

                # 표 생성
                company_df = pd.DataFrame(
                    company_table_data, index=st.session_state.selected_sheets
                )
                st.dataframe(company_df, use_container_width=True)

                st.markdown("---")

                # 태그 카테고리별 비교
                categories = [
                    ("리뷰_상담태그", "리뷰 전체 상담태그"),
                    ("리뷰_요청사항_상담태그", "리뷰 요청사항 상담태그"),
                    ("리뷰_도입문의_상담태그", "리뷰 도입문의 상담태그"),
                    ("리뷰_기능문의_상담태그", "리뷰 기능문의 상담태그"),
                    ##
                    ("업셀_상담태그", "업셀 전체 상담태그"),
                    ("업셀_요청사항_상담태그", "업셀 요청사항 상담태그"),
                    ("업셀_도입문의_상담태그", "업셀 도입문의 상담태그"),
                    ("업셀_기능문의_상담태그", "업셀 기능문의 상담태그"),
                    ##
                    ("푸시_상담태그", "푸시 전체 상담태그"),
                    ("푸시_요청사항_상담태그", "푸시 요청사항 상담태그"),
                    ("푸시_도입문의_상담태그", "푸시 도입문의 상담태그"),
                    ("푸시_기능문의_상담태그", "푸시 기능문의 상담태그"),
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
                        # 중분류 상담태그는 앞에 - 추가
                        if key in ["리뷰_상담태그", "업셀_상담태그", "푸시_상담태그"]:
                            st.write(f"### {title} 비교")
                        else:
                            st.write(f"### - {title} 비교")

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
                                    color = (
                                        "#6c757d"
                                        if delta is None
                                        else (
                                            "#28a745"
                                            if delta > 0
                                            else "#dc3545" if delta < 0 else "#6c757d"
                                        )
                                    )

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
                            # 대분류 전체 태그는 대분류만 제거, 나머지는 기존 clean_tag_name 사용
                            if key in [
                                "리뷰_상담태그",
                                "업셀_상담태그",
                                "푸시_상담태그",
                            ]:
                                clean_tag = "/".join(
                                    tag.split("/")[1:]
                                )  # 대분류만 제거
                            else:
                                clean_tag = clean_tag_name(tag)

                            row = {"태그": clean_tag}
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
                        st.dataframe(
                            styled_df, use_container_width=True, hide_index=True
                        )

                        # 추이 그래프 생성 (표 아래에 표시)
                        trend_fig = create_trend_chart(comparison_data, title, key)
                        if trend_fig:
                            st.pyplot(trend_fig)
                            plt.close(trend_fig)

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
                st.subheader("📈 전체 분석")
                col1, col2, col3 = st.columns(3)

                # ID 열이 있는 행 수 계산 (실제 상담 수)
                total_consultations = len(df[df["id"].notna() & (df["id"] != "")])

                with col1:
                    st.metric("총 태그 종류", len(tag_counts))
                with col2:
                    st.metric("총 상담 수", total_consultations)

                # 대분류별 업체 통계 표
                company_stats = analyze_company_stats(df)
                st.markdown("#### 상담 인입 업체 수 (중복 제거)")

                stats_data = {
                    "리뷰": [f"{company_stats['review']}개"],
                    "업셀": [f"{company_stats['upsell']}개"],
                    "푸시": [f"{company_stats['push']}개"],
                    "리뷰&업셀": [f"{company_stats['review_upsell']}개"],
                    "업셀&푸시": [f"{company_stats['upsell_push']}개"],
                    "푸시&리뷰": [f"{company_stats['push_review']}개"],
                    "리뷰&업셀&푸시": [f"{company_stats['review_upsell_push']}개"],
                }

                stats_df = pd.DataFrame(stats_data, index=["업체 수"])
                st.dataframe(stats_df, use_container_width=True)

                # 카테고리별 분석
                st.markdown("---")
                st.subheader("📊 서비스별 분석")

                categories = [
                    ("리뷰_상담태그", "리뷰 전체 상담태그"),
                    ("리뷰_요청사항_상담태그", "리뷰 요청사항 상담태그"),
                    ("리뷰_도입문의_상담태그", "리뷰 도입문의 상담태그"),
                    ("리뷰_기능문의_상담태그", "리뷰 기능문의 상담태그"),
                    ##
                    ("업셀_상담태그", "업셀 전체 상담태그"),
                    ("업셀_요청사항_상담태그", "업셀 요청사항 상담태그"),
                    ("업셀_도입문의_상담태그", "업셀 도입문의 상담태그"),
                    ("업셀_기능문의_상담태그", "업셀 기능문의 상담태그"),
                    ##
                    ("푸시_상담태그", "푸시 전체 상담태그"),
                    ("푸시_요청사항_상담태그", "푸시 요청사항 상담태그"),
                    ("푸시_도입문의_상담태그", "푸시 도입문의 상담태그"),
                    ("푸시_기능문의_상담태그", "푸시 기능문의 상담태그"),
                ]

                for key, title in categories:
                    data = category_counts.get(key, {})
                    if data:
                        # 전체 상담태그는 큰 제목, 중분류는 작은 제목
                        if key in ["리뷰_상담태그", "업셀_상담태그", "푸시_상담태그"]:
                            st.write(f"#### {title}")  # 큰 제목
                        else:
                            st.write(f"#### - {title}")  # 작은 제목

                        col1, col2 = st.columns([1, 2])

                        with col1:
                            # 테이블 표시
                            st.markdown(
                                f"· 태그 종류: {len(data)}개  \n· 총 개수: {sum(data.values())}개"
                            )

                            # 리뷰_상담태그는 대분류만 제거하고 표시
                            if (
                                key == "리뷰_상담태그"
                                or key == "업셀_상담태그"
                                or key == "푸시_상담태그"
                            ):
                                clean_data = [
                                    (
                                        "/".join(tag.split("/")[1:]),
                                        count,
                                    )  # 대분류만 제거
                                    for tag, count in data.items()
                                ]
                            else:
                                clean_data = [
                                    (clean_tag_name(tag), count)
                                    for tag, count in data.items()
                                ]

                            df_category = (
                                pd.DataFrame(clean_data, columns=["태그", "개수"])
                                .sort_values("개수", ascending=False)
                                .reset_index(drop=True)
                            )

                            # Top 3 하이라이트 적용
                            def highlight_top3(df):
                                def highlight_top3_rows(s):
                                    top3 = s.nlargest(3).sort_values(ascending=False)
                                    result = []
                                    opacities = [0.8, 0.5, 0.3]
                                    for v in s:
                                        if v in top3.values and v > 0:
                                            idx = top3.values.tolist().index(v)
                                            opacity = opacities[idx]
                                            result.append(
                                                f"background-color: rgba(255, 255, 0, {opacity})"
                                            )
                                        else:
                                            result.append("")
                                    return result

                                return df.style.apply(
                                    highlight_top3_rows, subset=["개수"]
                                )

                            styled_df = highlight_top3(df_category)
                            st.dataframe(
                                styled_df, use_container_width=True, hide_index=True
                            )

                        with col2:
                            # 차트 표시
                            chart_data = data
                            if key == "리뷰_상담태그":
                                # 상위 50개만 차트에 표시
                                chart_data = dict(
                                    sorted(
                                        data.items(),
                                        key=lambda x: int(x[1]),
                                        reverse=True,
                                    )[:50]
                                )
                            elif key == "리뷰_요청사항_상담태그":
                                # 상위 50개만 차트에 표시
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

                    # 통계 정보를 표 위에 표시
                    st.markdown(
                        f"· 태그 종류: {len(other_data)}개  \n· 총 개수: {sum(other_data.values())}개"
                    )

                    clean_other_data = [
                        (tag, count)  # 기타 태그는 원본 태그 이름 유지
                        for tag, count in other_data.items()
                    ]
                    df_other = (
                        pd.DataFrame(clean_other_data, columns=["태그", "개수"])
                        .sort_values("개수", ascending=False)
                        .reset_index(drop=True)
                    )

                    # Top 3 하이라이트 적용
                    def highlight_top3(df):
                        def highlight_top3_rows(s):
                            top3 = s.nlargest(3).sort_values(ascending=False)
                            result = []
                            opacities = [0.8, 0.5, 0.3]
                            for v in s:
                                if v in top3.values and v > 0:
                                    idx = top3.values.tolist().index(v)
                                    opacity = opacities[idx]
                                    result.append(
                                        f"background-color: rgba(255, 255, 0, {opacity})"
                                    )
                                else:
                                    result.append("")
                            return result

                        return df.style.apply(highlight_top3_rows, subset=["개수"])

                    styled_df_other = highlight_top3(df_other)
                    st.dataframe(
                        styled_df_other, use_container_width=True, hide_index=True
                    )

    else:
        st.info("👈 사이드바에서 분석 모드를 선택하고 버튼을 클릭하세요.")


if __name__ == "__main__":
    main()
