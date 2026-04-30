import os
import logging
import boto3

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
        decimal_to_json,
        query_library_user_image_records,
        with_presigned_url,
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
        decimal_to_json,
        query_library_user_image_records,
        with_presigned_url,
    )

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ['TABLE_NAME']
BUCKET_NAME = os.environ['BUCKET_NAME']
CORS_HEADERS = cors_headers('OPTIONS,GET')

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')


def lambda_handler(event, context):
    if is_preflight_request(event):
        return preflight_response(CORS_HEADERS)

    try:
        user_id = user_id_from_event(event)

        table = dynamodb.Table(TABLE_NAME)

        items = query_library_user_image_records(table, user_id, newest_first=True)

        enriched_items = []
        for item in items:
            try:
                enriched_items.append(with_presigned_url(item, s3, BUCKET_NAME))
            except Exception as e:
                logger.warning({'action': 'presign_failed', 'error': str(e), 'url': item.get('ImageURL')})
                item['PresignedURL'] = None
                enriched_items.append(item)

        logger.info({'action': 'list_images', 'count': len(enriched_items), 'user_id': user_id})

        return json_response(200, enriched_items, CORS_HEADERS, default=decimal_to_json)
    except Exception as e:
        logger.error({'action': 'list_images', 'error': str(e)})
        return error_response(500, 'Internal server error', CORS_HEADERS)
