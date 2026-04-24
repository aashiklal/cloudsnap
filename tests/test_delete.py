import json
import sys
import pytest
from tests.conftest import BUCKET_NAME


def _handler():
    if 'backend.delete.lambda_function' in sys.modules:
        del sys.modules['backend.delete.lambda_function']
    import backend.delete.lambda_function as m
    return m.lambda_handler


def _event(image_url):
    return {'queryStringParameters': {'image_url': image_url}}


def _seed_s3(s3, key):
    s3.put_object(Bucket=BUCKET_NAME, Key=key, Body=b'fake-image')


def _seed_ddb(table, url):
    table.put_item(Item={'ImageURL': url, 'Tags': []})


def test_delete_from_both(aws_resources):
    key = 'photo.jpg'
    url = f'https://{BUCKET_NAME}.s3.amazonaws.com/{key}'
    _seed_s3(aws_resources['s3'], key)
    _seed_ddb(aws_resources['table'], url)

    handler = _handler()
    resp = handler(_event(url), {})
    assert resp['statusCode'] == 200
    assert 'S3' in json.loads(resp['body'])['message']
    assert 'database' in json.loads(resp['body'])['message']


def test_delete_not_found(aws_resources):
    url = f'https://{BUCKET_NAME}.s3.amazonaws.com/nonexistent.jpg'
    handler = _handler()
    resp = handler(_event(url), {})
    assert resp['statusCode'] == 404


def test_delete_missing_param(aws_resources):
    handler = _handler()
    resp = handler({'queryStringParameters': {}}, {})
    assert resp['statusCode'] == 400


def test_delete_url_injection_rejected(aws_resources):
    handler = _handler()
    # Attempt to pass a non-S3 URL to trigger injection
    resp = handler(_event('https://evil.com/../../secrets'), {})
    assert resp['statusCode'] == 400
