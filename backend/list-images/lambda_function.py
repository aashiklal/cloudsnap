import json
import os
import logging
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ['TABLE_NAME']
BUCKET_NAME = os.environ['BUCKET_NAME']
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')
PRESIGN_EXPIRY = 3600  # 1 hour

CORS_HEADERS = {
    'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'OPTIONS,GET',
}

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')


def _presign(image_url: str) -> str:
    prefix = f'https://{BUCKET_NAME}.s3.amazonaws.com/'
    key = image_url[len(prefix):] if image_url.startswith(prefix) else image_url
    return s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': key},
        ExpiresIn=PRESIGN_EXPIRY,
    )


def _decimal(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError(f'Object of type {type(obj)} is not JSON serializable')


def lambda_handler(event, context):
    if (event.get('httpMethod') == 'OPTIONS'
            or event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS'):
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    try:
        claims = event.get('requestContext', {}).get('authorizer', {}).get('jwt', {}).get('claims', {})
        user_id = claims.get('sub', 'unknown')

        table = dynamodb.Table(TABLE_NAME)

        query_kwargs = {
            'IndexName': 'UserID-UploadedAt-index',
            'KeyConditionExpression': Key('UserID').eq(user_id),
            'ScanIndexForward': False,  # newest first
        }

        items = []
        while True:
            response = table.query(**query_kwargs)
            items.extend(response.get('Items', []))
            if 'LastEvaluatedKey' not in response:
                break
            query_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

        for item in items:
            try:
                item['PresignedURL'] = _presign(item['ImageURL'])
            except Exception as e:
                logger.warning({'action': 'presign_failed', 'error': str(e), 'url': item.get('ImageURL')})
                item['PresignedURL'] = None

        logger.info({'action': 'list_images', 'count': len(items), 'user_id': user_id})

        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps(items, default=_decimal),
        }
    except Exception as e:
        logger.error({'action': 'list_images', 'error': str(e)})
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Internal server error'}),
        }
