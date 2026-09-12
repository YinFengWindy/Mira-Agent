import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from conversation.service import ConversationService
from desktop_bridge.app_service import DesktopAppService
from session.manager import SessionManager


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message,media",
    [
        ("", None),
        (" \t\n", []),
        ("", ["   "]),
        (" ", ["", "\t", "\n"]),
    ],
)
async def test_empty_push_has_no_session_or_runtime_side_effects(
    tmp_path, message, media
):
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
@pytest.mark.parametrize(
    "message,media,expected_media",
    [
        ("  hello\n", [" "], None),
        ("", [" ", "image.png", "\t"], ["image.png"]),
        ("caption", ["document.pdf"], ["document.pdf"]),
    ],
)
async def test_push_with_content_survives_reload(
    tmp_path, message, media, expected_media
):
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


@pytest.mark.asyncio
@pytest.mark.parametrize("pause_at", ["append_messages", "save_async"])
async def test_persist_user_message_keeps_identity_across_concurrent_append(
    tmp_path,
    monkeypatch,
    pause_at,
):
    manager = SessionManager(tmp_path)
    session = manager.get_or_create("role:mira")
    presence = Mock()
    relationship = Mock()
    relationship.enrich_session_metadata.return_value = {"relationship": "updated"}
    service = DesktopAppService(
        role_service=SimpleNamespace(),
        session_manager=manager,
        conversation_service=ConversationService(manager),
        presence=presence,
        relationship_runtime=relationship,
    )
    entered = asyncio.Event()
    resume = asyncio.Event()
    original_operation = getattr(manager, pause_at)
    append_messages = manager.append_messages

    async def paused_operation(*args):
        # Inject a scheduling boundary; this tests the async return contract,
        # without assuming the default persistence implementation yields here.
        entered.set()
        await resume.wait()
        await original_operation(*args)

    monkeypatch.setattr(manager, pause_at, paused_operation)
    task = asyncio.create_task(
        service.persist_desktop_user_message(
            session=session,
            role_id="mira",
            content="my message",
            media=["photo.png"],
            metadata={"client_message_id": "client-user", "turn_id": "turn-user"},
        )
    )
    try:
        await asyncio.wait_for(entered.wait(), timeout=2)
        user_message = session.messages[0]
        assert not task.done()
        session.add_message("assistant", "proactive reply", proactive=True)
        assistant_message = session.messages[-1]
        await append_messages(session, [assistant_message])
        resume.set()
        persisted = await asyncio.wait_for(task, timeout=2)
    finally:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    assert persisted is user_message
    assert persisted["id"] != assistant_message["id"]
    assert isinstance(persisted["seq"], int)
    assert persisted["role"] == "user"
    assert persisted["content"] == "my message"
    assert persisted["media"] == ["photo.png"]
    assert persisted["metadata"]["client_message_id"] == "client-user"
    assert persisted["metadata"]["turn_id"] == "turn-user"
    presence.record_user_message.assert_called_once_with(session.key)
    relationship.handle_user_message.assert_called_once_with(session.key)
    reloaded = SessionManager(tmp_path).get_or_create(session.key)
    assert reloaded.metadata["relationship"] == "updated"
    assert {message["id"] for message in reloaded.messages} == {
        persisted["id"],
        assistant_message["id"],
    }
