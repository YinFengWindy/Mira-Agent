# Shiori 品牌母题图形

只保留品牌装饰图形(星芒、恶魔翅膀、蝴蝶结、樱瓣),用于空状态、加载、成就等情绪点缀场景。

**功能图标一律使用 Phosphor 或 `shared/icons.tsx` 中的原版图形,不再自绘**——这是 2026-09 视觉改造验收时定下的方向(自绘功能图标被逐一打回)。

## 绘制规则(新增母题时遵守)

- `viewBox="0 0 24 24"`,活动区域 20×20(四周留 2px)。
- 线性为主:`fill="none"`、`stroke="currentColor"`、`strokeWidth={1.7}`、圆头端点/转角。
- Duotone 副形:面积形用 `fill="currentColor"` + `opacity={0.15}`、无描边。
- 颜色只用 `currentColor`,组件签名 `({ className = "h-4 w-4" }: IconProps)`,svg 带 `aria-hidden="true"`。
