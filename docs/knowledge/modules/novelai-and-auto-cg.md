---
title: NovelAI 与自动 CG
kind: 领域说明
status: 当前有效
last_verified_commit: 966af779
source_paths:
  - plugins/scene_awareness/
  - plugins/novelai/
  - apps/backend/desktop_bridge/role_difference_service.py
  - apps/backend/desktop_bridge/story_image_generator.py
  - apps/desktop/renderer/src/app/useChatImageRegeneration.ts
  - apps/backend/bus/events_lifecycle.py
related:
  - roles.md
  - conversations-and-sessions.md
  - agent-lifecycle-and-tools.md
---

# NovelAI 与自动 CG

## NovelAI 基础能力

`plugins/novelai/backend/` 拥有设置、请求模型、HTTP 客户端、提示词标签、持久化、`NovelAIService.generate()`、生图工具、自动 CG 与 RPC。`plugins/novelai/ui/` 拥有 Image Studio、提示词标签库与历史界面，经 `nav.page` / `settings.section` 注册页面与设置。

手动 `generate_image` 工具和自动 CG 都应复用该服务，避免各自实现请求与错误处理。生成文件与元数据由插件写入 workspace 下的 `private_runtime/novelai/`；运行数据不应随插件停用或包升级删除。

启停只由宿主管理的 `[plugins.novelai].enabled` 决定，插件配置表单与运行时设置不再声明第二个 `enabled`。插件停用后，宿主撤销工具、RPC 与事件订阅。服务仍检查 Token，角色自动 CG 偏好仍独立生效。

## 插件归属核查（2026-09-11）

结论：核心生图实现已归位，但还不是完全可摘出的插件。以下为本轮源码核查发现，除重复 Enabled 状态外，本轮未修改这些边界。

| 残留 | 证据 | 影响 |
| --- | --- | --- |
| 聊天图片重生成由宿主编排 | `apps/desktop/renderer/src/app/useChatImageRegeneration.ts` 直接创建 `createPluginRpcClient("novelai")`；`main.tsx` 的 `canRegenerateLightboxImage` 只判断会话与消息 ID | 停用插件后，重生成按钮仍可能可点击；宿主尚无按插件能力注册的图片操作入口 |
| RPC 超时策略识别 NovelAI 方法名 | `apps/desktop/src/bridge/bridgeTimeoutPolicy.ts` 写死两个 `plugin.novelai.*` 方法的 5 分钟超时 | 新增插件长耗时 RPC 仍需修改宿主策略 |
| 故事与角色差分调用方持有供应商细节 | `story_image_generator.py` 固定 `nai-diffusion-4-5-full`；`story_simulation/director.py` 要求 NovelAI V4.5 标签；`role_difference_service.py` 固定 sampler、steps、strength 等参数 | 已通过工具调用而非直接导入插件服务，但供应商参数策略仍分散在宿主 |
| 角色自动 CG 开关属于核心角色表单 | `RoleCapabilitiesPanel.tsx`、`roleFormState.ts`、`appState.ts`、`useRoleManagement.ts` 与共享 `RoleForm` 持有 `autoSceneCgEnabled` | 停用插件不会撤下这项角色配置；尚无插件角色设置扩展位 |
| 品牌资源尚未共置 | `plugins/novelai/ui/index.tsx` 引用宿主 `assets/novelai-logo-dark.svg` | 插件包仍依赖宿主存放自己的 Logo |
| 插件仍直接调用部分宿主内部接口 | UI 使用 `window.miraDesktop.invoke("roles.list")`、`pickImages`；后端导入私有 `_resolve_path`、`DesktopSessionPresenter` 并直接创建 `RoleStore` | 共置不等于稳定 SDK 隔离；共享样式和通用类型复用本身不算归位遗漏 |

宿主中的 `_migrate_legacy_novelai_config()` 是升级旧 `[integrations.novelai]` 配置的一次性迁移，需要在插件加载前运行，不应仅为了清空关键字引用而移除。`SceneObservationCommitted` 是 Scene Awareness 与 NovelAI 共享的事件契约，也无需搬入 NovelAI 私有实现。角色差分和故事业务可以保留在各自模块，但供应商专属策略应逐步交回生图提供方。

