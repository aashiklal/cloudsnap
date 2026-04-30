import json
import sys
import pytest
from tests.conftest import TABLE_NAME, USER_ID


def _seed(table, items):
    for item in items:
        table.put_item(Item=item)


def _handler(aws_resources):
    if 'backend.list_images.lambda_function' in sys.modules:
        del sys.modules['backend.list_images.lambda_function']
    # handle hyphen in package name
    import importlib
    mod = importlib.import_module('backend.list-images.lambda_function'.replace('-', '_'))
    return mod.lambda_handler


# Import path uses underscore-mapped module name
import importlib, types


def get_handler():
    mod_name = 'backend.list_images.lambda_function'
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    import backend
    spec = importlib.util.spec_from_file_location(
        mod_name,
        'backend/list-images/lambda_function.py',
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod.lambda_handler


def _auth_event():
    return {'requestContext': {'authorizer': {'jwt': {'claims': {'sub': USER_ID}}}}}


def test_list_images_empty(aws_resources):
    handler = get_handler()
    resp = handler(_auth_event(), {})
    assert resp['statusCode'] == 200
    assert json.loads(resp['body']) == []


def test_list_images_returns_all_items(aws_resources):
    table = aws_resources['table']
    _seed(table, [
        {'ImageURL': 'https://bucket.s3.amazonaws.com/a.jpg', 'Tags': [{'tag': 'dog', 'count': 2}], 'UserID': USER_ID, 'UploadedAt': '2024-01-02T00:00:00Z'},
        {'ImageURL': 'https://bucket.s3.amazonaws.com/b.jpg', 'Tags': [{'tag': 'cat', 'count': 1}], 'UserID': USER_ID, 'UploadedAt': '2024-01-01T00:00:00Z'},
    ])
    handler = get_handler()
    resp = handler(_auth_event(), {})
    assert resp['statusCode'] == 200
    body = json.loads(resp['body'])
    assert len(body) == 2
    urls = {item['ImageURL'] for item in body}
    assert 'https://bucket.s3.amazonaws.com/a.jpg' in urls
    assert 'https://bucket.s3.amazonaws.com/b.jpg' in urls


def test_list_images_cors_headers(aws_resources):
    handler = get_handler()
    resp = handler(_auth_event(), {})
    assert 'Access-Control-Allow-Origin' in resp['headers']


def test_list_images_options_preflight(aws_resources):
    handler = get_handler()
    resp = handler({'requestContext': {'http': {'method': 'OPTIONS'}}}, {})
    assert resp['statusCode'] == 200


def test_list_images_returns_tags(aws_resources):
    table = aws_resources['table']
    _seed(table, [
        {'ImageURL': 'https://bucket.s3.amazonaws.com/c.jpg', 'Tags': [{'tag': 'person', 'count': 3}], 'UserID': USER_ID, 'UploadedAt': '2024-01-01T00:00:00Z'},
    ])
    handler = get_handler()
    resp = handler(_auth_event(), {})
    body = json.loads(resp['body'])
    match = next((i for i in body if i['ImageURL'].endswith('c.jpg')), None)
    assert match is not None
    assert match['Tags'][0]['tag'] == 'person'


def test_list_images_defaults_missing_processing_status_to_ready(aws_resources):
    table = aws_resources['table']
    _seed(table, [
        {'ImageURL': 'https://bucket.s3.amazonaws.com/legacy.jpg', 'Tags': [], 'UserID': USER_ID, 'UploadedAt': '2024-01-01T00:00:00Z'},
    ])
    handler = get_handler()
    resp = handler(_auth_event(), {})
    body = json.loads(resp['body'])
    assert body[0]['ProcessingStatus'] == 'ready'
