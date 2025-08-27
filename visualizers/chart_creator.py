"""차트 생성 로직"""

import matplotlib.pyplot as plt
import pandas as pd
from config import CHART_CONFIG, BLUE_SHADES


def clean_tag_name(tag):
    """태그에서 대분류 부분을 제거합니다."""
    if "/" in tag:
        parts = tag.split("/")
        remaining = "/".join(parts[1:])
        
        # 중분류 제거
        for prefix in ["도입문의/", "요청사항/", "기능문의/"]:
            if remaining.startswith(prefix):
                remaining = remaining.replace(prefix, "")
        
        # 소분류에서 /기능문의 제거
        if remaining.endswith("/기능문의"):
            remaining = remaining.replace("/기능문의", "")
            
        return remaining
    return tag


def create_chart(data, title):
    """차트를 생성합니다."""
    if not data:
        return None

    fig, ax = plt.subplots(figsize=CHART_CONFIG["figsize"])

    ax.set_xlabel("태그", fontsize=10)
    ax.set_ylabel("개수", fontsize=10)
    ax.set_title(title, fontsize=12)

    # 시그니처 색상 설정
    if "리뷰" in title:
        color = "#c198e1"  # R193 G152 B225
    elif "업셀" in title:
        color = "#ef9aae"  # R239 G154 B174
    elif "푸시" in title:
        color = "#5b9bd5"  # R91 G155 B213 (더 진한 파란색)
    else:
        color = "#87CEEB"  # 기본 색상

    sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)
    clean_tags = [clean_tag_name(tag) for tag, count in sorted_items]
    counts = [count for tag, count in sorted_items]

    bars = ax.bar(range(len(clean_tags)), counts, color=color)
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
    sheet_columns = [col for col in df.columns if col not in ["태그", "변화량"]]

    # 유의미한 태그만 필터링
    if key in ["리뷰_상담태그", "리뷰_요청사항_상담태그"]:
        df["max_value"] = df[sheet_columns].max(axis=1)
        df = df[df["max_value"] >= 5].drop("max_value", axis=1)

    # 상위 태그만 표시
    last_sheet = sheet_columns[-1]
    df = df.sort_values(last_sheet, ascending=False).head(CHART_CONFIG["top_tags_limit"])

    if len(df) == 0:
        return None

    fig, ax = plt.subplots(figsize=CHART_CONFIG["trend_figsize"])

    # 시그니처 색상 설정
    if "리뷰" in title:
        base_color = "#c198e1"  # R193 G152 B225
    elif "업셀" in title:
        base_color = "#ef9aae"  # R239 G154 B174
    elif "푸시" in title:
        base_color = "#5b9bd5"  # R91 G155 B213 (더 진한 파란색)
    else:
        base_color = "#87CEEB"  # 기본 색상
    
    # 베이스 색상의 다양한 음영 생성 (마지막 시트가 제일 진함)
    colors = []
    for i in range(len(sheet_columns)):
        if len(sheet_columns) == 1:
            opacity = 1.0
        else:
            opacity = 0.4 + (0.6 * i / (len(sheet_columns) - 1))
        r = int(base_color[1:3], 16) / 255
        g = int(base_color[3:5], 16) / 255
        b = int(base_color[5:7], 16) / 255
        colors.append((r, g, b, opacity))

    for i, sheet in enumerate(sheet_columns):
        values = df[sheet].values
        ax.plot(
            df["태그"],
            values,
            marker="o",
            linewidth=2.5,
            label=sheet,
            color=colors[i] if i < len(colors) else base_color,
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
    """상위 5개 값을 하이라이트합니다."""
    def high_top5(s):
        top5 = s.nlargest(5).sort_values(ascending=False)
        result = []
        opacities = [0.9, 0.7, 0.5, 0.3, 0.1]
        
        for v in s:
            if v in top5.values:
                idx = top5.values.tolist().index(v)
                opacity = opacities[idx]
                result.append(f"background-color: rgba(255, 255, 0, {opacity})")
            else:
                result.append("")
        return result

    numeric_cols = df.select_dtypes(include="number").columns
    return df.style.apply(high_top5, subset=numeric_cols)