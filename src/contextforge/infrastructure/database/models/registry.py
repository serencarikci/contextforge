"""Central import registry for all ORM models.

Alembic's migration environment and the application bootstrap must import
every mapped model exactly once before relying on ``Base.metadata`` (e.g. for
autogeneration or ``create_all``). Importing individual model modules from
scattered locations is error-prone, so this module provides a single place
that pulls in every module's ``infrastructure.models`` package.

Usage::

    from contextforge.infrastructure.database.models.registry import import_all_models

    import_all_models()
"""

from __future__ import annotations


def import_all_models() -> None:
    """Import every ORM model module so it registers with ``Base.metadata``."""
    from contextforge.infrastructure.database import models as _core_models  # noqa: F401
    from contextforge.modules.audit.infrastructure import models as _audit_models  # noqa: F401
    from contextforge.modules.customers.infrastructure import (
        models as _customer_models,  # noqa: F401
    )
    from contextforge.modules.documents.infrastructure import (
        models as _document_models,  # noqa: F401
    )
    from contextforge.modules.identity_access.infrastructure import (  # noqa: F401
        models as _identity_access_models,
    )
    from contextforge.modules.knowledge_spaces.infrastructure import (  # noqa: F401
        models as _knowledge_space_models,
    )
    from contextforge.modules.organizations.infrastructure import (  # noqa: F401
        models as _organization_models,
    )
    from contextforge.modules.projects.infrastructure import models as _project_models  # noqa: F401
