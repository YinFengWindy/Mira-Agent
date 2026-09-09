from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any

from agent.plugin_host import HostServices, PluginKernel
from agent.tool_hooks import ToolExecutionRequest, ToolExecutor
from bus.event_bus import EventBus

PLUGIN_DIR = Path(__file__).resolve().parents[3] / "plugins" / "shell_safety"


async def _invoke(tool_name: str, arguments: dict[str, Any]) -> Any:
    return {"tool": tool_name, "arguments": dict(arguments)}


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _make_plugin_root(tmp_path: Path) -> Path:
    root = tmp_path / "plugins"
    root.mkdir()
    shutil.copytree(PLUGIN_DIR, root / "shell_safety")
    return root


def _run_shell(root: Path, command: str) -> Any:
    bus = EventBus()
    kernel = PluginKernel([root], services=HostServices(event_bus=bus))
    _run(kernel.load_all())
    return _run(
        ToolExecutor(kernel.tool_hooks).execute(
            ToolExecutionRequest(
                call_id="c1",
                tool_name="shell",
                arguments={"command": command, "description": "测试命令"},
                source="passive",
            ),
            _invoke,
        )
    )


def test_shell_safety_hook_name_matches_legacy_convention(tmp_path: Path) -> None:
    """hook 名由 ToolHooksCapability 统一生成，须与旧系统
    f"plugin:{instance.name}:{md.handler_name}" 逐字一致（#182 评审）。"""
    bus = EventBus()
    kernel = PluginKernel([_make_plugin_root(tmp_path)], services=HostServices(event_bus=bus))
    _run(kernel.load_all())

    assert [h.name for h in kernel.tool_hooks] == ["plugin:shell_safety:block_interactive_shell"]


def test_shell_safety_blocks_sudo_without_non_interactive(tmp_path: Path) -> None:
    result = _run_shell(_make_plugin_root(tmp_path), "sudo pacman -Syu --noconfirm")

    assert result.status == "denied"
    assert "sudo -n" in result.output


def test_shell_safety_blocks_interactive_editor(tmp_path: Path) -> None:
    result = _run_shell(_make_plugin_root(tmp_path), "sudo -n vim /etc/example.service")

    assert result.status == "denied"
    assert "vim" in result.output


def test_shell_safety_blocks_package_write_without_noconfirm(tmp_path: Path) -> None:
    result = _run_shell(_make_plugin_root(tmp_path), "pacman -Syu")

    assert result.status == "denied"
    assert "--noconfirm" in result.output


def test_shell_safety_allows_non_interactive_package_write(tmp_path: Path) -> None:
    result = _run_shell(_make_plugin_root(tmp_path), "sudo -n pacman -Syu --noconfirm")

    assert result.status == "success"
    assert result.final_arguments["command"] == "sudo -n pacman -Syu --noconfirm"


def test_shell_safety_allows_package_query(tmp_path: Path) -> None:
    result = _run_shell(_make_plugin_root(tmp_path), "pacman -Q")

    assert result.status == "success"
    assert result.final_arguments["command"] == "pacman -Q"
