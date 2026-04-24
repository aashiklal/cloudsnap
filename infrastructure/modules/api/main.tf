resource "aws_apigatewayv2_api" "cloudsnap" {
  name          = "${var.project_name}-api-${var.environment}"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = [var.allowed_origin]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
    max_age       = 300
  }
}

# Cognito JWT authorizer — enforces authentication at the API Gateway level
resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.cloudsnap.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "cognito-jwt"

  jwt_configuration {
    audience = [var.cognito_user_pool_client_id]
    issuer   = "https://cognito-idp.${var.aws_region}.amazonaws.com/${var.cognito_user_pool.id}"
  }
}

locals {
  routes = {
    "POST /upload"          = "upload"
    "GET /search"           = "search-tags"
    "POST /modify-tags"     = "modify-tags"
    "DELETE /delete"        = "delete"
    "POST /search-by-image" = "search-by-image"
    "GET /images"           = "list-images"
  }
}

# Lambda integrations
resource "aws_apigatewayv2_integration" "lambda" {
  for_each = local.routes

  api_id                 = aws_apigatewayv2_api.cloudsnap.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.lambda_functions[each.value].invoke_arn
  payload_format_version = "2.0"
}

# Routes — all protected by Cognito JWT authorizer
resource "aws_apigatewayv2_route" "lambda" {
  for_each = local.routes

  api_id             = aws_apigatewayv2_api.cloudsnap.id
  route_key          = each.key
  target             = "integrations/${aws_apigatewayv2_integration.lambda[each.key].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_cloudwatch_log_group" "api_access" {
  name              = "/aws/apigateway/${var.project_name}-${var.environment}"
  retention_in_days = 30
}

resource "aws_apigatewayv2_stage" "prod" {
  api_id      = aws_apigatewayv2_api.cloudsnap.id
  name        = var.environment
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_access.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      responseLength = "$context.responseLength"
      durationMs     = "$context.responseLatency"
      userAgent      = "$context.identity.userAgent"
    })
  }

  default_route_settings {
    throttling_burst_limit = 500
    throttling_rate_limit  = 200
  }
}

# Allow API Gateway to invoke each Lambda
resource "aws_lambda_permission" "api_gateway" {
  for_each = local.routes

  statement_id  = "AllowAPIGatewayInvoke-${replace(replace(each.key, " ", "-"), "/", "")}"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_functions[each.value].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.cloudsnap.execution_arn}/*/*"
}
