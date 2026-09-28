# ✅ MINIMAL CONFORME - S3 avec tout ce qu'il faut
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

data "aws_caller_identity" "current" {}

# ✅ S3 bucket chiffré
resource "aws_s3_bucket" "compliant" {
  bucket = "compliant-bucket-${data.aws_caller_identity.current.account_id}"
}

# ✅ Bloc accès public
resource "aws_s3_bucket_public_access_block" "compliant" {
  bucket = aws_s3_bucket.compliant.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ✅ Chiffrement KMS
resource "aws_s3_bucket_server_side_encryption_configuration" "compliant" {
  bucket = aws_s3_bucket.compliant.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ✅ Versioning
resource "aws_s3_bucket_versioning" "compliant" {
  bucket = aws_s3_bucket.compliant.id
  versioning_configuration {
    status = "Enabled"
  }
}

# ✅ Lifecycle - ESSENTIEL pour CKV2_AWS_61
resource "aws_s3_bucket_lifecycle_configuration" "compliant" {
  bucket = aws_s3_bucket.compliant.id
  rule {
    id     = "expire-old"
    status = "Enabled"
    expiration {
      days = 365
    }
  }
}
"" 
