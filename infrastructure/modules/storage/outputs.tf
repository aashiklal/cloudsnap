output "bucket_name" { value = aws_s3_bucket.images.bucket }
output "bucket_arn"  { value = aws_s3_bucket.images.arn }
output "table_name"  { value = aws_dynamodb_table.cloudsnap.name }
output "table_arn"   { value = aws_dynamodb_table.cloudsnap.arn }
