locals {
  functions = {
    upload = {
      handler        = "lambda_function.lambda_handler"
      source_path    = "${path.root}/../backend/upload"
      shared_sources = ["http_api.py", "image_records.py"]
      extra_policy_statements = [
        {
          effect    = "Allow"
          actions   = ["s3:PutObject"]
          resources = ["${var.bucket_arn}/*"]
        },
        {
          effect    = "Allow"
          actions   = ["dynamodb:PutItem"]
          resources = [var.table_arn]
        }
      ]
    }
    search-tags = {
      handler        = "lambda_function.lambda_handler"
      source_path    = "${path.root}/../backend/search-tags"
      shared_sources = ["http_api.py", "image_records.py", "tag_commands.py"]
      extra_policy_statements = [
        {
          effect    = "Allow"
          actions   = ["dynamodb:Query"]
          resources = ["${var.table_arn}/index/UserID-UploadedAt-index"]
        },
        {
          effect    = "Allow"
          actions   = ["s3:GetObject"]
          resources = ["${var.bucket_arn}/*"]
        }
      ]
    }
    modify-tags = {
      handler        = "lambda_function.lambda_handler"
      source_path    = "${path.root}/../backend/modify-tags"
      shared_sources = ["http_api.py", "image_records.py", "tag_commands.py"]
      extra_policy_statements = [
        {
          effect    = "Allow"
          actions   = ["dynamodb:GetItem", "dynamodb:PutItem"]
          resources = [var.table_arn]
        }
      ]
    }
    delete = {
      handler        = "lambda_function.lambda_handler"
      source_path    = "${path.root}/../backend/delete"
      shared_sources = ["http_api.py", "image_records.py"]
      extra_policy_statements = [
        {
          effect    = "Allow"
          actions   = ["s3:DeleteObject", "s3:HeadObject"]
          resources = ["${var.bucket_arn}/*"]
        },
        {
          effect    = "Allow"
          actions   = ["dynamodb:GetItem", "dynamodb:DeleteItem"]
          resources = [var.table_arn]
        }
      ]
    }
    object-detection = {
      handler        = "lambda_function.lambda_handler"
      source_path    = "${path.root}/../backend/object-detection"
      shared_sources = ["image_records.py"]
      extra_policy_statements = [
        {
          effect    = "Allow"
          actions   = ["s3:GetObject"]
          resources = ["${var.bucket_arn}/*"]
        },
        {
          effect    = "Allow"
          actions   = ["dynamodb:UpdateItem"]
          resources = [var.table_arn]
        },
        {
          effect    = "Allow"
          actions   = ["rekognition:DetectLabels"]
          resources = ["*"]
        }
      ]
    }
    search-by-image = {
      handler        = "lambda_function.lambda_handler"
      source_path    = "${path.root}/../backend/search-by-image"
      shared_sources = ["http_api.py", "image_records.py", "tag_commands.py"]
      extra_policy_statements = [
        {
          effect    = "Allow"
          actions   = ["s3:GetObject"]
          resources = ["${var.bucket_arn}/*"]
        },
        {
          effect    = "Allow"
          actions   = ["dynamodb:Query"]
          resources = ["${var.table_arn}/index/UserID-UploadedAt-index"]
        },
        {
          effect    = "Allow"
          actions   = ["rekognition:DetectLabels"]
          resources = ["*"]
        }
      ]
    }
    list-images = {
      handler        = "lambda_function.lambda_handler"
      source_path    = "${path.root}/../backend/list-images"
      shared_sources = ["http_api.py", "image_records.py"]
      extra_policy_statements = [
        {
          effect    = "Allow"
          actions   = ["dynamodb:Query"]
          resources = ["${var.table_arn}/index/UserID-UploadedAt-index"]
        },
        {
          effect    = "Allow"
          actions   = ["s3:GetObject"]
          resources = ["${var.bucket_arn}/*"]
        }
      ]
    }
  }

  common_env_vars = {
    BUCKET_NAME    = var.bucket_name
    TABLE_NAME     = var.table_name
    ALLOWED_ORIGIN = var.allowed_origin
  }
}

# Dead-letter queue for the async object-detection Lambda
resource "aws_sqs_queue" "object_detection_dlq" {
  name                      = "${var.project_name}-object-detection-dlq-${var.environment}"
  message_retention_seconds = 1209600 # 14 days
}

