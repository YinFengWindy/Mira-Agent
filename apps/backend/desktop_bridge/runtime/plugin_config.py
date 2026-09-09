"""Plugin config schema channel: validate, merge into TOML, and hot-apply.

Owns the ``plugin.config.get``/``plugin.config.set`` request bodies so
``ReloadableDesktopService`` only has to dispatch to it, not implement
validation, TOML merging and the round-trip guard itself.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from agent.plugin_host.config_schema import format_validation_error
from agent.plugin_host.kernel import PLUGIN_ENABLED_CONFIG_KEY, PluginKernel
from bootstrap.app import AppRuntime
from desktop_bridge.plugin_config_text import merge_plugin_table
from desktop_bridge.runtime.apply import (
    RuntimeApplyError,
    RuntimeSettingsApplication,
    assert_plugin_table_isolated,
    read_plugin_table,
)


class RuntimePluginConfig:
    """Reads and writes one plugin's ``[plugins.<id>]`` table via its config schema."""

    def __init__(self, app: AppRuntime, settings: RuntimeSettingsApplication) -> None:
        self._app = app
        self._settings = settings

    def get(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Returns a plugin's declared JSON Schema (or None) and current values."""
        plugin_id = str(payload.get("plugin_id") or "").strip()
        if not plugin_id:
            raise RuntimeApplyError("runtime_invalid_request", "plugin_id 不能为空")
        kernel = self._plugin_kernel()
        schema = kernel.config_schemas.schema_for(plugin_id) if kernel is not None else None
        stored = dict(self._app.config.plugins.get(plugin_id, {}))
        # 启停状态归宿主所有，由 plugins.list / plugins.setEnabled 管理；
        # 不要混进配置表单的值里被 renderer 原样回传。
        _ = stored.pop(PLUGIN_ENABLED_CONFIG_KEY, None)
        if schema is None:
            values = stored
        else:
            defaults = kernel.config_schemas.defaults_for(plugin_id) or {}
            values = {**defaults, **stored}
        return {"plugin_id": plugin_id, "schema": schema, "values": values}

    async def set(
        self,
        payload: dict[str, Any],
        *,
        prepare_service: Callable,
        publish_service: Callable,
    ) -> dict[str, Any]:
        """Validates, commits and hot-applies one plugin's ``[plugins.<id>]`` table."""
        plugin_id = str(payload.get("plugin_id") or "").strip()
        values = payload.get("values")
        operation_id = payload.get("operation_id")
        if not plugin_id:
            raise RuntimeApplyError("runtime_invalid_request", "plugin_id 不能为空")
        if not isinstance(values, dict):
            raise RuntimeApplyError("runtime_invalid_request", "values 必须是对象")
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise RuntimeApplyError("runtime_invalid_request", "操作 ID 不能为空")
        kernel = self._plugin_kernel()
        if kernel is None or plugin_id not in kernel.config_schemas:
            raise RuntimeApplyError(
                "plugin_config_unsupported", f"插件 {plugin_id} 未声明配置模型",
            )
        try:
            normalized = kernel.config_schemas.validate(plugin_id, values)
        except ValidationError as exc:
            raise RuntimeApplyError(
                "plugin_config_invalid", format_validation_error(exc),
                # details 会被 JSON 序列化写回 renderer：去掉 url 与 ctx，
                # 后者可能携带异常对象等不可序列化内容。
                errors=exc.errors(include_url=False, include_context=False),
            ) from exc
        # 复用设置事务：定位-替换式合并 TOML 文本后走既有事务化落盘 + 热更新路径，
        # 不另起一套写盘逻辑（见 desktop_bridge/plugin_config_text.py）。
        # 合并与守卫都在事务锁内进行：本方法只改一张表、其余文本沿用"当前已提交
        # 的配置"，若在锁外读取基准文本，并发的 runtime.apply 会被整份覆盖掉。
        def _merge(current_text: str) -> str:
            # 启停状态与插件配置同住一张表，但它归宿主所有、不是配置模型的字段，
            # 校验时会被 pydantic 丢弃。整表替换必须把它显式带回来，否则用户改一次
            # 插件配置就会把停用的插件重新启用。
            values_to_write = dict(normalized)
            current = read_plugin_table(current_text, plugin_id)
            if PLUGIN_ENABLED_CONFIG_KEY in current:
                values_to_write[PLUGIN_ENABLED_CONFIG_KEY] = current[
                    PLUGIN_ENABLED_CONFIG_KEY
                ]
            merged = merge_plugin_table(current_text, plugin_id, values_to_write)
            self._assert_config_round_trip(
                kernel, plugin_id, current_text, merged, normalized,
            )
            return merged

        apply_payload: dict[str, Any] = {"operation_id": operation_id}
        expected_generation = payload.get("expected_generation")
        if expected_generation is not None:
            apply_payload["expected_generation"] = expected_generation
        result = await self._settings.apply(
            apply_payload,
            prepare_service=prepare_service,
            publish_service=publish_service,
            build_config_toml=_merge,
        )
        return {"plugin_id": plugin_id, "values": normalized, **result}

    def _plugin_kernel(self) -> "PluginKernel | None":
        """Returns the currently published generation's plugin kernel, if any."""
        core = self._app.core
        return core.plugin_manager if core is not None else None

    @staticmethod
    def _assert_config_round_trip(
        kernel: PluginKernel,
        plugin_id: str,
        original_text: str,
        merged_text: str,
        normalized: dict[str, Any],
    ) -> None:
        """Rejects a merge that changed anything outside the target plugin's table.

        Two independent things can go wrong when text-splicing TOML:

        1. The TOML encoder cannot represent every JSON value (``None`` is
           dropped silently), or the target table's own shape round-trips
           into something the model no longer accepts.
        2. The line-scanning merge misidentifies the target table's span
           (e.g. a table header look-alike inside an unrelated multi-line
           value) and rewrites or drops content that belongs to a *different*
           table entirely.

        (2) is checked by the shared ``assert_plugin_table_isolated`` guard
        (also used by the plugin enable/disable toggle); (1) is specific to
        this schema-validated write, so it stays here as an extra check on
        top of that shared one.
        """

        stored = assert_plugin_table_isolated(plugin_id, original_text, merged_text)
        try:
            reread = kernel.config_schemas.validate(plugin_id, stored)
        except ValidationError as exc:
            raise RuntimeApplyError(
                "plugin_config_unrepresentable",
                f"配置写入后无法按模型读回: {format_validation_error(exc)}",
            ) from exc
        if reread != normalized:
            raise RuntimeApplyError(
                "plugin_config_unrepresentable",
                "配置中存在无法用 TOML 表达的值，写入已取消",
            )
