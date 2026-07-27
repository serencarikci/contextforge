terraform {
  required_version = ">= 1.6.0"
}

variable "name_prefix" {
  type = string
}

variable "instance_class" {
  type    = string
  default = "db.shared"
}

variable "storage_gb" {
  type    = number
  default = 50
}

variable "database_name" {
  type    = string
  default = "contextforge"
}

output "endpoint" {
  value = "${var.name_prefix}-postgres.internal"
}

output "port" {
  value = 5432
}

output "database_name" {
  value = var.database_name
}
