
# INTENTIONAL SECURITY VIOLATION FOR PORTFOLIO DEMO
# Do not deploy this configuration.

resource "aws_security_group" "demo_public_ssh" {
  name        = "demo-public-ssh"
  description = "Intentional test: SSH open to the Internet"

  ingress {
    description = "Intentional violation for Checkov testing"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
