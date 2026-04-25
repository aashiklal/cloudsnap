variable "aws_region" {
  description = "AWS region to deploy resources into"
  type        = string
  default     = "ap-southeast-2"
}

variable "project_name" {
  description = "Project name — used as a prefix for all resource names"
  type        = string
  default     = "cloudsnap"
}

variable "environment" {
  description = "Deployment environment (prod, staging, dev)"
  type        = string
  default     = "prod"
}

variable "allowed_origin" {
  description = "CORS allowed origin — your CloudFront distribution or frontend URL (used for S3/Lambda)"
  type        = string
}

variable "allowed_origins" {
  description = "CORS allowed origins for API Gateway — include your CloudFront URL and http://localhost:3000 for local dev"
  type        = list(string)
}

variable "lambda_runtime" {
  description = "Python runtime version for all Lambda functions"
  type        = string
  default     = "python3.12"
}

variable "alert_email" {
  description = "Email address to receive CloudWatch alarm notifications"
  type        = string
}
