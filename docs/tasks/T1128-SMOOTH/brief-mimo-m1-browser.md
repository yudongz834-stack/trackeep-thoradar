DELIVERY-T1128-SMOOTH-M1
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar；任务号=T1128-SMOOTH-M1；交付=`www.thoradar.online` CDN 控制台归属/HTTPS 诊断、限定范围内修复与回读证据。
轨道位置：胸科雷达顺畅改造·⑧ 真实发布 CDN/www 阻断处理。
R级：R3（使用 PI 已登录的阿里云控制台；只允许本单列明的现有域名配置修复，其他先只读并报告）。
判级理由：`www` 公网 TLS 握手失败会阻断双域验真；需要控制台确认归属与 HTTPS 配置。云端配置改变按生产变更处理。
签发：PI 原话「你帮我做」「全部运行allow，不要我一直瘦点」「要不操作浏览器你让codex gpt 6.2 sol还有mimo 2.6 pro做？」（2026-11-28）。本单允许 Mimo 在以下边界内操作 CDN，不扩展为购买、证书私钥、DNS 迁移或全账号配置。
地形：只在 PI 日常 Chrome 中自行新建 CDN 控制台标签页；不得操作 Sol 的 RAM 标签 `48EFF9133344B0869DF5A6CE6D213FE5`，不得操作 PI 原有标签。报告只写 `docs/tasks/T1128-SMOOTH/mimo-m1-browser-report.md` 与 `online-release/mimo-m1/`；临时脚本只用 `D:/claude-tmp/mimo-m1-*`。不改产品、工作流、测试、任务地图，不 commit/push/deploy。
领域卡：无
经验卡：无卡。
Run 版本键：岗位卡=builder-jobspec 现役正本；model=mimo-v2.6-pro[1m]（口述 Mimo 2.6 Pro→manifest→cc-mimo opus 档→D:/npm-global/cc-mimo.cmd）；失败 run=`46129122449`（双域混入刷新返回 `InvalidDomain.NotFound`）与 `46130068894`（主域刷新缺 RAM 权限）。

## 已确认事实
1. 主域和 `www` 公共 DNS 均指向 `thoradar.online.w.kunlunaq.com.`；主域四个公开 HEAD 为 200 且 MD5 与 Git blob 一致，`www` 四个公开 HEAD 在 TLS 握手失败。共用 CNAME 不证明共享缓存。
2. 源站预检 GET 对两个 Host 均可得到 OSS 200；源站根路径 HEAD 为 403，不要用 HEAD 403 误判源站坏。
3. `www` 曾被 CDN 刷新 API 判定不属当前账号，整批请求失败。不要把 `www` 塞回当前自动刷新请求，也不要跳过双域验真。
4. 详细公开证据可读 `docs/tasks/T1128-SMOOTH/sol-s7-report.md`，但控制台事实需要你独立回读，不把旧报告当现状。

## 你要做的事
1. 先读 `D:/claude/skills/meta-web-access/SKILL.md` 与 `CONFIG.md`。你按无视觉模型处理：只用 DOM 文本和可机读状态，不 Read 截图；截图只可存盘留证。直接 CDP 从 `%LOCALAPPDATA%/Google/Chrome/User Data/DevToolsActivePort` 取 WebSocket，不依赖 `/json/version`。
2. 新建自己的 CDN 域名管理标签，读取域名列表，确认 `www.thoradar.online` 是否在当前账号、状态、CNAME、HTTPS 证书和回源。不得读取或输出账号 ID、个人认证信息、AccessKey、证书私钥或完整域名列表中的无关敏感信息。
3. 若 `www` **已在当前账号**：仅在既有配置内修复导致 TLS 失败的明确问题，并优先复用控制台已有且覆盖 `www` 的证书。每一步先回读变更范围；不得改主域、删域名、改源站、购买证书/套餐、上传或读取私钥、改 DNS、触发跨账号迁移。修复后重新打开配置回读，再做 `https://www.thoradar.online/`、`/index.html`、`/sw.js`、`/sw-retire.js` 的公开 HEAD/TLS 验证。
4. 若 `www` 不在当前账号、必须新增域名/收费/证书申请/私钥/DNS 或迁移才能继续：不要提交这些变更，记录具体卡点、页面证据和最小后续处理单。不要因为共用 CNAME 就猜归属。
5. 若发现 www 已迁入本账号并可管理，也只报告这一事实及建议恢复双域自动刷新；不得自行修改工作流、测试或真实发布。
6. 不执行 CDN 刷新，不触发工作流，不演练退役。结束关闭你创建的标签页，保留 Sol 与 PI 的标签。

## 验收与交付
- 区分「已修复且公开 TLS/四 URL 回读通过」「只查明原因未改」「已改但公开验证仍失败」三态，不混报。
- 报告含三行头（干了什么／PI 怎么亲手验／还剩什么坑）、结论、地图影响、验证状态、改动清单、遗留风险、地图终态；记录实际控制台字段、变更前后状态和公开验证退出码，隐去账号/个人信息。尾部复述 `DELIVERY-T1128-SMOOTH-M1`。
