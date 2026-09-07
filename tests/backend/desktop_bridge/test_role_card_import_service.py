from __future__ import annotations

import base64
import io
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from PIL import Image, PngImagePlugin

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


def _png_role_card(payload: dict[str, object]) -> bytes:
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text(
        "chara",
        base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode(),
    )
    image = Image.new("RGBA", (8, 8), (255, 0, 0, 255))
    output = io.BytesIO()
    image.save(output, format="PNG", pnginfo=metadata)
    return output.getvalue()


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
    assert "greetings" not in imported[0].profile.to_dict()
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
async def test_commit_keeps_long_card_description_out_of_the_role_summary(tmp_path) -> None:
    service, store = _service(tmp_path)
    card = _card()
    data = card["data"]
    assert isinstance(data, dict)
    data["description"] = "完整角色设定"
    data["system_prompt"] = ""
    source = _stage_card(tmp_path, card)
    preview = await service.preview({"source": str(source)})

    await service.commit(
        {
            "import_id": preview["import_id"],
            "overrides": {"profile": {"character": {"personality": "自定义性格"}}},
        }
    )

    imported = store.list_roles()[0]
    assert imported.description == ""
    assert imported.profile.character.profile == "完整角色设定"
    assert imported.profile.character.personality == "自定义性格"
    assert imported.system_prompt == "请遵循角色资料进行自然对话。"
    assert imported.profile.import_provenance is not None
    assert imported.profile.import_provenance.format == "tavern-json"


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


@pytest.mark.asyncio
async def test_commit_keeps_png_card_as_avatar_and_imported_asset(tmp_path) -> None:
    role_store = RoleStore(tmp_path)
    service = DesktopBridgeService(
        workspace=tmp_path,
        role_store=role_store,
        session_manager=SessionManager(tmp_path),
        agent_loop=SimpleNamespace(process_direct=AsyncMock()),
        event_bus=EventBus(),
    )
    source = tmp_path / "private_runtime" / "imports" / "role-cards" / "card.png"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(_png_role_card(_card()))

    preview = await service.handle(
        {"id": "preview", "method": "roles.cardImport.preview", "payload": {"source": str(source)}},
        emit_event=lambda _payload: None,
    )
    committed = await service.handle(
        {
            "id": "commit",
            "method": "roles.cardImport.commit",
            "payload": {"import_id": preview.payload["import_id"]},
        },
        emit_event=lambda _payload: None,
    )

    assert committed.error is None
    role = committed.payload["role"]
    assert role["avatar"]
    assert role["avatar_abs"]
    assert len(role["illustrations"]) == 1
    category = next(item for item in role["asset_categories"] if item["id"] == "imported-role-card")
    assert category["name"] == "导入角色卡"
    assert role["asset_category_bindings"][role["illustrations"][0]] == category["id"]
    await service.aclose()
