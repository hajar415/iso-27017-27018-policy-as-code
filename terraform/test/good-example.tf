# Example of FULLY COMPLIANT code - should PASS all checks

resource "aws_security_group" "compliant" {
  name        = "compliant-sg"
  description = "Compliant security group"

  # SSH ONLY from internal network (not public)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
    description = "SSH from internal"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "compliant"
  }
}