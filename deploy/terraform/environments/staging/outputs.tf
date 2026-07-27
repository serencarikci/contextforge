output "cluster_name" {
  value = module.kubernetes.cluster_name
}

output "postgres_endpoint" {
  value = module.postgres.endpoint
}

output "redis_url" {
  value = module.redis.url
}

output "object_storage_endpoint" {
  value = module.object_storage.endpoint
}

output "api_fqdn" {
  value = module.dns.fqdn
}
