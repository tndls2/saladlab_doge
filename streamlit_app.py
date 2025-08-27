import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from analyzers.tag_analyzer import (
    analyze_company_stats,
    analyze_tags,
    categorize_tags_advanced,
)
from config import CATEGORY_COLORS, COMPANY_CATEGORIES, TAG_CATEGORIES
from services.sheets_service import (
    get_google_sheets_service,
    get_sheet_list,
    load_sheet_data,
)
from utils.font_manager import setup_korean_font
from visualizers.chart_creator import (
    clean_tag_name,
    create_chart,
    create_trend_chart,
    highlight_top5_per_column,
)

# 초기 설정
st.set_page_config(page_title="샐러드랩 상담데이터 분석", page_icon="🥗", layout="wide")
load_dotenv()
setup_korean_font()


def render_single_analysis(selected_sheet):
    """단일 분석 모드 렌더링"""
    with st.spinner("데이터를 분석 중입니다..."):
        df = load_sheet_data(selected_sheet)
        if df is None:
            return

        st.success(f"'{selected_sheet}' 시트 데이터를 성공적으로 로드했습니다!")

        # 태그 분석
        tag_counts = analyze_tags(df)
        category_counts = categorize_tags_advanced(tag_counts)

        # 전체 통계
        st.subheader("📈 전체 분석")
        col1, col2, col3 = st.columns(3)

        total_consultations = len(df[df["id"].notna() & (df["id"] != "")])

        with col1:
            st.metric("총 태그 종류", len(tag_counts))
        with col2:
            st.metric("총 상담 수", total_consultations)

        # 업체 통계
        company_stats = analyze_company_stats(df)
        st.markdown("#### 상담 인입 업체 수")

        stats_data = {
            name: [f"{company_stats[key]}개"]
            for key, name in COMPANY_CATEGORIES.items()
        }
        stats_df = pd.DataFrame(stats_data, index=["업체 수"])
        st.dataframe(stats_df, use_container_width=True)

        # 카테고리별 분석
        st.markdown("---")
        st.subheader("📊 서비스별 분석")

        for key, title in TAG_CATEGORIES:
            data = category_counts.get(key, {})
            if not data:
                continue

            # 제목 스타일링
            if key in CATEGORY_COLORS:
                hex_color = CATEGORY_COLORS[key]
                # hex를 rgba로 변환하여 투명도 추가
                r = int(hex_color[1:3], 16)
                g = int(hex_color[3:5], 16)
                b = int(hex_color[5:7], 16)
                bg_color = f"rgba({r}, {g}, {b}, 0.3)"
                st.markdown(
                    f'<h4 style="background-color: {bg_color}; padding: 4px; border-radius: 3px;">{title}</h4>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<h4 style="padding: 4px; border-radius: 3px;">‣ {title}</h4>',
                    unsafe_allow_html=True,
                )

            col1, col2 = st.columns([1, 2])

            with col1:
                # 통계 정보
                st.markdown(
                    f"· 태그 종류: {len(data)}개  \n· 총 개수: {sum(data.values())}개"
                )

                # 테이블 데이터 준비
                if key in ["리뷰_상담태그", "업셀_상담태그", "푸시_상담태그"]:
                    clean_data = [
                        ("/".join(tag.split("/")[1:]), count)
                        for tag, count in data.items()
                    ]
                else:
                    clean_data = [
                        (clean_tag_name(tag), count) for tag, count in data.items()
                    ]

                df_category = (
                    pd.DataFrame(clean_data, columns=["태그", "개수"])
                    .sort_values("개수", ascending=False)
                    .reset_index(drop=True)
                )

                # Top 3 값 하이라이트
                def highlight_top3(df):
                    def highlight_top3_rows(row):
                        top3_values = df["개수"].drop_duplicates().nlargest(3).tolist()
                        opacities = [0.8, 0.5, 0.3]

                        value = row["개수"]
                        if value in top3_values and value > 0:
                            rank = top3_values.index(value)
                            opacity = opacities[rank]
                            return [
                                f"background-color: rgba(255, 255, 0, {opacity})"
                            ] * len(row)
                        return [""] * len(row)

                    return df.style.apply(highlight_top3_rows, axis=1)

                styled_df = highlight_top3(df_category)
                st.dataframe(styled_df, use_container_width=True, hide_index=True)

            with col2:
                # 차트 표시
                chart_data = data
                if key in ["리뷰_상담태그", "리뷰_요청사항_상담태그"]:
                    chart_data = dict(
                        sorted(data.items(), key=lambda x: int(x[1]), reverse=True)[:50]
                    )

                fig = create_chart(chart_data, title)
                if fig:
                    st.pyplot(fig)
                    plt.close(fig)

        # 기타 태그
        other_data = category_counts.get("기타", {})
        if other_data:
            st.write("### 기타 태그")
            st.markdown(
                f"· 태그 종류: {len(other_data)}개  \n· 총 개수: {sum(other_data.values())}개"
            )

            clean_other_data = [(tag, count) for tag, count in other_data.items()]
            df_other = (
                pd.DataFrame(clean_other_data, columns=["태그", "개수"])
                .sort_values("개수", ascending=False)
                .reset_index(drop=True)
            )

            def highlight_top3_other(df):
                def highlight_top3_rows(s):
                    top3_values = (
                        s.drop_duplicates()
                        .nlargest(3)
                        .sort_values(ascending=False)
                        .tolist()
                    )
                    result = []
                    opacities = [0.8, 0.5, 0.3]

                    for v in s:
                        if v in top3_values and v > 0:
                            idx = top3_values.index(v)
                            opacity = opacities[idx]
                            result.append(
                                f"background-color: rgba(255, 255, 0, {opacity})"
                            )
                        else:
                            result.append("")
                    return result

                return df.style.apply(highlight_top3_rows, subset=["개수"])

            styled_df_other = highlight_top3_other(df_other)
            st.dataframe(styled_df_other, use_container_width=True, hide_index=True)


