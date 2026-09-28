# ✅ MINIMAL CONFORME - VPC avec SG attaché à EC2
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# ✅ VPC
resource "aws_vpc" "compliant" {
  cidr_block = "10.0.0.0/16"
}

# ✅ Subnet
resource "aws_subnet" "compliant" {
  vpc_id            = aws_vpc.compliant.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-1a"
}

# ✅ Security Group SANS SSH/RDP ouvert au public
resource "aws_security_group" "compliant" {
  vpc_id = aws_vpc.compliant.id
  name   = "compliant-sg"
  
  # ✅ HTTPS UNIQUEMENT
  ingress {
    from_port   = 443
    to_port     = 443
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

# ✅ EC2 AVEC LE SG ATTACHÉ (CKV2_AWS_5 fix)
resource "aws_instance" "compliant" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t2.micro"
  subnet_id              = aws_subnet.compliant.id
  vpc_security_group_ids = [aws_security_group.compliant.id]
}
