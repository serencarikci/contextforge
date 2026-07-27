#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHART="${ROOT}/deploy/helm/contextforge"

if ! command -v helm >/dev/null 2>&1; then
  echo "helm not installed — skipping helm lint/template"
  exit 0
fi

echo "Running helm lint..."
helm lint "${CHART}"

echo "Running helm template (default values)..."
helm template contextforge "${CHART}" >/dev/null

echo "Running helm template (prod values)..."
helm template contextforge "${CHART}" -f "${CHART}/values-prod.yaml" >/dev/null

echo "Helm validation OK"
