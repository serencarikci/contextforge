#!/usr/bin/env bash
set -euo pipefail

export PATH="/Applications/Docker.app/Contents/Resources/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Starting Docker Desktop (if needed)"
open -a Docker >/dev/null 2>&1 || true
open /Applications/Docker.app >/dev/null 2>&1 || true
if [ -x "/Applications/Docker.app/Contents/MacOS/Docker Desktop.app/Contents/MacOS/Docker Desktop" ]; then
  open "/Applications/Docker.app/Contents/MacOS/Docker Desktop.app" >/dev/null 2>&1 || true
fi

echo "==> Waiting for Docker daemon (up to ~3 minutes)"
ready=0
for i in $(seq 1 60); do
  if docker info >/dev/null 2>&1; then
    echo
    echo "Docker is ready"
    ready=1
    break
  fi
  sleep 3
  printf '.'
  if (( i % 10 == 0 )); then
    echo " still waiting ($((i * 3))s) — menu bar'da Docker balinası yeşil olmalı"
  fi
done
echo

if [[ "$ready" -ne 1 ]]; then
  echo "ERROR: Docker daemon hâlâ ayakta değil."
  echo
  echo "Şunları yap:"
  echo "  1) Bu scripti Ctrl+C ile durdur"
  echo "  2) Finder → Applications → Docker.app → Open (veya Spotlight: Docker)"
  echo "  3) Menü çubuğunda balina ikonu yeşil/idle olana kadar bekle"
  echo "  4) Sonra tekrar: bash ./scripts/dev-up.sh"
  echo
  echo "Docker.app açılmıyorsa: https://www.docker.com/products/docker-desktop/ adresinden yeniden kur."
  echo "Hızlı test: docker info"
  exit 1
fi

echo "==> Starting compose stack"
docker compose up -d --build

echo "==> Waiting for API health"
for i in $(seq 1 40); do
  if curl -fsS --max-time 3 http://127.0.0.1:8000/api/v1/health/live >/dev/null 2>&1; then
    echo "API is healthy"
    break
  fi
  sleep 3
  printf '.'
done
echo

curl -fsS --max-time 5 http://127.0.0.1:8000/api/v1/health/live || true
echo
curl -fsS --max-time 5 http://127.0.0.1:8000/api/v1/health/ready || true
echo

echo "==> Bootstrapping development data"
uv run python scripts/bootstrap_dev.py

echo "==> Starting frontend on http://127.0.0.1:3001"
cd frontend/web
if [ ! -f .env.local ]; then
  cp .env.example .env.local
fi
export WATCHPACK_POLLING=true
export CHOKIDAR_USEPOLLING=true
exec npx next dev --port 3001 --hostname 127.0.0.1
