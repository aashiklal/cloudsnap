output "api_url" {
  value = aws_apigatewayv2_stage.prod.invoke_url
}

output "api_id" {
  value = aws_apigatewayv2_api.cloudsnap.id
}
