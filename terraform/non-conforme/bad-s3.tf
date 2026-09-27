# MAUVAIS : S3 bucket sans chiffrement
resource "aws_s3_bucket" "bad_bucket" {
  bucket = "my-insecure-bucket"
  # Pas de chiffrement = NON CONFORME à ISO 27018
}

# MAUVAIS : Security group qui accepte SSH de partout
resource "aws_security_group" "bad_sg" {
  name = "allow_all_ssh"
  
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}