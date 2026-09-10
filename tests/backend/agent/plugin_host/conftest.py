"""plugin_host 测试共享设施：全局 registry 清理与内核构造助手。"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

# 预热 agent.core 导入链，避免 agent.lifecycle.types 触发循环导入
from agent.core.passive_turn import ContextStore as _  # noqa: F401
from agent.lifecycle.types import BeforeTurnCtx
from agent.plugin_host import HostServices, PluginKernel
from agent.plugins.registry import plugin_registry
from agent.tools.registry import ToolRegistry
from bus.event_bus import EventBus

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]

# 夹具布局适配归仓库根 conftest 所有，两棵测试树共用同一份实现
from conftest import stage_plugin_fixture as stage_plugin_fixture


@pytest.fixture(autouse=True)
def _clean_registry():
    # 每个测试前后清空全局 registry，避免插件状态跨测试污染
    import sys

    modules_before = set(sys.modules)
    plugin_registry._handlers._handlers.clear()
    plugin_registry._classes.clear()
    plugin_registry._instances.clear()
    yield
    plugin_registry._handlers._handlers.clear()
    plugin_registry._classes.clear()
    plugin_registry._instances.clear()
    # 本测试期间导入的插件模块必须移除，避免污染旧 manager 测试的 sys.modules 查找
    for name in set(sys.modules) - modules_before:
        if name.startswith("akasic_plugin_"):
            _ = sys.modules.pop(name, None)


def make_kernel(
    plugin_dirs: list[Path],
    *,
    event_bus: EventBus,
    tools: ToolRegistry | None = None,
    namespace: str = "",
    strict: bool = False,
    plugin_configs: dict[str, dict] | None = None,
    workspace: Path | None = None,
) -> PluginKernel:
    # 插件数据落在 workspace 而非插件目录（issue #209），而 legacy 适配器会为每个
    # 插件装配 kv，因此夹具默认提供一个可写 workspace。这里刻意不复用
    # plugin_dirs[0]：workspace 若等于插件扫描根，"数据不写插件目录"这类断言即使
    # 内核实现改成直接从插件目录派生 workspace 也不会失败，隔离测试就失去了意义。
    # 独立的临时目录才能真正证明 kv/config 走的是宿主传入的 workspace。
    resolved_workspace = workspace
    if resolved_workspace is None:
        resolved_workspace = Path(
            tempfile.mkdtemp(prefix="shiori-plugin-host-test-workspace-")
        )
    return PluginKernel(
        plugin_dirs,
        services=HostServices(
            event_bus=event_bus,
            tool_registry=tools,
            plugin_configs=plugin_configs or {},
            workspace=resolved_workspace,
        ),
        namespace=namespace,
        strict=strict,
    )


def before_turn_ctx(**overrides: object) -> BeforeTurnCtx:
    defaults: dict = dict(
        session_key="test:123",
        channel="cli",
        chat_id="123",
        content="hello",
        timestamp=datetime.now(),
        retrieved_memory_block="",
        retrieval_trace_raw=None,
        history_messages=(),
    )
    defaults.update(overrides)
    return BeforeTurnCtx(**defaults)
