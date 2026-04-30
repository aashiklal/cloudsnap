from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone
from typing import Callable, Iterable
from urllib.parse import urlparse

from boto3.dynamodb.conditions import Key

READY_STATUS = 'ready'
PROCESSING_STATUS = 'processing'
FAILED_STATUS = 'failed'
PRESIGN_EXPIRY_SECONDS = 3600


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')


def decimal_to_json(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError(f'Object of type {type(obj)} is not JSON serializable')


def s3_key_from_image_url(bucket_name: str, image_url: str) -> str:
    prefix = f'https://{bucket_name}.s3.amazonaws.com/'
    return image_url[len(prefix):] if image_url.startswith(prefix) else image_url


def validated_s3_key_from_image_url(bucket_name: str, image_url: str) -> str | None:
    try:
        parsed = urlparse(image_url)
        host = parsed.netloc
        path = parsed.path.split('?')[0].lstrip('/')
        if host == f'{bucket_name}.s3.amazonaws.com' or host.startswith('s3.amazonaws.com'):
            if host.startswith('s3.amazonaws.com') and path.startswith(f'{bucket_name}/'):
                path = path[len(bucket_name) + 1:]
            if path:
                return path
    except Exception:
        pass
    return None


def image_url_for_s3_object(bucket_name: str, key: str) -> str:
    return f'https://{bucket_name}.s3.amazonaws.com/{key}'


def user_id_from_s3_key(key: str) -> str:
    return key.split('/')[0] if '/' in key else 'unknown'


def presign_image_url(s3_client, bucket_name: str, image_url: str) -> str:
    return s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_name, 'Key': s3_key_from_image_url(bucket_name, image_url)},
        ExpiresIn=PRESIGN_EXPIRY_SECONDS,
    )


def normalize_image_record(item: dict) -> dict:
    record = dict(item)
    record['Tags'] = record.get('Tags', [])
    record['ProcessingStatus'] = record.get('ProcessingStatus', READY_STATUS)
    return record


def new_processing_image_record(image_url: str, user_id: str) -> dict:
    return {
        'ImageURL': image_url,
        'UserID': user_id,
        'UploadedAt': utc_timestamp(),
        'Tags': [],
        'ProcessingStatus': PROCESSING_STATUS,
    }


def tags_from_rekognition_labels(labels: Iterable[dict]) -> list[dict]:
    return [
        {'tag': str(label['Name']).lower(), 'count': 1}
        for label in labels
    ]


def put_processing_image_record(table, image_url: str, user_id: str) -> dict:
    record = new_processing_image_record(image_url, user_id)
    table.put_item(Item=record)
    return record


def get_image_record(table, image_url: str) -> dict | None:
    return table.get_item(Key={'ImageURL': image_url}).get('Item')


def delete_image_record(table, image_url: str) -> None:
    table.delete_item(Key={'ImageURL': image_url})


def image_record_belongs_to_user(record: dict, user_id: str) -> bool:
    return record.get('UserID') == user_id


def delete_image_record_assets(table, s3_client, bucket_name: str, image_url: str) -> list[str]:
    image_key = validated_s3_key_from_image_url(bucket_name, image_url)
    if image_key is None:
        raise ValueError('Invalid image URL: must be a valid S3 URL for this bucket')

    deleted_from = []
    s3_client.delete_object(Bucket=bucket_name, Key=image_key)
    deleted_from.append('S3')
    delete_image_record(table, image_url)
    deleted_from.append('database')
    return deleted_from


def mark_image_record_ready(table, image_url: str, key: str, tags: list[dict]) -> None:
    now = utc_timestamp()
    table.update_item(
        Key={'ImageURL': image_url},
        UpdateExpression=(
            'SET Tags = :tags, '
            'ProcessingStatus = :status, '
            'ProcessingError = :empty_error, '
            'ProcessedAt = :processed_at, '
            'UserID = if_not_exists(UserID, :uid), '
            'UploadedAt = if_not_exists(UploadedAt, :ts)'
        ),
        ExpressionAttributeValues={
            ':tags': tags,
            ':status': READY_STATUS,
            ':empty_error': '',
            ':processed_at': now,
            ':uid': user_id_from_s3_key(key),
            ':ts': now,
        },
    )


def mark_image_record_failed(table, image_url: str, key: str, error: str) -> None:
    now = utc_timestamp()
    table.update_item(
        Key={'ImageURL': image_url},
        UpdateExpression=(
            'SET ProcessingStatus = :status, '
            'ProcessingError = :error, '
            'ProcessedAt = :processed_at, '
            'UserID = if_not_exists(UserID, :uid), '
            'UploadedAt = if_not_exists(UploadedAt, :ts), '
            'Tags = if_not_exists(Tags, :tags)'
        ),
        ExpressionAttributeValues={
            ':status': FAILED_STATUS,
            ':error': error[:500],
            ':processed_at': now,
            ':uid': user_id_from_s3_key(key),
            ':ts': now,
            ':tags': [],
        },
    )


def is_ready_image_record(item: dict) -> bool:
    return normalize_image_record(item)['ProcessingStatus'] == READY_STATUS


def query_library_user_image_records(table, user_id: str, newest_first: bool = False) -> list[dict]:
    query_kwargs = {
        'IndexName': 'UserID-UploadedAt-index',
        'KeyConditionExpression': Key('UserID').eq(user_id),
        'ScanIndexForward': not newest_first,
    }

    records = []
    while True:
        response = table.query(**query_kwargs)
        records.extend(normalize_image_record(item) for item in response.get('Items', []))
        if 'LastEvaluatedKey' not in response:
            break
        query_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

    return records


def with_presigned_url(record: dict, s3_client, bucket_name: str) -> dict:
    enriched = dict(record)
    enriched['PresignedURL'] = presign_image_url(s3_client, bucket_name, enriched['ImageURL'])
    return enriched


def to_search_result(record: dict, s3_client, bucket_name: str) -> dict:
    normalized = normalize_image_record(record)
    return {
        'imageUrl': normalized['ImageURL'],
        'presignedUrl': presign_image_url(s3_client, bucket_name, normalized['ImageURL']),
        'processingStatus': normalized['ProcessingStatus'],
    }


def search_ready_image_records(
    records: Iterable[dict],
    matches: Callable[[dict], bool],
    s3_client,
    bucket_name: str,
) -> list[dict]:
    return [
        to_search_result(record, s3_client, bucket_name)
        for record in records
        if is_ready_image_record(record) and matches(record)
    ]
