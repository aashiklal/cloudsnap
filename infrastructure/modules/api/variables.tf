variable "project_name"      { type = string }
variable "environment"       { type = string }
variable "aws_region"        { type = string }
variable "allowed_origins"   { type = list(string) }
variable "cognito_user_pool"           { type = any }
variable "cognito_user_pool_client_id" { type = string }
variable "lambda_functions"            { type = any }
