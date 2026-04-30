import json
import base64
import importlib
import sys
import pytest
from tests.conftest import VALID_JPEG_B64, BUCKET_NAME


def _handler(aws_resources):
    if 'backend.upload.lambda_function' in sys.modules:
        del sys.modules['backend.upload.lambda_function']
    import backend.upload.lambda_function as m
    return m.lambda_handler


def _event(image_b64, filename='test.jpg'):
    return {'body': json.dumps({'image': image_b64, 'filename': filename})}


def test_upload_valid_jpeg(aws_resources):
    handler = _handler(aws_resources)
    resp = handler(_event(VALID_JPEG_B64), {})
    assert resp['statusCode'] == 200
    body = json.loads(resp['body'])
    assert 'url' in body
    assert body['processingStatus'] == 'processing'

    stored = aws_resources['table'].get_item(Key={'ImageURL': body['url']})['Item']
    assert stored['ProcessingStatus'] == 'processing'
    assert stored['Tags'] == []


def test_upload_missing_fields(aws_resources):
    handler = _handler(aws_resources)
    resp = handler({'body': json.dumps({'filename': 'test.jpg'})}, {})
    assert resp['statusCode'] == 400


def test_upload_invalid_mime_type(aws_resources):
    handler = _handler(aws_resources)
    fake_text = base64.b64encode(b'this is just text').decode()
    resp = handler(_event(fake_text), {})
    assert resp['statusCode'] == 400
    assert 'Invalid file type' in json.loads(resp['body'])['error']


def test_upload_file_too_large(aws_resources):
    handler = _handler(aws_resources)
    large_data = base64.b64encode(b'\xff\xd8\xff' + b'\x00' * (11 * 1024 * 1024)).decode()
    resp = handler(_event(large_data), {})
    assert resp['statusCode'] == 400
    assert 'too large' in json.loads(resp['body'])['error'].lower()


def test_upload_cors_headers_present(aws_resources):
    handler = _handler(aws_resources)
    resp = handler(_event(VALID_JPEG_B64), {})
    assert 'Access-Control-Allow-Origin' in resp['headers']
