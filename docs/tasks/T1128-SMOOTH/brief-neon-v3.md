DELIVERY-T1128-SMOOTH-V3
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar-neon-v1；任务号=T1128-SMOOTH-V3；交付=Sol S4 两个边界漏口修复的独立复验。
轨道位置：胸科雷达顺畅改造·④ Neon V3 边界返修独立复验。
R级：R2
判级理由：复验 Service Worker 缓存写入校验返修；只读被审产品，不发布。
签发：PI 原话「算了，现在直接执行吧，不重启了」（2026-11-28）及「加快速度」「快点，做快一点啦！」；组合指定 agy Gemini 4 Neon 协助和验证。
地形：被审三件产品文件与 `tests/smooth/` 由派单方从 Sol S4 候选同步；复核写域仅本任务 `neon-v3/` 证据，不改产品、施工测试、旧回归、合同或任务地图。
领域卡：无
经验卡：无卡。
Run 版本键：岗位卡=verifier-jobspec 现役正本；基线=V2 报告及两个 `preserved=false` 原始探针；候选哈希以派单方同步后的三件文件现算为准。

## 独立复验范围
1. 新会话、只找错不施工。先记录 `index.html`、`sw.js`、`sw-retire.js` 哈希，并与 Sol S4 施工树逐字节核对；候选未同步或哈希不一致就停报，不拿旧 S3 结果冒充。
2. 亲自运行现有独立脚本 `node tests/neon-v2-verify.mjs <主仓 docs/tasks/T1128-SMOOTH/neon-v3/neon-v3-verify.json>`，保存 stdout/stderr。**不能只看进程退出码**：必须读取 JSON/输出，要求 `empty-briefing-date` 与 `comment-wrapped-site-data-stub` 都变为 `preserved=true`，且下一次导航仍渲染健康日期与论文数；任何 `preserved=false` 即复验失败。
3. 确认原空标记、坏 JSON、错字段类型等异常仍拒缓存，合法零篇仍接受；4 项核心负对照继续变红。复跑 S3 六项、S1 九项、S2 二十四项与 UX 46 项，保存原始输出。
4. 主仓整合前的 AICLS/POOLUP 结论沿用 V2：两套各 39/40、R08 测试选词失真未验。若 `index.html` 哈希相对 V2 改变则必须重跑；未变则不必重复耗时，不得写成 V3 新跑。
5. 只验这两个发现及既有核心回归，不再扩展新功能或无限寻找新边界。发现同一路径仍会污染健康缓存则列阻断；其它观察单列，不得掩盖。
6. 不 push/deploy/CDN，不访问真实 AI/NCBI/凭证；测试 Chrome 用独立临时配置并关闭。

交付 `D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/neon-v3/report.md`，三行头、结论/阻断/未验、实测命令与退出码、哈希、遗留风险、地图影响/终态齐全。最终尾部复述 `DELIVERY-T1128-SMOOTH-V3`。优先 5 分钟内交付；无法完成则保留证据并标未收口。
