output "api_gateway_url" {
  description = "Base URL for the API Gateway — set this as NEXT_PUBLIC_API_URL in the frontend"
  value       = module.api.api_url
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID — set as NEXT_PUBLIC_USER_POOL_ID in the frontend"
  value       = module.auth.user_pool.id
}

output "cognito_user_pool_client_id" {
  description = "Cognito App Client ID — set as NEXT_PUBLIC_USER_POOL_CLIENT_ID in the frontend"
  value       = module.auth.user_pool_client_id
}

output "image_bucket_name" {
  description = "S3 bucket name for image storage"
  value       = module.storage.bucket_name
}

output "dynamodb_table_name" {
  description = "DynamoDB table name"
  value       = module.storage.table_name
}
