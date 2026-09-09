"""A stable bridge endpoint routing work to leased runtime generations."""

from __future__ import annotations

import asyncio
import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from agent.plugin_host.config_schema import format_validation_error
from agent.plugin_host.kernel import PluginKernel
from bootstrap.app import AppRuntime
from bootstrap.runtime.generations import RuntimeLease
from core.common.cleanup import run_cleanup_steps
from core.roles import RoleStore
from core.common.runtime_scope import bind_runtime
from core.common.task_collector import TaskCollector
from desktop_bridge.method_policy import Handler, MethodPolicy, OwnerRouting, method_policy
from desktop_bridge.models import BridgeError, BridgeResponse
from desktop_bridge.plugin_config_text import merge_plugin_table
from desktop_bridge.runtime.apply import RuntimeApplyError, RuntimeSettingsApplication
from desktop_bridge.runtime.factory import build_desktop_service
from desktop_bridge.runtime.role_tasks import RuntimeRoleTasks
from desktop_bridge.service import DesktopBridgeService

logger = logging.getLogger(__name__)


@dataclass
class _ServiceGeneration:
    service: DesktopBridgeService
    lease: RuntimeLease
    requests: int = 0
    idle: asyncio.Event = field(default_factory=asyncio.Event)


class ReloadableDesktopService:
    """Keeps bridge identity and cancellation ownership stable across settings saves."""

    def __init__(self, app: AppRuntime, config_path: Path, roles: RoleStore) -> None:
        self.app = app
        self.roles = roles
        self.settings = RuntimeSettingsApplication(app, config_path, roles)
        self.role_tasks = RuntimeRoleTasks(app, roles)
        lease = app.pin()
        self._current = _ServiceGeneration(build_desktop_service(lease.core, roles), lease)
        self._entries = [self._current]
        self._listeners: set = set()
        self._retirements = TaskCollector("Desktop runtime retirement")

    @property
    def has_event_listeners(self) -> bool:
        """Reports whether the persistent desktop transport is connected."""
        return bool(self._listeners)

    def add_event_listener(self, listener) -> None:
        """Connects the same transport to current and draining generations."""
        self._listeners.add(listener)
        for entry in self._entries:
            entry.service.add_event_listener(listener)

    def remove_event_listener(self, listener) -> None:
        """Detaches a transport without affecting any running task."""
        self._listeners.discard(listener)
        for entry in self._entries:
            entry.service.remove_event_listener(listener)

    async def publish_event(self, payload) -> None:
        """Publishes host events through the currently connected transport."""
        await self._current.service.publish_event(payload)

    def start_background_tasks(self) -> None:
        """Starts initial bridge maintenance once the stream is ready."""
        self._current.service.start_background_tasks()

    def status(self):
        """Returns the committed configuration and capability state in one snapshot."""
        resolver = self._current.service.model_resolver
        config = self.app.config
        return {
            "generation": self.app.generation,
            "config_toml": self.settings.config_text,
            "models_registered": bool(config.model_registrations),
            "roles": {
                role.id: resolver.availability(role.id) if resolver else {"available": False}
                for role in self.roles.list_roles()
            },
        }

    async def handle(self, request, *, emit_event):
        """Pins ordinary requests and applies settings without replacing the endpoint."""
        method = str(request.get("method") or "")
        request_id = str(request.get("id") or "bridge-request")
        payload = request.get("payload") or {}
        if not isinstance(payload, dict):
            return BridgeResponse(request_id, "response", method,
                                  error=BridgeError("invalid_request", "payload 必须是对象"))
        policy = self.resolve_method_policy(method)
        if policy.handler is Handler.SETTINGS:
            try:
                result = self.status() if method == "runtime.status" else await self.settings.apply(
                    payload, prepare_service=self._prepare, publish_service=self._publish,
                )
                if method == "runtime.apply":
                    await self.publish_event({"id": request_id, "type": "event",
                                              "method": "runtime.applied", "payload": result})
                return BridgeResponse(request_id, "response", method, result)
            except RuntimeApplyError as exc:
                return BridgeResponse(request_id, "response", method,
                                      error=BridgeError(exc.code, str(exc), exc.details))
        if policy.handler is Handler.PLUGIN_CONFIG:
            try:
                result = (
                    self._plugin_config_get(payload) if method == "plugin.config.get"
                    else await self._plugin_config_set(payload)
                )
                return BridgeResponse(request_id, "response", method, result)
            except RuntimeApplyError as exc:
                return BridgeResponse(request_id, "response", method,
                                      error=BridgeError(exc.code, str(exc), exc.details))
        if policy.handler is Handler.ROLE_TASKS:
            role_id = str(payload.get("role_id") or "")
            try:
                if method == "roles.tasks.list":
                    tasks = self.role_tasks.list_tasks(role_id)
                else:
                    tasks = await self.role_tasks.cancel_task(role_id, str(payload.get("task_id") or ""))
                    await self.publish_event({"id": request_id, "type": "event", "method": "roles.tasks.updated",
                                              "payload": {"role_id": role_id}})
                return BridgeResponse(request_id, "response", method, {"tasks": tasks})
            except (KeyError, ValueError, RuntimeError) as error:
                return BridgeResponse(request_id, "response", method,
                                      error=BridgeError("invalid_request", str(error)))
        if not policy.admission_exempt and not self.app.accepting_work:
            return BridgeResponse(request_id, "response", method,
                                  error=BridgeError("runtime_reloading", "正在更新渠道配置，请稍后重试"))
        entry = self._owner(policy.owner_routing, payload)
        if method == "chat.send":
            session_key = f"role:{payload.get('role_id', '')}"
            if any(item.service.chat_service.is_busy(session_key) for item in self._entries):
                return BridgeResponse(request_id, "response", method,
                                      error=BridgeError("chat_busy", "当前会话已有正在执行的聊天任务"))
        entry.requests += 1
        entry.idle.clear()
        try:
            async with entry.lease.retain() as lease:
                with bind_runtime(lease):
                    return await entry.service.handle(request, emit_event=emit_event)
        finally:
            entry.requests -= 1
            if not entry.requests:
                entry.idle.set()

    def _owner(self, routing: OwnerRouting, payload):
        for entry in self._entries:
            service = entry.service
            if routing is OwnerRouting.BUSY_CHAT_SESSION and service.chat_service.is_busy(str(payload.get("session_key") or "")):
                return entry
            if routing is OwnerRouting.BUSY_VOICE_TURN and service.chat_service.owns_voice_turn(str(payload.get("voice_turn_id") or "")):
                return entry
            if routing is OwnerRouting.BUSY_VOICE_SYNTHESIS and service.voice_handler.owns_synthesis(str(payload.get("voice_request_id") or "")):
                return entry
        return self._current

    def resolve_method_policy(self, method: str) -> MethodPolicy:
        """Resolves dispatch policy, consulting the active generation's RPC registry.

        ``plugin.<id>.<method>`` (excluding ``plugin.config.*``, which stays
        in the static table) is whatever the owning plugin declared via
        ``ctx.rpc.register``; a plugin that is unregistered or was never
        registered falls back to the conservative default.
        """
        if method.startswith("plugin.") and not method.startswith("plugin.config."):
            kernel = self._plugin_kernel()
            if kernel is not None:
                policy = kernel.rpc.policy_for(method)
                if policy is not None:
                    return policy
            return MethodPolicy()
        return method_policy(method)

    def _plugin_kernel(self) -> "PluginKernel | None":
        """Returns the currently published generation's plugin kernel, if any."""
        core = self.app.core
        return getattr(core, "plugin_manager", None) if core is not None else None

    def _plugin_config_get(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Returns a plugin's declared JSON Schema (or None) and current values."""
        plugin_id = str(payload.get("plugin_id") or "").strip()
        if not plugin_id:
            raise RuntimeApplyError("runtime_invalid_request", "plugin_id 不能为空")
        kernel = self._plugin_kernel()
        schema = kernel.config_schemas.schema_for(plugin_id) if kernel is not None else None
        stored = dict(self.app.config.plugins.get(plugin_id, {}))
        if schema is None:
            values = stored
        else:
            defaults = kernel.config_schemas.defaults_for(plugin_id) or {}
            values = {**defaults, **stored}
        return {"plugin_id": plugin_id, "schema": schema, "values": values}

    async def _plugin_config_set(self, payload: dict[str, Any]) -> dict[str, Any]:
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
        # 不另起一套写盘逻辑（见 desktop_bridge/plugin_config_text.py）
        merged_text = merge_plugin_table(self.settings.config_text, plugin_id, normalized)
        self._assert_config_round_trip(kernel, plugin_id, merged_text, normalized)
        apply_payload: dict[str, Any] = {
            "config_toml": merged_text,
            "operation_id": operation_id,
        }
        expected_generation = payload.get("expected_generation")
        if expected_generation is not None:
            apply_payload["expected_generation"] = expected_generation
        result = await self.settings.apply(
            apply_payload, prepare_service=self._prepare, publish_service=self._publish,
        )
        return {"plugin_id": plugin_id, "values": normalized, **result}

    @staticmethod
    def _assert_config_round_trip(
        kernel: PluginKernel, plugin_id: str, merged_text: str, normalized: dict[str, Any],
    ) -> None:
        """Rejects a merge whose persisted form would not read back as validated.

        The TOML encoder cannot represent every JSON value (``None`` is
        dropped silently), and a hand-written config could place the plugin's
        table in a shape the merge does not recognise. Committing either would
        persist something other than what was validated, so the write is
        refused instead of silently changing the user's values.
        """

        try:
            parsed = tomllib.loads(merged_text)
        except tomllib.TOMLDecodeError as exc:
            raise RuntimeApplyError(
                "plugin_config_unrepresentable", f"合并后的配置无法解析: {exc}",
            ) from exc
        stored = parsed.get("plugins", {}).get(plugin_id, {})
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

    def _prepare(self, core):
        service = build_desktop_service(core, self.roles, activate_transport=False)
        service.story_simulation.skip_startup_recovery()
        return service

    def _publish(self, service):
        previous = self._current
        self._current = _ServiceGeneration(service, self.app.pin())
        service.register_desktop_push_channel(self.app.core.push_tool)
        self._entries.append(self._current)
        for listener in self._listeners:
            service.add_event_listener(listener)
        self._retirements.spawn(self._retire(previous), name="desktop-runtime-retire")

    async def _retire(self, entry):
        if entry.requests:
            await entry.idle.wait()
        await entry.service.chat_service.drain()
        await entry.service.story_simulation.drain()
        try:
            await run_cleanup_steps(("desktop.service.close", entry.service.aclose),
                                    ("desktop.runtime.release", entry.lease.release))
        finally:
            self._entries.remove(entry)

    async def aclose(self) -> None:
        """Cancels tasks only when the desktop bridge itself is shutting down."""
        self._retirements.cancel_all()
        await self._retirements.drain()
        try:
            await run_cleanup_steps(*[
                step for entry in self._entries
                for step in (("desktop.service.close", entry.service.aclose),
                             ("desktop.runtime.release", entry.lease.release))
            ])
        finally:
            self._entries.clear()
        if self._retirements.errors:
            raise ExceptionGroup("Desktop runtime retirement failed", self._retirements.errors)
