# 🚀 AWS App Runner 배포 가이드

## 📋 사전 준비

### 1. GitHub 리포지토리 준비
```bash
# 코드를 GitHub에 푸시
git add .
git commit -m "App Runner 배포 준비"
git push origin main
```

### 2. 환경변수 준비
- `SPREADSHEET_ID`: Google Sheets ID
- `GOOGLE_SERVICE_ACCOUNT`: token.json 내용을 JSON 문자열로 변환

## 🔧 App Runner 서비스 생성

### AWS 콘솔에서 배포

1. **AWS App Runner 콘솔** 접속
2. **"Create service"** 클릭
3. **Source 설정**:
   - Repository type: `Source code repository`
   - Provider: `GitHub`
   - Repository: 본인의 리포지토리 선택
   - Branch: `main`

4. **Deployment settings**:
   - Deployment trigger: `Automatic`
   - Configuration file: `Use a configuration file` 선택

5. **Service settings**:
   - Service name: `google-sheets-analyzer`
   - Virtual CPU: `0.25 vCPU`
   - Memory: `0.5 GB`

6. **Environment variables** 설정:
   ```
   SPREADSHEET_ID = 1DnOFmsfq_7vq4A1Hf9AVMEPnKP5aHzJsIJN6yeAkbkA
   GOOGLE_SERVICE_ACCOUNT = {"type":"service_account",...} (token.json 내용)
   ```

7. **Create & deploy** 클릭

## 🔐 보안 설정 (권장)

### AWS Secrets Manager 사용
```bash
# Google Service Account 저장
aws secretsmanager create-secret \
    --name "salad-lab/google-service-account" \
    --secret-string file://token.json

# Spreadsheet ID 저장
aws secretsmanager create-secret \
    --name "salad-lab/spreadsheet-id" \
    --secret-string "1DnOFmsfq_7vq4A1Hf9AVMEPnKP5aHzJsIJN6yeAkbkA"
```

## 📊 예상 비용
- **기본 설정**: 월 $7-15
- **실제 사용량에 따라 변동**

## 🔍 배포 확인
1. App Runner 콘솔에서 서비스 상태 확인
2. 제공된 URL로 앱 접속 테스트
3. Google Sheets 연동 확인

## 🛠️ 문제 해결

### 일반적인 오류
1. **환경변수 오류**: App Runner 콘솔에서 환경변수 재확인
2. **Google API 오류**: Service Account 권한 확인
3. **빌드 실패**: CloudWatch 로그 확인

### 로그 확인
- App Runner 콘솔 → Logs 탭
- CloudWatch에서 상세 로그 확인 가능