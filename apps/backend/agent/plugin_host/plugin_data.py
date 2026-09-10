"""插件私有数据的落盘位置：workspace，而不是插件目录（issue #209）。

插件目录在打包形态下位于应用安装目录内——PyInstaller 经 ``--add-data`` 把
``plugins/`` 摊在 ``sys._MEIPASS``，electron-builder 再把整个 runtime 放进
``resources/runtime``。往那里写用户数据有两个后果：NSIS 升级会重装
``resources/``，数据每次升级即丢；用户若把应用装到 ``Program Files``，写入
直接因权限失败。

因此插件的私有状态统一落在 workspace 下，与会话库、角色、记忆、配置同处一地，
按插件分目录。**插件目录是代码，用户数据归 workspace。**
"""

from __future__ import annotations

import logging
from pathlib import Path

# PluginKVStore 是通用工具而非旧系统语义，#184 删除旧插件系统时应把它移到
# plugin_host 下；在那之前从原处导入，避免这次修复顺带扩大改动面。
from agent.plugins.context import PluginKVStore

logger = logging.getLogger(__name__)

# workspace 下存放各插件私有数据的目录名
PLUGIN_DATA_DIRNAME = "plugins"
_KV_FILENAME = "kv.json"
_LEGACY_KV_FILENAME = ".kv.json"


def plugin_data_dir(workspace: Path, plugin_id: str) -> Path:
    """Returns the writable per-plugin data directory under the workspace."""

    return workspace / PLUGIN_DATA_DIRNAME / plugin_id


def open_plugin_kv(
    *, workspace: Path | None, plugin_id: str, plugin_dir: Path
) -> PluginKVStore:
    """Opens a plugin's KV store under the workspace, migrating legacy data once.

    宿主未提供 workspace 时直接报错，而不是退回写插件目录——那正是 #209 的
    病根，留一条静默回退等于把 bug 保留在最不容易被发现的路径上。
    """

    if workspace is None:
        raise RuntimeError(
            f"插件 {plugin_id} 需要 kv 存储，但宿主未提供 workspace；"
            "插件数据不能写入插件目录（见 issue #209）"
        )
    target = plugin_data_dir(workspace, plugin_id) / _KV_FILENAME
    _migrate_legacy_kv(plugin_dir / _LEGACY_KV_FILENAME, target, plugin_id=plugin_id)
    return PluginKVStore(target)


def _migrate_legacy_kv(legacy: Path, target: Path, *, plugin_id: str) -> None:
    """一次性把遗留在插件目录里的 ``.kv.json`` 搬到 workspace。

    不搬的话，已在使用 kv 的插件（novelai 的自动 CG 冷却与场景去重、
    scene_awareness 的会话场景状态）会在升级到本版本时状态归零——对 novelai
    而言意味着去重失效、同一场景被重复生图。
    """

    if target.exists() or not legacy.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    _ = target.write_text(legacy.read_text(encoding="utf-8"), encoding="utf-8")
    try:
        legacy.unlink()
    except OSError as error:
        # 打包形态下插件目录可能只读。数据已经落到新位置，旧文件残留无害且不再
        # 被读取，不值得为删不掉它而让插件加载失败。
        logger.warning("插件 %s 的旧 kv 文件删除失败，已忽略: %s", plugin_id, error)
