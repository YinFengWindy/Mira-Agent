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
_DISABLED_MARKER = "plugin.disabled"


def plugin_data_dir(workspace: Path, plugin_id: str) -> Path:
    """Returns the writable per-plugin data directory under the workspace."""

    return workspace / PLUGIN_DATA_DIRNAME / plugin_id


def migrate_legacy_disabled_marker(
    plugin_dir: Path, plugin_id: str, legacy_plugin_root: Path | None
) -> None:
    """把插件包上移前留下的 ``plugin.disabled`` 标记搬到新的插件目录。

    与 kv 同一个病根：该标记被 gitignore 覆盖，目录重命名经 git 落到本地时不会
    跟着搬，导致用户此前停用的插件在升级后**自己变回启用**。标记本身没有内容，
    迁移只是重建它。
    """

    if legacy_plugin_root is None:
        return
    target = plugin_dir / _DISABLED_MARKER
    legacy = legacy_plugin_root / plugin_id / _DISABLED_MARKER
    if target.exists() or not legacy.exists():
        return
    _ = target.write_text("", encoding="utf-8")
    logger.info("插件 %s 的停用标记已从 %s 迁移到 %s", plugin_id, legacy, target)
    try:
        legacy.unlink()
    except OSError as error:
        logger.warning("插件 %s 的旧停用标记删除失败，已忽略: %s", plugin_id, error)


def open_plugin_kv(
    *,
    workspace: Path | None,
    plugin_id: str,
    plugin_dir: Path,
    legacy_plugin_root: Path | None = None,
) -> PluginKVStore:
    """Opens a plugin's KV store under the workspace, migrating legacy data once.

    宿主未提供 workspace 时直接报错，而不是退回写插件目录——那正是 #209 的
    病根，留一条静默回退等于把 bug 保留在最不容易被发现的路径上。

    ``legacy_plugin_root`` 是插件包上移到仓库顶层之前的存放位置
    （``apps/backend/plugins``）。`.kv.json` 被 gitignore 覆盖，所以目录重命名
    经 git 落到本地时**不会**跟着搬——旧数据会留在那个位置，必须一并作为迁移来源。
    """

    if workspace is None:
        raise RuntimeError(
            f"插件 {plugin_id} 需要 kv 存储，但宿主未提供 workspace；"
            "插件数据不能写入插件目录（见 issue #209）"
        )
    target = plugin_data_dir(workspace, plugin_id) / _KV_FILENAME
    candidates = [plugin_dir / _LEGACY_KV_FILENAME]
    if legacy_plugin_root is not None:
        candidates.append(legacy_plugin_root / plugin_id / _LEGACY_KV_FILENAME)
    _migrate_legacy_kv(candidates, target, plugin_id=plugin_id)
    return PluginKVStore(target)


def _migrate_legacy_kv(
    candidates: list[Path], target: Path, *, plugin_id: str
) -> None:
    """一次性把遗留在插件目录里的 ``.kv.json`` 搬到 workspace。

    不搬的话，已在使用 kv 的插件（novelai 的自动 CG 冷却与场景去重、
    scene_awareness 的会话场景状态）会在升级到本版本时状态归零——对 novelai
    而言意味着去重失效、同一场景被重复生图。

    按 ``candidates`` 顺序取第一个存在的来源；其余候选即使也存在也只做清理，
    避免旧位置残留在下次启动时又被当成"待迁移"。
    """

    if target.exists():
        return
    source = next((path for path in candidates if path.exists()), None)
    if source is None:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    _ = target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    logger.info("插件 %s 的 kv 数据已从 %s 迁移到 %s", plugin_id, source, target)
    for path in candidates:
        if not path.exists():
            continue
        try:
            path.unlink()
        except OSError as error:
            # 打包形态下插件目录可能只读。数据已经落到新位置，旧文件残留无害且
            # 不再被读取，不值得为删不掉它而让插件加载失败。
            logger.warning("插件 %s 的旧 kv 文件删除失败，已忽略: %s", plugin_id, error)
