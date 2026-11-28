DELIVERY-T1128-SMOOTH-V1
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar-neon-v1；任务号=T1128-SMOOTH-V1；交付=独立复验报告、主动查错证据与原始输出。
轨道位置：胸科雷达顺畅改造·④ Neon V1 独立复验。
R级：R2
判级理由：独立复核 Service Worker 架构变更；只验本机候选，不含发布。
签发：PI 原话「算了，现在直接执行吧，不重启了」（2026-11-28）及指定 agy Gemini 4 Neon 协助和验证。
地形：被审对象=`D:/trackeep/trackeep-product/trackeep-thoradar-smooth-T1128`（零写入）；独立复核树=`D:/trackeep/trackeep-product/trackeep-thoradar-neon-v1`；入口为真实 Chrome、首页导航、异常响应、退出与多日降级。
领域卡：无
经验卡：无卡。
Run 版本键：岗位卡=verifier-jobspec 现役正本；轨道版本=T1128-SMOOTH v1；候选哈希：index `33c50bef723b0a3f32b51bc2d5927ff4391bb58eb474996f1a7d9dff96bc1def`，sw `f8a4e2bc4d5d81964475580c012e825281f409a171782640ad5cbc68a07bca24`，retire `5ae38f2ba965f4e1b1d340da2ba5fadd8b58af82a1e271a02ddff97ab5686199`。

## 独立性与写域
先读 `D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/acceptance-contract.md`，先亲自跑和查错，再读施工报告。不得修改被审工作树、主仓产品文件、施工测试、验收合同、旧回归或任务地图。
只可写：独立复核树 `D:/trackeep/trackeep-product/trackeep-thoradar-neon-v1` 和报告目录 `D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/neon-v1/`。独立树代码哈希须先与上面三个值核对，不符立即停手。

## 必做查错
1. 亲自重跑 `tests/smooth/verify-s1.mjs`、`tests/smooth/verify-s2.mjs` 和 UX 原脚本；保存退出码、stdout/stderr、机器 JSON。对 AICLS/POOLUP 的 R08 原始证据判断它究竟证明产品差异、测试失真还是未验，不得把 39/40 写成产品全绿。
2. 用完整正式页面自行构造至少三类施工任务书未点名的异常输入，至少包括：
   - HTTP 200、完整 HTML，但 `DATA_END` 出现在 `DATA_START` 前面；
   - HTTP 200、`Content-Type: application/json`，正文却是带完整官方标记的 HTML；
   - HTTP 503，正文却是完全合法且带官方标记的 HTML。
   健康缓存必须保持原字节，页面仍显示健康副本和诚实状态。可再加你认为更危险的边界，不必局限于这三类。
3. 至少一项独立负对照：只在自己复核树/测试服务器内存中移除相应校验，证明新增异常测试会变红；不得改被审正本。恢复用 cp，不用 git checkout。
4. 检查默认本地零注册/零缓存、生产域名门禁、导航白名单、AI/NCBI/POST/跨域绕过、日期与多日持续降级、退出后网络回退。发现项按严重度列出，写明具体输入→实际结果→为什么违反合同；发现数只是下限。
5. 记录来源、开始/结束时间、基线/候选哈希、Windows/Chrome/Node、重复次数与种子（无则写无）。不读真实钥匙，不访问真实 AI/NCBI 服务。

## 时限与交付
硬预算终点 2026-11-28 11:41:06；做不完就交部分复核并明确哪些未跑，不得省略失败或宣称完整。只找错不施工，不提供“我替你修好”的改动。
交付 `D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/neon-v1/report.md` 和全部原始输出。报告三行头、「按哪几条干的」「地图影响」「遗留风险」「证据」「地图终态」齐全；结论只能是通过/有条件通过/不通过/部分复核，并列出阻断项。最终尾部复述 `DELIVERY-T1128-SMOOTH-V1`。
