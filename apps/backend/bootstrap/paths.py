"""Repository-relative locations shared by the backend entry point and bootstrap.

插件包在 #178 之后位于仓库顶层 ``plugins/``，而后端自身在 ``apps/backend/``。
两者的相对关系在开发态与 PyInstaller 冻结态下不同，集中在这里解析一次，避免
各处再各写一份 ``parents[N]`` 魔数——那正是插件搬迁时要同时改四处的原因。
"""

from __future__ import annotations

import sys
from pathlib import Path

# bootstrap -> apps/backend -> apps -> 仓库根
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def resource_root() -> Path:
    """Returns the root holding bundled resources such as ``plugins/``.

    PyInstaller 把 ``--add-data`` 的内容摊在 bundle 根（``sys._MEIPASS``），
    开发态则是仓库根；两种形态下资源的相对布局一致，调用方只认这一个入口。
    """

    frozen_root = getattr(sys, "_MEIPASS", None)
    if isinstance(frozen_root, str) and frozen_root:
        return Path(frozen_root)
    return REPOSITORY_ROOT


def ensure_repository_root_importable() -> None:
    """Puts the repository root on ``sys.path`` so ``plugins.<id>`` resolves.

    后端进程的 ``sys.path[0]`` 是脚本目录 ``apps/backend``，仓库根不在其中；
    而插件包内部与 ``bootstrap`` 对默认记忆引擎都用 ``plugins.<id>.<module>``
    绝对导入。没有这一步，开发态下插件会在导入期全部失败并被静默跳过。
    冻结态由 PyInstaller 直接收集 ``plugins.*``，不需要也不应改路径。
    """

    if getattr(sys, "frozen", False):
        return
    root = str(REPOSITORY_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
