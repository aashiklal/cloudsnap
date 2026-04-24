variable "project_name"     { type = string }
variable "environment"      { type = string }
variable "aws_region"       { type = string }
variable "alert_email"      { type = string }
variable "lambda_functions" { type = any }
variable "table_name"       { type = string }
variable "bucket_name"      { type = string }
