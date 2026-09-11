from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from PIL import Image

from bus.event_bus import EventBus
from core.roles import RoleStore
from desktop_bridge.service import DesktopBridgeService
from desktop_bridge.role_requests import DesktopRoleRequestHandler
from session.manager import SessionManager


def _write_image(path: Path, color: tuple[int, int, int]) -> None:
    image = Image.new("RGB", (20, 20), "white")
    for x in range(6, 14):
        for y in range(4, 17):
            image.putpixel((x, y), color)
    image.save(path)




@pytest.mark.asyncio
async def test_role_card_preview_forwards_the_full_payload_to_its_service() -> None:
    card_import = SimpleNamespace(preview=AsyncMock(return_value={"import_id": "preview-1"}))
    handler = DesktopRoleRequestHandler(
        role_service=SimpleNamespace(),
        role_store=SimpleNamespace(),
        pet_packages=SimpleNamespace(),
        role_presenter=SimpleNamespace(),
        voice_handler=SimpleNamespace(),
        card_import_service=card_import,
        publish_event=AsyncMock(),
    )

    result = await handler.handle(
        "roles.cardImport.preview",
        {"source": "C:/workspace/private_runtime/imports/role-cards/card.json"},
    )

    card_import.preview.assert_awaited_once_with(
        {"source": "C:/workspace/private_runtime/imports/role-cards/card.json"}
    )
    assert result == {"import_id": "preview-1"}


@pytest.mark.asyncio
async def test_role_create_persists_structured_profile(tmp_path: Path) -> None:
    role_store = RoleStore(tmp_path)
    service = DesktopBridgeService(
        workspace=tmp_path,
        role_store=role_store,
        session_manager=SessionManager(tmp_path),
        agent_loop=SimpleNamespace(process_direct=AsyncMock()),
        event_bus=EventBus(),
    )
    profile = {
        "character": {
            "profile": "A meticulous archivist.",
            "personality": "Calm and precise.",
            "behavior_rules": "Use concise answers and cite the archive.",
            "response_constraints": "Use short paragraphs.",
            "nickname": "",
        },
        "knowledge_base": {"enabled": True, "entries": [], "raw_source": {}},
    }

    response = await service.handle(
        {
            "id": "create-structured-role",
            "method": "roles.create",
            "payload": {
                "name": "Mira",
                "description": "A role",
                "system_prompt": profile["character"]["behavior_rules"],
                "profile": profile,
            },
        },
        emit_event=lambda _payload: None,
    )

    assert response.error is None
    assert response.payload["role"]["profile"] == {"version": 1, **profile}
    persisted = role_store.get_role(response.payload["role"]["id"])
    assert persisted is not None
    assert persisted.profile.to_dict() == {"version": 1, **profile}

    update = await service.handle(
        {
            "id": "update-role-knowledge",
            "method": "roles.update",
            "payload": {
                "role_id": response.payload["role"]["id"],
                "profile": {
                    "knowledge_base": {
                        "enabled": False,
                        "entries": [],
                    }
                },
            },
        },
        emit_event=lambda _payload: None,
    )

    assert update.error is None
    assert update.payload["role"]["profile"]["character"] == profile["character"]
    assert update.payload["role"]["profile"]["knowledge_base"]["enabled"] is False
    assert "token_budget" not in update.payload["role"]["profile"]["knowledge_base"]

    cleared_rules = await service.handle(
        {
            "id": "clear-role-behavior-rules",
            "method": "roles.update",
            "payload": {
                "role_id": response.payload["role"]["id"],
                "system_prompt": "",
                "profile": {"character": {"behavior_rules": ""}},
            },
        },
        emit_event=lambda _payload: None,
    )
    assert cleared_rules.error is None
    character = cleared_rules.payload["role"]["profile"]["character"]
    assert character["behavior_rules"] == ""
    assert character["response_constraints"] == "Use short paragraphs."
    assert character["profile"] == "A meticulous archivist."
    await service.aclose()
