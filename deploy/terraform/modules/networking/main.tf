terraform {
  required_version = ">= 1.6.0"
}

variable "name_prefix" {
  type        = string
  description = "Prefix for networking resources"
}

variable "cidr_block" {
  type        = string
  description = "Primary CIDR (provider-specific wiring is intentionally stubbed)"
  default     = "10.20.0.0/16"
}

output "network_id" {
  description = "Stub network identifier for composition"
  value       = "${var.name_prefix}-network"
}

output "cidr_block" {
  value = var.cidr_block
}
