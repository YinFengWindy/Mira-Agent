from __future__ import annotations

import asyncio
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from core.roles import RoleAggregateService, RoleStore
from core.roles.model_runtime import RoleModelSnapshot
from core.roles.self_initializer import RoleSelfInitializer, SelfInitializationError
from core.roles.self_seed import LlmRoleSelfSeedGenerator
from session.manager import SessionManager


@pytest.fixture
def setup(tmp_path):
    store = RoleStore(tmp_path)
    service = RoleAggregateService.from_runtime(
        workspace=tmp_path,
        role_store=store,
        session_manager=SessionManager(tmp_path),
    )
    aggregate = service.create_role(
        name="Mira", role_id="mira", system_prompt="诚实", background="向导"
    )
    provider = SimpleNamespace(
        chat=AsyncMock(return_value=SimpleNamespace(content="# 我是谁\n\n生成内容\n"))
    )
    snapshot = RoleModelSnapshot(
        "selected", provider, "role-model", "none", role_id="mira"
    )
    initializer = RoleSelfInitializer(store, LlmRoleSelfSeedGenerator())
    return store, service, aggregate.memory_root / "SELF.md", snapshot, initializer


@pytest.mark.asyncio
async def test_seed_persists_success_and_survives_reopen_restart_and_rebinding(setup):
    store, service, path, snapshot, initializer = setup
    await initializer.ensure_seeded("mira", snapshot)
    saved = path.read_text(encoding="utf-8")
    state = store.get_role("mira").memory_init_state["self_seed"]
    assert state["status"] == "generated"
    assert state["model_registration_id"] == "selected"
    assert state["generated_at"] and state["last_attempt_at"]
    assert state["last_error"] is None
    service.open_role("mira")
    service.update_role(
        "mira",
        background="新背景",
        runtime_config={"dialogue_model_registration_id": "another"},
    )
    restarted = RoleSelfInitializer(
        RoleStore(store.workspace), LlmRoleSelfSeedGenerator()
    )
    await restarted.ensure_seeded("mira", replace(snapshot, registration_id="another"))
    snapshot.provider.chat.assert_awaited_once()
    assert path.read_text(encoding="utf-8") == saved


@pytest.mark.asyncio
async def test_failed_seed_preserves_role_session_and_default_then_retries(setup):
    store, service, path, snapshot, initializer = setup
    default = path.read_text(encoding="utf-8")
    snapshot.provider.chat.side_effect = TimeoutError("provider timeout")
    with pytest.raises(SelfInitializationError, match="再次发送"):
        await initializer.ensure_seeded("mira", snapshot)
    state = store.get_role("mira").memory_init_state["self_seed"]
    assert state["status"] == "pending"
    assert state["last_error"] == "provider timeout"
    assert path.read_text(encoding="utf-8") == default
    assert service.open_role("mira").session.key == "role:mira"
    snapshot.provider.chat.side_effect = None
    restarted = RoleSelfInitializer(
        RoleStore(store.workspace), LlmRoleSelfSeedGenerator()
    )
    await restarted.ensure_seeded("mira", snapshot)
    assert (
        store.get_role("mira").memory_init_state["self_seed"]["status"] == "generated"
    )
    assert snapshot.provider.chat.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("when", ["before", "during", "after"])
async def test_seed_never_overwrites_manual_edits(setup, when):
    store, service, path, snapshot, initializer = setup
    edited = "# 我是谁\n\n用户自己的内容\n"
    if when == "before":
        path.write_text(edited, encoding="utf-8")
    if when == "during":

        async def generate(**kwargs):
            path.write_text(edited, encoding="utf-8")
            return SimpleNamespace(content="新生成的内容")

        snapshot.provider.chat.side_effect = generate
    await initializer.ensure_seeded("mira", snapshot)
    if when == "after":
        path.write_text(edited, encoding="utf-8")
    service.open_role("mira")
    await initializer.ensure_seeded("mira", snapshot)
    assert path.read_text(encoding="utf-8") == edited
    assert snapshot.provider.chat.await_count == (0 if when == "before" else 1)
    assert store.get_role("mira").memory_init_state["self_seed"]["status"] == (
        "generated" if when == "after" else "user_edited"
    )


@pytest.mark.asyncio
async def test_pending_background_changes_during_generation_are_preserved(setup):
    store, service, path, snapshot, initializer = setup

    async def generate(**kwargs):
        service.update_role("mira", background="用户更新的背景")
        return SimpleNamespace(content="过期的生成内容")

    snapshot.provider.chat.side_effect = generate
    await initializer.ensure_seeded("mira", snapshot)
    assert "用户更新的背景" in path.read_text(encoding="utf-8")
    assert "过期的生成内容" not in path.read_text(encoding="utf-8")
    assert (
        store.get_role("mira").memory_init_state["self_seed"]["status"] == "user_edited"
    )


@pytest.mark.asyncio
async def test_cancelled_seed_remains_retryable(setup):
    store, _, path, snapshot, initializer = setup
    original = path.read_text(encoding="utf-8")
    snapshot.provider.chat.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await initializer.ensure_seeded("mira", snapshot)
    assert store.get_role("mira").memory_init_state["self_seed"]["status"] == "pending"
    assert path.read_text(encoding="utf-8") == original


@pytest.mark.asyncio
async def test_failure_does_not_reset_an_edit_saved_during_generation(setup):
    store, service, path, snapshot, initializer = setup

    async def generate(**kwargs):
        path.write_text("用户编辑", encoding="utf-8")
        service.open_role("mira")
        raise RuntimeError("failed after edit")

    snapshot.provider.chat.side_effect = generate
    with pytest.raises(SelfInitializationError):
        await initializer.ensure_seeded("mira", snapshot)
    state = store.get_role("mira").memory_init_state["self_seed"]
    assert state["status"] == "user_edited"
    assert state["last_error"] == "failed after edit"


@pytest.mark.asyncio
@pytest.mark.parametrize("changes", [{"purpose": "vision"}, {"role_id": "another"}])
async def test_seed_rejects_wrong_model_snapshot(setup, changes):
    _, _, _, snapshot, initializer = setup
    with pytest.raises(ValueError, match="对话模型"):
        await initializer.ensure_seeded("mira", replace(snapshot, **changes))
    snapshot.provider.chat.assert_not_called()
