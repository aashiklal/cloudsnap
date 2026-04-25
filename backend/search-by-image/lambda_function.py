import json
import os
import base64
import logging
import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ['TABLE_NAME']
BUCKET_NAME = os.environ['BUCKET_NAME']
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')
PRESIGN_EXPIRY = 3600

CORS_HEADERS = {
    'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'OPTIONS,POST',
}

dynamodb = boto3.resource('dynamodb')
rekognition = boto3.client('rekognition')

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # match upload limit


def lambda_handler(event, context):
    if (event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS'):
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    claims = event.get('requestContext', {}).get('authorizer', {}).get('jwt', {}).get('claims', {})
    user_id = claims.get('sub', 'unknown')

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
    matching_urls = []

    query_kwargs = {
        'IndexName': 'UserID-UploadedAt-index',
        'KeyConditionExpression': Key('UserID').eq(user_id),
    }
    while True:
        response = table.query(**query_kwargs)
        for item in response.get('Items', []):
            item_tag_names = {t['tag'].lower() for t in item.get('Tags', [])}
            if query_tags & item_tag_names:
                matching_urls.append(item['ImageURL'])
        if 'LastEvaluatedKey' not in response:
            break
        query_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

    logger.info({'action': 'search_by_image_done', 'results': len(matching_urls)})

    if not matching_urls:
        return _error(404, 'No matching images found')

    prefix = f'https://{BUCKET_NAME}.s3.amazonaws.com/'
    results = []
    for image_url in matching_urls:
        key = image_url[len(prefix):] if image_url.startswith(prefix) else image_url
        presigned = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': key},
            ExpiresIn=PRESIGN_EXPIRY,
        )
        results.append({'imageUrl': image_url, 'presignedUrl': presigned})

    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps(results),
    }


def _error(status: int, message: str) -> dict:
    return {
        'statusCode': status,
        'headers': CORS_HEADERS,
        'body': json.dumps({'error': message}),
    }
