terraform {
  required_version = ">= 1.6.0"
}

variable "name_prefix" {
  type = string
}

variable "cluster_type" {
  type        = string
  description = "kind | generic"
  default     = "generic"
}

variable "node_count" {
  type    = number
  default = 3
}

output "cluster_name" {
  value = "${var.name_prefix}-k8s"
}

output "cluster_type" {
  value = var.cluster_type
}

output "kubeconfig_path" {
  description = "Placeholder path; wire to provider-specific output in real environments"
  value       = "/tmp/${var.name_prefix}-kubeconfig"
}
