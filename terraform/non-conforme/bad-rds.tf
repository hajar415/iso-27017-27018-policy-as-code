# ❌ NON-CONFORME ISO 27017/27018
# RDS database SANS sécurité - sera bloqué par Checkov

resource "aws_db_instance" "unencrypted_db" {
  allocated_storage    = 20
  db_name              = "mydb"
  engine               = "mysql"
  engine_version       = "8.0"
  instance_class       = "db.t2.micro"
  username             = "admin"
  password             = "password123"  # ❌ VIOLATION : Password en clair !
  parameter_group_name = "default.mysql8.0"
  skip_final_snapshot  = true

  # ❌ VIOLATION : Pas de chiffrement
  storage_encrypted = false

  # ❌ VIOLATION : Publicly accessible
  publicly_accessible = true

  # ❌ VIOLATION : Pas de backup automatique
  backup_retention_period = 0

  # ❌ VIOLATION : Pas de groupe de sécurité
  # (vpc_security_group_ids absent)
}

# ❌ VIOLATION : RDS subnet group SANS isolation
resource "aws_db_subnet_group" "default" {
  name       = "main"
  subnet_ids = ["subnet-12345678", "subnet-87654321"]
}
