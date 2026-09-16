output "alb_sg" {
  value = aws_security_group.alb.id
}

output "backend_sg" {
  value = aws_security_group.backend.id
}

output "rds_sg" {
  value = aws_security_group.rds.id
}