# IAM role and policy per Lambda
resource "aws_iam_role" "lambda" {
  for_each = local.functions
  name     = "${var.project_name}-lambda-${each.key}-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  for_each   = local.functions
  role       = aws_iam_role.lambda[each.key].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_xray" {
  for_each   = local.functions
  role       = aws_iam_role.lambda[each.key].name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

resource "aws_iam_role_policy" "lambda_custom" {
  for_each = local.functions
  name     = "${var.project_name}-lambda-${each.key}-policy"
  role     = aws_iam_role.lambda[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      for stmt in each.value.extra_policy_statements : {
        Effect   = stmt.effect
        Action   = stmt.actions
        Resource = stmt.resources
      }
    ]
  })
}

# CloudWatch log groups with retention
resource "aws_cloudwatch_log_group" "lambda" {
  for_each          = local.functions
  name              = "/aws/lambda/${var.project_name}-${each.key}-${var.environment}"
  retention_in_days = 30
}

# Lambda functions
data "archive_file" "lambda" {
  for_each    = local.functions
  type        = "zip"
  output_path = "${path.module}/builds/${each.key}.zip"

  dynamic "source" {
    for_each = fileset(each.value.source_path, "*")
    content {
      content  = file("${each.value.source_path}/${source.value}")
      filename = source.value
    }
  }

  dynamic "source" {
    for_each = each.value.shared_sources
    content {
      content  = file("${path.root}/../backend/${source.value}")
      filename = source.value
    }
  }
}

# Upload all packages to S3 — avoids the 70MB direct-upload limit for large Lambdas
resource "aws_s3_object" "lambda_package" {
  for_each = local.functions

  bucket = var.bucket_name
  key    = "lambda-packages/${each.key}.zip"
  source = data.archive_file.lambda[each.key].output_path
  etag   = filemd5(data.archive_file.lambda[each.key].output_path)
}

resource "aws_lambda_function" "cloudsnap" {
  for_each = local.functions

  function_name = "${var.project_name}-${each.key}-${var.environment}"
  role          = aws_iam_role.lambda[each.key].arn
  handler       = each.value.handler
  runtime       = var.lambda_runtime
  timeout       = each.key == "object-detection" || each.key == "search-by-image" ? 120 : 30
  memory_size   = each.key == "object-detection" || each.key == "search-by-image" ? 1024 : 256

  s3_bucket        = var.bucket_name
  s3_key           = aws_s3_object.lambda_package[each.key].key
  source_code_hash = data.archive_file.lambda[each.key].output_base64sha256

  environment {
    variables = local.common_env_vars
  }

  publish = contains(["object-detection", "search-by-image"], each.key)

  tracing_config {
    mode = "Active"
  }

  dynamic "dead_letter_config" {
    for_each = each.key == "object-detection" ? [1] : []
    content {
      target_arn = aws_sqs_queue.object_detection_dlq.arn
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda]
}

# Allow object-detection Lambda to send failed events to its DLQ
resource "aws_iam_role_policy" "object_detection_dlq" {
  name = "${var.project_name}-lambda-object-detection-dlq-policy"
  role = aws_iam_role.lambda["object-detection"].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "sqs:SendMessage"
      Resource = aws_sqs_queue.object_detection_dlq.arn
    }]
  })
}

# S3 trigger for object-detection Lambda
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cloudsnap["object-detection"].function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.bucket_arn
}

# S3 event notification — fires object-detection on every image upload
resource "aws_s3_bucket_notification" "object_detection" {
  bucket = var.bucket_name

  lambda_function {
    lambda_function_arn = aws_lambda_function.cloudsnap["object-detection"].arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".jpg"
  }

  lambda_function {
    lambda_function_arn = aws_lambda_function.cloudsnap["object-detection"].arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".jpeg"
  }

  lambda_function {
    lambda_function_arn = aws_lambda_function.cloudsnap["object-detection"].arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".png"
  }

  lambda_function {
    lambda_function_arn = aws_lambda_function.cloudsnap["object-detection"].arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".gif"
  }

  lambda_function {
    lambda_function_arn = aws_lambda_function.cloudsnap["object-detection"].arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".webp"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}
