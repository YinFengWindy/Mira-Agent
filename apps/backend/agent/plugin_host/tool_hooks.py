"""共享工具 hook 适配器：把插件的函数式 pre-hook 适配为 ToolExecutor.ToolHook。

legacy 适配器与 v2 插件都需要这份逻辑（旧 ``@on_tool_pre`` 装饰器、v2 ``setup(ctx)``
里手写注册的 hook），提升到这里避免每个插件各写一份 matches/run。
"""

from __future__ import annotations

import inspect
from typing import Any, cast

from agent.lifecycle.types import PreToolCtx
from agent.tool_hooks.base import ToolHook
from agent.tool_hooks.types import HookContext, HookOutcome


def build_hook_name(plugin_id: str, handler_name: str) -> str:
    """生成插件 tool hook 的注册名：``plugin:{plugin_id}:{handler_name}``。

    与旧系统 ``f"plugin:{instance.name}:{md.handler_name}"`` 逐字一致；
    v2 插件经 ``ToolHooksCapability.add_handler``、legacy 适配器都复用这一份，
    避免各处各拼一份同形式的字符串（#182 评审）。
    """
    return f"plugin:{plugin_id}:{handler_name}"


class PluginToolHook(ToolHook):
    """将插件的 pre-tool handler 适配为 ToolExecutor 的 ToolHook 接口。"""

    event = "pre_tool_use"

    def __init__(
        self,
        name: str,
        handler: Any,
        tool_name_filter: str | None = None,
    ) -> None:
        self.name = name
        self._handler = handler
        self._tool_name_filter = tool_name_filter

    def matches(self, ctx: HookContext) -> bool:
        if self._tool_name_filter is None:
            return True
        return ctx.request.tool_name == self._tool_name_filter

    async def run(self, ctx: HookContext) -> HookOutcome:
        # 1. 构造 PreToolCtx（复制 arguments，避免插件直接改原对象）
        event = PreToolCtx(
            session_key=ctx.request.session_key,
            channel=ctx.request.channel,
            chat_id=ctx.request.chat_id,
            tool_name=ctx.request.tool_name,
            arguments=dict(ctx.current_arguments),
            call_id=ctx.request.call_id,
            source=ctx.request.source,
            request_text=ctx.request.request_text,
            tool_batch=ctx.request.tool_batch,
            tool_batch_index=ctx.request.tool_batch_index,
        )
        # 2. 调插件 handler，返回值决定行为
        result = self._handler(event)
        if inspect.isawaitable(result):
            result = await result
        # 3. None → 不改参；dict → 新 arguments；HookOutcome → 允许插件直接 deny
        if result is None:
            return HookOutcome()
        if isinstance(result, HookOutcome):
            return result
        if isinstance(result, dict):
            return HookOutcome(updated_input=cast("dict[str, Any]", result))
        return HookOutcome()
