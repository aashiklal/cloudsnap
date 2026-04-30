import json
import os
import re
import uuid
import base64
import logging
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
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
    from backend.image_records import image_url_for_s3_object, put_processing_image_record
except ModuleNotFoundError:
    from http_api import (
        cors_headers,
        error_response,
        is_preflight_request,
        json_response,
        preflight_response,
        user_id_from_event,
    )
    from image_records import image_url_for_s3_object, put_processing_image_record

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BUCKET_NAME = os.environ['BUCKET_NAME']
TABLE_NAME = os.environ['TABLE_NAME']
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png'}

CORS_HEADERS = cors_headers('OPTIONS,POST')


def lambda_handler(event, context):
    if is_preflight_request(event):
        return preflight_response(CORS_HEADERS)

    try:
        user_id = user_id_from_event(event)

        content_type = (event.get('headers') or {}).get('content-type', '')

        if 'multipart/form-data' in content_type:
            image_bytes, filename = _parse_multipart(event, content_type)
        else:
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

        safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', os.path.basename(filename))
        s3_key = f"{user_id}/{uuid.uuid4().hex}_{safe_name}"

        s3 = boto3.client('s3')
        s3.put_object(
            Body=image_bytes,
            Bucket=BUCKET_NAME,
            Key=s3_key,
            ContentType=mime_type,
        )

        image_url = image_url_for_s3_object(BUCKET_NAME, s3_key)

        table = boto3.resource('dynamodb').Table(TABLE_NAME)
        put_processing_image_record(table, image_url, user_id)

        logger.info({'action': 'upload', 'key': s3_key, 'size_bytes': len(image_bytes), 'user_id': user_id})

        return json_response(
            200,
            {
                'message': 'Image uploaded successfully; analysis is processing',
                'url': image_url,
                'processingStatus': 'processing',
            },
            CORS_HEADERS,
        )

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
    return 'application/octet-stream'


def _error(status: int, message: str) -> dict:
    return error_response(status, message, CORS_HEADERS)
