output "aws_vpc_id" {
  value = module.aws_vpc.vpc_id
}

output "aws_s3_bucket" {
  value = module.aws_s3.bucket_name
}

output "azure_storage_account" {
  value = module.azure_blob.storage_account_name
}

output "storage_account_key" {
  value     = module.azure_blob.storage_account_key
  sensitive = true
}

output "container_name" {
  value = module.azure_blob.container_name
}

output "gcp_bucket" {
  value = module.gcp_bucket.bucket_name
}

output "alb_dns_name" {
  value = module.aws_alb.alb_dns_name
}

output "rds_endpoint" {
  value = module.aws_rds.rds_endpoint
}

output "instance_id" {
  value = module.aws_autoscaling.iam_instance_profile
}