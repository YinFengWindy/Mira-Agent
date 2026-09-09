"""插件配置 schema 通道：解析 pydantic 配置模型，供 plugin.config.* 读写复用。

模型来源按优先级支持两条路径：

1. v2 manifest 的 ``config_model`` 字符串：``"模块:类名"``（相对插件包，例如
   ``"config:NovelAIConfig"`` 即导入 ``<import_path>.config`` 再取属性）或裸
   ``"类名"``（定义在入口模块里）。
2. legacy ``Plugin`` 子类的 ``ConfigModel`` 类属性（见
   ``agent.plugins.base.Plugin``、``agent.plugins.manager._load_plugin_config``）；
   经适配器加载的存量插件（如 qqbot）借此无需改造即可接入配置 schema 通道。

``format_validation_error`` 由本模块（新系统）拥有，旧 ``agent.plugins.manager``
反过来复用它，这样 #184 删除旧插件系统时不会带走仍在使用的格式化逻辑。
"""

from __future__ import annotations

import importlib
import sys
from typing import Any

from pydantic import BaseModel, ValidationError

from agent.plugin_host.handle import PluginRecord


class ConfigModelError(Exception):
    """``config_model``/``ConfigModel`` 声明非法，或未指向 pydantic BaseModel 子类。"""


def format_validation_error(error: ValidationError) -> str:
    """Renders a pydantic validation error as one readable ``path: msg`` line."""

    parts: list[str] = []
    for item in error.errors():
        path = ".".join(str(part) for part in item.get("loc", ())) or "<root>"
        parts.append(f"{path}: {item.get('msg', 'invalid')}")
    return "; ".join(parts)


def resolve_config_model(record: PluginRecord) -> type[BaseModel] | None:
    """Returns the plugin's declared config model class, or None when undeclared."""

    if record.manifest.config_model:
        return _resolve_manifest_config_model(record)
    return _resolve_legacy_config_model(record)


def _resolve_manifest_config_model(record: PluginRecord) -> type[BaseModel]:
    spec = str(record.manifest.config_model)
    module_suffix, sep, class_name = spec.partition(":")
    if sep:
        module_name = f"{record.import_path}.{module_suffix}"
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            raise ConfigModelError(
                f"插件 {record.name} 的 config_model 模块导入失败 ({module_name}): {e}"
            ) from e
    else:
        class_name = module_suffix
        module = sys.modules.get(record.import_path)
        if module is None:
            raise ConfigModelError(
                f"插件 {record.name} 的入口模块尚未导入，无法解析 config_model"
            )
    model_cls = getattr(module, class_name, None)
    if not (isinstance(model_cls, type) and issubclass(model_cls, BaseModel)):
        raise ConfigModelError(
            f"插件 {record.name} 的 config_model={spec!r} 未指向 pydantic BaseModel 子类"
        )
    return model_cls


def _resolve_legacy_config_model(record: PluginRecord) -> type[BaseModel] | None:
    from agent.plugins.registry import plugin_registry

    cls = plugin_registry.get_class(record.import_path)
    model_cls = getattr(cls, "ConfigModel", None) if cls is not None else None
    if model_cls is None:
        return None
    if not (isinstance(model_cls, type) and issubclass(model_cls, BaseModel)):
        raise ConfigModelError(
            f"插件 {record.name} 的 ConfigModel 不是 pydantic BaseModel 子类"
        )
    return model_cls


class PluginConfigSchemaRegistry:
    """内核持有的 plugin_id -> config 模型映射；供 plugin.config.* 通道查询。"""

    def __init__(self) -> None:
        self._models: dict[str, type[BaseModel]] = {}

    def register(self, plugin_id: str, model_cls: type[BaseModel]) -> None:
        self._models[plugin_id] = model_cls

    def unregister(self, plugin_id: str) -> None:
        self._models.pop(plugin_id, None)

    def __contains__(self, plugin_id: str) -> bool:
        return plugin_id in self._models

    def schema_for(self, plugin_id: str) -> dict[str, Any] | None:
        """Returns the JSON Schema for a plugin's config model, or None."""
        model_cls = self._models.get(plugin_id)
        return model_cls.model_json_schema() if model_cls is not None else None

    def defaults_for(self, plugin_id: str) -> dict[str, Any] | None:
        """Returns default values for fields that declare one, or None with no model.

        Reads defaults straight off ``model_fields`` instead of instantiating
        the model: constructing an instance fails for the whole model as soon
        as a single required field has no default, which would blank out
        every other field's default along with it. A field without a default
        (required) is simply absent from the result.
        """
        model_cls = self._models.get(plugin_id)
        if model_cls is None:
            return None
        return {
            name: field_info.get_default(call_default_factory=True)
            for name, field_info in model_cls.model_fields.items()
            if not field_info.is_required()
        }

    def validate(self, plugin_id: str, values: dict[str, Any]) -> dict[str, Any]:
        """Validates and normalizes values against the plugin's model.

        Raises ``KeyError`` when the plugin has no registered model, and
        ``pydantic.ValidationError`` when ``values`` fails validation.
        """
        model_cls = self._models[plugin_id]
        return model_cls.model_validate(values).model_dump(mode="json")
