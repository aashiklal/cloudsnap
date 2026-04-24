#!/bin/bash
set -e

echo "Bootstrapping LocalStack..."

awslocal s3 mb s3://cloudsnap-images-local

awslocal dynamodb create-table \
  --table-name cloudsnap-results-table \
  --attribute-definitions AttributeName=ImageURL,AttributeType=S \
  --key-schema AttributeName=ImageURL,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-southeast-2

echo "LocalStack bootstrap complete."
