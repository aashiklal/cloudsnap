import json
import os
import re
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
    'Access-Control-Allow-Methods': 'OPTIONS,GET',
}

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
TAG_PATTERN = re.compile(r'^tag[1-9][0-9]*$')
COUNT_PATTERN = re.compile(r'^tag[1-9][0-9]*count$')
NUMERIC_PATTERN = re.compile(r'^[0-9]+$')
TAG_VALUE_PATTERN = re.compile(r'^[a-zA-Z0-9 _-]{1,64}$')


def lambda_handler(event, context):
    if event.get('httpMethod') == 'OPTIONS' or event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    claims = event.get('requestContext', {}).get('authorizer', {}).get('jwt', {}).get('claims', {})
    user_id = claims.get('sub', 'unknown')

    parameters = event.get('queryStringParameters') or {}

    tags = {k: v for k, v in parameters.items() if TAG_PATTERN.match(k)}
    tagcounts = {k: v for k, v in parameters.items() if COUNT_PATTERN.match(k)}

    if not tags:
        return _error(400, 'At least one tag is required')

    indices = sorted(int(k[3:]) for k in tags)
    for i in indices:
        if f'tag{i}count' not in tagcounts:
            return _error(400, f'Missing tag{i}count for tag{i}')
        if f'tag{i}' not in tags:
            return _error(400, f'Missing tag{i} for tag{i}count')

    if len(tags) != len(tagcounts):
        return _error(400, 'Mismatched number of tags and counts')

    for tag, value in tags.items():
        if not TAG_VALUE_PATTERN.match(value):
            return _error(400, f'Invalid tag value for {tag}: must be alphanumeric (letters, numbers, spaces, hyphens, underscores, max 64 chars)')

    for tagcount, value in tagcounts.items():
        if not NUMERIC_PATTERN.match(value):
            return _error(400, f'Invalid count value for {tagcount}: must be numeric')

    tags_query = [
        {'tag': tags[f'tag{i}'].lower(), 'count': int(tagcounts[f'tag{i}count'])}
        for i in indices
    ]

    logger.info({'action': 'search_tags', 'query': tags_query, 'user_id': user_id})

    table = dynamodb.Table(TABLE_NAME)

    query_kwargs = {
        'IndexName': 'UserID-UploadedAt-index',
        'KeyConditionExpression': Key('UserID').eq(user_id),
    }

    matching_urls = []
    while True:
        response = table.query(**query_kwargs)
        for item in response.get('Items', []):
            item_tags = item.get('Tags', [])
            if all(
                any(t['tag'].lower() == q['tag'] and t['count'] >= q['count']
                    for t in item_tags)
                for q in tags_query
            ):
                matching_urls.append(item['ImageURL'])
        if 'LastEvaluatedKey' not in response:
            break
        query_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

    if not matching_urls:
        return _error(404, 'No matching images found')

    logger.info({'action': 'search_tags', 'results_count': len(matching_urls)})

    results = []
    prefix = f'https://{BUCKET_NAME}.s3.amazonaws.com/'
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
