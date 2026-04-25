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
    'Access-Control-Allow-Methods': 'OPTIONS,POST',
}

dynamodb = boto3.resource('dynamodb')
TAG_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9 _-]{1,64}$')


def lambda_handler(event, context):
    if event.get('httpMethod') == 'OPTIONS' or event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    try:
        claims = event.get('requestContext', {}).get('authorizer', {}).get('jwt', {}).get('claims', {})
        user_id = claims.get('sub', 'unknown')

        body = json.loads(event.get('body') or '{}')
        image_url = body.get('url')
        action_type_raw = body.get('type')

        if not image_url or action_type_raw is None:
            return _error(400, 'Missing required fields: url and type')

        if str(action_type_raw) not in ('0', '1'):
            return _error(400, 'Invalid type: must be 0 (remove) or 1 (add)')

        action_type = int(action_type_raw)

        table = dynamodb.Table(TABLE_NAME)

        try:
            response = table.get_item(Key={'ImageURL': image_url})
        except Exception as e:
            logger.error({'action': 'modify_tags', 'error': str(e)})
            return _error(500, 'Error fetching image record')

        if 'Item' not in response:
            return _error(404, 'Image not found')

        item = response['Item']

        if item.get('UserID') != user_id:
            return _error(403, 'You do not have permission to modify this image')

        # Dynamically detect which tag indices are present in the request body
        indices = sorted({
            int(re.search(r'\d+', k).group())
            for k in body if re.match(r'^tag\d+$', k)
        })

        indices_to_remove = []

        for i in indices:
            tag_key = f'tag{i}'
            count_key = f'tag{i}count'

            if count_key not in body:
                return _error(400, f'Missing {count_key} for {tag_key}')

            tag_name = str(body[tag_key]).strip()
            if not TAG_NAME_PATTERN.match(tag_name):
                return _error(400, f'Invalid tag name "{tag_name}": use letters, numbers, spaces, hyphens, underscores (max 64 chars)')

            try:
                count = int(body[count_key])
            except (ValueError, TypeError):
                return _error(400, f'{count_key} must be an integer')
            if count < 1:
                return _error(400, f'{count_key} must be at least 1')

            for idx, tag in enumerate(item['Tags']):
                if tag['tag'].lower() == tag_name.lower():
                    if action_type == 1:
                        tag['count'] += count
                    else:
                        tag['count'] = max(0, tag['count'] - count)
                        if tag['count'] == 0:
                            indices_to_remove.append(idx)
                    break
            else:
                if action_type == 1:
                    item['Tags'].append({'tag': tag_name, 'count': count})

        for idx in sorted(indices_to_remove, reverse=True):
            item['Tags'].pop(idx)

        try:
            table.put_item(Item=item)
        except Exception as e:
            logger.error({'action': 'modify_tags', 'error': str(e)})
            return _error(500, 'Error updating image tags')

        logger.info({'action': 'modify_tags', 'image_url': image_url, 'type': action_type})

        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'Tags updated successfully'}),
        }

    except Exception as e:
        logger.error({'action': 'modify_tags', 'error': str(e)})
        return _error(500, 'Internal server error')


def _error(status: int, message: str) -> dict:
    return {
        'statusCode': status,
        'headers': CORS_HEADERS,
        'body': json.dumps({'error': message}),
    }
