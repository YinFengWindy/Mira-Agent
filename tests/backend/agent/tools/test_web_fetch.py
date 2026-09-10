from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from agent.tools.web_fetch import (
    WebFetchTool,
    _to_markdown,
    _to_text,
    _validate_url_target,
)

_HTML = b"<html><body><script>x</script><p>Hello <b>world</b></p></body></html>"


class _Resp:
    def __init__(
        self,
        *,
        status=200,
        headers=None,
        content=b"",
        encoding="utf-8",
        url="https://x",
    ):
        self.status_code = status
        self.headers = headers or {}
        self.content = content
        self.encoding = encoding
        self.url = url


def _tool_returning(resp_or_error) -> WebFetchTool:
    requester = MagicMock()
    if isinstance(resp_or_error, BaseException):
        requester.get = AsyncMock(side_effect=resp_or_error)
    else:
        requester.get = AsyncMock(return_value=resp_or_error)
    return WebFetchTool(requester=requester)


@pytest.mark.asyncio
async def test_web_fetch_renders_text_and_markdown():
    tool = _tool_returning(
        _Resp(
            headers={"content-type": "text/html", "content-length": "20"},
            content=_HTML,
        )
    )

    text_result = json.loads(
        await tool.execute(url="https://example.com", format="text")
    )
    markdown_result = json.loads(
        await tool.execute(url="https://example.com", format="markdown")
    )

    assert text_result["text"] == "Hello world"
    assert "Hello" in markdown_result["text"]


@pytest.mark.asyncio
async def test_web_fetch_reports_http_error_binary_timeout_and_bad_scheme():
    not_found = _tool_returning(_Resp(status=404))
    binary = _tool_returning(_Resp(headers={"content-type": "application/pdf"}))
    slow = _tool_returning(httpx.TimeoutException("slow"))

    assert (
        "HTTP 404"
        in json.loads(await not_found.execute(url="https://example.com"))["error"]
    )
    assert (
        "二进制内容"
        in json.loads(await binary.execute(url="https://example.com"))["error"]
    )
    assert (
        "请求超时" in json.loads(await slow.execute(url="https://example.com"))["error"]
    )
    assert (
        "http:// 或 https://" in json.loads(await slow.execute(url="ftp://x"))["error"]
    )


def test_web_fetch_helpers_strip_markup_and_flag_intranet():
    assert _validate_url_target("http://127.0.0.1")
    assert _to_text(b"<html><body><style>x</style><p>Hi</p></body></html>") == "Hi"
    assert "Title" in _to_markdown("<h1>Title</h1>")
