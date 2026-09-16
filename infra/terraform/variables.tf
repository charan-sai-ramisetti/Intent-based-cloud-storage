variable "project_name" {}
variable "environment" {}

variable "aws_region" {}
variable "vpc_cidr" {}
variable "public_subnet_cidrs" { type = list(string) }
variable "private_subnet_cidrs" { type = list(string) }
variable "availability_zones" { type = list(string) }

variable "ami_id" {}
variable "ec2_instance_type" {}
variable "db_password" {
  type      = string
  sensitive = true
}


variable "azure_location" {}

variable "gcp_project_id" {}
variable "gcp_region" {}
variable "acm-arn" {}
