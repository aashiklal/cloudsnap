import json
import os
import logging
import urllib.parse
import boto3

try:
    from backend.image_records import (
        image_url_for_s3_object,
        mark_image_record_failed,
        mark_image_record_ready,
        tags_from_rekognition_labels,
    )
except ModuleNotFoundError:
    from image_records import (
        image_url_for_s3_object,
        mark_image_record_failed,
        mark_image_record_ready,
        tags_from_rekognition_labels,
    )

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
    image_url = image_url_for_s3_object(bucket, key)

    logger.info({'action': 'object_detection_start', 'bucket': bucket, 'key': key})

    try:
        response = rekognition.detect_labels(
            Image={'S3Object': {'Bucket': bucket, 'Name': key}},
            MaxLabels=20,
            MinConfidence=70,
        )
    except Exception as e:
        logger.error({'action': 'rekognition_error', 'error': str(e), 'key': key})
        _mark_failed(image_url, key, str(e))
        raise

    tags = tags_from_rekognition_labels(response['Labels'])

    table = dynamodb.Table(TABLE_NAME)
    try:
        mark_image_record_ready(table, image_url, key, tags)
    except Exception as e:
        logger.error({'action': 'dynamodb_error', 'error': str(e), 'key': key})
        raise

    logger.info({'action': 'object_detection_done', 'key': key, 'tag_count': len(tags)})

    return {'statusCode': 200, 'body': 'Object detection completed'}


def _mark_failed(image_url: str, key: str, error: str) -> None:
    table = dynamodb.Table(TABLE_NAME)
    try:
        mark_image_record_failed(table, image_url, key, error)
    except Exception as ddb_error:
        logger.error({'action': 'dynamodb_mark_failed_error', 'error': str(ddb_error), 'key': key})
