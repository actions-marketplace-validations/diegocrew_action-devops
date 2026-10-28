terraform {
  required_version = ">= 1.0"
}

output "message" {
  description = "Provider-free fixture for cross-platform validation."
  value       = "hello"
}
