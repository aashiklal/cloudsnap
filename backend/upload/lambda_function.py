import json
import os
import base64
import logging
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BUCKET_NAME = os.environ['BUCKET_NAME']
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}

CORS_HEADERS = {
    'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'OPTIONS,POST',
}


def lambda_handler(event, context):
    if event.get('httpMethod') == 'OPTIONS' or event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    try:
        data = json.loads(event['body'])
        image_b64 = data.get('image')
        filename = data.get('filename')

        if not image_b64 or not filename:
            return _error(400, 'Missing required fields: image and filename')

        decoded_image = base64.b64decode(image_b64)

        if len(decoded_image) > MAX_SIZE_BYTES:
            return _error(400, f'File too large. Maximum size is {MAX_SIZE_BYTES // (1024*1024)}MB')

        # Detect MIME type from magic bytes
        mime_type = _detect_mime_type(decoded_image)
        if mime_type not in ALLOWED_MIME_TYPES:
            return _error(400, f'Invalid file type. Allowed types: {", ".join(ALLOWED_MIME_TYPES)}')

        s3 = boto3.client('s3')
        s3.put_object(
            Body=decoded_image,
            Bucket=BUCKET_NAME,
            Key=filename,
            ContentType=mime_type,
        )

        logger.info({'action': 'upload', 'filename': filename, 'size_bytes': len(decoded_image)})

        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': f'Image uploaded successfully', 'url': f'https://{BUCKET_NAME}.s3.amazonaws.com/{filename}'}),
        }

    except (NoCredentialsError, PartialCredentialsError):
        logger.error('AWS credentials error')
        return _error(500, 'AWS configuration error')
    except Exception as e:
        logger.error({'action': 'upload', 'error': str(e)})
        return _error(500, 'Internal server error')


def _detect_mime_type(data: bytes) -> str:
    if data[:3] == b'\xff\xd8\xff':
        return 'image/jpeg'
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'image/png'
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return 'image/gif'
    if data[:4] in (b'RIFF', b'WEBP') or data[8:12] == b'WEBP':
        return 'image/webp'
    return 'application/octet-stream'


def _error(status: int, message: str) -> dict:
    return {
        'statusCode': status,
        'headers': CORS_HEADERS,
        'body': json.dumps({'error': message}),
    }
