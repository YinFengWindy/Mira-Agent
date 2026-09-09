from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from agent.lifecycle.types import PreToolCtx
from agent.plugin_host.tool_hooks import PluginToolHook
from agent.tool_hooks import HookOutcome

if TYPE_CHECKING:
    from agent.plugin_host.runtime_context import PluginRuntimeContext

_DEFAULT_REPEAT_LIMIT = 3
_DENY_PREFIX = "tool_loop_guard:"
_EXCLUDED_TOOLS = frozenset({"task_output", "task_stop"})
_PLUGIN_NAME = "tool_loop_guard"


@dataclass
class _LoopState:
    signature: str = ""
    repeat_count: int = 0


class _ToolLoopGuard:
    """检测连续重复的工具调用并提前截断；v2 插件不再继承旧 Plugin ABC。"""

    def __init__(self, repeat_limit: int) -> None:
        self._states: dict[str, _LoopState] = {}
        self._repeat_limit = repeat_limit

    async def detect_repeated_tool_call(self, event: PreToolCtx) -> HookOutcome | None:
        signature, active_index = self._event_signature(event)
        if not signature or event.tool_batch_index != active_index:
            return None
        state_key = self._state_key(event)
        state = self._states.setdefault(state_key, _LoopState())
        if signature == state.signature:
            state.repeat_count += 1
        else:
            state.signature = signature
            state.repeat_count = 1
        if state.repeat_count < self._repeat_limit:
            return None
        return HookOutcome(
            decision="deny",
            reason=(
                f"{_DENY_PREFIX}连续重复调用工具 "
                f"{state.repeat_count} 次，已截断并进入收尾。"
            ),
        )

    def _state_key(self, event: PreToolCtx) -> str:
        if event.session_key:
            return f"{event.source}:{event.session_key}"
        return f"{event.source}:{event.channel}:{event.chat_id}"

    def _signature(self, tool_name: str, arguments: dict[str, Any]) -> str:
        args = json.dumps(arguments, ensure_ascii=False, sort_keys=True)
        return f"{tool_name}:{args}"

    def _event_signature(self, event: PreToolCtx) -> tuple[str, int]:
        if not event.tool_batch:
            if event.tool_name in _EXCLUDED_TOOLS:
                return "", 0
            return self._signature(event.tool_name, event.arguments), 0

        parts: list[str] = []
        active_index = -1
        for index, tool_call in enumerate(event.tool_batch):
            tool_name = str(tool_call.get("name", ""))
            if tool_name in _EXCLUDED_TOOLS:
                continue
            arguments = tool_call.get("arguments")
            if not isinstance(arguments, dict):
                arguments = {}
            if active_index < 0:
                active_index = index
            parts.append(self._signature(tool_name, cast("dict[str, Any]", arguments)))
        if active_index < 0:
            return "", 0
        return "|".join(parts), active_index


async def setup(ctx: "PluginRuntimeContext") -> None:
    """装配 tool_loop_guard：读取 repeat_limit 配置，注册 pre-tool hook。"""
    raw_limit = ctx.config.get("repeat_limit", _DEFAULT_REPEAT_LIMIT)
    try:
        repeat_limit = max(2, int(raw_limit))
    except (TypeError, ValueError):
        repeat_limit = _DEFAULT_REPEAT_LIMIT
    guard = _ToolLoopGuard(repeat_limit)
    ctx.tool_hooks.add(
        PluginToolHook(
            name=f"plugin:{_PLUGIN_NAME}:detect_repeated_tool_call",
            handler=guard.detect_repeated_tool_call,
        )
    )
