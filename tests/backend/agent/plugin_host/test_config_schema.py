"""config_schema.py：manifest / legacy 两条模型来源解析、schema 导出与校验。"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from agent.plugin_host.config_schema import (
    ConfigModelError,
    PluginConfigSchemaRegistry,
    resolve_config_model,
)
from agent.plugin_host.handle import PluginRecord
from agent.plugin_host.kernel import _import_module
from agent.plugin_host.manifest import PluginManifest


def _record(
    tmp_path: Path,
    *,
    import_path: str,
    entry: str = "plugin.py",
    config_model: str | None = None,
) -> PluginRecord:
    manifest = PluginManifest(
        id=import_path,
        entry=entry,
        capabilities=(),
        config_model=config_model,
        api=2,
    )
    return PluginRecord(
        name=import_path,
        plugin_dir=tmp_path,
        entry_file=tmp_path / entry,
        import_path=import_path,
        manifest=manifest,
    )


# ── manifest config_model：裸类名 ────────────────────────────────────────────


def test_manifest_bare_class_name_resolves_from_entry_module(tmp_path: Path):
    (tmp_path / "plugin.py").write_text(
        "from pydantic import BaseModel\n\n\n"
        "class DemoConfig(BaseModel):\n"
        "    name: str = 'demo'\n"
        "    count: int = 1\n",
        encoding="utf-8",
    )
    record = _record(tmp_path, import_path="cfg_bare_demo", config_model="DemoConfig")
    _import_module(record.import_path, record.entry_file)

    model_cls = resolve_config_model(record)

    assert model_cls is not None
    assert model_cls.__name__ == "DemoConfig"
    assert model_cls().model_dump() == {"name": "demo", "count": 1}


def test_manifest_bare_class_name_missing_raises(tmp_path: Path):
    (tmp_path / "plugin.py").write_text("value = 1\n", encoding="utf-8")
    record = _record(tmp_path, import_path="cfg_bare_missing", config_model="NoSuchConfig")
    _import_module(record.import_path, record.entry_file)

    with pytest.raises(ConfigModelError, match="pydantic BaseModel"):
        resolve_config_model(record)


# ── manifest config_model：模块:类名 ─────────────────────────────────────────


def test_manifest_module_colon_class_resolves_from_submodule(tmp_path: Path):
    (tmp_path / "plugin.py").write_text("async def setup(ctx):\n    return None\n", encoding="utf-8")
    (tmp_path / "config.py").write_text(
        "from pydantic import BaseModel\n\n\n"
        "class NovelAIConfig(BaseModel):\n"
        "    api_key: str = ''\n",
        encoding="utf-8",
    )
    record = _record(
        tmp_path, import_path="cfg_module_demo", config_model="config:NovelAIConfig"
    )
    _import_module(record.import_path, record.entry_file)

    model_cls = resolve_config_model(record)

    assert model_cls is not None
    assert model_cls.__name__ == "NovelAIConfig"


def test_manifest_module_colon_class_import_failure_raises(tmp_path: Path):
    (tmp_path / "plugin.py").write_text("async def setup(ctx):\n    return None\n", encoding="utf-8")
    record = _record(
        tmp_path, import_path="cfg_module_missing", config_model="config:NovelAIConfig"
    )
    _import_module(record.import_path, record.entry_file)

    with pytest.raises(ConfigModelError, match="导入失败"):
        resolve_config_model(record)


def test_manifest_config_model_not_a_base_model_raises(tmp_path: Path):
    (tmp_path / "plugin.py").write_text("class NotAModel:\n    pass\n", encoding="utf-8")
    record = _record(tmp_path, import_path="cfg_not_model", config_model="NotAModel")
    _import_module(record.import_path, record.entry_file)

    with pytest.raises(ConfigModelError, match="pydantic BaseModel"):
        resolve_config_model(record)


# ── legacy Plugin.ConfigModel 类属性 ─────────────────────────────────────────


def test_legacy_config_model_attribute_is_discovered_after_import(tmp_path: Path):
    (tmp_path / "plugin.py").write_text(
        "from pydantic import BaseModel\n"
        "from agent.plugins import Plugin\n\n\n"
        "class LegacyConfig(BaseModel):\n"
        "    app_id: str = ''\n\n\n"
        "class LegacyPlugin(Plugin):\n"
        "    name = 'legacy_demo'\n"
        "    ConfigModel = LegacyConfig\n",
        encoding="utf-8",
    )
    record = _record(tmp_path, import_path="cfg_legacy_demo")
    _import_module(record.import_path, record.entry_file)

    model_cls = resolve_config_model(record)

    assert model_cls is not None
    assert model_cls.__name__ == "LegacyConfig"


def test_legacy_plugin_without_config_model_returns_none(tmp_path: Path):
    (tmp_path / "plugin.py").write_text(
        "from agent.plugins import Plugin\n\n\n"
        "class PlainPlugin(Plugin):\n"
        "    name = 'plain_demo'\n",
        encoding="utf-8",
    )
    record = _record(tmp_path, import_path="cfg_legacy_plain")
    _import_module(record.import_path, record.entry_file)

    assert resolve_config_model(record) is None


def test_legacy_config_model_not_a_base_model_raises(tmp_path: Path):
    (tmp_path / "plugin.py").write_text(
        "from agent.plugins import Plugin\n\n\n"
        "class BadPlugin(Plugin):\n"
        "    name = 'bad_demo'\n"
        "    ConfigModel = object\n",
        encoding="utf-8",
    )
    record = _record(tmp_path, import_path="cfg_legacy_bad")
    _import_module(record.import_path, record.entry_file)

    with pytest.raises(ConfigModelError, match="pydantic BaseModel"):
        resolve_config_model(record)


def test_no_declaration_at_all_returns_none(tmp_path: Path):
    (tmp_path / "plugin.py").write_text("value = 1\n", encoding="utf-8")
    record = _record(tmp_path, import_path="cfg_no_declaration")
    _import_module(record.import_path, record.entry_file)

    assert resolve_config_model(record) is None


# ── PluginConfigSchemaRegistry ───────────────────────────────────────────────


class _DemoConfig(BaseModel):
    api_key: str = ""
    max_results: int = 5


def test_registry_schema_for_and_defaults_for_undeclared_plugin_are_none():
    registry = PluginConfigSchemaRegistry()

    assert registry.schema_for("missing") is None
    assert registry.defaults_for("missing") is None
    assert "missing" not in registry


def test_registry_schema_for_exports_json_schema_and_defaults():
    registry = PluginConfigSchemaRegistry()
    registry.register("demo", _DemoConfig)

    schema = registry.schema_for("demo")
    defaults = registry.defaults_for("demo")

    assert schema is not None
    assert schema["properties"]["api_key"]["default"] == ""
    assert defaults == {"api_key": "", "max_results": 5}
    assert "demo" in registry


def test_registry_validate_normalizes_values():
    registry = PluginConfigSchemaRegistry()
    registry.register("demo", _DemoConfig)

    normalized = registry.validate("demo", {"api_key": "secret", "max_results": "9"})

    assert normalized == {"api_key": "secret", "max_results": 9}


def test_registry_validate_raises_on_invalid_values():
    registry = PluginConfigSchemaRegistry()
    registry.register("demo", _DemoConfig)

    with pytest.raises(ValidationError):
        registry.validate("demo", {"max_results": "not-a-number"})


def test_registry_unregister_removes_model():
    registry = PluginConfigSchemaRegistry()
    registry.register("demo", _DemoConfig)

    registry.unregister("demo")

    assert "demo" not in registry
    assert registry.schema_for("demo") is None
