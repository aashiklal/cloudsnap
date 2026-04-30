from __future__ import annotations

import json
import os
from typing import Any, Callable

DEFAULT_ALLOWED_HEADERS = 'Content-Type,Authorization'


def cors_headers(allowed_methods: str, allowed_origin: str | None = None) -> dict[str, str]:
    return {
        'Access-Control-Allow-Origin': allowed_origin or os.environ.get('ALLOWED_ORIGIN', '*'),
        'Access-Control-Allow-Headers': DEFAULT_ALLOWED_HEADERS,
        'Access-Control-Allow-Methods': allowed_methods,
    }


def is_preflight_request(event: dict) -> bool:
    return (
        event.get('httpMethod') == 'OPTIONS'
        or event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS'
    )


def preflight_response(headers: dict[str, str]) -> dict[str, Any]:
    return {'statusCode': 200, 'headers': headers, 'body': ''}


def json_response(
    status_code: int,
    body: Any,
    headers: dict[str, str],
    default: Callable[[Any], Any] | None = None,
) -> dict[str, Any]:
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body, default=default),
    }


def error_response(status_code: int, message: str, headers: dict[str, str]) -> dict[str, Any]:
    return json_response(status_code, {'error': message}, headers)


def user_id_from_event(event: dict, default: str = 'unknown') -> str:
    claims = event.get('requestContext', {}).get('authorizer', {}).get('jwt', {}).get('claims', {})
    return claims.get('sub', default)
