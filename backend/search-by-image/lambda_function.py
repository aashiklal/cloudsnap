import json
import os
import base64
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
        query_library_user_image_records,
        search_ready_image_records,
    )
    from backend.tag_commands import has_any_tag
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
        query_library_user_image_records,
        search_ready_image_records,
    )
    from tag_commands import has_any_tag

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ['TABLE_NAME']
BUCKET_NAME = os.environ['BUCKET_NAME']
CORS_HEADERS = cors_headers('OPTIONS,POST')

dynamodb = boto3.resource('dynamodb')
rekognition = boto3.client('rekognition')
s3 = boto3.client('s3')

MAX_IMAGE_BYTES = 4 * 1024 * 1024  # Rekognition Image.Bytes limit is 5 MB; Lambda payload cap makes 4 MB the safe ceiling


def lambda_handler(event, context):
    if is_preflight_request(event):
        return preflight_response(CORS_HEADERS)

    user_id = user_id_from_event(event)

    try:
        raw_body = event.get('body', '')
        if event.get('isBase64Encoded'):
            image_bytes = base64.b64decode(raw_body)
        else:
            body = json.loads(raw_body or '{}')
            image_b64 = body.get('imageFile') or body.get('image', '')
            if not image_b64:
                return _error(400, 'Missing image data')
            image_bytes = base64.b64decode(image_b64)

        if len(image_bytes) > MAX_IMAGE_BYTES:
            return _error(400, 'Image exceeds 10 MB limit')

        logger.info({'action': 'search_by_image_start', 'size_bytes': len(image_bytes), 'user_id': user_id})

        rekog_response = rekognition.detect_labels(
            Image={'Bytes': image_bytes},
            MaxLabels=20,
            MinConfidence=70,
        )
    except rekognition.exceptions.InvalidImageException:
        return _error(400, 'Invalid or unsupported image format')
    except Exception as e:
        logger.error({'action': 'rekognition_error', 'error': str(e)})
        return _error(500, 'Image analysis failed')

    query_tags = {label['Name'].lower() for label in rekog_response['Labels']}

    if not query_tags:
        return _error(404, 'No objects detected in query image')

    logger.info({'action': 'search_by_image_tags', 'tags': list(query_tags)})

    table = dynamodb.Table(TABLE_NAME)
    records = query_library_user_image_records(table, user_id)
    results = search_ready_image_records(
        records,
        lambda record: has_any_tag(record.get('Tags', []), query_tags),
        s3,
        BUCKET_NAME,
    )

    logger.info({'action': 'search_by_image_done', 'results': len(results)})

    if not results:
        return _error(404, 'No matching images found')

    return json_response(200, results, CORS_HEADERS)


def _error(status: int, message: str) -> dict:
    return error_response(status, message, CORS_HEADERS)
