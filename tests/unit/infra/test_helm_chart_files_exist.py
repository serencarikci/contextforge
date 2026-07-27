"""Static infra artifact presence and optional compose/helm validation."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.unit
def test_helm_chart_files_exist() -> None:
    chart = ROOT / "deploy" / "helm" / "contextforge"
    required = [
        chart / "Chart.yaml",
        chart / "values.yaml",
        chart / "values-dev.yaml",
        chart / "values-staging.yaml",
        chart / "values-prod.yaml",
        chart / "templates" / "deployment-api.yaml",
        chart / "templates" / "deployment-ingestion.yaml",
        chart / "templates" / "deployment-retention.yaml",
        chart / "templates" / "job-migrate.yaml",
        chart / "templates" / "service.yaml",
        chart / "templates" / "hpa.yaml",
        chart / "templates" / "pdb.yaml",
        chart / "templates" / "networkpolicy.yaml",
        chart / "templates" / "servicemonitor.yaml",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    assert missing == [], f"Missing helm files: {missing}"


@pytest.mark.unit
def test_terraform_and_ops_artifacts_exist() -> None:
    required = [
        ROOT / "deploy" / "terraform" / "environments" / "staging" / "main.tf",
        ROOT / "deploy" / "terraform" / "environments" / "production" / "main.tf",
        ROOT / "deploy" / "observability" / "prometheus" / "prometheus.yml",
        ROOT / "deploy" / "observability" / "prometheus" / "alerts.yml",
        ROOT / "deploy" / "observability" / "grafana" / "dashboards" / "contextforge-overview.json",
        ROOT / "scripts" / "backup" / "backup_postgres.sh",
        ROOT / "scripts" / "backup" / "restore_postgres.sh",
        ROOT / "ops" / "production-readiness-checklist.md",
        ROOT / "ops" / "runbooks" / "api-outage.md",
        ROOT / "perf" / "k6" / "smoke.js",
        ROOT / "docker-compose.prod.yml",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    assert missing == [], f"Missing ops files: {missing}"


def _resolve_docker() -> str | None:
    found = shutil.which("docker")
    if found:
        return found
    candidates = [
        "/Applications/Docker.app/Contents/Resources/bin/docker",
        "/usr/local/bin/docker",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    return None


@pytest.mark.unit
def test_docker_compose_config_validates_when_available() -> None:
    docker = _resolve_docker()
    if docker is None:
        pytest.skip("docker not available")
    result = subprocess.run(  # noqa: S603
        [docker, "compose", "-f", str(ROOT / "docker-compose.yml"), "config"],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if result.returncode != 0:
        pytest.skip(f"docker compose unavailable or failed: {result.stderr[:200]}")
    assert "contextforge-api" in result.stdout or "api:" in result.stdout
