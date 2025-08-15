# 사내 업무 효율화 프로젝트

사내 업무 효율성 개선을 위한 **업무 종합 자동화 플랫폼**입니다.

현재는 Google Sheets 기반의 태그 분석 기능을 제공하며, 앞으로 다양한 데이터 소스와 분석 기능이 지속적으로 추가될 예정입니다.

> **현재 버전**: v1.0 (상담내역 데이터 태그 분석 및 시각화)

## 🎯 프로젝트 목적

반복적이고 수작업으로 진행되던 업무를 **자동화**하여, 업무 효율성과 정확성을 높이는 것을 목표로 합니다. 
이를 통해 작업 속도와 품질을 동시에 향상시키고, 더 가치 있는 업무에 집중할 수 있도록 지원합니다.
> 💡 업무에 필요한 특정 기능이 있으시면 언제든 제안해 주세요!

## 🚀 현재 기능 (v1.0)

### 📊 상담 데이터 분석 기능

1. **시트 목록 조회**: 상담내역 스프레드시트의 모든 시트 정보를 한 번에 확인
2. **태그 데이터 분석 및 차트 생성**: 상담 태그, 카테고리별 데이터를 자동으로 분석하고 집계 & 막대 그래프로 시각화
3. **자동 리포트 생성**: 분석 결과를 바탕으로 리포트 시트 자동 생성

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
- Google Sheets API 접근을 위한`token.json` 파일 다운로드
- spreadsheeet_id 정보가 저장된 `.env` 파일 다운로드


## 🖥️ 사용법

### FastAPI 버전 (기존)
```bash
python run_server.py
```
- **API 문서**: http://localhost:8000/docs
- **서버 주소**: http://localhost:8000

### Streamlit 버전 (새로운 웹 인터페이스)
```bash
python run_streamlit.py
```
- **웹 앱**: http://localhost:8501
- 직관적인 웹 인터페이스로 분석 결과 확인
