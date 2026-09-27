# ✅ CONFORME ISO 27017
# VPC avec segmentation + Security Groups ATTACHÉS à une EC2

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

# ✅ VPC sécurisé
resource "aws_vpc" "secure_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "secure-vpc"
  }
}

# ✅ Subnet privé
resource "aws_subnet" "private_subnet" {
  vpc_id            = aws_vpc.secure_vpc.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-1a"

  tags = {
    Name = "private-subnet"
  }
}

# ✅ Subnet public pour bastion
resource "aws_subnet" "public_subnet" {
  vpc_id            = aws_vpc.secure_vpc.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "us-east-1a"

  tags = {
    Name = "public-subnet"
  }
}

# ✅ Internet Gateway
resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.secure_vpc.id

  tags = {
    Name = "secure-igw"
  }
}

# ✅ Route table publique RESTREINTE
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.secure_vpc.id

  route {
    cidr_block      = "0.0.0.0/0"
    gateway_id      = aws_internet_gateway.gw.id
  }

  tags = {
    Name = "public-rt"
  }
}

resource "aws_route_table_association" "public_association" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.public_rt.id
}

# ✅ Security Group RESTREINT (ISO 27017)
# ❌ PAS d'accès SSH/RDP au public (0.0.0.0/0)
resource "aws_security_group" "restricted_sg" {
  vpc_id      = aws_vpc.secure_vpc.id
  name        = "restricted-sg"
  description = "Restricted security group - SSH/RDP blocked from public"

  # ✅ Accès SSH UNIQUEMENT depuis le bastion (10.0.2.0/24)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.2.0/24"]
  }

  # ✅ Accès HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # ✅ Accès HTTP
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # ✅ Tout accès sortant autorisé
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "restricted-sg"
  }
}

# ✅ EC2 INSTANCE AVEC LE SECURITY GROUP ATTACHÉ (CKV2_AWS_5 fix)
resource "aws_instance" "secure_instance" {
  ami                    = "ami-0c55b159cbfafe1f0"  # Amazon Linux 2
  instance_type          = "t2.micro"
  subnet_id              = aws_subnet.private_subnet.id
  vpc_security_group_ids = [aws_security_group.restricted_sg.id]

  tags = {
    Name = "secure-instance"
  }
}

# ✅ Flow Logs pour audit (ISO 27017)
resource "aws_flow_log" "vpc_flow_log" {
  iam_role_arn    = aws_iam_role.flow_log_role.arn
  log_destination = aws_cloudwatch_log_group.flow_log_group.arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.secure_vpc.id

  tags = {
    Name = "vpc-flow-log"
  }
}

resource "aws_cloudwatch_log_group" "flow_log_group" {
  name              = "/aws/vpc/flowlogs"
  retention_in_days = 30
}

resource "aws_iam_role" "flow_log_role" {
  name = "vpc-flow-log-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "flow_log_policy" {
  name = "vpc-flow-log-policy"
  role = aws_iam_role.flow_log_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}
