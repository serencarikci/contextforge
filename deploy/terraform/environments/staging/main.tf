module "networking" {
  source      = "../../modules/networking"
  name_prefix = var.name_prefix
}

module "kubernetes" {
  source       = "../../modules/kubernetes"
  name_prefix  = var.name_prefix
  cluster_type = var.cluster_type
}

module "postgres" {
  source      = "../../modules/postgres"
  name_prefix = var.name_prefix
}

module "redis" {
  source      = "../../modules/redis"
  name_prefix = var.name_prefix
}

module "object_storage" {
  source      = "../../modules/object_storage"
  name_prefix = var.name_prefix
}

module "dns" {
  source      = "../../modules/dns"
  zone_name   = var.dns_zone
  record_name = "api"
  target      = module.kubernetes.cluster_name
}

resource "null_resource" "composition_marker" {
  triggers = {
    network = module.networking.network_id
    cluster = module.kubernetes.cluster_name
    env     = "staging"
  }
}
