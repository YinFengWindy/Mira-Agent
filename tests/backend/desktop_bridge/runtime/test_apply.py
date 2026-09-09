"""RuntimeSettingsApplication.build_config_toml：派生文本必须在事务锁内计算。"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from agent.config import load_config_text
from bootstrap.app import AppRuntime, RuntimeFeatures
from core.roles.store import RoleStore
from desktop_bridge.runtime.apply import RuntimeSettingsApplication


def _config(*, optimizer: bool) -> str:
    # optimizer 取值不同会让 Config 真的不相等，从而走 prepare/publish 异步慢路径；
    # 若两份配置相等，apply 会同步提交、根本不让出控制权，测试就失去区分度。
    return (
        "[llm]\nregistrations = []\n"
        f"\n[agent.maintenance]\nmemory_optimizer_enabled = {str(optimizer).lower()}\n"
        '\n[proactive]\nenabled = false\nprofile = "quiet"\n'
    )


@pytest.mark.asyncio
async def test_build_config_toml_sees_the_text_committed_by_a_queued_apply(tmp_path: Path):
    """并发的 runtime.apply 先提交时，派生回调必须看到它提交后的文本。

    插件配置写入只改一张表、其余文本沿用当前已提交的配置。如果基准文本在事务锁
    外读取，一个刚刚落地的 runtime.apply 会被整份覆盖掉——用户的设置静默丢失。
    这里让两次 apply 排队，断言后一次的派生回调拿到的是前一次的提交结果。
    """
    original = _config(optimizer=False)
    updated = _config(optimizer=True)
    path = tmp_path / "config.toml"
    path.write_text(original, encoding="utf-8")
    app = AppRuntime(
        load_config_text(original), tmp_path,
        features=RuntimeFeatures(enable_message_channels=False, enable_proactive=False),
    )
    await app.start()
    settings = RuntimeSettingsApplication(app, path, RoleStore(tmp_path))
    try:
        seen: list[str] = []
        # 用闸门把第一次 apply 钉在 prepare 上，制造确定性的交错，不依赖调度顺序
        gate = asyncio.Event()
        original_prepare = app.prepare

        async def _gated_prepare(config):
            await gate.wait()
            return await original_prepare(config)

        app.prepare = _gated_prepare

        async def _first() -> None:
            await settings.apply(
                {"config_toml": updated, "operation_id": "first"},
                prepare_service=lambda core: None,
                publish_service=lambda service: None,
            )

        async def _second() -> None:
            def _derive(current: str) -> str:
                seen.append(current)
                return current

            await settings.apply(
                {"operation_id": "second"},
                prepare_service=lambda core: None,
                publish_service=lambda service: None,
                build_config_toml=_derive,
            )

        first = asyncio.create_task(_first())
        # 第一次 apply 拿到锁后停在闸门上
        for _ in range(5):
            await asyncio.sleep(0)
        second = asyncio.create_task(_second())
        # 给第二次 apply 充分的机会：修复到位时它应当阻塞在锁上而不是立刻派生
        for _ in range(5):
            await asyncio.sleep(0)
        assert not seen, "派生回调在第一次 apply 提交之前就跑了，说明它不在事务锁内"
        gate.set()
        await asyncio.gather(first, second)

        assert seen, "派生回调没有被调用"
        assert seen[0] == updated, (
            "派生回调看到的是陈旧文本，说明合并发生在事务锁之外，"
            "并发的 runtime.apply 会被静默覆盖"
        )
    finally:
        await app.shutdown()
