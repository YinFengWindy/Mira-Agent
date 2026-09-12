from __future__ import annotations

from typing import TYPE_CHECKING, cast

from agent.lifecycle.types import BeforeTurnCtx, TurnState

if TYPE_CHECKING:
    from agent.plugin_host.runtime_context import PluginRuntimeContext


class ChatIdCommandModule:
    slot = "setup_helper.chatid"
    requires = ("before_turn.acquire_session", "session:session")
    produces = ("session:ctx",)

    async def run(self, frame: object) -> object:
        if "session:ctx" in frame.slots:  # type: ignore[attr-defined]
            return frame
        state: TurnState = frame.input  # type: ignore[attr-defined]
        if _normalize_command(state.msg.content) not in {"/chatid", "/myid"}:
            return frame
        chat_id = state.msg.chat_id or "（未知）"
        reply = _format_reply(chat_id, channel=state.msg.channel)
        frame.slots["session:ctx"] = _abort_ctx(state, reply)  # type: ignore[attr-defined]
        return frame


async def setup(ctx: "PluginRuntimeContext") -> None:
    """装配 setup_helper：贡献 before_turn 命令模块与 /chatid bot 命令。"""
    ctx.lifecycle.contribute(
        "before_turn", cast("list[object]", [ChatIdCommandModule()])
    )
    ctx.bot_commands.add("chatid", "查看我的 chat_id（配置 proactive 用）")


def _normalize_command(content: str) -> str:
    parts = (content or "").strip().split(maxsplit=1)
    if not parts:
        return ""
    head = parts[0].lower()
    if "@" in head:
        head = head.split("@", 1)[0]
    return head


def _format_reply(chat_id: str, channel: str = "telegram") -> str:
    lines = [
        f"你的 chat_id 是：`{chat_id}`",
        "",
        "将它填入 config.toml 即可开启主动推送：",
        "",
        "```toml",
        "[proactive]",
        "enabled = true",
        "",
        "[proactive.target]",
        f'channel = "{channel}"',
        f'chat_id = "{chat_id}"',
        "```",
    ]
    return "\n".join(lines)


def _abort_ctx(state: TurnState, reply: str) -> BeforeTurnCtx:
    return BeforeTurnCtx(
        session_key=state.session_key,
        channel=state.msg.channel,
        chat_id=state.msg.chat_id,
        content=state.msg.content,
        timestamp=state.msg.timestamp,
        skill_names=[],
        retrieved_memory_block="",
        retrieval_trace_raw=None,
        history_messages=(),
        abort=True,
        abort_reply=reply,
    )
