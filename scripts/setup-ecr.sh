#!/bin/bash

# ECR 리포지토리 생성 스크립트

AWS_REGION="ap-northeast-2"
REPOSITORY_NAME="google-sheets-analyzer"

echo "🚀 ECR 리포지토리 생성 중..."

# ECR 리포지토리 생성
aws ecr create-repository \
    --repository-name $REPOSITORY_NAME \
    --region $AWS_REGION \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256

echo "✅ ECR 리포지토리 생성 완료!"
echo "📋 리포지토리 URI: $(aws ecr describe-repositories --repository-names $REPOSITORY_NAME --region $AWS_REGION --query 'repositories[0].repositoryUri' --output text)"