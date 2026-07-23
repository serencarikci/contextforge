# Contributing to ContextForge

Thank you for contributing.

## Development setup

1. Install Python 3.13 and [uv](https://docs.astral.sh/uv/).
2. Install Docker and Docker Compose.
3. Copy `.env.example` to `.env`.
4. Run `make install`.
5. Start infrastructure with `make up`, or run the API locally with `make dev` after starting dependencies.

## Pre-commit

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

## Coding standards

* Prefer explicit dependency injection over globals.
* Keep the domain layer free of FastAPI and SQLAlchemy imports.
* Add type annotations to all public functions.
* Do not log secrets, credentials, cookies, or request bodies.
* Use UTC timestamps in the backend.
* Write tests for new behavior (unit, integration, or architecture as appropriate).

## Pull requests

* Keep changes focused.
* Ensure `make lint`, `make type-check`, and `make test` pass.
* Update documentation when commands or architecture change.
* Do not commit `.env`, credentials, or local volume data.

## Commit messages

Use concise, imperative commit subjects. Example:

```text
feat: add document metadata repository
```
