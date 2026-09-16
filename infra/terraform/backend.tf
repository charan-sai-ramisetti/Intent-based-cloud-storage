terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket         = "tricloud-vault-64ede16a"
    key            = "dev/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "tricloud-vault-lock-table"
    encrypt        = true
  }
}