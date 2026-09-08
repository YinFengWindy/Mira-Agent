from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from conversation.service import ConversationService
from desktop_bridge.app_service import DesktopAppService
from session.manager import SessionManager


@pytest.mark.asyncio
@pytest.mark.parametrize("message,media", [
    ("", None),
    (" \t\n", []),
    ("", ["   "]),
    (" ", ["", "\t", "\n"]),
])
async def test_empty_push_has_no_session_or_runtime_side_effects(tmp_path, message, media):
    manager = SessionManager(tmp_path)
    session = manager.get_or_create("role:mira")
    session.add_message("assistant", "existing history")
    await manager.save_async(session)
    before = list(session.messages)
    updated_at = session.updated_at
    presence = Mock()
    relationship = Mock()
    conversation = Mock()
    service = DesktopAppService(
        role_service=SimpleNamespace(),
        session_manager=manager,
        conversation_service=conversation,
        presence=presence,
        relationship_runtime=relationship,
    )

    for chat_id in ("role:mira", "role:new"):
        with pytest.raises(ValueError, match="非空"):
            await service.apply_desktop_push(chat_id, message=message, media=media)

    assert session.messages == before
    assert session.updated_at == updated_at
    assert "role:new" not in manager._cache
    assert presence.mock_calls == []
    assert relationship.mock_calls == []
    assert conversation.mock_calls == []
    reloaded = SessionManager(tmp_path)
    assert reloaded.get_or_create("role:mira").messages == before
    assert not reloaded._store.session_exists("role:new")


@pytest.mark.asyncio
@pytest.mark.parametrize("message,media,expected_media", [
    ("  hello\n", [" "], None),
    ("", [" ", "image.png", "\t"], ["image.png"]),
    ("caption", ["document.pdf"], ["document.pdf"]),
])
async def test_push_with_content_survives_reload(tmp_path, message, media, expected_media):
    manager = SessionManager(tmp_path)
    service = DesktopAppService(
        role_service=SimpleNamespace(),
        session_manager=manager,
        conversation_service=ConversationService(manager),
    )

    await service.apply_desktop_push("role:mira", message=message, media=media)

    reloaded = SessionManager(tmp_path).get_or_create("role:mira")
    assert len(reloaded.messages) == 1
    assert reloaded.messages[0]["content"] == message
    assert reloaded.messages[0].get("media") == expected_media
