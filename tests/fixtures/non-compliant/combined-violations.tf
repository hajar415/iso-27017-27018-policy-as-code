# This VIOLATES ISO 27017: SSH is publicly accessible

resource "aws_security_group" "public_ssh" {
  name = "public-ssh-bad"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# This VIOLATES ISO 27018: S3 without KMS encryption

resource "aws_s3_bucket" "unencrypted" {
  bucket = "unencrypted-bucket"
}