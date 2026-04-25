from __future__ import annotations

import json
import os
import logging
from typing import Optional
from urllib.parse import urlparse
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BUCKET_NAME = os.environ['BUCKET_NAME']
TABLE_NAME = os.environ['TABLE_NAME']
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')

CORS_HEADERS = {
    'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'OPTIONS,DELETE',
}

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')


def lambda_handler(event, context):
    if event.get('httpMethod') == 'OPTIONS' or event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    claims = event.get('requestContext', {}).get('authorizer', {}).get('jwt', {}).get('claims', {})
    user_id = claims.get('sub', 'unknown')

    image_url = (event.get('queryStringParameters') or {}).get('image_url', '')

    if not image_url:
        return _error(400, 'Missing required parameter: image_url')

    image_key = _extract_s3_key(image_url)
    if image_key is None:
        return _error(400, 'Invalid image URL: must be a valid S3 URL for this bucket')

    table = dynamodb.Table(TABLE_NAME)
    s3_exists = False
    dynamodb_exists = False
    item = None

    try:
        s3_client.head_object(Bucket=BUCKET_NAME, Key=image_key)
        s3_exists = True
    except ClientError:
        pass

    try:
        response = table.get_item(Key={'ImageURL': image_url})
        if 'Item' in response:
            dynamodb_exists = True
            item = response['Item']
    except ClientError:
        pass

    if not s3_exists and not dynamodb_exists:
        return _error(404, 'Image not found in S3 or database')

    if item and item.get('UserID') != user_id:
        return _error(403, 'You do not have permission to delete this image')

    deleted_from = []
    try:
        if s3_exists:
            s3_client.delete_object(Bucket=BUCKET_NAME, Key=image_key)
            deleted_from.append('S3')
        if dynamodb_exists:
            table.delete_item(Key={'ImageURL': image_url})
            deleted_from.append('database')
    except ClientError as e:
        logger.error({'action': 'delete', 'error': str(e)})
        return _error(500, f'Error deleting image: {e}')

    logger.info({'action': 'delete', 'image_url': image_url, 'deleted_from': deleted_from})

    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({'message': f'Successfully deleted image from {" and ".join(deleted_from)}'}),
    }


def _extract_s3_key(url: str) -> Optional[str]:
    """Return the S3 object key if the URL belongs to our bucket, else None."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc
        # Strip query strings before extracting the key
        path = parsed.path.split('?')[0].lstrip('/')
        if host == f'{BUCKET_NAME}.s3.amazonaws.com' or host.startswith('s3.amazonaws.com'):
            if host.startswith('s3.amazonaws.com') and path.startswith(f'{BUCKET_NAME}/'):
                path = path[len(BUCKET_NAME) + 1:]
            if path:
                return path
    except Exception:
        pass
    return None


def _error(status: int, message: str) -> dict:
    return {
        'statusCode': status,
        'headers': CORS_HEADERS,
        'body': json.dumps({'error': message}),
    }
