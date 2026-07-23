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


MODULES_ROOT = ROOT / "modules"


def _module_domain_dirs() -> list[Path]:
    """Every `src/contextforge/modules/<module>/domain` directory that exists."""
    if not MODULES_ROOT.is_dir():
        return []
    return sorted(
        module_dir / "domain"
        for module_dir in MODULES_ROOT.iterdir()
        if module_dir.is_dir() and (module_dir / "domain").is_dir()
    )


def _module_application_dirs() -> list[Path]:
    """Every `src/contextforge/modules/<module>/application` directory that exists."""
    if not MODULES_ROOT.is_dir():
        return []
    return sorted(
        module_dir / "application"
        for module_dir in MODULES_ROOT.iterdir()
        if module_dir.is_dir() and (module_dir / "application").is_dir()
    )


@pytest.mark.architecture
def test_domain_does_not_import_fastapi() -> None:
    forbidden = {"fastapi", "starlette", "uvicorn"}
    domain_dirs = [ROOT / "domain", *_module_domain_dirs()]
    for domain_dir in domain_dirs:
        for path in _python_files(domain_dir):
            imported = _imported_modules(path)
            assert imported.isdisjoint(forbidden), f"{path} imports {imported & forbidden}"


@pytest.mark.architecture
def test_domain_does_not_import_sqlalchemy() -> None:
    forbidden = {"sqlalchemy", "alembic", "asyncpg"}
    domain_dirs = [ROOT / "domain", *_module_domain_dirs()]
    for domain_dir in domain_dirs:
        for path in _python_files(domain_dir):
            imported = _imported_modules(path)
            assert imported.isdisjoint(forbidden), f"{path} imports {imported & forbidden}"


@pytest.mark.architecture
def test_module_domain_directories_are_discovered() -> None:
    """Guard against this test file silently scanning zero module domains."""
    assert len(_module_domain_dirs()) >= 5, (
        "Expected to discover domain packages under src/contextforge/modules/*/domain; "
        "if modules were renamed/removed, update this assertion accordingly."
    )


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
    application_dirs = [ROOT / "application", *_module_application_dirs()]
    for application_dir in application_dirs:
        for path in _python_files(application_dir):
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


@pytest.mark.architecture
def test_application_does_not_import_api_modules() -> None:
    """Application (use cases/ports) must not depend on the HTTP transport layer."""
    forbidden_prefix = "contextforge.api"
    application_dirs = [ROOT / "application", *_module_application_dirs()]
    for application_dir in application_dirs:
        for path in _python_files(application_dir):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert not node.module.startswith(forbidden_prefix), (
                        f"{path} imports api module {node.module}"
                    )
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not alias.name.startswith(forbidden_prefix), (
                            f"{path} imports api module {alias.name}"
                        )
