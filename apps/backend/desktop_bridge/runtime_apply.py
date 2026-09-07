"""Serial, recoverable settings application shared by all desktop callers."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from agent.config import load_config_text
from bootstrap.app import AppRuntime
from core.roles.model_updates import prepare_role_model_updates
from core.roles.store import RoleStore
from desktop_bridge.config_transaction import ConfigTransaction


class RuntimeApplyError(ValueError):
    """A stable settings failure that never changes bridge health."""

    def __init__(self, error_code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = error_code
        self.details = details


class RuntimeSettingsApplication:
    """Prepares candidates, commits persistence, and remembers idempotent results."""

    def __init__(self, app: AppRuntime, config_path: Path, role_store: RoleStore) -> None:
        self.app = app
        self.roles = role_store
        self.transaction = ConfigTransaction(config_path, role_store.workspace)
        self.config_text = config_path.read_text(encoding="utf-8")
        self._lock = asyncio.Lock()
        self._results: dict[str, tuple[str, dict[str, Any]]] = {}

    async def apply(
        self, payload: dict[str, Any], *, prepare_service: Callable,
        publish_service: Callable,
    ) -> dict[str, Any]:
        """Applies a complete draft once; failures leave draft ownership with the UI."""
        async with self._lock:
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
                with self.roles._lock:
                    roles_payload = prepare_role_model_updates(
                        self.roles, updates, {item.id for item in config.model_registrations},
                    )
                    self.transaction.commit(text, roles_payload)
            except (OSError, ValueError, RuntimeError) as exc:
                raise RuntimeApplyError("runtime_commit_failed", str(exc)) from exc
            self.config_text = text
            result = {"generation": generation, "changed": bool(updates)}
            self._results[operation_id] = fingerprint, result
            return result
        candidate = None
        service = None
        try:
            candidate = await self.app.prepare(config)
            service = prepare_service(candidate.core)

            def commit() -> None:
                # Read the current role records again after asynchronous preparation.
                # Only model fields are merged, so intervening state is retained.
                with self.roles._lock:
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
        self._results[operation_id] = fingerprint, result
        return result
