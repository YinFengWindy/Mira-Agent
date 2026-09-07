from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agent.config import load_config_text
from agent.provider import LLMProvider, LLMResponse
from bootstrap.app import AppRuntime, RuntimeFeatures
from core.roles.store import RoleStore
from desktop_bridge.runtime_service import ReloadableDesktopService
from desktop_bridge.runtime_service import _ServiceGeneration

_REGISTRATION = "00000000-0000-4000-a000-000000000001"


@pytest.mark.asyncio
async def test_reloading_rejects_new_work_without_queuing_a_late_chat():
    service = object.__new__(ReloadableDesktopService)
    service.app = SimpleNamespace(accepting_work=False)
    service._owner = lambda *args: pytest.fail("rejected request must never reach a handler")
    response = await asyncio.wait_for(service.handle(
        {"method": "chat.send", "payload": {"role_id": "role", "content": "message"}},
        emit_event=lambda event: None,
    ), 0.1)
    assert response.error.code == "runtime_reloading"


@pytest.mark.asyncio
async def test_retirement_releases_generation_even_if_handler_cleanup_fails():
    handler = SimpleNamespace(chat_service=SimpleNamespace(drain=AsyncMock()),
                              story_simulation=SimpleNamespace(drain=AsyncMock()),
                              aclose=AsyncMock(side_effect=OSError("close failed")))
    lease = SimpleNamespace(release=AsyncMock())
    entry = _ServiceGeneration(handler, lease)
    service = object.__new__(ReloadableDesktopService)
    service._entries = [entry]
    with pytest.raises(OSError, match="close failed"):
        await service._retire(entry)
    lease.release.assert_awaited_once()
    assert not service._entries


def _config(model=""):
    registration = (
        f'[[llm.registrations]]\nid = "{_REGISTRATION}"\nprovider = "openai"\n'
        f'model = "{model}"\napi_key = "fake-key"\n'
        if model else "[llm]\nregistrations = []\n"
    )
    return registration + '\n[agent.maintenance]\nmemory_optimizer_enabled = false\n[proactive]\nenabled = false\nprofile = "quiet"\n'


@pytest.mark.asyncio
async def test_empty_boot_register_bind_and_chat_preserves_existing_turn(tmp_path, monkeypatch):
    monkeypatch.setattr("bootstrap.tools._resolve_plugin_dirs", lambda workspace: [])
    calls = []
    entered = asyncio.Event()
    finish = asyncio.Event()
    hold = False

    async def fake_chat(self, **kwargs):
        model = kwargs["model"]
        calls.append(model)
        if hold and model == "first":
            entered.set()
            await finish.wait()
        return LLMResponse(content=f"reply from {model}")

    monkeypatch.setattr(LLMProvider, "chat", fake_chat)
    path = tmp_path / "config.toml"
    path.write_text(_config(), encoding="utf-8")
    app = AppRuntime(load_config_text(_config()), tmp_path,
                     features=RuntimeFeatures(enable_message_channels=False, enable_proactive=False))
    await app.start()
    service = ReloadableDesktopService(app, path, RoleStore(tmp_path))
    events = []

    async def request(method, payload=None):
        response = await service.handle({"id": method, "method": method, "payload": payload or {}},
                                        emit_event=events.append)
        assert response.error is None, response.error
        return response.payload

    try:
        assert (await request("health"))["ok"]
        created = await request("roles.create", {"name": "Role", "system_prompt": "Role prompt"})
        role_id = created["role"]["id"]
        await request("session.openByRole", {"role_id": role_id})
        unbound = await service.handle({"method": "chat.send", "payload": {"role_id": role_id, "content": "hi"}},
                                       emit_event=events.append)
        assert unbound.error.code == "model_configuration_required"
        assert not app.session_manager.get_or_create(f"role:{role_id}").messages
        await request("runtime.apply", {"config_toml": _config("first"), "operation_id": "first",
                                        "expected_generation": 1})
        assert not service.roles.get_role(role_id).runtime_config["dialogue_model_registration_id"]
        await request("roles.update", {"role_id": role_id, "runtime_config": {
            "dialogue_model_registration_id": _REGISTRATION,
        }})
        hold = True
        await request("chat.send", {"role_id": role_id, "content": "old task", "turn_id": "old"})
        await asyncio.wait_for(entered.wait(), 5)
        old_service = service._current.service
        await request("runtime.apply", {"config_toml": _config("second"), "operation_id": "second",
                                        "expected_generation": 2})
        assert old_service.chat_service.is_busy(f"role:{role_id}")
        assert not finish.is_set()
        assert app.generation == 3
        assert (await request("runtime.status"))["config_toml"] == _config("second")
        finish.set()
        await asyncio.wait_for(old_service.chat_service.drain(), 5)
        await request("chat.send", {"role_id": role_id, "content": "new task", "turn_id": "new"})
        await asyncio.wait_for(service._current.service.chat_service.drain(), 5)
        assert calls[-1] == "second"
        assert any(item["method"] == "chat.done" for item in events)
        await request("runtime.apply", {"config_toml": _config(), "operation_id": "empty",
                                        "expected_generation": 3,
                                        "role_model_updates": [{"role_id": role_id, "runtime_config": {
                                            "dialogue_model_registration_id": "",
                                        }}]})
        assert not service.status()["models_registered"]
        assert (await request("health"))["ok"]
        assert app.session_manager.get_or_create(f"role:{role_id}").messages
    finally:
        finish.set()
        await service.aclose()
        await app.shutdown()


@pytest.mark.asyncio
async def test_invalid_apply_and_generation_conflict_preserve_active_files(tmp_path, monkeypatch):
    monkeypatch.setattr("bootstrap.tools._resolve_plugin_dirs", lambda workspace: [])
    path = tmp_path / "config.toml"
    path.write_text(_config(), encoding="utf-8")
    app = AppRuntime(load_config_text(_config()), tmp_path,
                     features=RuntimeFeatures(enable_message_channels=False, enable_proactive=False))
    await app.start()
    service = ReloadableDesktopService(app, path, RoleStore(tmp_path))
    try:
        for text, expected, code in [("invalid TOML", 1, "runtime_config_invalid"),
                                      (_config("model"), 9, "runtime_generation_conflict")]:
            response = await service.handle({"method": "runtime.apply", "payload": {
                "config_toml": text, "operation_id": code, "expected_generation": expected,
            }}, emit_event=lambda event: None)
            assert response.error.code == code
            assert path.read_text(encoding="utf-8") == _config()
            assert app.generation == 1
    finally:
        await service.aclose()
        await app.shutdown()
