"""Background worker that periodically executes retention policies."""

from __future__ import annotations

import asyncio
import signal
from typing import Any

from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.infrastructure.database.session import DatabaseManager
from contextforge.modules.admin.application.services.retention_service import (
    RetentionCleanupService,
)
from contextforge.shared.config.settings import get_settings
from contextforge.shared.logging.setup import configure_logging, get_logger

logger = get_logger(__name__)


class RetentionWorker:
    """Long-running process that ticks retention cleanup on an interval."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._stop = asyncio.Event()
        self._database = DatabaseManager(self._settings.postgres)
        self._service = RetentionCleanupService(self._settings.admin)

    def request_stop(self, *_args: Any) -> None:
        self._stop.set()

    async def run_forever(self) -> None:
        configure_logging(
            self._settings.logging,
            environment=self._settings.app.environment.value,
        )
        interval = self._settings.admin.retention_worker_interval_seconds
        logger.info("retention_worker_started", extra={"interval_seconds": interval})
        while not self._stop.is_set():
            try:
                uow = SqlAlchemyUnitOfWork(self._database.session_factory)
                results = await self._service.run_all_enabled(uow)
                logger.info(
                    "retention_worker_tick",
                    extra={
                        "policies_run": len(results),
                        "deleted_total": sum(item.deleted_count for item in results),
                    },
                )
            except Exception:
                logger.exception("retention_worker_tick_failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except TimeoutError:
                continue
        await self._database.dispose()
        logger.info("retention_worker_stopped")


def main() -> None:
    worker = RetentionWorker()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, worker.request_stop)
        except NotImplementedError:
            signal.signal(sig, lambda *_: worker.request_stop())
    try:
        loop.run_until_complete(worker.run_forever())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
