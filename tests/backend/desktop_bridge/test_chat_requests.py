from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from desktop_bridge.chat_requests import DesktopChatRequestHandler
from desktop_bridge.session_presenter import DesktopSessionPresenter
from session.manager import Session


@pytest.mark.asyncio
async def test_send_serializes_returned_user_message_when_session_tail_has_changed():
    session = Session(key="role:mira")
    session.add_message(
        "user",
        "my message",
        id="user-id",
        seq=1,
        media=["photo.png"],
        metadata={"client_message_id": "client-user", "turn_id": "turn-user"},
    )
    persisted = session.messages[0]
    session.add_message("assistant", "proactive reply", id="assistant-id", seq=2)
    app_service = Mock()
    app_service.build_desktop_user_message_metadata.side_effect = (
        lambda metadata, **kwargs: metadata
    )
    app_service.persist_desktop_user_message = AsyncMock(return_value=persisted)
    role_service = Mock()
    role_service.open_role_async = AsyncMock(
        return_value=SimpleNamespace(
            role=SimpleNamespace(id="mira"),
            session=session,
        )
    )
    chat_service = Mock()
    chat_service.is_busy.return_value = False
    start_chat_turn = Mock()
    handler = DesktopChatRequestHandler(
        role_service=role_service,
        app_service=app_service,
        chat_service=chat_service,
        start_chat_turn=start_chat_turn,
        session_presenter=DesktopSessionPresenter(Mock()),
        sanitize_voice_metrics=Mock(),
    )
    emit_event = AsyncMock()

    response = await handler.handle(
        "chat.send",
        {
            "role_id": "mira",
            "content": "my message",
            "media": ["photo.png"],
            "client_message_id": "client-user",
            "turn_id": "turn-user",
        },
        request_id="request-user",
        emit_event=emit_event,
    )

    assert response["message"]["id"] == "user-id"
    assert response["message"]["seq"] == 1
    assert response["message"]["role"] == "user"
    assert response["message"]["content"] == "my message"
    assert response["message"]["media"] == ["photo.png"]
    assert response["message"]["metadata"]["client_message_id"] == "client-user"
    assert response["turn_id"] == "turn-user"
    assert response["session"]["key"] == session.key
    app_service.persist_desktop_user_message.assert_awaited_once()
    start_chat_turn.assert_called_once_with(
        request_id="request-user",
        turn_id="turn-user",
        session_key=session.key,
        content="my message",
        media=["photo.png"],
        metadata=app_service.persist_desktop_user_message.call_args.kwargs["metadata"],
        omit_user_turn=True,
        emit_event=emit_event,
    )
