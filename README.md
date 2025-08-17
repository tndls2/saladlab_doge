# 🥗 샐러드랩 상담데이터 분석기

샐러드랩 상담 데이터를 자동으로 분석하고 시각화하는 **Streamlit 기반 웹 애플리케이션**입니다.

Google Sheets에 저장된 상담 태그 데이터를 실시간으로 분석하여 인사이트를 제공합니다.

> **현재 버전**: v2.0 (상담 태그 분석 및 다중 시트 비교)

## 🎯 프로젝트 목적

상담 데이터의 **태그 분석**을 통해 고객 문의 패턴을 파악하고, 데이터 기반 의사결정을 지원합니다.
- 리뷰, 업셀, 푸시 카테고리별 상담 현황 분석
- 시기별 상담 트렌드 비교 분석
- 직관적인 차트를 통한 데이터 시각화

## 🚀 주요 기능

### 📊 단일 분석 모드
1. **카테고리별 태그 분석**: 리뷰/업셀/푸시 상담태그 자동 분류
2. **시각화**: 전체 태그는 막대차트, 중분류는 도넛차트로 표시
3. **데이터 테이블**: 태그별 개수와 비율을 표 형태로 제공

### 🔄 다중 비교 모드
1. **시트간 비교**: 여러 시트의 상담 데이터를 동시에 비교
2. **변화량 분석**: 시기별 상담량 증감 추이 확인
3. **상위 태그 하이라이트**: 각 카테고리별 상위 5개 태그 강조 표시

## 📋 기술 요구사항

- Python 3.7+
- Google Cloud Console 프로젝트
- Google Sheets API 활성화
- Service Account 인증 정보

## 🛠️ 설치 및 설정

### 1. 가상환경 생성 및 패키지 설치
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate     # Windows

# 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 설정
- Google Sheets API 접근을 위한 `token.json` 파일 다운로드
- spreadsheet_id 정보가 저장된 `.env` 파일 다운로드

## 🖥️ 사용법

### Streamlit 웹 애플리케이션
```bash
python run_streamlit.py
```
- **웹 앱**: http://localhost:8501
- 사이드바에서 분석 모드 선택 (단일 분석 / 다중 비교)
- 분석할 시트 선택 후 버튼 클릭
- 실시간으로 차트와 데이터 테이블 확인

### 주요 차트 유형
- **막대 차트**: 전체 상담태그 (리뷰_상담태그, 업셀_상담태그, 푸시_상담태그)
- **비교 테이블**: 다중 시트 분석 시 변화량과 상위 태그 하이라이트

## 📈 데이터 구조

상담 태그는 다음과 같은 계층 구조로 분류됩니다:
```
대분류/중분류/소분류
예: 리뷰/요청사항/기능개선, 업셀/도입문의/가격문의
```

## 🔧 기술 스택

- **Frontend**: Streamlit
- **Backend**: Python 3.7+
- **Data Processing**: Pandas, Matplotlib
- **API**: Google Sheets API v4
- **Authentication**: Google Service Account

## 📄 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다.

```
MIT License

Copyright (c) 2025 Suin Park

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
