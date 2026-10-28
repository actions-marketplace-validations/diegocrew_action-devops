# Intentionally incomplete security configuration; scanned, never deployed.
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

resource "aws_s3_bucket" "fixture" {
  bucket = "action-devops-checkov-fixture"
}
