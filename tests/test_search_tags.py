import json
import sys
import pytest
from tests.conftest import TABLE_NAME, USER_ID


def _handler():
    if 'backend.search-tags.lambda_function' in sys.modules:
        del sys.modules['backend.search-tags.lambda_function']
    import importlib
    mod = importlib.import_module('backend.search-tags.lambda_function')
    return mod.lambda_handler


def _event(params):
    return {
        'queryStringParameters': params,
        'requestContext': {'authorizer': {'jwt': {'claims': {'sub': USER_ID}}}},
    }


def _seed(table, url, tags):
    table.put_item(Item={'ImageURL': url, 'Tags': tags, 'UserID': USER_ID, 'UploadedAt': '2024-01-01T00:00:00Z'})


def test_search_returns_matching_image(aws_resources):
    _seed(aws_resources['table'], 'https://example.com/cat.jpg', [{'tag': 'cat', 'count': 3}])
    handler = _handler()
    resp = handler(_event({'tag1': 'cat', 'tag1count': '2'}), {})
    assert resp['statusCode'] == 200
    results = json.loads(resp['body'])
    assert any(r['imageUrl'] == 'https://example.com/cat.jpg' for r in results)


def test_search_count_too_high_no_match(aws_resources):
    _seed(aws_resources['table'], 'https://example.com/cat.jpg', [{'tag': 'cat', 'count': 1}])
    handler = _handler()
    resp = handler(_event({'tag1': 'cat', 'tag1count': '5'}), {})
    assert resp['statusCode'] == 404


def test_search_no_results(aws_resources):
    handler = _handler()
    resp = handler(_event({'tag1': 'unicorn', 'tag1count': '1'}), {})
    assert resp['statusCode'] == 404


def test_search_mismatched_tag_count(aws_resources):
    handler = _handler()
    resp = handler(_event({'tag1': 'cat', 'tag2count': '2'}), {})
    assert resp['statusCode'] == 400


def test_search_no_params(aws_resources):
    handler = _handler()
    resp = handler(_event({}), {})
    assert resp['statusCode'] == 400


def test_search_invalid_tag_value(aws_resources):
    handler = _handler()
    resp = handler(_event({'tag1': 'inv@lid!', 'tag1count': '2'}), {})
    assert resp['statusCode'] == 400
