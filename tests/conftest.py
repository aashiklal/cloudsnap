import os
import base64
import pytest
import boto3
from moto import mock_aws

REGION = 'ap-southeast-2'
BUCKET_NAME = 'test-cloudsnap-bucket'
TABLE_NAME = 'test-cloudsnap-table'
ALLOWED_ORIGIN = 'http://localhost:3000'

# Minimal valid JPEG (2x2 white pixels)
VALID_JPEG_B64 = base64.b64encode(
    b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
    b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
    b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
    b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\x1e!'
    b'\xff\xd9'
).decode()


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', REGION)
    monkeypatch.setenv('BUCKET_NAME', BUCKET_NAME)
    monkeypatch.setenv('TABLE_NAME', TABLE_NAME)
    monkeypatch.setenv('ALLOWED_ORIGIN', ALLOWED_ORIGIN)


@pytest.fixture
def aws_resources():
    with mock_aws():
        s3 = boto3.client('s3', region_name=REGION)
        s3.create_bucket(
            Bucket=BUCKET_NAME,
            CreateBucketConfiguration={'LocationConstraint': REGION},
        )

        ddb = boto3.resource('dynamodb', region_name=REGION)
        table = ddb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{'AttributeName': 'ImageURL', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'ImageURL', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )
        yield {'s3': s3, 'table': table}
