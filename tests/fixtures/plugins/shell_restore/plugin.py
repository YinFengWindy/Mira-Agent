from __future__ import annotations

from agent.lifecycle.types import PreToolCtx
from agent.plugins import Plugin, on_tool_pre
from plugins.shell_restore.backend.plugin import rewrite_rm_to_mv as _rewrite_rm_to_mv


class ShellRestore(Plugin):
    """legacy PluginManager 机制测试专用：复用真实 shell_restore 的改写逻辑，

    仅补一层 @on_tool_pre 装饰器以驱动旧 registry/manager 路径。
    """

    name = "shell_restore"

    @on_tool_pre(tool_name="shell")
    async def rewrite_rm_to_mv(self, event: PreToolCtx) -> dict[str, object] | None:
        return await _rewrite_rm_to_mv(event)


__all__ = ["ShellRestore"]
