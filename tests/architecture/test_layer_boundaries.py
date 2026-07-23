"""Architecture boundary tests."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "src" / "contextforge"


def _python_files(directory: Path) -> list[Path]:
    return sorted(path for path in directory.rglob("*.py") if path.is_file())


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


@pytest.mark.architecture
def test_domain_does_not_import_fastapi() -> None:
    forbidden = {"fastapi", "starlette", "uvicorn"}
    for path in _python_files(ROOT / "domain"):
        imported = _imported_modules(path)
        assert imported.isdisjoint(forbidden), f"{path} imports {imported & forbidden}"


@pytest.mark.architecture
def test_domain_does_not_import_sqlalchemy() -> None:
    forbidden = {"sqlalchemy", "alembic", "asyncpg"}
    for path in _python_files(ROOT / "domain"):
        imported = _imported_modules(path)
        assert imported.isdisjoint(forbidden), f"{path} imports {imported & forbidden}"


@pytest.mark.architecture
def test_application_does_not_import_concrete_infrastructure() -> None:
    """Application may define ports but must not import infrastructure adapters."""
    forbidden_prefixes = (
        "contextforge.infrastructure.database",
        "contextforge.infrastructure.repositories",
        "contextforge.infrastructure.cache",
        "contextforge.infrastructure.vector_store",
        "contextforge.infrastructure.object_storage",
    )
    for path in _python_files(ROOT / "application"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                module = node.module
                assert not any(module.startswith(prefix) for prefix in forbidden_prefixes), (
                    f"{path} imports infrastructure module {module}"
                )
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(
                        alias.name.startswith(prefix) for prefix in forbidden_prefixes
                    ), f"{path} imports infrastructure module {alias.name}"
