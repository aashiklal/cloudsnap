import json
import os
import logging
from decimal import Decimal
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


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj)
        return super().default(obj)


def lambda_handler(event, context):
    if (event.get('httpMethod') == 'OPTIONS'
            or event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS'):
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    try:
        table = dynamodb.Table(TABLE_NAME)
        response = table.scan(ProjectionExpression='ImageURL, Tags')
        items = response.get('Items', [])

        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ProjectionExpression='ImageURL, Tags',
                ExclusiveStartKey=response['LastEvaluatedKey'],
            )
            items.extend(response.get('Items', []))

        logger.info({'action': 'list_images', 'count': len(items)})

        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps(items, cls=DecimalEncoder),
        }
    except Exception as e:
        logger.error({'action': 'list_images', 'error': str(e)})
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Internal server error'}),
        }
