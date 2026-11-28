DELIVERY-T1128-SMOOTH-A3
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar-neon-v1；任务号=T1128-SMOOTH-A3；交付=Sol S4 两个边界漏口修复的独立复验。
轨道位置：胸科雷达顺畅改造·④ Astra V3 边界返修独立复验。
R级：R2
判级理由：复验 Service Worker 缓存写入校验返修；只读被审产品，不发布。
签发：PI 原话「继续做，我睡一会，然后我看agy额度好像已经没有了，但是你需要把活干完」（2026-11-28）；据此将验证席从 agy Neon 换成未参与施工的 Codex Astra 新会话，不降低复验标准。
地形：被审三件产品文件与 `tests/smooth/` 由派单方从 Sol S4 候选同步；复核写域仅 `astra-v3/` 证据和复核自有测试适配副本，不改产品、施工测试、旧回归、合同或任务地图。
领域卡：无
经验卡：无卡。
Run 版本键：岗位卡=verifier-jobspec 现役正本；基线=Neon V2 报告及两个 `preserved=false` 原始探针；候选 `index.html=33c50bef...1def`、`sw.js=e882e9e2...394f`、`sw-retire.js=5ae38f2b...6199`，须现算全值核对。

## 独立复验范围
1. 新会话、只找错不施工。先记录三件哈希并与 Sol S4 施工树逐字节核对；候选未同步或不一致就停报，不拿旧 S3 结果冒充。
2. 原 `tests/neon-v2-verify.mjs` 的内存变异锚点仍按 S3 写法，直接在 S4 会锚点漂移。可在 `astra-v3/` 建自己的运行副本，只适配 `s3GuardBlock` 到 S4 当前源码并保留样本、判定和其它变异，不得改产品或放宽 `preserved` 判据。保存适配 diff。亲自运行该独立对抗脚本，保存 stdout/stderr/JSON。
3. **不能只看进程退出码**：读取 JSON/输出，要求 `empty-briefing-date` 与 `comment-wrapped-site-data-stub` 均为 `preserved=true`，缓存字节保持 539012，下一次导航仍渲染健康日期与论文数；任何 `preserved=false` 即失败。原空标记、坏 JSON、错字段类型仍拒缓存，合法零篇仍接受。
4. S4 的脚本上下文校验会纵深拦住部分旧变异，因此不得机械要求旧 4 项全部变红。逐项记录：MIME 与 503 撤防应变红；其余若 SURVIVED，须确认缓存未污染并解释是 S4 新防护接住。另亲自运行 Sol 留下的 `no-date-guard.sw.js`、`no-script-guard.sw.js` 两个变异工人，专项应分别 7/2、8/1，证明新防护撤掉后测试确实变红。
5. 复跑 S3 九项、S1 九项、S2 二十四项与 UX 46 项，保存原始输出。`index.html` 相对 Neon V2 未变，AICLS/POOLUP 沿用 V2 各 39/40、R08 测试失真未验；不冒充本轮新跑。
6. 只验这两个发现及既有核心回归，不扩新功能。发现仍会污染健康缓存列阻断；其它观察单列，不掩盖。
7. 不 push/deploy/CDN，不访问真实 AI/NCBI/凭证；测试 Chrome 用独立临时配置并关闭，按 PID 核身份验尸。

交付 `D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/astra-v3/report.md`，三行头、结论/阻断/未验、实测命令与退出码、哈希、遗留风险、地图影响/终态齐全。最终尾部复述 `DELIVERY-T1128-SMOOTH-A3`。优先完成核心对抗与 S3/S1/S2，再补 UX；无法完成则保留证据并标未收口。
