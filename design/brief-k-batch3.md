# Batch3 前端席任务书（Kimi K3 · K3-B 生产化）

## 委任状（五行简化版）
- 轨道位置：trackeep-thoradar → 施工席（前端）
- R 级：R2——只允许新建/修改 `D:\trackeep-thoradar\design\index-batch3.html` 这一个文件（不得碰 index.html、engine、config、data）
- 签发：Orchestrator，2026-10-18，PI 口谕「开工」
- 你的上一作 k3-b.html 被 PI 终审定案——这次把它接上真管线

## 输入
- UI 底稿：`design/k3-b.html`（视觉语言、token 冻结块、雷达图交互逐字保留）
- 数据契约参照：现役 `index.html` 里 `/*__THORADAR_DATA_START__*/` 到 `/*__THORADAR_DATA_END__*/` 之间的 `const SITE_DATA = {...}`（真实 10-17 数据，schema 即契约）
- 滚动窗数据：`data/radar_latest.json`（同 papers schema，90 天滚动去重档，由引擎生成——本次先按契约写 fetch，文件后到）

## 硬性契约（违者返工）
1. **注入标记**：成品必须含 `/*__THORADAR_DATA_START__*/` 与 `/*__THORADAR_DATA_END__*/` 两个标记行，中间是 `const SITE_DATA = {...};`——引擎用字符串区间替换注入，标记行一字不能动。开发时把现役 index.html 的 SITE_DATA 原样嵌进去当测试数据。
2. **滚动窗合并**：页面加载时 `fetch('data/radar_latest.json')`（相对路径）。成功→与 SITE_DATA.papers 按 pmid 去重合并（radar_latest 优先，今天数据以 SITE_DATA 为准）；**失败→静默降级只用注入数据**，控制台留一行提示即可，不许白屏。
3. **时间滑杆**：1–90 天连续拖动。锚点＝数据里最大 briefing_date（不是今天——档案测试数据是旧的）；滑 N 天显示窗口内论文，滑杆旁诚实标注「数据窗口 MM-DD ~ MM-DD · N 天」。窗口内无论文→诚实空态（不凑数）。
4. **档位过滤**：S/A/B/C 四个可多选 chip（默认全开），与滑杆、单刊过滤叠加。
5. **单刊点选**：雷达图扇区/图例点选→列表过滤到该刊；再点或「清除」恢复。
6. **三态显示**：status.kind = retracted → 🚫 已撤稿（醒目、置灰解读）；concern → ⚠ 关注声明；corrected → 📄 更正启事；publish_state = degraded → 「解读暂停」样式。空 ok 不动。
7. **诚实渲染**：if_val/zone/日期/期数全部实况渲染，空值「—」；禁止任何硬编码数字、演示钮、假期号。
8. 零 CDN、单文件、token 冻结块逐字。

## 输出（唯一允许写的文件）
`design/index-batch3.html`。交付时在文件头注释写：合并策略、三态分支、滑杆锚点各一行。

## 禁区
- 只写上述一个文件；不跑引擎、不改配置、禁 git、禁联网
- Python 不需要；验证靠读代码与内嵌测试数据自查（可在浏览器打开 file:// 自查渲染）
