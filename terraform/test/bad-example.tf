# Example of NON-COMPLIANT code - should FAIL checks

resource "aws_security_group" "non_compliant" {
  name = "non-compliant-sg"

  # SSH OPEN TO PUBLIC - VIOLATION!
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # PUBLIC ACCESS - BAD!
  }
}