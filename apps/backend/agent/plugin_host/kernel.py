"""插件内核：发现、装配、生命周期与失败回滚；对宿主暴露与旧 manager 同构的聚合面。

内核只拥有"插件如何被装配、启动、停止和清理"；phase 顺序、事件语义、
工具错误路径等产品语义仍由 Shiori 核心模块定义。
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from agent.plugin_host.capabilities import (
    BackgroundCapability,
    BotCommandsCapability,
    ChannelsCapability,
    LifecycleCapability,
    ProactiveGatesCapability,
    RpcCapability,
    ToolHooksCapability,
    ToolsCapability,
)
from agent.plugin_host.config_schema import (
    PluginConfigSchemaRegistry,
    resolve_config_model,
)
from agent.plugin_host.effects import EffectScope
from agent.plugin_host.events import ScopedEventBus
from agent.plugin_host.handle import PluginHandle, PluginRecord, PluginState
from agent.plugin_host.legacy import LegacyPluginError, load_legacy_plugin
from agent.plugin_host.manifest import (
    DEFAULT_ENTRY,
    ManifestError,
    load_manifest,
    synthesize_legacy_manifest,
)
from agent.plugin_host.plugin_data import (
    DISABLED_MARKER,
    migrate_legacy_disabled_marker,
    migrate_legacy_plugin_config,
    open_plugin_kv,
)
from agent.plugin_host.rpc import PluginRpcRegistry
from agent.plugin_host.runtime_context import PluginRuntimeContext
from bus.event_bus import EventBus

logger = logging.getLogger(__name__)

# 启停状态与插件自己的配置同住 [plugins.<id>] 表，但它归宿主所有、不是插件配置
# 模型的字段。凡是整表读写这张表的地方都必须认得这个键，否则会互相覆盖。
PLUGIN_ENABLED_CONFIG_KEY = "enabled"


@dataclass
class HostServices:
    """宿主提供给插件装配的服务集合；capability 只暴露其中被声明的切面。"""

    event_bus: EventBus
    tool_registry: Any = None
    workspace: Path | None = None
    session_manager: Any = None
    memory_engine: Any = None
    app_config: Any = None
    light_provider: Any = None
    light_model: str = ""
    plugin_configs: dict[str, dict[str, Any]] = field(default_factory=dict)
    relationship_runtime: Any = None
    # 插件包上移到仓库顶层之前的位置（apps/backend/plugins）。gitignore 覆盖的
    # 本地状态（.kv.json / plugin.disabled）不会随目录重命名搬走，需要从这里
    # 一次性迁移；打包形态下该目录不存在，字段为 None 即可。
    legacy_plugin_root: Path | None = None


class PluginKernel:
    """cordis 风格插件内核：作用域 effect 回滚 + capability 注入。

    对 bootstrap 暴露与旧 PluginManager 相同的聚合属性（load_all、
    loaded_count、七个 phase 列表、tool_hooks、channels、proactive_gates、
    telegram_bot_commands、terminate_all），使宿主接线保持不变。
    """

    def __init__(
        self,
        plugin_dirs: list[Path],
        *,
        services: HostServices,
        namespace: str = "",
        strict: bool = False,
    ) -> None:
        self._dirs = plugin_dirs
        self._services = services
        self._namespace = namespace
        self._strict = strict
        self._handles: dict[str, PluginHandle] = {}
        self._active_order: list[str] = []
        # 每个内核（= 每个 runtime generation）独立一份 RPC/配置 schema 注册表
        self.rpc = PluginRpcRegistry()
        self.config_schemas = PluginConfigSchemaRegistry()

    # ── 发现 ──────────────────────────────────────────────────────────────

    def discover(self) -> list[PluginRecord]:
        """扫描插件目录；同名 first-wins，legacy 目录必须含 plugin.py。"""
        records: list[PluginRecord] = []
        seen_names: set[str] = set()
        for d in self._dirs:
            if not d.is_dir():
                continue
            source = d.name
            for child in sorted(d.iterdir()):
                if not child.is_dir():
                    continue
                if child.name in seen_names:
                    logger.warning("插件名重复，跳过: %s (%s)", child.name, child)
                    continue
                record = self._build_record(child, source)
                if record is None:
                    continue
                seen_names.add(child.name)
                records.append(record)
        return records

    def _build_record(self, child: Path, source: str) -> PluginRecord | None:
        try:
            manifest = load_manifest(child)
        except ManifestError as e:
            logger.warning("插件 manifest 无效，跳过: %s (%s)", child.name, e)
            if self._strict:
                raise
            return None
        except Exception as e:
            logger.warning("manifest.yaml 读取失败 (%s): %s", child, e)
            manifest = None
        if manifest is None or not manifest.is_v2:
            # legacy 目录（含旧四字段 manifest）以 DEFAULT_ENTRY（backend/plugin.py）
            # 为准入条件；与 manifest.py 共享同一个常量，避免布局改一处漏一处
            if not (child / DEFAULT_ENTRY).exists():
                return None
            manifest = synthesize_legacy_manifest(child)
        entry_file = child / manifest.entry
        suffix = f"_{self._namespace}" if self._namespace else ""
        return PluginRecord(
            name=child.name,
            plugin_dir=child,
            entry_file=entry_file,
            import_path=f"akasic_plugin_{source}_{child.name}{suffix}",
            manifest=manifest,
        )

    # ── 加载 ──────────────────────────────────────────────────────────────

    async def load_all(self) -> None:
        for record in self.discover():
            await self._load_one(record)

    async def load(self, name: str) -> bool:
        """按目录名加载单个已发现插件；已激活时幂等返回 True。"""
        for record in self.discover():
            if record.name == name:
                await self._load_one(record)
                handle = self._handles.get(name)
                return handle is not None and handle.state is PluginState.ACTIVE
        return False

    async def _load_one(self, record: PluginRecord) -> None:
        existing = self._handles.get(record.name)
        if existing is not None and existing.state is PluginState.ACTIVE:
            return
        handle = PluginHandle(record=record, effects=EffectScope(record.manifest.id))
        self._handles[record.name] = handle
        migrate_legacy_disabled_marker(
            record.plugin_dir, handle.plugin_id, self._services.legacy_plugin_root
        )
        migrate_legacy_plugin_config(
            record.plugin_dir, handle.plugin_id, self._services.legacy_plugin_root
        )
        if (record.plugin_dir / DISABLED_MARKER).exists():
            handle.state = PluginState.DISABLED
            logger.info("插件已禁用（%s）: %s", DISABLED_MARKER, record.name)
            return
        if not self._config_enabled(record.manifest.id):
            handle.state = PluginState.DISABLED
            logger.info("插件已禁用（配置状态）: %s", record.name)
            return
        handle.state = PluginState.LOADING
        try:
            self._import_entry(handle)
            self._register_config_schema(handle)
            if record.manifest.is_v2:
                await self._setup_v2(handle)
            else:
                scoped_bus = ScopedEventBus(self._services.event_bus, handle.effects)
                handle.instance = await load_legacy_plugin(
                    handle, scoped_bus=scoped_bus, deps=self._services
                )
        except Exception as e:
            await self._rollback_failed_load(handle, e)
            if self._strict:
                raise
            return
        handle.state = PluginState.ACTIVE
        self._active_order.append(record.name)
        logger.info("插件已加载: %s", record.name)

    def _config_enabled(self, plugin_id: str) -> bool:
        """Reads the ``[plugins.<id>].enabled`` config flag; absent means enabled.

        This is the enable/disable source of truth introduced by issue #174
        (desktop plugin management list, hot load/unload) — independent of
        the legacy ``plugin.disabled`` marker file above, which stays as-is
        for compatibility but is not something new code should rely on.
        """
        stored = self._services.plugin_configs.get(plugin_id, {})
        return bool(stored.get(PLUGIN_ENABLED_CONFIG_KEY, True))

    def _import_entry(self, handle: PluginHandle) -> None:
        record = handle.record
        # 先登记命名空间清理（最后处置），代际热重载时不残留 sys.modules 条目
        if self._namespace:
            handle.effects.add(
                "import:namespace",
                lambda: _purge_modules(record.import_path),
            )
        try:
            _import_module(record.import_path, record.entry_file)
        except Exception as e:
            # 导入可能已部分触发 __init_subclass__ 注册，回滚 registry
            from agent.plugins.registry import plugin_registry

            plugin_registry.remove_plugin(record.import_path)
            raise LegacyPluginError(f"插件 {record.name} 导入失败: {e}") from e

    def _register_config_schema(self, handle: PluginHandle) -> None:
        """解析并登记插件的配置模型（若声明了）；失败时向上抛出触发本插件回滚。

        model 解析对 v2 manifest 的 ``config_model`` 与 legacy ``ConfigModel``
        类属性一视同仁（后者要求入口模块已导入完成 __init_subclass__ 注册，
        此时机点在 _import_entry 之后，两条路径都已满足）。
        """
        model_cls = resolve_config_model(handle.record)
        if model_cls is None:
            return
        self.config_schemas.register(handle.plugin_id, model_cls)
        handle.effects.add(
            "config_schema",
            lambda: self.config_schemas.unregister(handle.plugin_id),
        )

    async def _setup_v2(self, handle: PluginHandle) -> None:
        module = sys.modules[handle.record.import_path]
        setup = getattr(module, "setup", None)
        if not callable(setup):
            raise ManifestError(
                f"v2 插件 {handle.record.name} 的入口缺少 setup(ctx) 函数"
            )
        setup_fn = cast(
            "Callable[[PluginRuntimeContext], Awaitable[None]]", setup
        )
        context = PluginRuntimeContext(
            plugin_id=handle.plugin_id,
            plugin_dir=handle.record.plugin_dir,
            manifest=handle.record.manifest,
            effects=handle.effects,
            capabilities=self._build_capabilities(handle),
        )
        await setup_fn(context)

    def _build_capabilities(self, handle: PluginHandle) -> dict[str, Any]:
        from agent.plugins.config import PluginConfig

        services = self._services
        builders: dict[str, Any] = {
            "events": lambda: ScopedEventBus(services.event_bus, handle.effects),
            "kv": lambda: open_plugin_kv(
                workspace=services.workspace,
                plugin_id=handle.plugin_id,
                plugin_dir=handle.record.plugin_dir,
                legacy_plugin_root=services.legacy_plugin_root,
            ),
            "config": lambda: PluginConfig(
                services.plugin_configs.get(handle.plugin_id, {})
            ),
            "tools": lambda: ToolsCapability(
                services.tool_registry,
                handle.effects,
                handle.contributions,
                handle.plugin_id,
            ),
            "lifecycle": lambda: LifecycleCapability(
                handle.contributions, handle.effects
            ),
            "tool_hooks": lambda: ToolHooksCapability(
                handle.contributions, handle.effects, handle.plugin_id
            ),
            "proactive_gates": lambda: ProactiveGatesCapability(
                handle.contributions, handle.effects
            ),
            "channels": lambda: ChannelsCapability(
                handle.contributions, handle.effects
            ),
            "background": lambda: BackgroundCapability(
                handle.effects, handle.plugin_id
            ),
            "bot_commands": lambda: BotCommandsCapability(
                handle.contributions, handle.effects
            ),
            "rpc": lambda: RpcCapability(self.rpc, handle.effects, handle.plugin_id),
        }
        return {
            name: builders[name]()
            for name in handle.record.manifest.capabilities
            if name in builders
        }

    async def _rollback_failed_load(
        self, handle: PluginHandle, error: Exception
    ) -> None:
        logger.warning("插件 %s 加载失败，回滚: %s", handle.record.name, error)
        _ = await handle.effects.dispose_all()
        handle.contributions = type(handle.contributions)()
        handle.state = PluginState.FAILED
        handle.error = error

    # ── 卸载 ──────────────────────────────────────────────────────────────

    async def unload(self, name: str) -> list[Exception]:
        """卸载单个插件：逆序处置其全部 effect，其他插件不受影响。"""
        handle = self._handles.get(name)
        if handle is None or handle.state is not PluginState.ACTIVE:
            return []
        handle.state = PluginState.UNLOADING
        errors = await handle.effects.dispose_all()
        handle.contributions = type(handle.contributions)()
        handle.instance = None
        handle.state = PluginState.DISPOSED
        if name in self._active_order:
            self._active_order.remove(name)
        # 允许再次 load：丢弃已处置句柄
        self._handles.pop(name, None)
        return errors

    async def terminate_all(self) -> None:
        """Releases only this kernel's subscriptions, plugins and import namespace."""
        errors: list[Exception] = []
        for name in list(self._active_order):
            errors.extend(await self.unload(name))
        self._handles.clear()
        if errors:
            raise ExceptionGroup("Plugin cleanup failed", errors)

    # ── 聚合面（与旧 PluginManager 同构，供 bootstrap 接线） ────────────────

    @property
    def loaded_count(self) -> int:
        return len(self._active_order)

    def states(self) -> list[dict[str, str]]:
        """Returns per-plugin lifecycle snapshots for diagnostics."""
        return [handle.describe() for handle in self._handles.values()]

    def _active_handles(self) -> list[PluginHandle]:
        return [self._handles[name] for name in self._active_order if name in self._handles]

    def _collect_phase(self, slot: str) -> list[object]:
        modules: list[object] = []
        for handle in self._active_handles():
            modules.extend(handle.contributions.phase_modules[slot])
        return modules

    @property
    def before_turn_modules(self) -> list[object]:
        return self._collect_phase("before_turn")

    @property
    def before_reasoning_modules(self) -> list[object]:
        return self._collect_phase("before_reasoning")

    @property
    def prompt_render_modules(self) -> list[object]:
        return self._collect_phase("prompt_render")

    @property
    def before_step_modules(self) -> list[object]:
        return self._collect_phase("before_step")

    @property
    def after_step_modules(self) -> list[object]:
        return self._collect_phase("after_step")

    @property
    def after_reasoning_modules(self) -> list[object]:
        return self._collect_phase("after_reasoning")

    @property
    def after_turn_modules(self) -> list[object]:
        return self._collect_phase("after_turn")

    @property
    def tool_hooks(self) -> list[Any]:
        return [h for handle in self._active_handles() for h in handle.contributions.tool_hooks]

    @property
    def channels(self) -> list[Any]:
        return [c for handle in self._active_handles() for c in handle.contributions.channels]

    @property
    def proactive_gates(self) -> list[Any]:
        return [g for handle in self._active_handles() for g in handle.contributions.proactive_gates]

    @property
    def telegram_bot_commands(self) -> list[tuple[str, str]]:
        """聚合两条来源：legacy 实例的 telegram_bot_commands() 与 v2 的 bot_commands 贡献。

        迁移期两条路径并存，任何一侧插件的命令都不应"静默消失"；两条来源之间不做
        去重，若同一命令被两侧同时贡献会重复出现（目前没有插件这样做，暂不处理）。
        """
        commands: list[tuple[str, str]] = []
        for handle in self._active_handles():
            getter = getattr(handle.instance, "telegram_bot_commands", None)
            if getter is not None:
                for command, description in getter():
                    commands.append((str(command), str(description)))
            commands.extend(handle.contributions.bot_commands)
        return commands


def _import_module(module_name: str, path: Path) -> None:
    # 把入口文件当成包加载，允许插件内部相对 import；先入 sys.modules 再执行
    spec = importlib.util.spec_from_file_location(
        module_name,
        path,
        submodule_search_locations=[str(path.parent)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载插件文件: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)


def _purge_modules(import_path: str) -> None:
    for module_name in tuple(sys.modules):
        if module_name == import_path or module_name.startswith(import_path + "."):
            _ = sys.modules.pop(module_name, None)
