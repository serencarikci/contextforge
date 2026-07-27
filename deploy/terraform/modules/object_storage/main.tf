terraform {
  required_version = ">= 1.6.0"
}

variable "name_prefix" {
  type = string
}

variable "bucket_name" {
  type    = string
  default = "contextforge-documents"
}

output "endpoint" {
  value = "${var.name_prefix}-objects.internal:9000"
}

output "bucket_name" {
  value = var.bucket_name
}
