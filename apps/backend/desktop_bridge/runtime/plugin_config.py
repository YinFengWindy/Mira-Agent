"""Plugin config schema channel: validate, merge into TOML, and hot-apply.

Owns the ``plugin.config.get``/``plugin.config.set`` request bodies so
``ReloadableDesktopService`` only has to dispatch to it, not implement
validation, TOML merging and the round-trip guard itself.
"""

from __future__ import annotations

import tomllib
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ValidationError

from agent.plugin_host.config_schema import (
    format_validation_error,
    validate_against,
)
from agent.plugin_host.kernel import PluginKernel
from bootstrap.app import AppRuntime
from desktop_bridge.plugin_config_text import merge_plugin_table
from desktop_bridge.runtime.apply import RuntimeApplyError, RuntimeSettingsApplication


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
        # 取出模型类并一路持有：本方法要等事务锁，期间可能有别的 apply 发布新
        # generation 并处置旧内核，届时再回查注册表会抛 KeyError（并发保存直接
        # 变成 internal_error）。模型类不可变，与 generation 无关。
        model_cls = kernel.config_schemas.model_for(plugin_id) if kernel else None
        if model_cls is None:
            raise RuntimeApplyError(
                "plugin_config_unsupported", f"插件 {plugin_id} 未声明配置模型",
            )
        try:
            normalized = validate_against(model_cls, values)
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
            merged = merge_plugin_table(current_text, plugin_id, normalized)
            self._assert_config_round_trip(
                model_cls, plugin_id, current_text, merged, normalized,
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
            # 幂等指纹按"本次逻辑操作"计算，而不是派生出来的整份配置文本：
            # 后者会随无关设置的变化而变，导致同一请求原样重试被误判为
            # runtime_operation_conflict。
            fingerprint_source={"plugin_id": plugin_id, "values": normalized},
        )
        return {"plugin_id": plugin_id, "values": normalized, **result}

    def _plugin_kernel(self) -> "PluginKernel | None":
        """Returns the currently published generation's plugin kernel, if any."""
        core = self._app.core
        return core.plugin_manager if core is not None else None

    @staticmethod
    def _assert_config_round_trip(
        model_cls: type[BaseModel],
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

        The previous guard only re-validated the target plugin's own table,
        which is blind to (2): a merge that silently mangled an unrelated
        table would sail through as long as the target table still parsed.
        So this parses the whole document before and after the merge and
        requires every key outside ``plugins.<plugin_id>`` to compare equal;
        any difference anywhere rejects the entire write.
        """

        try:
            before = tomllib.loads(original_text)
        except tomllib.TOMLDecodeError as exc:
            # The pre-merge text is the config the runtime is already running
            # with, so a decode failure here indicates a bug upstream of this
            # module rather than a user mistake — but never assume anything
            # about it and refuse the write regardless.
            raise RuntimeApplyError(
                "plugin_config_unrepresentable", f"当前配置无法解析: {exc}",
            ) from exc
        try:
            after = tomllib.loads(merged_text)
        except tomllib.TOMLDecodeError as exc:
            raise RuntimeApplyError(
                "plugin_config_unrepresentable", f"合并后的配置无法解析: {exc}",
            ) from exc
        if _without_plugin_table(before, plugin_id) != _without_plugin_table(after, plugin_id):
            raise RuntimeApplyError(
                "plugin_config_unrepresentable",
                "合并后配置中出现了与目标插件无关的改动，写入已取消",
            )
        stored = after.get("plugins", {}).get(plugin_id, {})
        try:
            reread = validate_against(model_cls, stored)
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


def _without_plugin_table(document: dict[str, Any], plugin_id: str) -> dict[str, Any]:
    """Returns a shallow copy of ``document`` with ``plugins.<plugin_id>`` removed."""
    rest = dict(document)
    plugins = dict(rest.get("plugins", {}))
    plugins.pop(plugin_id, None)
    rest["plugins"] = plugins
    return rest
