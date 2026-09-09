from __future__ import annotations

import asyncio
import os
import shlex
import shutil
from pathlib import Path
from typing import Any

from agent.plugin_host import HostServices, PluginKernel
from agent.tool_hooks import ToolExecutionRequest, ToolExecutor
from bus.event_bus import EventBus

PLUGIN_DIR = Path(__file__).resolve().parents[3] / "plugins" / "shell_restore"


async def _invoke(tool_name: str, arguments: dict[str, Any]) -> Any:
    return {"tool": tool_name, "arguments": dict(arguments)}


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _make_plugin_root(tmp_path: Path) -> Path:
    root = tmp_path / "plugins"
    root.mkdir()
    shutil.copytree(PLUGIN_DIR, root / "shell_restore")
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


def test_shell_rm_hook_rewrites_rm_and_creates_restore_dir(tmp_path: Path) -> None:
    restore_dir = tmp_path / "restore"
    os.environ["AKASIC_RESTORE_DIR"] = str(restore_dir)
    try:
        result = _run_shell(_make_plugin_root(tmp_path), "rm -rf foo bar")

        assert result.status == "success"
        assert restore_dir.is_dir()
        assert shlex.split(result.final_arguments["command"]) == [
            "mv",
            "--",
            "foo",
            "bar",
            str(restore_dir),
        ]
        assert shlex.split(result.output["arguments"]["command"]) == [
            "mv",
            "--",
            "foo",
            "bar",
            str(restore_dir),
        ]
    finally:
        os.environ.pop("AKASIC_RESTORE_DIR", None)


def test_shell_rm_hook_rewrites_sudo_rm(tmp_path: Path) -> None:
    restore_dir = tmp_path / "restore"
    os.environ["AKASIC_RESTORE_DIR"] = str(restore_dir)
    try:
        result = _run_shell(_make_plugin_root(tmp_path), "sudo rm -f /tmp/a")

        assert result.status == "success"
        assert shlex.split(result.final_arguments["command"]) == [
            "sudo",
            "mv",
            "--",
            "/tmp/a",
            str(restore_dir),
        ]
    finally:
        os.environ.pop("AKASIC_RESTORE_DIR", None)


def test_shell_rm_hook_skips_non_rm_command(tmp_path: Path) -> None:
    restore_dir = tmp_path / "restore"
    os.environ["AKASIC_RESTORE_DIR"] = str(restore_dir)
    try:
        result = _run_shell(_make_plugin_root(tmp_path), "ls -la")

        assert result.status == "success"
        assert not restore_dir.exists()
        assert result.final_arguments["command"] == "ls -la"
    finally:
        os.environ.pop("AKASIC_RESTORE_DIR", None)
