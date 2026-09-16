resource "aws_db_subnet_group" "db_subnet_group" {
  name = "${var.project_name}-${var.environment}-db-subnet-group"

  subnet_ids = var.private_subnets

  tags = {
    Name = "TriCloud DB Subnet Group"
  }
}

resource "aws_db_instance" "postgres" {

  identifier = "${var.project_name}-${var.environment}-db"

  engine = "postgres"
  engine_version = "15"

  instance_class = "db.t3.micro"

  allocated_storage = 20

  db_name  = var.db_name
  username = var.db_user
  password = var.db_password

  db_subnet_group_name = aws_db_subnet_group.db_subnet_group.name

  vpc_security_group_ids = [var.db_sg]

  publicly_accessible = false

  skip_final_snapshot = true
}