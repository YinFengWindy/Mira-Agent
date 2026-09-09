"""Serial, recoverable settings application shared by all desktop callers."""

from __future__ import annotations

import asyncio
import hashlib
import json
import tomllib
from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path
from typing import Any

from agent.config import load_config_text
from bootstrap.app import AppRuntime
from core.roles.model_updates import prepare_role_model_updates
from core.roles.store import RoleStore
from desktop_bridge.config_transaction import ConfigTransaction


_RESULT_HISTORY_LIMIT = 64


class RuntimeApplyError(ValueError):
    """A stable settings failure that never changes bridge health."""

    def __init__(self, error_code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = error_code
        self.details = details


def read_plugin_table(config_toml: str, plugin_id: str) -> dict[str, Any]:
    """Returns the ``[plugins.<plugin_id>]`` table from a config document.

    Callers that derive a new table from the current one need to read it
    inside the settings lock (see ``RuntimeSettingsApplication.apply``'s
    ``build_config_toml``), so they parse the text they were handed rather
    than the runtime's possibly-newer ``AppRuntime.config``.
    """

    try:
        document = tomllib.loads(config_toml)
    except tomllib.TOMLDecodeError as exc:
        raise RuntimeApplyError(
            "plugin_config_unrepresentable", f"当前配置无法解析: {exc}",
        ) from exc
    return dict(document.get("plugins", {}).get(plugin_id, {}))


def assert_plugin_table_isolated(
    plugin_id: str, original_text: str, merged_text: str,
) -> dict[str, Any]:
    """Rejects a ``[plugins.<plugin_id>]`` merge that touched anything else.

    Shared by every caller that text-splices one plugin's table
    (``plugin.config.set``, the plugin enable/disable toggle) so the same
    "parses both documents, only the target table may differ" guard is not
    reimplemented per caller. Schema-specific re-validation (pydantic
    round-trip) is the caller's own concern on top of this; this function
    only proves the merge did not corrupt anything *outside* the target
    table. Returns the merged document's own ``plugins.<plugin_id>`` table
    (``{}`` when absent) for the caller to validate further.
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
    return dict(after.get("plugins", {}).get(plugin_id, {}))


def _without_plugin_table(document: dict[str, Any], plugin_id: str) -> dict[str, Any]:
    """Returns a shallow copy of ``document`` with ``plugins.<plugin_id>`` removed."""
    rest = dict(document)
    plugins = dict(rest.get("plugins", {}))
    plugins.pop(plugin_id, None)
    rest["plugins"] = plugins
    return rest


class RuntimeSettingsApplication:
    """Prepares candidates, commits persistence, and remembers idempotent results."""

    def __init__(self, app: AppRuntime, config_path: Path, role_store: RoleStore) -> None:
        self.app = app
        self.roles = role_store
        self.transaction = ConfigTransaction(config_path, role_store.workspace)
        self.config_text = config_path.read_text(encoding="utf-8")
        self._lock = asyncio.Lock()
        self._results: OrderedDict[str, tuple[str, dict[str, Any]]] = OrderedDict()

    async def apply(
        self, payload: dict[str, Any], *, prepare_service: Callable,
        publish_service: Callable,
        build_config_toml: Callable[[str], str] | None = None,
    ) -> dict[str, Any]:
        """Applies a complete draft once; failures leave draft ownership with the UI.

        A caller that derives its new text from the *current* committed text
        (rather than owning a full draft, as the settings UI does) passes
        ``build_config_toml``: it runs inside this lock, so a concurrent apply
        cannot slip a commit in between reading the current text and writing
        the derived one. Deriving outside the lock would silently drop the
        other writer's changes.
        """
        async with self._lock:
            if build_config_toml is not None:
                payload = {**payload, "config_toml": build_config_toml(self.config_text)}
            return await self._apply(payload, prepare_service, publish_service)

    async def _apply(self, payload, prepare_service, publish_service):
        text = payload.get("config_toml")
        operation_id = payload.get("operation_id")
        updates = payload.get("role_model_updates", [])
        if not isinstance(text, str) or not isinstance(operation_id, str) or not operation_id.strip():
            raise RuntimeApplyError("runtime_invalid_request", "配置内容和操作 ID 不能为空")
        if not isinstance(updates, list) or any(not isinstance(item, dict) for item in updates):
            raise RuntimeApplyError("runtime_invalid_request", "角色模型更新必须是数组")
        fingerprint = hashlib.sha256(json.dumps(
            {"config": text, "updates": updates}, sort_keys=True, ensure_ascii=False,
        ).encode("utf-8")).hexdigest()
        previous = self._results.get(operation_id)
        if previous is not None:
            if previous[0] != fingerprint:
                raise RuntimeApplyError("runtime_operation_conflict", "操作 ID 已用于其他配置")
            return previous[1]
        generation = self.app.generation
        expected = payload.get("expected_generation")
        if expected is not None and (type(expected) is not int or expected != generation):
            raise RuntimeApplyError("runtime_generation_conflict", "配置已更新，请重新读取后保存",
                                    generation=generation)
        try:
            config = load_config_text(text)
            prepare_role_model_updates(self.roles, updates, {item.id for item in config.model_registrations})
        except (ValueError, TypeError) as exc:
            raise RuntimeApplyError("runtime_config_invalid", str(exc)) from exc
        if config == self.app.config:
            try:
                with self.roles.lock:
                    roles_payload = prepare_role_model_updates(
                        self.roles, updates, {item.id for item in config.model_registrations},
                    )
                    self.transaction.commit(text, roles_payload)
            except (OSError, ValueError, RuntimeError) as exc:
                raise RuntimeApplyError("runtime_commit_failed", str(exc)) from exc
            self.config_text = text
            result = {"generation": generation, "changed": bool(updates)}
            self._remember(operation_id, fingerprint, result)
            return result
        candidate = None
        service = None
        try:
            candidate = await self.app.prepare(config)
            service = prepare_service(candidate.core)

            def commit() -> None:
                # Read the current role records again after asynchronous preparation.
                # Only model fields are merged, so intervening state is retained.
                with self.roles.lock:
                    roles_payload = prepare_role_model_updates(
                        self.roles, updates, {item.id for item in config.model_registrations},
                    )
                    self.transaction.commit(text, roles_payload)

            await self.app.publish(candidate, commit=commit)
        except BaseException as exc:
            try:
                if service is not None:
                    await service.aclose()
            finally:
                if candidate is not None:
                    await self.app.discard(candidate)
            if isinstance(exc, asyncio.CancelledError):
                raise
            details = exc.to_details() if hasattr(exc, "to_details") else {}
            raise RuntimeApplyError(getattr(exc, "code", "runtime_apply_failed"), str(exc), **details) from exc
        self.config_text = text
        publish_service(service)
        result = {"generation": self.app.generation, "changed": self.app.generation != generation}
        self._remember(operation_id, fingerprint, result)
        return result

    def _remember(self, operation_id: str, fingerprint: str, result: dict[str, Any]) -> None:
        # Retries arrive shortly after the original attempt; a bounded window
        # keeps idempotency without growing for the lifetime of the bridge.
        self._results[operation_id] = fingerprint, result
        while len(self._results) > _RESULT_HISTORY_LIMIT:
            self._results.popitem(last=False)
