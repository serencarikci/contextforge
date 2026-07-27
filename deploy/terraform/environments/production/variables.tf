variable "name_prefix" {
  type    = string
  default = "contextforge-production"
}

variable "cluster_type" {
  type    = string
  default = "generic"
}

variable "dns_zone" {
  type    = string
  default = "production.example.com"
}
