import json
import os
import re
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ['TABLE_NAME']
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')

CORS_HEADERS = {
    'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'OPTIONS,GET',
}

dynamodb = boto3.resource('dynamodb')
TAG_PATTERN = re.compile(r'^tag[1-9][0-9]*$')
COUNT_PATTERN = re.compile(r'^tag[1-9][0-9]*count$')
NUMERIC_PATTERN = re.compile(r'^[0-9]+$')
ALPHA_PATTERN = re.compile(r'^[a-zA-Z]+$')


def lambda_handler(event, context):
    if event.get('httpMethod') == 'OPTIONS' or event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    parameters = event.get('queryStringParameters') or {}

    tags = {k: v for k, v in parameters.items() if TAG_PATTERN.match(k)}
    tagcounts = {k: v for k, v in parameters.items() if COUNT_PATTERN.match(k)}

    if len(tags) != len(tagcounts):
        return _error(400, 'Mismatched number of tags and counts')

    if not tags:
        return _error(400, 'At least one tag is required')

    for tag, value in tags.items():
        if not ALPHA_PATTERN.match(value):
            return _error(400, f'Invalid tag value for {tag}: must be alphabetic')

    for tagcount, value in tagcounts.items():
        if not NUMERIC_PATTERN.match(value):
            return _error(400, f'Invalid count value for {tagcount}: must be numeric')

    tags_query = [
        {'tag': tags[f'tag{i}'], 'count': int(tagcounts[f'tag{i}count'])}
        for i in range(1, len(tags) + 1)
    ]

    logger.info({'action': 'search_tags', 'query': tags_query})

    table = dynamodb.Table(TABLE_NAME)
    # Full table scan — acceptable at this scale; a GSI or OpenSearch would be used in production
    response = table.scan()
    matching_urls = []

    for item in response['Items']:
        item_tags = item.get('Tags', [])
        match = all(
            any(t['tag'] == q['tag'] and t['count'] >= q['count'] for t in item_tags)
            for q in tags_query
        )
        if match:
            matching_urls.append(item['ImageURL'])

    if not matching_urls:
        return _error(404, 'No matching images found')

    logger.info({'action': 'search_tags', 'results_count': len(matching_urls)})

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
