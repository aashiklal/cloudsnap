locals {
  bucket_name = "${var.project_name}-img-${var.environment}"
  table_name  = "${var.project_name}-results-table"
}

# S3 bucket for image storage
resource "aws_s3_bucket" "images" {
  bucket = local.bucket_name
}

resource "aws_s3_bucket_public_access_block" "images" {
  bucket = aws_s3_bucket.images.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "images" {
  bucket = aws_s3_bucket.images.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_cors_configuration" "images" {
  bucket = aws_s3_bucket.images.id

  cors_rule {
    allowed_headers = ["Content-Type", "Authorization"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE"]
    allowed_origins = [var.allowed_origin]
    max_age_seconds = 3000
  }
}

resource "aws_s3_bucket_versioning" "images" {
  bucket = aws_s3_bucket.images.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "images" {
  bucket = aws_s3_bucket.images.id

  rule {
    id     = "transition-and-expire"
    status = "Enabled"

    filter {}

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 365
      storage_class = "GLACIER"
    }

    # Expire old non-current versions after 90 days to control storage costs
    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# Unified DynamoDB table — single source of truth for all Lambda functions
resource "aws_dynamodb_table" "cloudsnap" {
  name         = local.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "ImageURL"

  attribute {
    name = "ImageURL"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }
}
