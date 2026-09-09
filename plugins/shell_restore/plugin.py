from __future__ import annotations

import logging
import os
import shlex
from pathlib import Path
from typing import TYPE_CHECKING

from agent.lifecycle.types import PreToolCtx
from agent.plugin_host.tool_hooks import PluginToolHook

if TYPE_CHECKING:
    from agent.plugin_host.runtime_context import PluginRuntimeContext

logger = logging.getLogger("plugin.shell_restore")

_PLUGIN_NAME = "shell_restore"


def _restore_dir() -> str:
    return os.environ.get("AKASIC_RESTORE_DIR", str(Path.home() / "restore"))


def rewrite_command(command: str) -> str | None:
    """把 `rm ...` 命令改写为 `mv -- targets... restore_dir`；非 rm 命令返回 None。

    模块级纯函数，供本插件的 pre-tool hook 与测试 fixture 共用同一份改写逻辑。
    """
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return None
    if not tokens:
        return None
    # 读取 rm 前面的前缀（sudo、env、VAR=val 等）
    prefix: list[str] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if Path(token).name == "rm":
            break
        if token == "sudo" or token == "env" or "=" in token:
            prefix.append(token)
            i += 1
            continue
        return None
    if i >= len(tokens) or Path(tokens[i]).name != "rm":
        return None
    # 跳过 rm 名字本身
    i += 1
    # 跳过 rm 选项，收集目标路径
    targets: list[str] = []
    parsing_options = True
    while i < len(tokens):
        token = tokens[i]
        i += 1
        if parsing_options and token == "--":
            parsing_options = False
            continue
        if parsing_options and token.startswith("-") and token != "-":
            continue
        parsing_options = False
        targets.append(token)
    if not targets:
        return None
    # 改写为 mv -- targets... restore_dir
    parts = [*prefix, "mv", "--"]
    parts.extend(targets)
    parts.append(_restore_dir())
    return shlex.join(parts)


async def rewrite_rm_to_mv(event: PreToolCtx) -> dict[str, object] | None:
    """shell 工具的 pre-tool hook：命中 rm 时改写为 mv 并确保 restore 目录存在。"""
    command = str(event.arguments.get("command", "")).strip()
    rewritten = rewrite_command(command)
    if rewritten is None:
        return None
    Path(_restore_dir()).mkdir(parents=True, exist_ok=True)
    logger.info("[%s:rewrite_rm_to_mv] rm → mv: %r", _PLUGIN_NAME, rewritten)
    return dict(event.arguments, command=rewritten)


async def setup(ctx: "PluginRuntimeContext") -> None:
    """装配 shell_restore：注册 shell 工具的 rm→mv pre-tool hook。"""
    ctx.tool_hooks.add(
        PluginToolHook(
            name=f"plugin:{_PLUGIN_NAME}:rewrite_rm_to_mv",
            handler=rewrite_rm_to_mv,
            tool_name_filter="shell",
        )
    )
