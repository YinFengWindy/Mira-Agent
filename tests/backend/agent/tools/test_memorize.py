from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.tools.memorize import MemorizeTool
from memory2.memorizer import Memorizer
from memory2.store import MemoryStore2
from plugins.default_memory.backend.engine import DefaultMemoryEngine


def _make_default_engine(
    *,
    retriever=None,
    memorizer=None,
    tagger=None,
):
    engine = DefaultMemoryEngine.__new__(DefaultMemoryEngine)
    engine._config = None
    engine._workspace = Path(".")
    engine._provider = None
    engine._light_provider = None
    engine._light_model = ""
    engine._v1_store = None
    engine._v2_store = None
    engine._embedder = None
    engine._memorizer = memorizer
    engine._retriever = retriever
    engine._tagger = tagger
    engine._post_response_worker = None
    engine._event_bus = None
    engine._consolidation = None
    engine.closeables = []
    return engine


def _memorize_tool(engine) -> MemorizeTool:
    spec = engine.tool_profile().memorize
    assert spec is not None
    return MemorizeTool(engine, spec)


@pytest.mark.asyncio
async def test_memorize_tool_cover_branches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    memorizer = MagicMock()
    memorizer.save_item_with_supersede = AsyncMock(return_value="new:mem-1")

    class _Tagger:
        async def tag(self, summary: str) -> dict[str, str]:
            assert summary == "记住这条流程"
            return {"scope": "task"}

    tool = _memorize_tool(
        _make_default_engine(
            retriever=MagicMock(),
            memorizer=memorizer,
            tagger=cast(Any, _Tagger()),
        )
    )
    result = await tool.execute(
        summary="记住这条流程",
        memory_kind="procedure",
        steps=["先查", "再做"],
        role_id="mira",
    )

    payload = json.loads(result)
    assert payload["item_id"] == "mem-1"
    assert payload["status"] == "new"
    extra = memorizer.save_item_with_supersede.await_args.kwargs["extra"]
    assert extra["trigger_tags"] == {"scope": "task"}
    assert extra["rule_schema"]["required_tools"] == []
    assert extra["rule_schema"]["forbidden_tools"] == []

    class _BadTagger:
        async def tag(self, summary: str) -> dict[str, str]:
            raise RuntimeError("bad")

    bad = _memorize_tool(
        _make_default_engine(
            retriever=MagicMock(),
            memorizer=memorizer,
            tagger=cast(Any, _BadTagger()),
        )
    )
    await bad.execute(summary="普通偏好", memory_kind="procedure", role_id="mira")
    await bad.execute(summary="偏好", memory_kind="preference", role_id="mira")


@pytest.mark.asyncio
async def test_memorize_tool_should_not_create_second_active_procedure_when_incremental_update():
    class _Embedder:
        async def embed(self, text: str) -> list[float]:
            return [1.0, 0.0]

    store = MemoryStore2(":memory:")
    memorizer = Memorizer(store, cast(Any, _Embedder()))
    tool = _memorize_tool(
        _make_default_engine(
            retriever=MagicMock(),
            memorizer=memorizer,
        )
    )

    await memorizer.save_item(
        summary="查询 Steam 游戏信息时，必须先使用 steam_mcp 工具查询游戏详情，再用 web_search 补充验证价格和评价信息。",
        memory_type="procedure",
        extra={
            "steps": [
                "使用 steam_mcp 工具查询游戏详情",
                "使用 web_search 补充验证价格和评价",
            ],
            "tool_requirement": "steam_mcp",
            "role_id": "mira",
        },
        source_ref="seed",
    )

    await tool.execute(
        summary="查询 Steam 游戏信息时，先判断区服（大陆区/港区/美区），再使用 steam_mcp 工具查询游戏详情。",
        memory_kind="procedure",
        tool_requirement="steam_mcp",
        steps=["判断目标区服", "使用 steam_mcp 工具查询游戏详情"],
        role_id="mira",
    )

    rows = store._db.execute(
        "SELECT id, summary FROM memory_items WHERE memory_type='procedure' AND status='active'"
    ).fetchall()
    assert len(rows) == 1
    assert "steam_mcp" in rows[0][1]
    assert "区服" in rows[0][1]


@pytest.mark.asyncio
async def test_memorize_tool_should_coerce_language_reply_rule_to_preference():
    memorizer = MagicMock()
    memorizer.save_item_with_supersede = AsyncMock(return_value="new:mem-1")
    tool = _memorize_tool(
        _make_default_engine(
            retriever=MagicMock(),
            memorizer=memorizer,
        )
    )

    await tool.execute(
        summary="之后跟我说话只用中文，不要夹杂英文，专有名词也尽量翻译。",
        memory_kind="procedure",
        role_id="mira",
    )

    assert (
        memorizer.save_item_with_supersede.await_args.kwargs["memory_type"]
        == "preference"
    )
