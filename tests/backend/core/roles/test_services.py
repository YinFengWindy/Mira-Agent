from __future__ import annotations

import pytest

from core.roles import RoleAggregateService, RoleStore
from session.manager import SessionManager


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
