import json
import os
import logging
import urllib.parse
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ['TABLE_NAME']
BUCKET_NAME = os.environ['BUCKET_NAME']

dynamodb = boto3.resource('dynamodb')
rekognition = boto3.client('rekognition')


def lambda_handler(event, context):
    record = event['Records'][0]
    bucket = record['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(record['s3']['object']['key'])

    logger.info({'action': 'object_detection_start', 'bucket': bucket, 'key': key})

    try:
        response = rekognition.detect_labels(
            Image={'S3Object': {'Bucket': bucket, 'Name': key}},
            MaxLabels=20,
            MinConfidence=70,
        )
    except Exception as e:
        logger.error({'action': 'rekognition_error', 'error': str(e), 'key': key})
        raise

    tags = [
        {'tag': label['Name'].lower(), 'count': 1}
        for label in response['Labels']
    ]

    image_url = f'https://{bucket}.s3.amazonaws.com/{key}'

    table = dynamodb.Table(TABLE_NAME)
    table.put_item(Item={'ImageURL': image_url, 'Tags': tags})

    logger.info({'action': 'object_detection_done', 'key': key, 'tag_count': len(tags)})

    return {'statusCode': 200, 'body': 'Object detection completed'}
