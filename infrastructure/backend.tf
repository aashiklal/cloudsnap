# Remote state — create the S3 bucket and DynamoDB table manually once before running terraform init.
# See README.md for bootstrap instructions.
terraform {
  backend "s3" {
    bucket       = "cloudsnap-tfstate"
    key          = "cloudsnap/terraform.tfstate"
    region       = "ap-southeast-2"
    use_lockfile = true
    encrypt      = true
  }
}
