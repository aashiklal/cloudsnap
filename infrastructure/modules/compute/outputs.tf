output "lambda_functions" {
  value = {
    for k, fn in aws_lambda_function.cloudsnap : k => {
      arn           = fn.arn
      function_name = fn.function_name
      invoke_arn    = fn.invoke_arn
    }
  }
}
