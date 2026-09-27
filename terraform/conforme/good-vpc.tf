# Compliant VPC with proper security groups
resource "aws_vpc" "secure_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "secure-vpc"
    ISO  = "27017-compliant"
  }
}

# Properly restricted security group
resource "aws_security_group" "restricted_sg" {
  name        = "restricted-sg"
  description = "Restricted security group - ISO 27017 compliant"
  vpc_id      = aws_vpc.secure_vpc.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
    description = "SSH from internal network only"
  }

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS outbound"
  }

  tags = {
    Name = "restricted-sg"
  }
}