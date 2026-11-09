【委任状】
轨道位置：ThorRadar 原型交叉审计席（审对手卷，只读不改）
R级：R1（审计意见供主控汇总拍板，不落产线）
判级理由：PI 授权额度换速度的交叉审计环节，独立于被审卷作者
签发：M席（主控）2026-11-07
键字段：XREV-GROK-KIMI
目标目录：D:	rackeep-thoradar（/d/trackeep-thoradar，审计对象在其 design 子目录）

# 任务：审计 Kimi 的两版原型 proto-a-view-radar.html 与 proto-b-widget.html
对照标准（PI 纠偏令 v2，原文在 proto-brief-1107-kimi-a.md 顶部）：
1. 底版＝产线 index.html 原样复制（可 diff 验证：`git diff --no-index ../index.html g-proto-a-view-radar.html | head -100` 看改动面（B 版同法））
2. 版块小改不大改（禁 hero/禁新配色/禁重排布局语法）
3. 交互层是否真实现了：视图切换器（概览/阅读/个性化）三态可切？雷达改独立视图？阅读态标题截断放开？个性化全屏态？
4. JS 切换逻辑追踪：两版各自切换器 click 处理器改哪些元素显隐？B 版挂件（阅读态缩角落可展开）真的实现了吗？有没有死按钮或漏切换？
5. 引擎注入标记（__THORADAR_DATA_*）是否保留（保留＝以后可接引擎数据）？

交卷 ≤40 行：先一句话总评（可上线级/方向对细节糊/跑偏），再列发现（每条带行号），最后「遗留风险」节 ≥30 字。只读，不改任何文件。
