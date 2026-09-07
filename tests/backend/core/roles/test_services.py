from __future__ import annotations

import pytest

from core.roles import RoleAggregateService, RoleStore
from session.manager import SessionManager
from types import SimpleNamespace
from unittest.mock import AsyncMock
from core.roles.self_seed import LlmRoleSelfSeedGenerator


@pytest.mark.asyncio
async def test_new_role_generates_self_from_profile_and_profile_edits_preserve_it(tmp_path):
    provider = SimpleNamespace(chat=AsyncMock(return_value=SimpleNamespace(content="# 我是谁\n\n角色自我认知")))
    service = RoleAggregateService.from_runtime(
        workspace=tmp_path,
        role_store=RoleStore(tmp_path),
        session_manager=SessionManager(tmp_path),
        self_seed_generator=LlmRoleSelfSeedGenerator(provider=provider, model="test"),
    )
    aggregate = await service.create_role_async(
        role_id="mira", name="Mira", system_prompt="旧规则", background="旧背景",
        profile={"character": {"profile": "{{char}}的新资料", "response_constraints": "回答简洁"}},
    )
    prompt = provider.chat.await_args.kwargs["messages"][1]["content"]
    assert "Mira的新资料" in prompt
    assert "回答简洁" in prompt
    assert "旧背景" not in prompt and "旧规则" not in prompt
    self_path = aggregate.memory_root / "SELF.md"
    saved_self = self_path.read_text(encoding="utf-8")
    history_path = aggregate.memory_root / "HISTORY.md"
    saved_history = history_path.read_text(encoding="utf-8")

    await service.update_role_async("mira", profile={"character": {"profile": "再次更新的资料"}})
    await service.open_role_async("mira")

    provider.chat.assert_awaited_once()
    assert self_path.read_text(encoding="utf-8") == saved_self
    assert history_path.read_text(encoding="utf-8") == saved_history


def test_role_deletion_requires_a_lifecycle_listener(tmp_path) -> None:
    store = RoleStore(tmp_path)
    service = RoleAggregateService.from_runtime(
        workspace=tmp_path,
        role_store=store,
        session_manager=SessionManager(tmp_path),
    )
    service.create_role(
        role_id="mira",
        name="Mira",
        system_prompt="You are Mira.",
    )

    with pytest.raises(RuntimeError, match="角色删除生命周期监听器"):
        service.delete_role("mira")

    assert store.get_role("mira") is not None


def test_role_deletion_listener_can_be_removed(tmp_path) -> None:
    service = RoleAggregateService.from_runtime(
        workspace=tmp_path,
        role_store=RoleStore(tmp_path),
        session_manager=SessionManager(tmp_path),
    )
    deleted_role_ids: list[str] = []
    service.add_role_deleted_listener(deleted_role_ids.append)
    service.remove_role_deleted_listener(deleted_role_ids.append)
    service.create_role(
        role_id="mira",
        name="Mira",
        system_prompt="You are Mira.",
    )

    with pytest.raises(RuntimeError, match="角色删除生命周期监听器"):
        service.delete_role("mira")

    assert deleted_role_ids == []


def test_sync_role_creation_persists_the_structured_profile(tmp_path) -> None:
    service = RoleAggregateService.from_runtime(
        workspace=tmp_path,
        role_store=RoleStore(tmp_path),
        session_manager=SessionManager(tmp_path),
    )

    aggregate = service.create_role(
        role_id="mira",
        name="Mira",
        system_prompt="Legacy fallback.",
        profile={
            "character": {
                "profile": "A careful archivist.",
                "personality": "Quiet and precise.",
                "behavior_rules": "Answer from the archive.",
            }
        },
    )

    assert aggregate.role.profile.character.profile == "A careful archivist."
    assert aggregate.role.profile.character.personality == "Quiet and precise."
