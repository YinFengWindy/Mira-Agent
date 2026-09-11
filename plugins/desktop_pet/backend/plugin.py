from __future__ import annotations

from typing import TYPE_CHECKING

from plugins.desktop_pet.backend.rpc import DesktopPetRpcHandlers
from plugins.desktop_pet.backend.tool import DesktopPetActionTool

if TYPE_CHECKING:
    from agent.plugin_host.runtime_context import PluginRuntimeContext


async def setup(ctx: "PluginRuntimeContext") -> None:
    """装配 desktop_pet 后端：角色动作工具 + 绑定解析 RPC。

    从 legacy ``Plugin`` ABC 迁到 v2 ``setup(ctx)``（#181-C）。动机不是迁移
    本身，而是 ``ctx.rpc``：桌宠 controller 这一步搬进插件宿主渲染进程后，
    只能调 ``plugin.desktop_pet.*``，而它需要知道该渲染哪个角色的哪个桌宠包。
    legacy 适配器给的是旧 ``PluginContext`` 上帝对象，没有 RPC 登记入口。

    这里不需要 ``ctx.effect``：``ctx.tools.register`` 与 ``ctx.rpc.register``
    各自把反注册登记进 EffectScope，卸载时自动回收；插件本身不持有别的
    资源（没有任务、没有连接、没有文件监听），所以也就没有 #227 那个
    LIFO 顺序问题可踩。
    """
    # 局部导入：与 novelai 的 `_register_rpc` 同一条纪律，插件模块加载期不把
    # 桌面桥接的依赖链拉进来（见 capabilities.RpcCapability.register 的注释）。
    from desktop_bridge.method_policy import Concurrency

    # 宿主那一个 RoleStore，不是 RoleStore(ctx.workspace)。写锁是按实例的
    # threading.RLock，自己新建一个就是新建一把锁——本插件现在会写 pet 包
    # （pets.import/remove/select 都是读-改-写整份角色清单），两把锁竞写同一份
    # roles.json 会互相覆盖。见 manifest.KNOWN_CAPABILITIES 里 role_store 那段。
    role_store = ctx.role_store
    if role_store is None:
        raise RuntimeError("桌宠插件需要 role_store")
    ctx.tools.register(
        DesktopPetActionTool(
            role_store=role_store,
            event_bus=ctx.events,
            tool_registry=ctx.tools,
        ),
        risk="external-side-effect",
        always_on=True,
        search_hint="桌宠 移动 位置 动作 挥手 跳跃",
    )
    handlers = DesktopPetRpcHandlers(role_store=role_store)
    ctx.rpc.register(
        "binding.get", handlers.binding_get, concurrency=Concurrency.READ_ONLY
    )
    ctx.rpc.register("pets.list", handlers.pets_list, concurrency=Concurrency.READ_ONLY)
    # 三个写方法用默认的 Concurrency.MUTATION，与它们此前作为 roles.pets.*
    # 走 _DEFAULT_POLICY 时的并发语义一致。
    ctx.rpc.register("pets.import", handlers.pets_import)
    ctx.rpc.register("pets.remove", handlers.pets_remove)
    ctx.rpc.register("pets.select", handlers.pets_select)
