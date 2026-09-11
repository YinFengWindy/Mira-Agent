"""Host legacy plugin-fixture layout adapter."""

import shutil
from pathlib import Path

PLUGIN_FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "plugins"


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
    shutil.copytree(
        PLUGIN_FIXTURES_DIR / name, target, ignore=shutil.ignore_patterns("__pycache__")
    )
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
