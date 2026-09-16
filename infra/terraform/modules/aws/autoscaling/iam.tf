data "aws_caller_identity" "current" {}

output "current_aws_account_id" {
  value = data.aws_caller_identity.current.account_id
  description = "The AWS Account ID that Terraform is using"
}

output "current_aws_user_arn" {
  value = data.aws_caller_identity.current.arn
  description = "The ARN of the AWS user/role that Terraform is using"
}

# ==========================================
# S3 bucket for Ansible SSM connection plugin file transfer
# ==========================================
resource "aws_s3_bucket" "ansible_ssm" {
  bucket = "tricloud-ansible-ssm-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_lifecycle_configuration" "ansible_ssm_cleanup" {
  bucket = aws_s3_bucket.ansible_ssm.id

  rule {
    id     = "expire-old-objects"
    status = "Enabled"

    expiration {
      days = 1
    }
  }
}

resource "aws_s3_bucket_public_access_block" "ansible_ssm" {
  bucket = aws_s3_bucket.ansible_ssm.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ==========================================
# IAM role for EC2 instance (SSM + S3 access for Ansible)
# ==========================================
resource "aws_iam_role" "ec2_ssm_role" {
  name = "tricloud-ec2-ssm-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ec2_ssm_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# S3 access for Ansible SSM connection plugin (file transfer)
resource "aws_iam_role_policy" "ansible_ssm_s3" {
  name = "ansible-ssm-s3"
  role = aws_iam_role.ec2_ssm_role.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ]
      Resource = [
        aws_s3_bucket.ansible_ssm.arn,
        "${aws_s3_bucket.ansible_ssm.arn}/*"
      ]
    }]
  })
}

# Secrets Manager access for application secrets
resource "aws_iam_role_policy" "secrets_manager_access" {
  name = "ansible-secretsmanager-access"
  role = aws_iam_role.ec2_ssm_role.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ]
      Resource = "arn:aws:secretsmanager:ap-south-1:*:secret:tricloud/production/*"
    }]
  })
}

resource "aws_iam_instance_profile" "ssm_profile" {
  name = "tricloud-ssm-profile"
  role = aws_iam_role.ec2_ssm_role.name
}
