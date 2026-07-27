terraform {
  required_version = ">= 1.6.0"
}

variable "name_prefix" {
  type = string
}

variable "memory_mb" {
  type    = number
  default = 512
}

output "endpoint" {
  value = "${var.name_prefix}-redis.internal"
}

output "port" {
  value = 6379
}

output "url" {
  value = "redis://${var.name_prefix}-redis.internal:6379/0"
}
