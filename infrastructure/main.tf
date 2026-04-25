terraform {
  required_version = ">= 1.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

module "storage" {
  source         = "./modules/storage"
  project_name   = var.project_name
  environment    = var.environment
  allowed_origin = var.allowed_origin
}

module "auth" {
  source       = "./modules/auth"
  project_name = var.project_name
  environment  = var.environment
}

module "compute" {
  source           = "./modules/compute"
  project_name     = var.project_name
  environment      = var.environment
  aws_region       = var.aws_region
  bucket_name      = module.storage.bucket_name
  bucket_arn       = module.storage.bucket_arn
  table_name       = module.storage.table_name
  table_arn        = module.storage.table_arn
  allowed_origin   = var.allowed_origin
  lambda_runtime   = var.lambda_runtime
}

module "api" {
  source            = "./modules/api"
  project_name      = var.project_name
  environment       = var.environment
  aws_region        = var.aws_region
  allowed_origins   = var.allowed_origins
  cognito_user_pool            = module.auth.user_pool
  cognito_user_pool_client_id  = module.auth.user_pool_client_id
  lambda_functions             = module.compute.lambda_functions
}

module "observability" {
  source           = "./modules/observability"
  project_name     = var.project_name
  environment      = var.environment
  aws_region       = var.aws_region
  alert_email      = var.alert_email
  lambda_functions = module.compute.lambda_functions
  table_name       = module.storage.table_name
  bucket_name      = module.storage.bucket_name
}
