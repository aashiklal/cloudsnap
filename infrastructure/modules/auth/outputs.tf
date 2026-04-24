output "user_pool" {
  value = aws_cognito_user_pool.cloudsnap
}

output "user_pool_client_id" {
  value = aws_cognito_user_pool_client.web.id
}

output "identity_pool_id" {
  value = aws_cognito_identity_pool.cloudsnap.id
}
