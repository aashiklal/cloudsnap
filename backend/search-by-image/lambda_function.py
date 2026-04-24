import json
import os
import base64
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ['TABLE_NAME']
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')

CORS_HEADERS = {
    'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'OPTIONS,POST',
}

dynamodb = boto3.resource('dynamodb')
rekognition = boto3.client('rekognition')

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # Rekognition limit for inline image bytes


def lambda_handler(event, context):
    if (event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS'):
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

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
            return _error(400, 'Image exceeds 5 MB limit for inline detection')

        logger.info({'action': 'search_by_image_start', 'size_bytes': len(image_bytes)})

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

    # Scan DynamoDB and match images that share at least one detected tag
    table = dynamodb.Table(TABLE_NAME)
    matching_urls = []

    scan_kwargs = {'ProjectionExpression': 'ImageURL, Tags'}
    while True:
        response = table.scan(**scan_kwargs)
        for item in response.get('Items', []):
            item_tag_names = {t['tag'].lower() for t in item.get('Tags', [])}
            if query_tags & item_tag_names:
                matching_urls.append(item['ImageURL'])
        if 'LastEvaluatedKey' not in response:
            break
        scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

    logger.info({'action': 'search_by_image_done', 'results': len(matching_urls)})

    if not matching_urls:
        return _error(404, 'No matching images found')

    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps(matching_urls),
    }


def _error(status: int, message: str) -> dict:
    return {
        'statusCode': status,
        'headers': CORS_HEADERS,
        'body': json.dumps({'error': message}),
    }
