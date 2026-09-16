variable "project_name" {}
variable "environment" {}

variable "ami_id" {}
variable "instance_type" {}

variable "security_group_id" {}
variable "private_subnets" {}

variable "app_target_group_arn" {
  description = "ARN of the application target group (Caddy :8080)"
}