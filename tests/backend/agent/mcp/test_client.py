from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import agent.mcp.client as mcp_client_module

from agent.mcp.client import McpClient, McpToolError, _infer_cwd


class _Pipe:
    def __init__(
        self, lines: list[bytes] | None = None, *, block_on_eof: bool = False
    ) -> None:
        self._lines = list(lines or [])
        # 行读完后是否一直挂起（模拟仍然存活、暂时没有输出的真实流）
        self._block_on_eof = block_on_eof
        self.writes: list[bytes] = []

    def write(self, data: bytes) -> None:
        self.writes.append(data)

    async def drain(self) -> None:
        return None

    async def readline(self) -> bytes:
        if self._lines:
            return self._lines.pop(0)
        if self._block_on_eof:
            await asyncio.Event().wait()
        return b""


class _Proc:
    def __init__(
        self,
        stdout_lines: list[bytes],
        stderr_lines: list[bytes] | None = None,
        *,
        with_stderr: bool = True,
        stderr_blocks: bool = False,
    ) -> None:
        self.stdin = _Pipe()
        self.stdout = _Pipe(stdout_lines)
        self.stderr: _Pipe | None = (
            _Pipe(stderr_lines, block_on_eof=stderr_blocks) if with_stderr else None
        )
        self.terminated = False

    def terminate(self) -> None:
        self.terminated = True

    async def wait(self) -> None:
        return None


@pytest.mark.asyncio
async def test_mcp_client_and_loop_factory_cover_core_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    script = tmp_path / "server.py"
    script.write_text("print(1)", encoding="utf-8")
    assert _infer_cwd(["python", str(script)]) == str(tmp_path)
    assert _infer_cwd(["python", "srv.py"]) is None

    proc = _Proc(
        [
            b'{"jsonrpc":"2.0","id":1,"result":{}}\n',
            b'{"jsonrpc":"2.0","method":"note"}\n',
            b'{"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"tool1","description":"desc","inputSchema":{"type":"object"}}]}}\n',
            b"not json\n",
            b'{"jsonrpc":"2.0","id":3,"result":{"content":[{"text":"ok"}]}}\n',
        ],
        [b"warn\n", b""],
    )
    monkeypatch.setattr(
        "agent.mcp.client.asyncio.create_subprocess_exec", AsyncMock(return_value=proc)
    )
    client = McpClient("docs", ["python", str(script)], env={"X": "1"})
    infos = await client.connect()
    assert infos[0].name == "tool1"
    assert proc.stdin.writes
    assert await client.call("tool1", {"q": "x"}) == "ok"
    await client.disconnect()
    assert proc.terminated is True

    error_proc = _Proc(
        [
            b'{"jsonrpc":"2.0","id":1,"error":{"code":-32602,"message":"bad args","data":{"field":"q"}}}\n'
        ]
    )
    error_client = McpClient("docs", ["python", str(script)])
    error_client._process = error_proc
    with pytest.raises(McpToolError) as exc_info:
        await error_client.call("tool1", {"q": "x"})
    assert exc_info.value.code == -32602
    assert exc_info.value.data == {"field": "q"}
    assert exc_info.value.server == "docs"
    assert exc_info.value.tool_name == "tool1"

    proc = _Proc([b""])
    monkeypatch.setattr(
        "agent.mcp.client.asyncio.create_subprocess_exec", AsyncMock(return_value=proc)
    )
    client = McpClient("docs", ["python", str(script)])
    client._process = proc
    with pytest.raises(ConnectionError):
        await client._recv(expected_id=1)


@pytest.mark.asyncio
async def test_mcp_recv_timeout_includes_stage_and_recent_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    script = tmp_path / "server.py"
    script.write_text("print(1)", encoding="utf-8")
    proc = _Proc([])
    client = McpClient("docs", ["python", str(script)])
    client._process = proc
    client._recent_stdout.append('{"jsonrpc":"2.0","method":"note"}')
    client._recent_stderr.append("GitHub MCP Server running on stdio")

    async def raise_timeout(awaitable, *args, **kwargs):
        awaitable.close()
        raise asyncio.TimeoutError

    monkeypatch.setattr(mcp_client_module.asyncio, "wait_for", raise_timeout)
    with pytest.raises(TimeoutError) as exc:
        await client._recv(expected_id=1, stage="initialize", timeout=12.0)
    text = str(exc.value)
    assert "initialize" in text
    assert "12s" in text
    assert "expected_id=1" in text
    assert "recent_stderr=GitHub MCP Server running on stdio" in text


_HANDSHAKE_LINES = [
    b'{"jsonrpc":"2.0","id":1,"result":{}}\n',
    b'{"jsonrpc":"2.0","id":2,"result":{"tools":[]}}\n',
]


@pytest.mark.asyncio
async def test_mcp_connect_fails_when_stderr_unavailable(
    monkeypatch: pytest.MonkeyPatch,
):
    """stderr 不可用时 connect() 必须报错，而不是把异常留给后台任务。"""
    proc = _Proc(_HANDSHAKE_LINES, with_stderr=False)
    monkeypatch.setattr(
        "agent.mcp.client.asyncio.create_subprocess_exec", AsyncMock(return_value=proc)
    )
    client = McpClient("docs", ["python", "srv.py"])
    with pytest.raises(RuntimeError, match="stderr"):
        await client.connect()
    assert client._stderr_task is None


@pytest.mark.asyncio
async def test_mcp_disconnect_leaves_no_pending_stderr_task(
    monkeypatch: pytest.MonkeyPatch,
):
    """disconnect() 返回后 stderr 排空任务必须已经结束且不再被持有。"""
    # stderr 读完后继续挂起，排空协程只能靠 disconnect() 收掉。
    proc = _Proc(_HANDSHAKE_LINES, [b"warn\n"], stderr_blocks=True)
    monkeypatch.setattr(
        "agent.mcp.client.asyncio.create_subprocess_exec", AsyncMock(return_value=proc)
    )
    client = McpClient("docs", ["python", "srv.py"])
    _ = await client.connect()
    task = client._stderr_task
    assert task is not None
    assert not task.done()

    await client.disconnect()
    assert client._stderr_task is None
    assert task.done()


@pytest.mark.asyncio
async def test_mcp_stderr_drain_logs_failure_instead_of_swallowing(
    caplog: pytest.LogCaptureFixture,
):
    """排空过程中的异常必须留下 warning，不能被静默吞掉。"""

    class _BrokenStream:
        async def readline(self) -> bytes:
            raise OSError("stream closed")

    client = McpClient("docs", ["python", "srv.py"])
    with caplog.at_level(logging.WARNING, logger="agent.mcp.client"):
        await client._drain_stderr(_BrokenStream())

    assert "stream closed" in caplog.text


@pytest.mark.asyncio
async def test_mcp_stderr_drain_survives_undecodable_output():
    """非 UTF-8 的 stderr 不能中断排空循环，否则子进程会被写满的管道卡住。"""
    stream = _Pipe([b"\xff\xfe bad\n", b"after\n", b""])
    client = McpClient("docs", ["python", "srv.py"])

    await client._drain_stderr(stream)

    assert list(client._recent_stderr)[-1] == "after"
