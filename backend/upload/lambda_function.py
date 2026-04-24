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
        content_type = (event.get('headers') or {}).get('content-type', '')

        if 'multipart/form-data' in content_type:
            image_bytes, filename = _parse_multipart(event, content_type)
        else:
            # Fallback: JSON body with base64-encoded image
            data = json.loads(event['body'])
            image_b64 = data.get('image')
            filename = data.get('filename')
            if not image_b64 or not filename:
                return _error(400, 'Missing required fields: image and filename')
            image_bytes = base64.b64decode(image_b64)

        if not filename:
            return _error(400, 'Missing filename')

        if len(image_bytes) > MAX_SIZE_BYTES:
            return _error(400, f'File too large. Maximum size is {MAX_SIZE_BYTES // (1024 * 1024)} MB')

        mime_type = _detect_mime_type(image_bytes)
        if mime_type not in ALLOWED_MIME_TYPES:
            return _error(400, f'Invalid file type. Allowed types: {", ".join(ALLOWED_MIME_TYPES)}')

        s3 = boto3.client('s3')
        s3.put_object(
            Body=image_bytes,
            Bucket=BUCKET_NAME,
            Key=filename,
            ContentType=mime_type,
        )

        logger.info({'action': 'upload', 'filename': filename, 'size_bytes': len(image_bytes)})

        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'message': 'Image uploaded successfully',
                'url': f'https://{BUCKET_NAME}.s3.amazonaws.com/{filename}',
            }),
        }

    except (NoCredentialsError, PartialCredentialsError):
        logger.error('AWS credentials error')
        return _error(500, 'AWS configuration error')
    except Exception as e:
        logger.error({'action': 'upload', 'error': str(e)})
        return _error(500, 'Internal server error')


def _parse_multipart(event: dict, content_type: str) -> tuple[bytes, str]:
    """Parse a multipart/form-data body sent by API Gateway (always base64-encoded)."""
    boundary = None
    for part in content_type.split(';'):
        part = part.strip()
        if part.startswith('boundary='):
            boundary = part[len('boundary='):].strip('"')
            break
    if not boundary:
        raise ValueError('Missing multipart boundary')

    raw = event.get('body', '')
    body_bytes = base64.b64decode(raw) if event.get('isBase64Encoded') else raw.encode()

    sep = f'--{boundary}'.encode()
    end = f'--{boundary}--'.encode()
    image_bytes = b''
    filename = ''

    for chunk in body_bytes.split(sep):
        if not chunk or chunk == b'--\r\n' or chunk.startswith(end):
            continue
        chunk = chunk.lstrip(b'\r\n')
        if b'\r\n\r\n' not in chunk:
            continue
        headers_raw, _, data = chunk.partition(b'\r\n\r\n')
        data = data.rstrip(b'\r\n')
        headers_text = headers_raw.decode('utf-8', errors='replace')

        if 'name="file"' in headers_text or 'name="image"' in headers_text:
            image_bytes = data
            for header_line in headers_text.splitlines():
                if 'filename=' in header_line:
                    fname_part = header_line.split('filename=')[-1].strip().strip('"')
                    filename = fname_part
        elif 'name="filename"' in headers_text:
            filename = data.decode('utf-8', errors='replace').strip()

    return image_bytes, filename


def _detect_mime_type(data: bytes) -> str:
    if data[:3] == b'\xff\xd8\xff':
        return 'image/jpeg'
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'image/png'
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return 'image/gif'
    if data[:4] == b'RIFF' or data[8:12] == b'WEBP':
        return 'image/webp'
    return 'application/octet-stream'


def _error(status: int, message: str) -> dict:
    return {
        'statusCode': status,
        'headers': CORS_HEADERS,
        'body': json.dumps({'error': message}),
    }
