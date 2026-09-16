provider "aws" {
  region = "ap-south-1"
}

# -------------------------------
# Security Group
# -------------------------------
resource "aws_security_group" "benchmark_sg" {
  name        = "benchmark-sg"
  description = "Security group for benchmark EC2"

  ingress {
    description = "SSH access (open to all - NOT recommended for production)"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# -------------------------------
# EC2 Instance
# -------------------------------
resource "aws_instance" "benchmark_ec2" {
  ami           = "ami-0f5ee92e2d63afc18"   # Ubuntu 22.04 (ap-south-1)
  instance_type = "t3.micro"

  key_name = "lockpad-key"

  vpc_security_group_ids = [aws_security_group.benchmark_sg.id]

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }

  user_data = <<-EOF
              #!/bin/bash
              apt update -y
              apt install -y python3-pip
              pip3 install requests
              EOF

  tags = {
    Name = "benchmark-ec2"
  }
}

# -------------------------------
# Output Public IP
# -------------------------------
output "ec2_public_ip" {
  value = aws_instance.benchmark_ec2.public_ip
}