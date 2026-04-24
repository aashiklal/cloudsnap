locals {
  function_names = [for k, v in var.lambda_functions : v.function_name]
}

resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-alerts-${var.environment}"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# CloudWatch alarm — error rate > 5% per Lambda over 5 minutes
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = var.lambda_functions

  alarm_name          = "${each.value.function_name}-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 5
  alarm_description   = "Lambda ${each.value.function_name} error rate exceeded 5%"
  treat_missing_data  = "notBreaching"

  metric_query {
    id          = "error_rate"
    expression  = "errors / invocations * 100"
    label       = "Error Rate (%)"
    return_data = true
  }

  metric_query {
    id = "errors"
    metric {
      metric_name = "Errors"
      namespace   = "AWS/Lambda"
      period      = 300
      stat        = "Sum"
      dimensions = {
        FunctionName = each.value.function_name
      }
    }
  }

  metric_query {
    id = "invocations"
    metric {
      metric_name = "Invocations"
      namespace   = "AWS/Lambda"
      period      = 300
      stat        = "Sum"
      dimensions = {
        FunctionName = each.value.function_name
      }
    }
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

# X-Ray sampling rule for CloudSnap traces
resource "aws_xray_sampling_rule" "cloudsnap" {
  rule_name      = "${var.project_name}-${var.environment}"
  priority       = 1000
  reservoir_size = 5
  fixed_rate     = 0.10
  url_path       = "*"
  host           = "*"
  http_method    = "*"
  service_type   = "*"
  service_name   = "${var.project_name}-*"
  resource_arn   = "*"
  version        = 1
}

# CloudWatch dashboard
locals {
  # Build metrics lists without flatten — flatten() destroys inner arrays in Terraform
  invocation_metrics = [
    for fn in var.lambda_functions :
    ["AWS/Lambda", "Invocations", "FunctionName", fn.function_name]
  ]
  error_metrics = [
    for fn in var.lambda_functions :
    ["AWS/Lambda", "Errors", "FunctionName", fn.function_name]
  ]
  duration_metrics = [
    for fn in var.lambda_functions :
    ["AWS/Lambda", "Duration", "FunctionName", fn.function_name]
  ]
}

resource "aws_cloudwatch_dashboard" "cloudsnap" {
  dashboard_name = "${var.project_name}-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        width  = 24
        height = 6
        properties = {
          title   = "Lambda Invocations"
          region  = var.aws_region
          period  = 300
          stat    = "Sum"
          view    = "timeSeries"
          metrics = local.invocation_metrics
        }
      },
      {
        type   = "metric"
        width  = 24
        height = 6
        properties = {
          title   = "Lambda Errors"
          region  = var.aws_region
          period  = 300
          stat    = "Sum"
          view    = "timeSeries"
          metrics = local.error_metrics
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          title   = "Lambda Duration (P95)"
          region  = var.aws_region
          period  = 300
          stat    = "p95"
          view    = "timeSeries"
          metrics = local.duration_metrics
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          title  = "DynamoDB Consumed Capacity"
          region = var.aws_region
          period = 300
          stat   = "Sum"
          view   = "timeSeries"
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", var.table_name],
            ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", var.table_name],
          ]
        }
      }
    ]
  })
}
