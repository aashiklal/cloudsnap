import json
import sys
import base64
import importlib
import importlib.util
import boto3
from unittest.mock import patch, MagicMock
import pytest
from tests.conftest import TABLE_NAME, VALID_JPEG_B64, USER_ID


def get_handler():
    mod_name = 'backend.search_by_image.lambda_function'
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(
        mod_name,
        'backend/search-by-image/lambda_function.py',
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod.lambda_handler


def _event(image_b64=None, is_base64=False, raw_body=None):
    auth = {'requestContext': {'authorizer': {'jwt': {'claims': {'sub': USER_ID}}}}}
    if raw_body is not None:
        return {'body': raw_body, 'isBase64Encoded': is_base64, **auth}
    body = json.dumps({'imageFile': image_b64 or VALID_JPEG_B64})
    return {'body': body, 'isBase64Encoded': False, **auth}


MOCK_LABELS = {
    'Labels': [
        {'Name': 'Dog', 'Confidence': 92.0},
        {'Name': 'Animal', 'Confidence': 85.0},
    ]
}


def _seed(table, items):
    for item in items:
        table.put_item(Item=item)


def test_search_by_image_finds_matching(aws_resources):
    table = aws_resources['table']
    _seed(table, [
        {'ImageURL': 'https://bucket.s3.amazonaws.com/dog.jpg', 'Tags': [{'tag': 'dog', 'count': 1}], 'UserID': USER_ID, 'UploadedAt': '2024-01-02T00:00:00Z'},
        {'ImageURL': 'https://bucket.s3.amazonaws.com/cat.jpg', 'Tags': [{'tag': 'cat', 'count': 1}], 'UserID': USER_ID, 'UploadedAt': '2024-01-01T00:00:00Z'},
    ])

    mock_rekog = MagicMock()
    mock_rekog.detect_labels.return_value = MOCK_LABELS
    mock_rekog.exceptions.InvalidImageException = Exception

    real_client = boto3.client
    with patch('boto3.client', side_effect=lambda svc, **kw: mock_rekog if svc == 'rekognition' else real_client(svc, **kw)):
        handler = get_handler()
        resp = handler(_event(), {})

    assert resp['statusCode'] == 200
    results = json.loads(resp['body'])
    image_urls = [r['imageUrl'] for r in results]
    assert 'https://bucket.s3.amazonaws.com/dog.jpg' in image_urls
    assert 'https://bucket.s3.amazonaws.com/cat.jpg' not in image_urls


def test_search_by_image_no_matches_returns_404(aws_resources):
    table = aws_resources['table']
    _seed(table, [
        {'ImageURL': 'https://bucket.s3.amazonaws.com/sky.jpg', 'Tags': [{'tag': 'sky', 'count': 1}], 'UserID': USER_ID, 'UploadedAt': '2024-01-01T00:00:00Z'},
    ])

    mock_rekog = MagicMock()
    mock_rekog.detect_labels.return_value = MOCK_LABELS
    mock_rekog.exceptions.InvalidImageException = Exception

    with patch('boto3.client', return_value=mock_rekog):
        handler = get_handler()
        resp = handler(_event(), {})

    assert resp['statusCode'] == 404


def test_search_by_image_no_labels_detected(aws_resources):
    mock_rekog = MagicMock()
    mock_rekog.detect_labels.return_value = {'Labels': []}
    mock_rekog.exceptions.InvalidImageException = Exception

    with patch('boto3.client', return_value=mock_rekog):
        handler = get_handler()
        resp = handler(_event(), {})

    assert resp['statusCode'] == 404
    assert 'No objects detected' in json.loads(resp['body'])['error']


def test_search_by_image_options_preflight(aws_resources):
    handler = get_handler()
    resp = handler({'requestContext': {'http': {'method': 'OPTIONS'}}}, {})
    assert resp['statusCode'] == 200


def test_search_by_image_cors_headers(aws_resources):
    mock_rekog = MagicMock()
    mock_rekog.detect_labels.return_value = {'Labels': []}
    mock_rekog.exceptions.InvalidImageException = Exception

    with patch('boto3.client', return_value=mock_rekog):
        handler = get_handler()
        resp = handler(_event(), {})

    assert 'Access-Control-Allow-Origin' in resp['headers']


def test_search_by_image_missing_image_field(aws_resources):
    handler = get_handler()
    resp = handler({'body': json.dumps({}), 'isBase64Encoded': False}, {})
    assert resp['statusCode'] == 400
    assert 'Missing image' in json.loads(resp['body'])['error']
