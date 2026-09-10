"""plugin_host 测试共享设施：全局 registry 清理与内核构造助手。"""

from __future__ import annotations

import shutil
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
FIXTURES_DIR = REPOSITORY_ROOT / "tests" / "fixtures" / "plugins"


def stage_plugin_fixture(name: str, dest_root: Path) -> Path:
    """把扁平布局的测试夹具就地重整成内核要求的 `<id>/backend/` 布局。

    `tests/fixtures/plugins/` 服务的是旧 `PluginManager`（扁平 `plugin.py`），
    而 spec 要求那批存量测试**原样**通过，作为「迁移未破坏行为」的证据，所以
    夹具本身保持旧形状。新内核要求 backend/ 布局，由这里重整，避免同一份夹具
    在仓库里留两份逐字重复、日后必然分叉的副本。#184 删除旧系统后，夹具可以
    直接改成新布局，这个函数随之删除。

    只把 Python 源码（`*.py` 与含 `__init__.py` 的 Python 子包）下沉到
    `backend/`；其余一律留在包根——`manifest.yaml`、`plugin.disabled`、
    `_conf_schema.json` 这类包级文件是已知例子，但白名单方式在新增夹具文件
    时必须逐个更新，稍不注意就会把 `.kv.json` 这类非后端代码也错误下沉（曾经
    发生：`counter/.kv.json` 被当成后端代码搬进 `backend/`，夹具静默失真且
    不报错）。反过来按"是不是 Python 代码"判断更不容易漏。`__pycache__` 直接
    跳过，不管在包根还是子目录里。
    """

    target = dest_root / name
    shutil.copytree(FIXTURES_DIR / name, target, ignore=shutil.ignore_patterns("__pycache__"))
    backend = target / "backend"
    backend.mkdir(exist_ok=True)
    for item in sorted(target.iterdir()):
        if item.name == "backend":
            continue
        if _is_python_source(item):
            shutil.move(str(item), str(backend / item.name))
    return target


def _is_python_source(item: Path) -> bool:
    """判断一个包根条目是否属于后端 Python 代码，需要下沉到 `backend/`。"""

    if item.is_file():
        return item.suffix == ".py"
    if item.is_dir():
        return (item / "__init__.py").exists()
    return False


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
