from __future__ import annotations

import json

import pytest

from agent.tools.web_search import WebSearchTool


@pytest.mark.asyncio
async def test_web_search_covers_filters(monkeypatch: pytest.MonkeyPatch):
    class _Response:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    class _Client:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url: str, json: dict, headers: dict) -> _Response:
            assert json["params"]["arguments"]["numResults"] == 20
            assert json["params"]["arguments"]["livecrawl"] == "preferred"
            assert json["params"]["arguments"]["type"] == "deep"
            return _Response(
                'data: {"result":{"content":[{"text":"hello world"}]}}\n\n'
            )

    monkeypatch.setattr("httpx.AsyncClient", _Client)
    result = json.loads(
        await WebSearchTool().execute(
            query="搜索 网络",
            num_results=99,
            livecrawl="preferred",
            type="deep",
        )
    )
    assert result["result"] == "hello world"

    class _BadClient(_Client):
        async def post(self, url: str, json: dict, headers: dict) -> _Response:
            raise RuntimeError("net down")

    monkeypatch.setattr("httpx.AsyncClient", _BadClient)
    result = json.loads(await WebSearchTool().execute(query="x"))
    assert "搜索失败" in result["error"]

    class _EmptyClient(_Client):
        async def post(self, url: str, json: dict, headers: dict) -> _Response:
            return _Response("data: not-json\n\ndata: {}")

    monkeypatch.setattr("httpx.AsyncClient", _EmptyClient)
    result = json.loads(await WebSearchTool().execute(query="x"))
    assert result["count"] == 0
