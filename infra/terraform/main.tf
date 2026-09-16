module "aws_vpc" {
  source               = "./modules/aws/vpc"
  project_name         = var.project_name
  environment          = var.environment
  vpc_cidr             = var.vpc_cidr
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  availability_zones   = var.availability_zones
}

module "aws_sg" {
  source       = "./modules/aws/security-groups"
  project_name = var.project_name
  environment  = var.environment
  vpc_id       = module.aws_vpc.vpc_id
}

module "aws_alb" {
  source            = "./modules/aws/alb"
  project_name      = var.project_name
  environment       = var.environment
  subnet_ids        = module.aws_vpc.public_subnet_ids
  security_group_id = module.aws_sg.alb_sg
  vpc_id            = module.aws_vpc.vpc_id
  acm_certificate_arn =var.acm-arn
}

module "aws_rds" {

  source = "./modules/aws/rds"

  project_name = var.project_name
  environment  = var.environment

  private_subnets = module.aws_vpc.private_subnet_ids
  db_sg           = module.aws_sg.rds_sg

  db_name     = "tricloud_vault"
  db_user     = "tricloud_vault"
  db_password = var.db_password
}

module "aws_autoscaling" {
  source               = "./modules/aws/autoscaling"
  project_name         = var.project_name
  environment          = var.environment
  ami_id               = var.ami_id
  instance_type        = var.ec2_instance_type
  security_group_id    = module.aws_sg.backend_sg
  private_subnets      = module.aws_vpc.private_subnet_ids
  app_target_group_arn = module.aws_alb.app_target_group_arn
}

module "aws_s3" {
  source       = "./modules/aws/s3-storage"
  project_name = var.project_name
  environment  = var.environment
}

module "azure_blob" {
  source       = "./modules/azure/blob-storage"
  project_name = var.project_name
  environment  = var.environment
  location     = var.azure_location
}

module "gcp_bucket" {
  source         = "./modules/gcp/storage-bucket"
  project_name   = var.project_name
  environment    = var.environment
  gcp_project_id = var.gcp_project_id
}