import json
import sys
import importlib
import importlib.util
from unittest.mock import patch, MagicMock
import pytest
from tests.conftest import TABLE_NAME, BUCKET_NAME


def get_handler():
    mod_name = 'backend.object_detection.lambda_function'
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(
        mod_name,
        'backend/object-detection/lambda_function.py',
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod.lambda_handler


def _s3_event(bucket=BUCKET_NAME, key='photo.jpg'):
    return {
        'Records': [{
            's3': {
                'bucket': {'name': bucket},
                'object': {'key': key},
            }
        }]
    }


MOCK_LABELS = {
    'Labels': [
        {'Name': 'Dog', 'Confidence': 95.0},
        {'Name': 'Animal', 'Confidence': 88.0},
        {'Name': 'Outdoors', 'Confidence': 75.0},
    ]
}


def test_object_detection_stores_tags(aws_resources):
    mock_rekog = MagicMock()
    mock_rekog.detect_labels.return_value = MOCK_LABELS

    with patch('boto3.client', return_value=mock_rekog):
        handler = get_handler()
        resp = handler(_s3_event(), {})

    assert resp['statusCode'] == 200

    table = aws_resources['table']
    image_url = f'https://{BUCKET_NAME}.s3.amazonaws.com/photo.jpg'
    result = table.get_item(Key={'ImageURL': image_url})
    assert 'Item' in result
    tags = result['Item']['Tags']
    tag_names = {t['tag'] for t in tags}
    assert 'dog' in tag_names
    assert 'animal' in tag_names
    assert result['Item']['ProcessingStatus'] == 'ready'
    assert result['Item']['ProcessingError'] == ''
    assert 'ProcessedAt' in result['Item']


def test_object_detection_rekognition_called_with_correct_args(aws_resources):
    mock_rekog = MagicMock()
    mock_rekog.detect_labels.return_value = MOCK_LABELS

    with patch('boto3.client', return_value=mock_rekog):
        handler = get_handler()
        handler(_s3_event(bucket='my-bucket', key='images/cat.png'), {})

    mock_rekog.detect_labels.assert_called_once_with(
        Image={'S3Object': {'Bucket': 'my-bucket', 'Name': 'images/cat.png'}},
        MaxLabels=20,
        MinConfidence=70,
    )


def test_object_detection_url_encoded_key(aws_resources):
    mock_rekog = MagicMock()
    mock_rekog.detect_labels.return_value = {'Labels': [{'Name': 'Car', 'Confidence': 90.0}]}

    with patch('boto3.client', return_value=mock_rekog):
        handler = get_handler()
        event = _s3_event(key='my%20photo.jpg')
        resp = handler(event, {})

    assert resp['statusCode'] == 200
    # key should be decoded: space not %20
    table = aws_resources['table']
    image_url = f'https://{BUCKET_NAME}.s3.amazonaws.com/my photo.jpg'
    result = table.get_item(Key={'ImageURL': image_url})
    assert 'Item' in result


def test_object_detection_rekognition_error_raises(aws_resources):
    mock_rekog = MagicMock()
    mock_rekog.detect_labels.side_effect = Exception('Rekognition unavailable')

    with patch('boto3.client', return_value=mock_rekog):
        handler = get_handler()
        with pytest.raises(Exception, match='Rekognition unavailable'):
            handler(_s3_event(), {})

    table = aws_resources['table']
    image_url = f'https://{BUCKET_NAME}.s3.amazonaws.com/photo.jpg'
    result = table.get_item(Key={'ImageURL': image_url})
    assert result['Item']['ProcessingStatus'] == 'failed'
    assert result['Item']['ProcessingError'] == 'Rekognition unavailable'
