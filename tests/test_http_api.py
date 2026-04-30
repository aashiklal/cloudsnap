import json
from decimal import Decimal

from backend.http_api import (
    cors_headers,
    error_response,
    is_preflight_request,
    json_response,
    preflight_response,
    user_id_from_event,
)


def test_cors_headers_use_allowed_origin_from_environment(monkeypatch):
    monkeypatch.setenv('ALLOWED_ORIGIN', 'https://app.example.com')

    assert cors_headers('OPTIONS,GET') == {
        'Access-Control-Allow-Origin': 'https://app.example.com',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'OPTIONS,GET',
    }


def test_preflight_detection_supports_api_gateway_v1_and_v2_events():
    assert is_preflight_request({'httpMethod': 'OPTIONS'})
    assert is_preflight_request({'requestContext': {'http': {'method': 'OPTIONS'}}})
    assert not is_preflight_request({'httpMethod': 'GET'})


def test_preflight_response_has_empty_body():
    headers = cors_headers('OPTIONS,POST', allowed_origin='*')

    assert preflight_response(headers) == {'statusCode': 200, 'headers': headers, 'body': ''}


def test_json_and_error_responses_include_headers_and_serialized_body():
    headers = cors_headers('OPTIONS,GET', allowed_origin='*')
    response = json_response(200, {'count': Decimal('2')}, headers, default=int)
    error = error_response(400, 'Bad request', headers)

    assert response['statusCode'] == 200
    assert response['headers'] == headers
    assert json.loads(response['body']) == {'count': 2}
    assert error['statusCode'] == 400
    assert json.loads(error['body']) == {'error': 'Bad request'}


def test_user_id_from_event_reads_jwt_sub_or_default():
    assert user_id_from_event({
        'requestContext': {'authorizer': {'jwt': {'claims': {'sub': 'user-123'}}}},
    }) == 'user-123'
    assert user_id_from_event({}) == 'unknown'
