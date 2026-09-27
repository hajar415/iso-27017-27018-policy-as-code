# MAUVAIS : RDS sans backups
resource "aws_db_instance" "bad_db" {
  allocated_storage    = 20
  engine               = "mysql"
  instance_class       = "db.t2.micro"
  identifier           = "bad-database"
  backup_retention_period = 0
  region               = "us-east-1"
}