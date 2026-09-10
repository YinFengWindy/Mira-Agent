from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from agent.mcp.registry import McpServerRegistry


@pytest.mark.asyncio
async def test_registry_add_list_remove_and_reload_from_disk(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    class _Client:
        def __init__(self, name: str, command: list[str], env=None, cwd=None):
            self.name = name
            self.command = command
            self.env = env
            self.cwd = cwd

        async def connect(self):
            return [SimpleNamespace(name="mcp_tool", description="Read remote docs")]

        async def disconnect(self):
            return None

    class _Wrapper:
        def __init__(self, client, info):
            self.client = client
            self.info = info
            self.name = f"{client.name}:{info.name}"
            self.description = info.description
            self.parameters = {"type": "object", "properties": {}, "required": []}

        def to_schema(self):
            return {"type": "function", "function": {"name": self.name}}

    monkeypatch.setattr("agent.mcp.registry.McpClient", _Client)
    monkeypatch.setattr("agent.mcp.registry.McpToolWrapper", _Wrapper)
    tools = MagicMock()
    registry = McpServerRegistry(tmp_path / "mcp.json", tools)
    added = await registry.add("docs", ["python", "srv.py"], env={"K": "V"}, cwd="/tmp")
    assert "已连接 MCP server 'docs'" in added
    tools.register.assert_called_once()
    assert "docs（1 个工具）" in registry.list_servers()
    assert "不存在" in await registry.remove("missing")
    assert "已注销" in await registry.remove("docs")

    (tmp_path / "mcp.json").write_text("{bad", encoding="utf-8")
    assert registry._load_raw_configs() == {}
    (tmp_path / "mcp.json").write_text(
        json.dumps({"servers": {"docs": {"command": ["x"]}}}), encoding="utf-8"
    )
    await registry.load_and_connect_all()
