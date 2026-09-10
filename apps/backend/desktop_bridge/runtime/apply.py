"""Serial, recoverable settings application shared by all desktop callers."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class DerivedWrite:
    """Bundles a text deriver with the fingerprint identifying its logical write.

    Some callers (e.g. ``plugin.config.set``) don't own a full draft; they
    derive the new config text from the currently committed text inside the
    apply lock instead of supplying it directly (see ``apply``'s docstring
    for why the derivation itself must run inside the lock).

    ``fingerprint_payload`` must describe that logical operation and be
    computable *without* running ``build_config_toml`` — that is the whole
    point of carrying it separately: it lets ``apply`` check idempotency
    before deriving, so a retry of an already-applied write still hits the
    remembered result even if deriving and merging again would now fail
    (e.g. the round-trip guard rejecting a merge against text that changed
    in the meantime). Bundling the two fields together, rather than passing
    them as independent optional parameters, keeps "this is a derived write"
    a single explicit concept a caller cannot supply half of.
    """

    build_config_toml: Callable[[str], str]
    fingerprint_payload: dict[str, Any]


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
        derive: DerivedWrite | None = None,
    ) -> dict[str, Any]:
        """Applies a complete draft once; failures leave draft ownership with the UI.

        A caller that derives its new text from the *current* committed text
        (rather than owning a full draft, as the settings UI does) passes
        ``derive``: ``derive.build_config_toml`` runs inside this lock, so a
        concurrent apply cannot slip a commit in between reading the current
        text and writing the derived one. Deriving outside the lock would
        silently drop the other writer's changes.

        The idempotency memo is checked *before* deriving, not after: a
        derived write's fingerprint is computed from ``derive.fingerprint_payload``,
        which needs no materialized text, so there is no reason to run the
        (possibly now-failing) derivation just to discover the request was
        already applied. Checking after derivation — as this used to — means
        a plain retry can fail the round-trip guard if the committed text
        changed in the meantime, instead of returning the remembered result.
        """
        async with self._lock:
            operation_id = payload.get("operation_id")
            updates = payload.get("role_model_updates", [])
            if not isinstance(operation_id, str) or not operation_id.strip():
                raise RuntimeApplyError("runtime_invalid_request", "配置内容和操作 ID 不能为空")
            if not isinstance(updates, list) or any(
                not isinstance(item, dict) for item in updates
            ):
                raise RuntimeApplyError("runtime_invalid_request", "角色模型更新必须是数组")
            if derive is not None:
                fingerprint = self._fingerprint(derive.fingerprint_payload, updates)
            else:
                text = payload.get("config_toml")
                if not isinstance(text, str):
                    raise RuntimeApplyError("runtime_invalid_request", "配置内容不能为空")
                fingerprint = self._fingerprint(text, updates)
            memoized = self._check_memo(operation_id, fingerprint)
            if memoized is not None:
                return memoized
            if derive is not None:
                derived_text = derive.build_config_toml(self.config_text)
                payload = {**payload, "config_toml": derived_text}
            return await self._apply(
                operation_id, payload, prepare_service, publish_service, fingerprint,
            )

    @staticmethod
    def _fingerprint(
        identity: str | dict[str, Any], updates: list[dict[str, Any]],
    ) -> str:
        """Hashes an operation's identity plus role updates into a retry fingerprint.

        ``identity`` is either the full draft text, or a derived write's
        logical payload — never the text a derived write *produces*, which
        would drift with unrelated concurrent settings changes and defeat
        idempotent retries (see ``DerivedWrite``).
        """
        try:
            encoded = json.dumps(
                {"identity": identity, "updates": updates},
                sort_keys=True, ensure_ascii=False,
            )
        except TypeError as exc:
            raise RuntimeApplyError(
                "runtime_invalid_request", f"操作载荷无法序列化: {exc}",
            ) from exc
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def _check_memo(self, operation_id: str, fingerprint: str) -> dict[str, Any] | None:
        """Returns the remembered result for a byte-identical retry, else None.

        Raises when ``operation_id`` was already used for a *different*
        logical write, so retries can never silently reuse another
        operation's remembered result.
        """
        previous = self._results.get(operation_id)
        if previous is None:
            return None
        if previous[0] != fingerprint:
            raise RuntimeApplyError("runtime_operation_conflict", "操作 ID 已用于其他配置")
        return previous[1]

    async def _apply(
        self,
        operation_id: str,
        payload: dict[str, Any],
        prepare_service: Callable,
        publish_service: Callable,
        fingerprint: str,
    ) -> dict[str, Any]:
        text = payload["config_toml"]
        updates = payload.get("role_model_updates", [])
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
