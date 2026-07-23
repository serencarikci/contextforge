#!/usr/bin/env python
"""Verify that the RBAC reference catalog (permissions/system roles) exists.

The canonical permission and system-role catalog is seeded declaratively by
the ``20260723_0002`` Alembic migration (see
``contextforge.shared.constants.rbac``), not by application code. This script
exists as an explicit, named verification step (``make seed-system-data``)
for local/CI workflows that want to fail fast with a clear message if
migrations have not been applied, rather than discovering it later as a
confusing foreign-key or "role not found" error.

It performs no writes: if the expected rows are already present (the normal
case after ``alembic upgrade head``) it is a no-op that only prints counts.
"""

from __future__ import annotations

import asyncio
import sys
import uuid

from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.infrastructure.database.session import DatabaseManager
from contextforge.shared.config.settings import get_settings
from contextforge.shared.constants.rbac import PERMISSIONS, SYSTEM_ROLES

_NO_SUCH_ORGANIZATION_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


async def verify_system_data(uow: SqlAlchemyUnitOfWork) -> tuple[int, int]:
    """Return (permission_count, system_role_count). Raises if either is missing."""
    async with uow:
        permissions = await uow.rbac.list_permissions()
        roles = await uow.rbac.list_roles(_NO_SUCH_ORGANIZATION_ID)
        system_roles = [role for role in roles if role.is_system]

    expected_permission_codes = {code for code, _ in PERMISSIONS}
    expected_role_codes = {code for code, _, _ in SYSTEM_ROLES}

    found_permission_codes = {permission.code for permission in permissions}
    found_role_codes = {role.code for role in system_roles}

    missing_permissions = expected_permission_codes - found_permission_codes
    missing_roles = expected_role_codes - found_role_codes

    if missing_permissions or missing_roles:
        details = []
        if missing_permissions:
            details.append(f"missing permissions: {sorted(missing_permissions)}")
        if missing_roles:
            details.append(f"missing system roles: {sorted(missing_roles)}")
        msg = (
            "RBAC reference data is not fully seeded ("
            + "; ".join(details)
            + "). Run `make migrate` (alembic upgrade head) first."
        )
        raise RuntimeError(msg)

    return len(permissions), len(system_roles)


async def _main() -> int:
    settings = get_settings()
    database = DatabaseManager(settings.postgres)
    try:
        uow = SqlAlchemyUnitOfWork(database.session_factory)
        try:
            permission_count, role_count = await verify_system_data(uow)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    finally:
        await database.dispose()

    print("ContextForge system RBAC reference data verified (seeded by migrations).")
    print(f"  permissions:  {permission_count}")
    print(f"  system roles: {role_count}")
    return 0


def main() -> None:
    sys.exit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
