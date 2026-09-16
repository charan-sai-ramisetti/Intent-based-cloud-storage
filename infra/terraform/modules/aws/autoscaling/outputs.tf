output "asg_name" {
  value = aws_autoscaling_group.backend.name
}

output "iam_instance_profile" {
  value = aws_iam_instance_profile.ssm_profile.name
}

output "launch_template_id" {
  value = aws_launch_template.backend.id
}
