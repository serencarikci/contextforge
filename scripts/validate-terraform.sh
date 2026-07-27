#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v terraform >/dev/null 2>&1; then
  echo "terraform not installed — skipping fmt/validate"
  exit 0
fi

echo "Running terraform fmt -check..."
terraform fmt -check -recursive "${ROOT}/deploy/terraform"

for env in staging production; do
  dir="${ROOT}/deploy/terraform/environments/${env}"
  echo "Validating ${env}..."
  (
    cd "${dir}"
    terraform init -backend=false >/dev/null
    terraform validate
  )
done

echo "Terraform validation OK"
