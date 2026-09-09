from __future__ import annotations

import pytest

from agent.plugin_host.effects import EffectScope


@pytest.mark.asyncio
async def test_dispose_all_runs_in_reverse_order():
    scope = EffectScope("demo")
    order: list[str] = []
    scope.add("a", lambda: order.append("a"))
    scope.add("b", lambda: order.append("b"))

    async def dispose_c():
        order.append("c")

    scope.add("c", dispose_c)

    errors = await scope.dispose_all()
    assert errors == []
    assert order == ["c", "b", "a"]


@pytest.mark.asyncio
async def test_dispose_error_collected_without_blocking_rest():
    scope = EffectScope("demo")
    order: list[str] = []
    scope.add("ok-first", lambda: order.append("first"))

    def broken():
        raise RuntimeError("cleanup boom")

    scope.add("broken", broken)
    scope.add("ok-last", lambda: order.append("last"))

    errors = await scope.dispose_all()
    assert [str(e) for e in errors] == ["cleanup boom"]
    # 失败不阻断其余清理，逆序继续
    assert order == ["last", "first"]


@pytest.mark.asyncio
async def test_add_after_dispose_rejected():
    scope = EffectScope("demo")
    await scope.dispose_all()
    with pytest.raises(RuntimeError, match="已处置"):
        scope.add("late", lambda: None)


@pytest.mark.asyncio
async def test_labels_report_registration_order():
    scope = EffectScope("demo")
    scope.add("one", lambda: None)
    scope.add("two", lambda: None)
    assert scope.labels == ["one", "two"]
