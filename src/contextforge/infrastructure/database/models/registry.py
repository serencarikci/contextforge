from __future__ import annotations


def import_all_models() -> None:
    from contextforge.infrastructure.database import models as _core_models  # noqa: F401
    from contextforge.modules.admin.infrastructure import models as _admin_models  # noqa: F401
    from contextforge.modules.audit.infrastructure import models as _audit_models  # noqa: F401
    from contextforge.modules.chat.infrastructure import models as _chat_models  # noqa: F401
    from contextforge.modules.customers.infrastructure import (
        models as _customer_models,  # noqa: F401
    )
    from contextforge.modules.documents.infrastructure import (
        models as _document_models,  # noqa: F401
    )
    from contextforge.modules.identity_access.infrastructure import (  # noqa: F401
        models as _identity_access_models,
    )
    from contextforge.modules.ingestion.infrastructure import (  # noqa: F401
        models as _ingestion_models,
    )
    from contextforge.modules.knowledge_spaces.infrastructure import (  # noqa: F401
        models as _knowledge_space_models,
    )
    from contextforge.modules.organizations.infrastructure import (  # noqa: F401
        models as _organization_models,
    )
    from contextforge.modules.projects.infrastructure import models as _project_models  # noqa: F401
