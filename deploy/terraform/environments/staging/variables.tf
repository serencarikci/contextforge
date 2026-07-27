variable "name_prefix" {
  type    = string
  default = "contextforge-staging"
}

variable "cluster_type" {
  type    = string
  default = "generic"
}

variable "dns_zone" {
  type    = string
  default = "staging.example.com"
}
