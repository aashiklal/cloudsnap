import pytest

from backend.image_records import (
    FAILED_STATUS,
    PROCESSING_STATUS,
    READY_STATUS,
    delete_image_record_assets,
    image_url_for_s3_object,
    mark_image_record_failed,
    mark_image_record_ready,
    new_processing_image_record,
    normalize_image_record,
    query_library_user_image_records,
    search_ready_image_records,
    tags_from_rekognition_labels,
    validated_s3_key_from_image_url,
)
from tests.conftest import BUCKET_NAME, USER_ID


def test_validated_s3_key_from_image_url_accepts_only_configured_bucket():
    assert validated_s3_key_from_image_url(
        BUCKET_NAME,
        f'https://{BUCKET_NAME}.s3.amazonaws.com/{USER_ID}/image.jpg',
    ) == f'{USER_ID}/image.jpg'
    assert validated_s3_key_from_image_url(
        BUCKET_NAME,
        f'https://s3.amazonaws.com/{BUCKET_NAME}/{USER_ID}/image.jpg',
    ) == f'{USER_ID}/image.jpg'
    assert validated_s3_key_from_image_url(
        BUCKET_NAME,
        f'https://other-bucket.s3.amazonaws.com/{USER_ID}/image.jpg',
    ) is None


def test_new_and_normalized_image_records_default_processing_state():
    record = new_processing_image_record('https://example.com/image.jpg', USER_ID)

    assert record['UserID'] == USER_ID
    assert record['Tags'] == []
    assert record['ProcessingStatus'] == PROCESSING_STATUS
    assert normalize_image_record({'ImageURL': 'legacy.jpg'}) == {
        'ImageURL': 'legacy.jpg',
        'Tags': [],
        'ProcessingStatus': READY_STATUS,
    }


def test_tags_from_rekognition_labels_are_lowercase_image_record_tags():
    assert tags_from_rekognition_labels([{'Name': 'Dog'}, {'Name': 'Animal'}]) == [
        {'tag': 'dog', 'count': 1},
        {'tag': 'animal', 'count': 1},
    ]


def test_query_library_user_image_records_normalizes_and_sorts(aws_resources):
    table = aws_resources['table']
    table.put_item(Item={
        'ImageURL': 'https://example.com/old.jpg',
        'UserID': USER_ID,
        'UploadedAt': '2024-01-01T00:00:00Z',
    })
    table.put_item(Item={
        'ImageURL': 'https://example.com/new.jpg',
        'UserID': USER_ID,
        'UploadedAt': '2024-01-02T00:00:00Z',
        'ProcessingStatus': PROCESSING_STATUS,
    })

    records = query_library_user_image_records(table, USER_ID, newest_first=True)

    assert [record['ImageURL'] for record in records] == [
        'https://example.com/new.jpg',
        'https://example.com/old.jpg',
    ]
    assert records[0]['ProcessingStatus'] == PROCESSING_STATUS
    assert records[1]['ProcessingStatus'] == READY_STATUS
    assert records[1]['Tags'] == []


def test_mark_image_record_ready_and_failed_update_processing_state(aws_resources):
    table = aws_resources['table']
    ready_url = image_url_for_s3_object(BUCKET_NAME, f'{USER_ID}/ready.jpg')
    failed_url = image_url_for_s3_object(BUCKET_NAME, f'{USER_ID}/failed.jpg')

    mark_image_record_ready(table, ready_url, f'{USER_ID}/ready.jpg', [{'tag': 'dog', 'count': 1}])
    mark_image_record_failed(table, failed_url, f'{USER_ID}/failed.jpg', 'x' * 600)

    ready = table.get_item(Key={'ImageURL': ready_url})['Item']
    failed = table.get_item(Key={'ImageURL': failed_url})['Item']

    assert ready['ProcessingStatus'] == READY_STATUS
    assert ready['ProcessingError'] == ''
    assert ready['Tags'] == [{'tag': 'dog', 'count': 1}]
    assert failed['ProcessingStatus'] == FAILED_STATUS
    assert failed['Tags'] == []
    assert len(failed['ProcessingError']) == 500


def test_delete_image_record_assets_deletes_s3_object_and_table_row(aws_resources):
    s3 = aws_resources['s3']
    table = aws_resources['table']
    key = f'{USER_ID}/delete.jpg'
    url = image_url_for_s3_object(BUCKET_NAME, key)
    s3.put_object(Bucket=BUCKET_NAME, Key=key, Body=b'image')
    table.put_item(Item={
        'ImageURL': url,
        'UserID': USER_ID,
        'UploadedAt': '2024-01-01T00:00:00Z',
        'Tags': [],
    })

    assert delete_image_record_assets(table, s3, BUCKET_NAME, url) == ['S3', 'database']
    assert table.get_item(Key={'ImageURL': url}).get('Item') is None
    assert s3.list_objects_v2(Bucket=BUCKET_NAME).get('Contents') is None


def test_delete_image_record_assets_rejects_other_bucket_urls(aws_resources):
    with pytest.raises(ValueError):
        delete_image_record_assets(
            aws_resources['table'],
            aws_resources['s3'],
            BUCKET_NAME,
            'https://other-bucket.s3.amazonaws.com/delete.jpg',
        )


def test_search_ready_image_records_skips_processing_records(aws_resources):
    results = search_ready_image_records(
        [
            {'ImageURL': f'https://{BUCKET_NAME}.s3.amazonaws.com/ready.jpg', 'ProcessingStatus': READY_STATUS},
            {'ImageURL': f'https://{BUCKET_NAME}.s3.amazonaws.com/processing.jpg', 'ProcessingStatus': PROCESSING_STATUS},
        ],
        lambda record: True,
        aws_resources['s3'],
        BUCKET_NAME,
    )

    assert len(results) == 1
    assert results[0]['imageUrl'] == f'https://{BUCKET_NAME}.s3.amazonaws.com/ready.jpg'
    assert results[0]['processingStatus'] == READY_STATUS
