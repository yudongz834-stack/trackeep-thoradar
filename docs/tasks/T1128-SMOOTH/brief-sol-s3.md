DELIVERY-T1128-SMOOTH-S3
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar-smooth-T1128；任务号=T1128-SMOOTH-S3；交付=空数据标记毒页修复、专项与回归证据。
轨道位置：胸科雷达顺畅改造·③.4 Sol S3 独立复核发现项返修。
R级：R2
判级理由：修复 Service Worker 缓存完整性校验漏口，属架构变更返修；不发布。
签发：PI 原话「算了，现在直接执行吧，不重启了」（2026-11-28）及「加快速度」「快点，做快一点啦！」；只修 Neon V1 已证实的一项漏口，不扩需求。
地形：仅改 `sw.js` 写入校验和 `tests/smooth/` 测试/证据；邻接 Cache Storage 健康副本与独立异常样本。
领域卡：无
经验卡：无卡。
Run 版本键：岗位卡=builder-jobspec 现役正本；轨道版本=T1128-SMOOTH v1；基线=S2 index `33c50bef...1def`、sw `f8a4e2bc...a24`。

## 唯一问题
Neon 的独立样本：HTTP 200、`text/html`、按顺序含 `/*__THORADAR_DATA_START__*/` 与 `/*__THORADAR_DATA_END__*/`、以 `</html>` 结束，但正文只有 156B 的损坏壳，没有 `const SITE_DATA = ...`。当前 sw 接受并覆盖健康缓存。原始证据：`D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/neon-v1/neon-v1-verify.json` 的 `adversarial-empty-markers-stub`。

## 只做这项修复
- 写域仅 `D:/trackeep/trackeep-product/trackeep-thoradar-smooth-T1128/sw.js`、`tests/smooth/`、`docs/tasks/T1128-SMOOTH/`。其它只读，禁改 Neon 文件、被审证据、旧回归、CI、任务地图。
- 在两个标记之间验证真实 `const SITE_DATA = <JSON>` 数据块：用 JSON.parse，不用 eval；对象必须含字符串 `briefing_date` 和数组 `papers`。允许合法的零篇数组，不得把零篇日误判为毒页。缺块、JSON 坏、字段类型错都拒缓存。
- 保留现有状态码/basic/MIME/标记顺序/完整 HTML 校验，不放宽其它路径。
- 把 Neon 的 156B 空标记样本加入施工自测；另加缺 SITE_DATA、坏 JSON、字段类型错与合法零篇样本。修复前应先复现红，修复后健康缓存字节不变；做一项删新校验变红的负对照。
- 复跑 S1、S2 全套和 UX；原始 stdout/stderr/JSON、哈希、环境、时间落盘。AICLS/POOLUP 的 R08 既有失真继续如实登记，不改旧测试。
- 不做其它改进，不 push/deploy/CDN，不碰真实凭证。尽快完成，若 10 分钟仍未修复，交当前证据并标未收口。

交付 `sol-s3-report.md` 和证据，报告三行头、地图影响、遗留风险、证据、地图终态齐全。最终尾部复述 `DELIVERY-T1128-SMOOTH-S3`。
