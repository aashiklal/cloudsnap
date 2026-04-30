from __future__ import annotations

import os
import logging
import boto3
from botocore.exceptions import ClientError

try:
    from backend.http_api import (
        cors_headers,
        error_response,
        is_preflight_request,
        json_response,
        preflight_response,
        user_id_from_event,
    )
    from backend.image_records import (
        delete_image_record_assets,
        get_image_record,
        image_record_belongs_to_user,
        validated_s3_key_from_image_url,
    )
except ModuleNotFoundError:
    from http_api import (
        cors_headers,
        error_response,
        is_preflight_request,
        json_response,
        preflight_response,
        user_id_from_event,
    )
    from image_records import (
        delete_image_record_assets,
        get_image_record,
        image_record_belongs_to_user,
        validated_s3_key_from_image_url,
    )

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BUCKET_NAME = os.environ['BUCKET_NAME']
TABLE_NAME = os.environ['TABLE_NAME']

CORS_HEADERS = cors_headers('OPTIONS,DELETE')

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')


def lambda_handler(event, context):
    if is_preflight_request(event):
        return preflight_response(CORS_HEADERS)

    user_id = user_id_from_event(event)

    image_url = (event.get('queryStringParameters') or {}).get('image_url', '')

    if not image_url:
        return _error(400, 'Missing required parameter: image_url')

    if validated_s3_key_from_image_url(BUCKET_NAME, image_url) is None:
        return _error(400, 'Invalid image URL: must be a valid S3 URL for this bucket')

    table = dynamodb.Table(TABLE_NAME)

    try:
        item = get_image_record(table, image_url)
    except ClientError as e:
        logger.error({'action': 'delete', 'error': str(e)})
        return _error(500, f'Database error: {e}')

    if item is None:
        return _error(404, 'Image not found in database')

    if not image_record_belongs_to_user(item, user_id):
        return _error(403, 'You do not have permission to delete this image')

    try:
        deleted_from = delete_image_record_assets(table, s3_client, BUCKET_NAME, image_url)
    except ClientError as e:
        logger.error({'action': 'delete', 'error': str(e)})
        return _error(500, f'Error deleting image: {e}')

    logger.info({'action': 'delete', 'image_url': image_url, 'deleted_from': deleted_from})

    return json_response(200, {'message': f'Successfully deleted image from {" and ".join(deleted_from)}'}, CORS_HEADERS)


def _error(status: int, message: str) -> dict:
    return error_response(status, message, CORS_HEADERS)
