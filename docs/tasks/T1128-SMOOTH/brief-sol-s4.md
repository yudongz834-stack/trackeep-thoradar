DELIVERY-T1128-SMOOTH-S4
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar-smooth-T1128；任务号=T1128-SMOOTH-S4；交付=两个边界毒页修复与复验证据。
轨道位置：胸科雷达顺畅改造·③.4 Sol S4 边界发现项返修。
R级：R2
判级理由：Service Worker 缓存写入校验仍有同类污染路径；仅本机返修，不发布。
签发：PI 原话「算了，现在直接执行吧，不重启了」（2026-11-28）及「加快速度」「快点，做快一点啦！」；只修 Neon V2 两个实测探针，不扩需求。
地形：仅 `sw.js` 的 SITE_DATA 上下文/日期校验与 `tests/smooth/` 测试证据；邻接健康 Cache Storage。
领域卡：无
经验卡：无卡。
Run 版本键：岗位卡=builder-jobspec 现役正本；基线=S3 sw `900061dd45ad04e9f9c4391e5d2756f8b080a4bc4144ede9b913b6deabb5aa8b`。

## 只修两个已复现输入
独立脚本：`D:/trackeep/trackeep-product/trackeep-thoradar-neon-v1/tests/neon-v2-verify.mjs`；当前输出：`docs/tasks/T1128-SMOOTH/neon-v2/neon-v2-verify.stdout.txt` 第 11–12 行均为 `preserved=false`。
1. `empty-briefing-date`：合法 JSON 但日期为空字符串。要求 `briefing_date` 是 `YYYY-MM-DD` 且为真实有效日期，空串和非法日期拒缓存；合法零篇仍允许。
2. `comment-wrapped-site-data-stub`：整个数据声明放在 `<!-- ... -->` 注释里。校验声明必须位于真实 `<script>` 上下文且不在 HTML 注释中；拒绝注释包装。不得误拒正式 `index.html` 当前结构。

写域仅 `D:/trackeep/trackeep-product/trackeep-thoradar-smooth-T1128/sw.js`、`tests/smooth/`、`docs/tasks/T1128-SMOOTH/`。其它只读，禁改 Neon 文件、旧回归、CI、任务地图。

## 验证
- 把这两个样本加入施工测试；修复前复现红，修复后缓存原字节不变且下次仍显示健康 40 篇；至少一项删对应校验的负对照变红。
- 复跑 S3 六项、S1 九项、S2 二十四项、UX 46 项，保存原始输出和候选哈希。合法零篇必须继续接受。
- 主控会把同一 S3 候选交给 Neon 用 V2 独立脚本复跑，要求两个 PROBE 也变为 preserved=true。
- 不做其它改动，不 push/deploy/CDN。优先 5 分钟内交付；若不能，保存当前证据并标未收口。

交付 `sol-s4-report.md` 与证据，报告三行头、地图影响、遗留风险、证据、地图终态齐全。最终尾部复述 `DELIVERY-T1128-SMOOTH-S4`。
