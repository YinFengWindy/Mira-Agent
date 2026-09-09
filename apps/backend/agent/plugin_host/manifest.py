"""插件 manifest：v2 插件必备的声明文件，legacy 插件由适配器合成隐式 manifest。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# v1 首批 capability 名称；manifest 只能声明这里列出的能力
KNOWN_CAPABILITIES = frozenset(
    {
        "tools",
        "lifecycle",
        "tool_hooks",
        "proactive_gates",
        "channels",
        "events",
        "kv",
        "config",
        "background",
    }
)

# legacy Plugin ABC 经适配器运行时隐式获得全部能力（旧 PluginContext 语义）
LEGACY_CAPABILITIES = tuple(sorted(KNOWN_CAPABILITIES))


class ManifestError(Exception):
    """manifest 缺失必填字段或声明了未知 capability。"""


@dataclass
class PluginManifest:
    """插件包声明：身份、入口与所需 capability。"""

    id: str
    version: str | None = None
    desc: str | None = None
    author: str | None = None
    entry: str = "plugin.py"
    capabilities: tuple[str, ...] = ()
    config_model: str | None = None
    api: int = 1
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def is_v2(self) -> bool:
        return self.api >= 2


def load_manifest(plugin_dir: Path) -> PluginManifest | None:
    """读取 manifest.yaml；不存在返回 None，格式非法抛 ManifestError。

    只有显式声明 ``api: 2`` 的 manifest 才按 v2 契约解析；
    只含 name/version/desc/author 的旧四字段 manifest 保持 legacy 元信息覆盖语义。
    """
    manifest_path = plugin_dir / "manifest.yaml"
    if not manifest_path.exists():
        return None
    import yaml

    loaded = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ManifestError(f"manifest.yaml 格式错误，期望 dict: {manifest_path}")
    raw: dict[str, object] = loaded
    api = int(str(raw.get("api", 1)))
    plugin_id = str(raw.get("id") or raw.get("name") or plugin_dir.name)
    capabilities = _parse_capabilities(raw, manifest_path, required=api >= 2)
    return PluginManifest(
        id=plugin_id,
        version=_optional_str(raw.get("version")),
        desc=_optional_str(raw.get("desc")),
        author=_optional_str(raw.get("author")),
        entry=str(raw.get("entry") or "plugin.py"),
        capabilities=capabilities,
        config_model=_optional_str(raw.get("config_model")),
        api=api,
        metadata={k: v for k, v in raw.items() if isinstance(k, str)},
    )


def synthesize_legacy_manifest(plugin_dir: Path) -> PluginManifest:
    """为无 manifest（或旧四字段 manifest）的 legacy 插件合成隐式 manifest。"""
    return PluginManifest(
        id=plugin_dir.name,
        entry="plugin.py",
        capabilities=LEGACY_CAPABILITIES,
        api=1,
    )


def _parse_capabilities(
    raw: dict[str, object], manifest_path: Path, *, required: bool
) -> tuple[str, ...]:
    value = raw.get("capabilities")
    if value is None:
        if required:
            raise ManifestError(f"v2 manifest 缺少 capabilities 声明: {manifest_path}")
        return LEGACY_CAPABILITIES
    if not isinstance(value, list):
        raise ManifestError(f"capabilities 必须是列表: {manifest_path}")
    names = tuple(str(item) for item in value)
    unknown = [name for name in names if name not in KNOWN_CAPABILITIES]
    if unknown:
        raise ManifestError(
            f"manifest 声明了未知 capability {unknown}: {manifest_path}"
        )
    return names


def _optional_str(value: object) -> str | None:
    return None if value is None else str(value)
