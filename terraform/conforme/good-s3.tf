# ✅ CONFORME ISO 27018
# S3 bucket avec chiffrement KMS obligatoire

resource "aws_s3_bucket" "encrypted_bucket" {
  bucket = "my-encrypted-bucket-${data.aws_caller_identity.current.account_id}"
}

# Bloc l'accès public
resource "aws_s3_bucket_public_access_block" "encrypted_bucket" {
  bucket = aws_s3_bucket.encrypted_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Chiffrement KMS OBLIGATOIRE (ISO 27018)
resource "aws_s3_bucket_server_side_encryption_configuration" "encrypted_bucket" {
  bucket = aws_s3_bucket.encrypted_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3_key.arn
    }
    bucket_key_enabled = true
  }
}

# Versioning pour backup (ISO 27017)
resource "aws_s3_bucket_versioning" "encrypted_bucket" {
  bucket = aws_s3_bucket.encrypted_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Logging pour audit (ISO 27018)
resource "aws_s3_bucket_logging" "encrypted_bucket" {
  bucket = aws_s3_bucket.encrypted_bucket.id

  target_bucket = aws_s3_bucket.log_bucket.id
  target_prefix = "logs/"
}

# Bucket pour les logs
resource "aws_s3_bucket" "log_bucket" {
  bucket = "my-log-bucket-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_public_access_block" "log_bucket" {
  bucket = aws_s3_bucket.log_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Clé KMS pour chiffrement
resource "aws_kms_key" "s3_key" {
  description             = "KMS key for S3 encryption (ISO 27018)"
  deletion_window_in_days = 10
  enable_key_rotation     = true
}

resource "aws_kms_alias" "s3_key" {
  name          = "alias/s3-encryption-key"
  target_key_id = aws_kms_key.s3_key.key_id
}

# Récupère l'ID du compte
data "aws_caller_identity" "current" {}
