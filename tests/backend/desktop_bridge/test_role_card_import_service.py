from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bus.event_bus import EventBus
from core.roles import RoleAggregateService, RoleStore
from desktop_bridge.role_card_import_service import DesktopRoleCardImportService
from desktop_bridge.service import DesktopBridgeService
from session.manager import SessionManager


def _card(*, name: str = "小诗") -> dict[str, object]:
    return {
        "spec": "chara_card_v2",
        "data": {
            "name": name,
            "description": "角色资料",
            "personality": "安静、细心",
            "system_prompt": "遵守边界",
            "first_mes": "你好。",
        },
    }


def _service(tmp_path):
    store = RoleStore(tmp_path)
    aggregate_service = RoleAggregateService.from_runtime(
        workspace=tmp_path,
        role_store=store,
        session_manager=SessionManager(tmp_path),
    )
    return (
        DesktopRoleCardImportService(
            workspace=tmp_path,
            role_service=aggregate_service,
            role_store=store,
        ),
        store,
    )


def _stage_card(tmp_path, payload: dict[str, object]):
    source = tmp_path / "private_runtime" / "imports" / "role-cards" / "card.json"
    source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return source


@pytest.mark.asyncio
async def test_preview_stages_card_without_creating_a_role(tmp_path) -> None:
    service, store = _service(tmp_path)
    source = _stage_card(tmp_path, _card())

    preview = await service.preview({"source": str(source)})

    assert preview["name"] == "小诗"
    assert preview["import_id"]
    assert preview["system_prompt"] == "遵守边界"
    assert store.list_roles() == []


@pytest.mark.asyncio
async def test_commit_creates_role_only_after_preview_confirmation(tmp_path) -> None:
    service, store = _service(tmp_path)
    source = _stage_card(tmp_path, _card())
    preview = await service.preview({"source": str(source)})

    result = await service.commit(
        {
            "import_id": preview["import_id"],
            "overrides": {"name": "已导入的小诗"},
        }
    )

    assert result["role"]["name"] == "已导入的小诗"
    imported = store.list_roles()
    assert len(imported) == 1
    assert imported[0].profile.character.personality == "安静、细心"
    assert imported[0].profile.greetings.default == "你好。"
    with pytest.raises(ValueError, match="导入预览已失效"):
        await service.commit({"import_id": preview["import_id"]})


@pytest.mark.asyncio
async def test_cancel_invalidates_preview_without_creating_a_role(tmp_path) -> None:
    service, store = _service(tmp_path)
    source = _stage_card(tmp_path, _card())
    preview = await service.preview({"source": str(source)})

    assert await service.cancel({"import_id": preview["import_id"]}) == {"cancelled": True}
    with pytest.raises(ValueError, match="导入预览已失效"):
        await service.commit({"import_id": preview["import_id"]})
    assert store.list_roles() == []


@pytest.mark.asyncio
async def test_preview_rejects_sources_outside_the_staging_directory(tmp_path) -> None:
    service, _store = _service(tmp_path)
    source = tmp_path / "outside.json"
    source.write_text(json.dumps(_card(), ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="受控导入目录"):
        await service.preview({"source": str(source)})


@pytest.mark.asyncio
async def test_default_desktop_bridge_service_exposes_role_card_preview(tmp_path) -> None:
    role_store = RoleStore(tmp_path)
    service = DesktopBridgeService(
        workspace=tmp_path,
        role_store=role_store,
        session_manager=SessionManager(tmp_path),
        agent_loop=SimpleNamespace(process_direct=AsyncMock()),
        event_bus=EventBus(),
    )
    source = _stage_card(tmp_path, _card())

    response = await service.handle(
        {
            "id": "role-card-preview",
            "method": "roles.cardImport.preview",
            "payload": {"source": str(source)},
        },
        emit_event=lambda _payload: None,
    )

    assert response.error is None
    assert response.payload["name"] == "小诗"
    assert response.payload["import_id"]
    await service.aclose()
