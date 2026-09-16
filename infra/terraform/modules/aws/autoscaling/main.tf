resource "aws_launch_template" "backend" {
  name_prefix   = "${var.project_name}-${var.environment}-lt"
  image_id      = var.ami_id
  instance_type = var.instance_type

  vpc_security_group_ids = [var.security_group_id]

  iam_instance_profile {
    name = aws_iam_instance_profile.ssm_profile.name
  }

  metadata_options {
    http_tokens = "required"
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash

    sudo snap install amazon-ssm-agent --classic
    sudo systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service
    sudo systemctl start snap.amazon-ssm-agent.amazon-ssm-agent.service
  EOF
  )

  tag_specifications {
    resource_type = "instance"

    tags = {
      Name        = "${var.project_name}-${var.environment}-backend"
      Environment = var.environment
      Project     = var.project_name
    }
  }
}

resource "aws_autoscaling_group" "backend" {
  name               = "${var.project_name}-${var.environment}-asg"
  min_size           = 1
  max_size           = 3
  desired_capacity   = 1
  vpc_zone_identifier = var.private_subnets

  launch_template {
    id      = aws_launch_template.backend.id
    version = "$Latest"
  }

  target_group_arns = [
    var.app_target_group_arn
  ]

  health_check_type         = "EC2"
  health_check_grace_period = 3600

  tag {
    key                 = "Name"
    value               = "${var.project_name}-${var.environment}-backend"
    propagate_at_launch = true
  }

  tag {
    key                 = "Environment"
    value               = var.environment
    propagate_at_launch = true
  }

  tag {
    key                 = "Project"
    value               = var.project_name
    propagate_at_launch = true
  }
}

resource "aws_autoscaling_policy" "cpu_target_tracking" {
  name                   = "${var.project_name}-${var.environment}-cpu-scaling"
  autoscaling_group_name = aws_autoscaling_group.backend.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }

    target_value = 70.0
  }
}