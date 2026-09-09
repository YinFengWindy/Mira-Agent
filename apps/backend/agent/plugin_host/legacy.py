"""legacy 适配器：让旧 Plugin ABC / 装饰器插件零改动跑在新内核上。

全部注册被改道经作用域上下文登记为 effect，使卸载与失败回滚和 v2 插件同构；
配置解析、manifest 覆盖、工具包装等行为逻辑直接复用旧 manager 的实现，
保证迁移期行为一致（旧模块的整体删除属于收尾 ticket）。
"""

from __future__ import annotations

import functools
import logging
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from infra.channels.contract import Channel

from agent.plugin_host.capabilities import (
    ChannelsCapability,
    LifecycleCapability,
    PHASE_SLOTS,
    ProactiveGatesCapability,
    ToolHooksCapability,
    ToolsCapability,
)
from agent.plugin_host.events import ScopedEventBus
from agent.plugin_host.handle import PluginHandle
from agent.plugins.manager import (
    _EVENT_TYPE_MAP,
    _PluginConfigError,
    _PluginToolHook,
    _apply_manifest,
    _load_module_list,
    _load_plugin_config,
    _make_execute,
)
from agent.plugins.registry import MetadataKind, plugin_registry

logger = logging.getLogger(__name__)


class LegacyPluginError(Exception):
    """legacy 插件加载失败（类缺失、配置无效或 initialize 抛错）。"""


async def load_legacy_plugin(
    handle: PluginHandle,
    *,
    scoped_bus: ScopedEventBus,
    deps: Any,
) -> Any:
    """执行旧 _load_one 的装配流程，注册全部改走 handle.effects。

    调用方（内核）负责模块导入与失败时的 effect 处置。
    """
    record = handle.record
    import_path = record.import_path
    cls = plugin_registry._classes.get(import_path)
    if cls is None:
        raise LegacyPluginError(f"插件 {record.name} 未注册类")

    instance = cls()
    _apply_manifest(instance, record.plugin_dir)
    plugin_id = str(instance.name) if instance.name else record.name
    try:
        plugin_config = _load_plugin_config(
            record.plugin_dir,
            getattr(cls, "ConfigModel", None),
            deps.plugin_configs.get(plugin_id),
        )
    except _PluginConfigError as e:
        raise LegacyPluginError(f"插件 {record.name} 配置无效: {e}") from e

    # 旧 PluginContext 保持原字段，但 event_bus 换成作用域代理修复卸载不解绑缺陷
    from agent.plugins.context import PluginContext, PluginKVStore

    instance.context = PluginContext(
        event_bus=scoped_bus,
        tool_registry=deps.tool_registry,
        plugin_id=plugin_id,
        plugin_dir=record.plugin_dir,
        kv_store=PluginKVStore(record.plugin_dir / ".kv.json"),
        config=plugin_config,
        app_config=deps.app_config,
        light_provider=deps.light_provider,
        light_model=deps.light_model,
        workspace=deps.workspace,
        session_manager=deps.session_manager,
        memory_engine=deps.memory_engine,
        relationship_runtime=deps.relationship_runtime,
    )
    plugin_registry.register_instance(import_path, instance)
    handle.effects.add(
        "registry:instance",
        lambda: plugin_registry.remove_plugin(import_path),
    )

    _bind_lifecycle_handlers(instance, import_path, scoped_bus)
    _register_tools(instance, handle, deps)
    _bind_tool_hooks(instance, handle, import_path)
    _collect_phase_modules(instance, handle)
    _collect_proactive_gates(instance, handle)

    # initialize 失败：先给插件 terminate 机会（对齐旧回滚），再交内核处置 effects
    try:
        await instance.initialize()
    except Exception as e:
        try:
            await instance.terminate()
        except Exception as terminate_error:
            logger.warning(
                "插件 %s 回滚 terminate 失败: %s", record.name, terminate_error
            )
        raise LegacyPluginError(f"插件 {record.name} 初始化失败: {e}") from e

    # terminate 作为最后登记的 effect，卸载时最先执行（先 terminate 再解绑）
    handle.effects.add("legacy:terminate", instance.terminate)

    # 渠道在 initialize 成功后收集，保持旧语义
    channels_capability = ChannelsCapability(handle.contributions, handle.effects)
    for channel in _load_module_list(instance, "channels"):
        channels_capability.add(cast("Channel", channel))

    handle.instance = instance
    return instance


def _bind_lifecycle_handlers(
    instance: Any, import_path: str, scoped_bus: ScopedEventBus
) -> None:
    for md in plugin_registry.get_handlers_by_module_path(import_path):
        if md.kind != MetadataKind.LIFECYCLE:
            continue
        ctx_type = _EVENT_TYPE_MAP.get(md.event_type)  # type: ignore[arg-type]
        if ctx_type is None:
            continue
        scoped_bus.on(ctx_type, functools.partial(md.handler, instance))


def _register_tools(instance: Any, handle: PluginHandle, deps: Any) -> None:
    # 旧行为：宿主未提供 ToolRegistry 时静默跳过工具注册
    if deps.tool_registry is None:
        return
    from agent.tools.base import Tool as AgentTool

    tools_capability = ToolsCapability(
        deps.tool_registry, handle.effects, handle.contributions, handle.plugin_id
    )
    for md in plugin_registry.get_handlers_by_module_path(handle.record.import_path):
        if md.kind != MetadataKind.TOOL:
            continue
        bound = functools.partial(md.handler, instance, None)
        tool_name = md.tool_name or md.handler_name
        ToolCls = type(
            f"PluginTool_{tool_name}",
            (AgentTool,),
            {
                "name": tool_name,
                "description": (md.handler.__doc__ or "").strip(),
                "parameters": md.tool_schema
                or {"type": "object", "properties": {}, "required": []},
                "execute": _make_execute(bound),
            },
        )
        tools_capability.register(
            ToolCls(),
            risk=md.tool_risk or "read-write",
            always_on=bool(md.tool_always_on),
            search_hint=md.tool_search_hint,
        )
        logger.info("插件工具已注册: %s (来自 %s)", tool_name, handle.plugin_id)


def _bind_tool_hooks(instance: Any, handle: PluginHandle, import_path: str) -> None:
    hooks_capability = ToolHooksCapability(handle.contributions, handle.effects)
    for md in plugin_registry.get_handlers_by_module_path(import_path):
        if md.kind != MetadataKind.TOOL_HOOK:
            continue
        hook = _PluginToolHook(
            name=f"plugin:{getattr(instance, 'name', import_path)}:{md.handler_name}",
            handler=functools.partial(md.handler, instance),
            tool_name_filter=md.hook_tool_name,
        )
        hooks_capability.add(hook)
        logger.info("插件 tool hook 已注册: %s", hook.name)


def _collect_phase_modules(instance: Any, handle: PluginHandle) -> None:
    lifecycle = LifecycleCapability(handle.contributions, handle.effects)
    for slot in PHASE_SLOTS:
        modules = _load_module_list(instance, f"{slot}_modules")
        if modules:
            lifecycle.contribute(slot, modules)


def _collect_proactive_gates(instance: Any, handle: PluginHandle) -> None:
    from agent.core.proactive_turn.gates import ProactiveGate

    gates_capability = ProactiveGatesCapability(handle.contributions, handle.effects)
    for gate in _load_module_list(instance, "proactive_gates"):
        if not isinstance(gate, ProactiveGate):
            raise TypeError(
                f"插件 {type(instance).__name__}.proactive_gates 返回了无效 gate: "
                f"{type(gate).__name__}"
            )
        gates_capability.add(gate)
