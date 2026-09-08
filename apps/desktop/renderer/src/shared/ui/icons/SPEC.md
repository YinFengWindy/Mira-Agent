# Shiori icon spec

自绘图标集,替代 Phosphor 与旧 `shared/icons.tsx`。目标气质:柔和、圆润、轻盈,与粉紫玻璃主题同源。

## 硬性规则

- `viewBox="0 0 24 24"`,活动区域 20×20(四周留 2px),关键笔画落在 0.5px 网格上。
- 线性为主:`fill="none"`、`stroke="currentColor"`、`strokeWidth={1.7}`、`strokeLinecap="round"`、`strokeLinejoin="round"`。
- Duotone 副形:面积型的次要形状用 `fill="currentColor"` + `opacity={0.15}`、无描边,让图标在任何语义色下自动出双色调。每个图标最多一个副形,小图标可以没有。
- 圆润语言:矩形 `rx>=3`;路径转角优先用圆弧;避免尖锐夹角(<60°)与细碎装饰。
- 单色继承:任何颜色都来自 `currentColor`,禁止硬编码色值。
- 组件形式:`export function XxxIcon({ className = "h-4 w-4" }: IconProps)`,`IconProps` 从 `./types` 导入;svg 上加 `aria-hidden="true"`。
- 语义命名与 Phosphor 对应表保持一致(如 `GearIcon` 对应 Phosphor `Gear`),便于逐步替换。

## 范本(以下四个为质量基准)

见 `brand.tsx` 中 `SparkleIcon`、`WingIcon`、`RibbonIcon`、`PetalIcon`。
功能图标以 `interface.tsx` 中最终验收过的形为准。

## 质量红线

- 视觉重量一致:并排 16px 渲染时没有一个明显更黑或更飘。
- 识别优先:宁可平庸可认,不要花哨难认。
- 不要用 `transform` 拼装(缩放会破坏线宽),直接按 24 网格画坐标。
