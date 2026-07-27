from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
import yaml

from contextforge.modules.rag.application.prompts.registry import PromptRegistry
from contextforge.shared.config.settings import PromptSettings


class _FakeOverrideSource:
    async def active_slot_contents(self, uow, *, organization_id, language):
        return {"system": "DB SYSTEM OVERRIDE"}


@pytest.mark.asyncio
async def test_prompt_registry_applies_db_overrides(tmp_path: Path) -> None:
    version_dir = tmp_path / "v1"
    version_dir.mkdir()
    (version_dir / "en.yaml").write_text(
        yaml.safe_dump(
            {
                "version": "v1",
                "language": "en",
                "system": "YAML SYSTEM",
                "user": "YAML USER",
                "citation": "cite {{chunk_id}}",
                "multilingual": "lang {{language}}",
            }
        ),
        encoding="utf-8",
    )
    registry = PromptRegistry(
        PromptSettings(active_version="v1", default_language="en"),
        root=tmp_path,
        override_source=_FakeOverrideSource(),
    )

    class _DummyUow:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

    bundle = await registry.get_for_organization(
        _DummyUow(),  # type: ignore[arg-type]
        organization_id=uuid4(),
        language="en",
    )
    assert bundle.system == "DB SYSTEM OVERRIDE"
    assert bundle.user == "YAML USER"
