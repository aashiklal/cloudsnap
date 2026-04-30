import json
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
    from backend.image_records import get_image_record, image_record_belongs_to_user
    from backend.tag_commands import TagCommandError, apply_tag_mutation, parse_modify_tag_command
except ModuleNotFoundError:
    from http_api import (
        cors_headers,
        error_response,
        is_preflight_request,
        json_response,
        preflight_response,
        user_id_from_event,
    )
    from image_records import get_image_record, image_record_belongs_to_user
    from tag_commands import TagCommandError, apply_tag_mutation, parse_modify_tag_command

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ['TABLE_NAME']

CORS_HEADERS = cors_headers('OPTIONS,POST')

dynamodb = boto3.resource('dynamodb')


def lambda_handler(event, context):
    if is_preflight_request(event):
        return preflight_response(CORS_HEADERS)

    try:
        user_id = user_id_from_event(event)

        body = json.loads(event.get('body') or '{}')
        image_url = body.get('url')
        action_type_raw = body.get('type')

        if not image_url or action_type_raw is None:
            return _error(400, 'Missing required fields: url and type')

        try:
            action_type, tag_commands = parse_modify_tag_command(body)
        except TagCommandError as e:
            return _error(e.status_code, e.message)

        table = dynamodb.Table(TABLE_NAME)

        try:
            item = get_image_record(table, image_url)
        except Exception as e:
            logger.error({'action': 'modify_tags', 'error': str(e)})
            return _error(500, 'Error fetching image record')

        if item is None:
            return _error(404, 'Image not found')

        if not image_record_belongs_to_user(item, user_id):
            return _error(403, 'You do not have permission to modify this image')

        item['Tags'] = apply_tag_mutation(item.get('Tags', []), action_type, tag_commands)

        try:
            table.put_item(Item=item)
        except Exception as e:
            logger.error({'action': 'modify_tags', 'error': str(e)})
            return _error(500, 'Error updating image tags')

        logger.info({'action': 'modify_tags', 'image_url': image_url, 'type': action_type})

        return json_response(200, {'message': 'Tags updated successfully'}, CORS_HEADERS)

    except Exception as e:
        logger.error({'action': 'modify_tags', 'error': str(e)})
        return _error(500, 'Internal server error')


def _error(status: int, message: str) -> dict:
    return error_response(status, message, CORS_HEADERS)
