# 🚀 GitHub Actions + ECR + App Runner 배포 가이드

## 📋 배포 아키텍처

```
GitHub → GitHub Actions → ECR → App Runner
```

## 🔧 1단계: AWS 리소스 생성

### ECR 리포지토리 생성
```bash
chmod +x scripts/setup-ecr.sh
./scripts/setup-ecr.sh
```

### App Runner 서비스 생성
```bash
# ECR URI를 실제 값으로 수정 후 실행
chmod +x scripts/create-apprunner.sh
./scripts/create-apprunner.sh
```

## 🔐 2단계: GitHub Secrets 설정

GitHub 리포지토리 → Settings → Secrets and variables → Actions

### 필수 Secrets
```
AWS_ACCESS_KEY_ID: AKIA...
AWS_SECRET_ACCESS_KEY: ...
APP_RUNNER_SERVICE_ARN: arn:aws:apprunner:ap-northeast-2:...
GOOGLE_SERVICE_ACCOUNT: {"type":"service_account",...}
```

### AWS IAM 사용자 권한
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:PutImage"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "apprunner:StartDeployment",
                "apprunner:DescribeService"
            ],
            "Resource": "arn:aws:apprunner:*:*:service/google-sheets-analyzer/*"
        }
    ]
}
```

## 🚀 3단계: 배포 실행

### 자동 배포
```bash
git add .
git commit -m "CI/CD 파이프라인 설정"
git push origin main
```

### 수동 배포
GitHub Actions 탭에서 "Deploy to AWS App Runner" 워크플로우 실행

## 📊 4단계: 배포 확인

1. **GitHub Actions**: 빌드 및 배포 상태 확인
2. **ECR**: 이미지 푸시 확인
3. **App Runner**: 서비스 상태 및 URL 확인

## 🔍 모니터링

### CloudWatch 로그
- App Runner 서비스 로그 자동 수집
- 에러 및 성능 모니터링

### 비용 최적화
- ECR 이미지 라이프사이클 정책 설정
- App Runner 자동 스케일링 활용

## 🛠️ 문제 해결

### 일반적인 오류
1. **ECR 권한 오류**: IAM 정책 확인
2. **App Runner 배포 실패**: CloudWatch 로그 확인
3. **환경변수 오류**: GitHub Secrets 재확인

### 유용한 명령어
```bash
# ECR 이미지 목록 확인
aws ecr list-images --repository-name google-sheets-analyzer

# App Runner 서비스 상태 확인
aws apprunner describe-service --service-arn YOUR_SERVICE_ARN

# 수동 배포 트리거
aws apprunner start-deployment --service-arn YOUR_SERVICE_ARN
```