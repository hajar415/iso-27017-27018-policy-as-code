# BON : S3 bucket avec chiffrement KMS
resource "aws_s3_bucket" "good_bucket" {
  bucket = "my-secure-bucket"
}

# Chiffrement côté serveur avec KMS
resource "aws_s3_bucket_server_side_encryption_configuration" "good_bucket_encryption" {
  bucket = aws_s3_bucket.good_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3_key.arn
    }
  }
}

# BON : Security group qui ferme SSH
resource "aws_security_group" "good_sg" {
  name = "restricted_ssh"
  
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Clé KMS pour chiffrer S3
resource "aws_kms_key" "s3_key" {
  description = "KMS key for S3 encryption"
}"# Test workflow trigger" 