本轮通过真实插件配置通道验证：表单不再暴露 Enabled，修改 NSFW 设置可保存并读回，显式启用与省略启用字段均保持插件 ACTIVE。插件测试另验证宿主禁用时不注册生图工具/RPC，以及卸载清理和自动 CG 任务释放。

## 自动 CG 生命周期

1. Scene Awareness 插件在 `BeforeTurn` 捕获被动回合上下文，并在 `AfterTurn` 对非空回复调度场景判断；主动消息则从 `ProactiveMessageCommitted` 接入同一判断链。
2. `plugins/scene_awareness/backend/decision.py` 使用独立观察器 system prompt，并强制模型调用内部函数 `submit_scene_observation`，将结果归为 `started`、`same`、`changed`、`closed` 或 `none`。观察结果同时携带持续场景 `scene_key` 与可见定格 `visual_key`。
3. Scene Awareness 对函数参数执行协议和语义校验；有效结果才会持久化这两个键并发布 `SceneObservationCommitted`。`scene_key` 供场景追问保持连续性，`visual_key` 供图片生成判断重复。
4. NovelAI 插件订阅场景观察事件，`AutoCgController` 根据视觉定格、冷却和手动生成抑制规则决定是否生成。
5. 成功图片通过消息推送发送，并同步回权威角色会话。

`AfterTurnCtx.will_dispatch` 只表示核心消息总线是否还需下发回复，不表示回合是否完成。桌面桥接直接取得回复时该值为 `false`，场景观察仍必须处理这个有效回合。

## 防重复与失败处理

- 自动生成冷却为 5 个用户回合。
- `scene_key` 表示持续场景；`visual_key` 表示当前可见定格。自动 CG 使用 `visual_key` 去重，因此同一场景中的动作、姿势、人物位置关系、构图、服装、道具或光线变化可以生成新的 CG。
- `same + should_generate=true` 表示持续场景不变但视觉定格变化；它必须提供新的 `visual_key`，并在普通 5 回合冷却结束后生成。
- 重复定格的策略日志使用 `scene_cg_duplicate_visual`，不再把持续场景本身标记为重复。
- 当前回合若已经调用 `generate_image`，不再追加自动 CG。
- 场景协议无效时，观察器会携带校验原因请求一次修复；控制器不再对同一请求做无反馈重试。
- 修复后仍无效时，不发布场景事件，也不写入场景状态；日志只记录工具调用数量、工具名、参数键和文本长度等响应形态。
- 图片生成保留自身重试；主回复不因后台自动 CG 失败而失败。
- `started` 建立首个场景，`same` 延续当前场景，`changed` 建立新场景，`closed` 关闭场景状态，`none` 表示当前没有可观测场景。
- `started` 和 `changed` 必须携带新的稳定 `scene_key`、`visual_key` 与完整 CG 参数；同一场景的视觉变化使用 `same`、原 `scene_key`、新的 `visual_key` 和完整 CG 参数；完全相同的定格使用 `same`、原有两个键且不生成；`closed` 和 `none` 的场景、视觉和图像字段必须为空。

## 修改影响

- 修改冷却、`scene_key` 或 `visual_key`：检查状态持久化、重复图片、会话切换、角色隔离和场景追问连续性。
- 修改场景判断输出：同步更新工具 schema、五态迁移、场景/视觉键语义校验和协议修复。
- 修改图片生成：检查手动工具与自动 CG 的共享服务、提示词标签、素材和消息附件格式。
- 修改消息推送：确认渠道收到图片，且 Session/Conversation 中也保留对应消息。

## 验收重点

至少覆盖：无场景结果不落状态、场景开始和切换时生成、同一场景的视觉变化在 5 回合冷却后生成、完全相同定格不重复生成、场景关闭后清理、同回合手动生成抑制、协议反馈修复、协议失败不发事件、生成重试、后台失败不阻塞文本回复、成功图片同步到权威会话。
