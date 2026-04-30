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
        query_library_user_image_records,
        search_ready_image_records,
    )
    from backend.tag_commands import TagCommandError, parse_search_tag_command, tags_satisfy_query
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
    from tag_commands import TagCommandError, parse_search_tag_command, tags_satisfy_query

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

    user_id = user_id_from_event(event)

    parameters = event.get('queryStringParameters') or {}
    try:
        tags_query = parse_search_tag_command(parameters)
    except TagCommandError as e:
        return _error(e.status_code, e.message)

    logger.info({'action': 'search_tags', 'query': tags_query, 'user_id': user_id})

    table = dynamodb.Table(TABLE_NAME)

    records = query_library_user_image_records(table, user_id)
    results = search_ready_image_records(
        records,
        lambda record: tags_satisfy_query(record.get('Tags', []), tags_query),
        s3,
        BUCKET_NAME,
    )

    if not results:
        return _error(404, 'No matching images found')

    logger.info({'action': 'search_tags', 'results_count': len(results)})

    return json_response(200, results, CORS_HEADERS)


def _error(status: int, message: str) -> dict:
    return error_response(status, message, CORS_HEADERS)
