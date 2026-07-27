terraform {
  required_version = ">= 1.6.0"
}

variable "zone_name" {
  type        = string
  description = "DNS zone stub (provider wiring left to the adopter)"
}

variable "record_name" {
  type = string
}

variable "target" {
  type = string
}

output "fqdn" {
  value = "${var.record_name}.${var.zone_name}"
}
