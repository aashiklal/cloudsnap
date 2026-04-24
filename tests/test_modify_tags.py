import json
import sys
import pytest


def _handler():
    if 'backend.modify-tags.lambda_function' in sys.modules:
        del sys.modules['backend.modify-tags.lambda_function']
    import importlib
    return importlib.import_module('backend.modify-tags.lambda_function').lambda_handler


def _event(body):
    return {'body': json.dumps(body)}


def _seed(table, url, tags):
    table.put_item(Item={'ImageURL': url, 'Tags': tags})


def test_add_tag_increments_count(aws_resources):
    _seed(aws_resources['table'], 'https://example.com/img.jpg', [{'tag': 'dog', 'count': 2}])
    handler = _handler()
    resp = handler(_event({'url': 'https://example.com/img.jpg', 'type': '1', 'tag1': 'dog', 'tag1count': 3}), {})
    assert resp['statusCode'] == 200
    item = aws_resources['table'].get_item(Key={'ImageURL': 'https://example.com/img.jpg'})['Item']
    assert item['Tags'][0]['count'] == 5


def test_add_new_tag_creates_entry(aws_resources):
    _seed(aws_resources['table'], 'https://example.com/img.jpg', [{'tag': 'dog', 'count': 2}])
    handler = _handler()
    resp = handler(_event({'url': 'https://example.com/img.jpg', 'type': '1', 'tag1': 'cat', 'tag1count': 1}), {})
    assert resp['statusCode'] == 200
    item = aws_resources['table'].get_item(Key={'ImageURL': 'https://example.com/img.jpg'})['Item']
    tags = {t['tag']: t['count'] for t in item['Tags']}
    assert tags['cat'] == 1


def test_remove_tag_decrements_count(aws_resources):
    _seed(aws_resources['table'], 'https://example.com/img.jpg', [{'tag': 'dog', 'count': 5}])
    handler = _handler()
    resp = handler(_event({'url': 'https://example.com/img.jpg', 'type': '0', 'tag1': 'dog', 'tag1count': 3}), {})
    assert resp['statusCode'] == 200
    item = aws_resources['table'].get_item(Key={'ImageURL': 'https://example.com/img.jpg'})['Item']
    assert item['Tags'][0]['count'] == 2


def test_remove_tag_to_zero_deletes_it(aws_resources):
    _seed(aws_resources['table'], 'https://example.com/img.jpg', [{'tag': 'dog', 'count': 2}])
    handler = _handler()
    resp = handler(_event({'url': 'https://example.com/img.jpg', 'type': '0', 'tag1': 'dog', 'tag1count': 2}), {})
    assert resp['statusCode'] == 200
    item = aws_resources['table'].get_item(Key={'ImageURL': 'https://example.com/img.jpg'})['Item']
    assert len(item['Tags']) == 0


def test_invalid_type(aws_resources):
    handler = _handler()
    resp = handler(_event({'url': 'https://example.com/img.jpg', 'type': '2'}), {})
    assert resp['statusCode'] == 400


def test_image_not_found(aws_resources):
    handler = _handler()
    resp = handler(_event({'url': 'https://example.com/missing.jpg', 'type': '1', 'tag1': 'cat', 'tag1count': 1}), {})
    assert resp['statusCode'] == 404
