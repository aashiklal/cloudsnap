import json
import sys
import pytest
from tests.conftest import TABLE_NAME


def _handler():
    if 'backend.search-tags.lambda_function' in sys.modules:
        del sys.modules['backend.search-tags.lambda_function']
    import importlib
    mod = importlib.import_module('backend.search-tags.lambda_function')
    return mod.lambda_handler


def _event(params):
    return {'queryStringParameters': params}


def _seed(table, url, tags):
    table.put_item(Item={'ImageURL': url, 'Tags': tags})


def test_search_returns_matching_image(aws_resources):
    _seed(aws_resources['table'], 'https://example.com/cat.jpg', [{'tag': 'cat', 'count': 3}])
    handler = _handler()
    resp = handler(_event({'tag1': 'cat', 'tag1count': '2'}), {})
    assert resp['statusCode'] == 200
    assert 'https://example.com/cat.jpg' in json.loads(resp['body'])


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
    resp = handler(_event({'tag1': 'cat123', 'tag1count': '2'}), {})
    assert resp['statusCode'] == 400
