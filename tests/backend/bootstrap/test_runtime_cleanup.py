import pytest

from bootstrap.runtime_cleanup import run_cleanup_steps


@pytest.mark.asyncio
async def test_cleanup_continues_after_failure_and_reports_error():
    calls = []

    async def fail():
        calls.append("fail")
        raise RuntimeError("stop failed")

    async def cleanup():
        calls.append("cleanup")

    with pytest.raises(RuntimeError, match="stop failed"):
        await run_cleanup_steps(("fail", fail), ("cleanup", cleanup))
    assert calls == ["fail", "cleanup"]
