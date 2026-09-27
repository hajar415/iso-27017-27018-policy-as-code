# ❌ NON-CONFORME ISO 27018
# S3 bucket SANS chiffrement (sera bloqué par Checkov)

resource "aws_s3_bucket" "unencrypted_bucket" {
  bucket = "my-insecure-bucket-${data.aws_caller_identity.current.account_id}"
  # ❌ VIOLATION : Pas de chiffrement configuré
}

# ❌ VIOLATION : Accès public autorisé
resource "aws_s3_bucket_public_access_block" "unencrypted_bucket" {
  bucket = aws_s3_bucket.unencrypted_bucket.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# ❌ VIOLATION : Pas de versioning (pas de backup)
# (ce bloc est volontairement absent)

# ❌ VIOLATION : Pas de logging
# (ce bloc est volontairement absent)

# Récupère l'ID du compte
data "aws_caller_identity" "current" {}
