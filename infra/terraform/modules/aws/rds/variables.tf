variable "project_name" {}
variable "environment" {}

variable "private_subnets" {
  type = list(string)
}

variable "db_sg" {}

variable "db_name" {}
variable "db_user" {}
variable "db_password" {}