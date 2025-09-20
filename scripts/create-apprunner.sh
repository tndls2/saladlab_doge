#!/bin/bash

# App Runner 서비스 생성 스크립트

AWS_REGION="ap-northeast-2"
SERVICE_NAME="google-sheets-analyzer"
ECR_REPOSITORY_URI="YOUR_ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/google-sheets-analyzer"

echo "🚀 App Runner 서비스 생성 중..."

# App Runner 서비스 생성
aws apprunner create-service \
    --service-name $SERVICE_NAME \
    --source-configuration '{
        "ImageRepository": {
            "ImageIdentifier": "'$ECR_REPOSITORY_URI':latest",
            "ImageConfiguration": {
                "Port": "8501",
                "RuntimeEnvironmentVariables": {
                    "PORT": "8501",
                    "SPREADSHEET_ID": "1DnOFmsfq_7vq4A1Hf9AVMEPnKP5aHzJsIJN6yeAkbkA"
                }
            },
            "ImageRepositoryType": "ECR"
        },
        "AutoDeploymentsEnabled": true
    }' \
    --instance-configuration '{
        "Cpu": "0.25 vCPU",
        "Memory": "0.5 GB"
    }' \
    --region $AWS_REGION

echo "✅ App Runner 서비스 생성 완료!"