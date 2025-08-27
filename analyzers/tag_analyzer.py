"""태그 분석 로직"""

import pandas as pd
from collections import Counter


def parse_tags(tag_string):
    """태그 문자열을 파싱하여 개별 태그 리스트로 반환합니다."""
    if not tag_string or pd.isna(tag_string):
        return []
    return [tag.strip() for tag in str(tag_string).split(",") if tag.strip()]


def analyze_tags(df, tag_column="tags"):
    """태그 열을 분석하여 각 태그별 개수를 반환합니다."""
    if tag_column not in df.columns:
        return {}

    tag_counts = Counter()
    for tag_string in df[tag_column]:
        unique_tags = set(parse_tags(tag_string))
        for tag in unique_tags:
            tag_counts[tag] += 1

    return dict(tag_counts)


def categorize_tags_advanced(tag_counts):
    """태그를 대분류, 중분류에 따라 세분화하여 분류합니다."""
    categories = {
        "리뷰_상담태그": {},
        "리뷰_요청사항_상담태그": {},
        "리뷰_도입문의_상담태그": {},
        "리뷰_기능문의_상담태그": {},
        "업셀_상담태그": {},
        "업셀_요청사항_상담태그": {},
        "업셀_도입문의_상담태그": {},
        "업셀_기능문의_상담태그": {},
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
            if is_request:
                categories["리뷰_요청사항_상담태그"][tag] = count
            elif is_intro:
                categories["리뷰_도입문의_상담태그"][tag] = count
            elif is_function:
                categories["리뷰_기능문의_상담태그"][tag] = count

        elif first_category == "업셀":
            categories["업셀_상담태그"][tag] = count
            if is_request:
                categories["업셀_요청사항_상담태그"][tag] = count
            elif is_intro:
                categories["업셀_도입문의_상담태그"][tag] = count
            elif is_function:
                categories["업셀_기능문의_상담태그"][tag] = count

        elif first_category == "푸시":
            categories["푸시_상담태그"][tag] = count
            if is_request:
                categories["푸시_요청사항_상담태그"][tag] = count
            elif is_intro:
                categories["푸시_도입문의_상담태그"][tag] = count
            elif is_function:
                categories["푸시_기능문의_상담태그"][tag] = count

        else:
            categories["기타"][tag] = count

    return categories


def analyze_company_stats(df, tag_column="tags", company_column="name"):
    """대분류별 업체 수를 계산합니다."""
    if tag_column not in df.columns or company_column not in df.columns:
        return {"review": 0, "upsell": 0, "push": 0, "review_upsell": 0, 
                "upsell_push": 0, "push_review": 0, "review_upsell_push": 0}

    company_sets = {
        "review": set(), "upsell": set(), "push": set(),
        "review_upsell": set(), "upsell_push": set(), 
        "push_review": set(), "review_upsell_push": set()
    }

    for _, row in df.iterrows():
        if pd.isna(row[company_column]) or row[company_column] == "":
            continue

        company = str(row[company_column]).strip()
        tags = parse_tags(row[tag_column])

        is_review = any(tag.startswith("리뷰") for tag in tags)
        is_upsell = any(tag.startswith("업셀") for tag in tags)
        is_push = any(tag.startswith("푸시") for tag in tags)

        if is_review:
            company_sets["review"].add(company)
        if is_upsell:
            company_sets["upsell"].add(company)
        if is_push:
            company_sets["push"].add(company)

        if is_review and is_upsell:
            company_sets["review_upsell"].add(company)
        if is_upsell and is_push:
            company_sets["upsell_push"].add(company)
        if is_push and is_review:
            company_sets["push_review"].add(company)
        if is_review and is_upsell and is_push:
            company_sets["review_upsell_push"].add(company)

    return {key: len(companies) for key, companies in company_sets.items()}