def render_multi_comparison(selected_sheets):
    """다중 비교 모드 렌더링"""
    with st.spinner(f"{len(selected_sheets)}개 시트를 비교 분석 중입니다..."):
        # 모든 시트 데이터 로드
        sheet_data = {}
        tag_counts_all = {}
        category_counts_all = {}
        company_stats_all = {}

        for sheet in selected_sheets:
            df = load_sheet_data(sheet)
            if df is not None:
                sheet_data[sheet] = df
                tag_counts_all[sheet] = analyze_tags(df)
                category_counts_all[sheet] = categorize_tags_advanced(
                    tag_counts_all[sheet]
                )
                company_stats_all[sheet] = analyze_company_stats(df)

        if len(sheet_data) < 2:
            st.error("비교할 데이터가 부족합니다.")
            return

        # 비교 통계
        st.subheader("📊 다중 비교 통계")
        cols = st.columns(len(sheet_data))
        sheet_list = list(tag_counts_all.items())

        for i, (sheet, tag_counts) in enumerate(sheet_list):
            sheet_df = sheet_data[sheet]
            current_total = len(
                sheet_df[sheet_df["id"].notna() & (sheet_df["id"] != "")]
            )

            # 전월 대비 변화량
            delta = None
            if i > 0:
                prev_sheet = sheet_list[i - 1][0]
                prev_df = sheet_data[prev_sheet]
                prev_total = len(prev_df[prev_df["id"].notna() & (prev_df["id"] != "")])
                delta = current_total - prev_total

            with cols[i]:
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
        st.markdown("#### 상담 인입 업체 수")
        company_table_data = {}

        for category, name in COMPANY_CATEGORIES.items():
            category_values = []
            for i, sheet in enumerate(selected_sheets):
                current_stats = company_stats_all[sheet]
                current_count = current_stats[category]

                change_text = ""
                if i > 0:
                    prev_sheet = selected_sheets[i - 1]
                    prev_stats = company_stats_all[prev_sheet]
                    prev_count = prev_stats[category]
                    change = current_count - prev_count
                    if change != 0:
                        if prev_count > 0:
                            change_rate = (change / prev_count) * 100
                            change_text = f" ({change_rate:+.1f}%)"
                        else:
                            change_text = " (new)"

                category_values.append(f"{current_count}개{change_text}")

            company_table_data[name] = category_values

        company_df = pd.DataFrame(company_table_data, index=selected_sheets)
        st.dataframe(company_df, use_container_width=True)

        st.markdown("---")

        # 태그 카테고리별 비교
        for key, title in TAG_CATEGORIES:
            category_data = {}
            all_tags = set()

            for sheet in selected_sheets:
                if sheet in category_counts_all:
                    data = category_counts_all[sheet].get(key, {})
                    category_data[sheet] = data
                    all_tags.update(data.keys())

            if not all_tags:
                continue

            # 제목 스타일링
            if key in CATEGORY_COLORS:
                hex_color = CATEGORY_COLORS[key]
                # hex를 rgba로 변환하여 투명도 추가
                r = int(hex_color[1:3], 16)
                g = int(hex_color[3:5], 16)
                b = int(hex_color[5:7], 16)
                bg_color = f"rgba({r}, {g}, {b}, 0.3)"
                st.markdown(
                    f'<h4 style="background-color: {bg_color}; padding: 4px; border-radius: 3px; margin-bottom: 9px;">{title}</h4>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<h4 style="padding: 4px; border-radius: 3px; margin-bottom: 9px;">‣ {title}</h4>',
                    unsafe_allow_html=True,
                )

            # 각 시트별 통계
            stats_cols = st.columns(len(selected_sheets))
            for i, sheet in enumerate(selected_sheets):
                sheet_data_for_category = category_data.get(sheet, {})
                current_count = sum(sheet_data_for_category.values())

                delta = None
                if i > 0:
                    prev_sheet = selected_sheets[i - 1]
                    prev_data = category_data.get(prev_sheet, {})
                    prev_count = sum(prev_data.values())
                    if prev_count > 0:
                        delta = current_count - prev_count

                with stats_cols[i]:
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

            # 비교 테이블 생성
            comparison_data = []
            for tag in all_tags:
                if key in ["리뷰_상담태그", "업셀_상담태그", "푸시_상담태그"]:
                    clean_tag = "/".join(tag.split("/")[1:])
                else:
                    clean_tag = clean_tag_name(tag)

                row = {"태그": clean_tag}
                counts = []
                for sheet in selected_sheets:
                    count = category_data.get(sheet, {}).get(tag, 0)
                    row[sheet] = count
                    counts.append(count)

                row["변화량"] = max(counts) - min(counts) if counts else 0
                comparison_data.append(row)

            df_comparison = pd.DataFrame(comparison_data).sort_values(
                "변화량", ascending=False
            )
            display_df = df_comparison.drop("변화량", axis=1).reset_index(drop=True)

            styled_df = highlight_top5_per_column(display_df)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)

            # 추이 그래프
            trend_fig = create_trend_chart(comparison_data, title, key)
            if trend_fig:
                st.pyplot(trend_fig)
                plt.close(trend_fig)


def main():
    """메인 애플리케이션"""
    st.title("🥗 샐러드랩 상담데이터 분석")
    st.markdown("---")

    # 시트 로드
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
    analysis_mode = st.sidebar.radio("분석 모드", ["단일 분석", "다중 비교"])

    if analysis_mode == "단일 분석":
        selected_sheet = st.sidebar.selectbox("분석할 시트 선택", sheets)
        if st.sidebar.button("분석 시작"):
            st.session_state.analyze = True
            st.session_state.compare = False
            st.session_state.selected_sheet = selected_sheet
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
            st.rerun()
        elif len(selected_sheets) < 2:
            st.sidebar.warning("비교하려면 2개 이상의 시트를 선택하세요.")

    # 메인 컨텐츠
    if hasattr(st.session_state, "compare") and st.session_state.compare:
        render_multi_comparison(st.session_state.selected_sheets)
    elif hasattr(st.session_state, "analyze") and st.session_state.analyze:
        render_single_analysis(st.session_state.selected_sheet)
    else:
        st.info("👈 사이드바에서 분석 모드를 선택하고 버튼을 클릭하세요.")


if __name__ == "__main__":
    main()
