"""Application entrypoint."""

from __future__ import annotations

import uvicorn

from contextforge.bootstrap.app_factory import create_app
from contextforge.shared.config.settings import get_settings

app = create_app()


def run() -> None:
    """Run the API server using application settings."""
    settings = get_settings()
    uvicorn.run(
        "contextforge.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.app.environment == "local" and settings.app.debug,
        log_config=None,
    )


if __name__ == "__main__":
    run()
