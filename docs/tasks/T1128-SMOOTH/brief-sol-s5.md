DELIVERY-T1128-SMOOTH-S5
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar-smooth-T1128；任务号=T1128-SMOOTH-S5；交付=可发布的正常/退役部署流程、CI 验证闸与模拟证据。
轨道位置：胸科雷达顺畅改造·⑥ Sol S5 发布接线。
R级：R2（实际发布另属 R3，唯 PI 亲手）。
判级理由：修改部署工作流、CDN 刷新与退役映射，影响公开网站交付链；本单只做本机代码与模拟验证。
签发：PI 在知悉「核心修复完成、线上交付未完成」后原话「继续做」（2026-11-28）。
地形：写域仅 `.github/workflows/deploy_oss.yml`、`tests/smooth/`、`docs/tasks/T1128-SMOOTH/`；邻接正式 OSS/CDN 发布链，严禁真实外呼。
领域卡：无
经验卡：无卡。
Run 版本键：岗位卡=builder-jobspec 现役正本；合同=`release-contract.md`；C1 三件哈希=`33c50bef...1def` / `e882e9e2...394f` / `5ae38f2b...6199`。

## 必读事实
- 现流程 `.github/workflows/deploy_oss.yml` 只上传首页等旧对象，没有两件 worker，也没有 CDN 刷新。
- 主控只读实测线上：`/sw.js` 当前 404；首页与 404 响应均有 `Content-MD5`，可用于验真。首页现有 `Cache-Control: public, max-age=60, s-maxage=3600`，不要改其它对象缓存策略。
- 可复用 `D:/trackeep/trackeep-workbench/cache-prototype/.github/workflows/deploy_oss.yml` 中固定 aliyun CLI v3.5.4＋SHA-256、RefreshObjectCaches 重试与 Content-MD5 轮询的做法，但不得照搬它对 feed/api/data/index 缓存策略的其它改动。

## 必做
1. **CI 验证闸**：新增 `smooth-verify`（Windows runner），checkout 全历史、Node 24，先跑发布静态检查、`verify-source`、S1/S2/S3、UX；部署 job `needs: smooth-verify`。现有测试认 Windows Chrome 路径，保持真实入口，不改测试判据。结果输出到 runner temp，避免污染写域。已知 AICLS/POOLUP R08 不加入充数。
2. **上传**：两件 worker 以 JavaScript MIME 和禁止缓存的 Cache-Control 上传；首页保持现缓存头并在两件 worker 之后最后上传。正常 `/sw.js`＝仓内 `sw.js`。
3. **退役模式**：`workflow_dispatch` 增加布尔 `retire`，默认 false。为 true 时把仓内 `sw-retire.js` 上传为真实 `/sw.js`，同时保留 `/sw-retire.js`；为 false 时恢复仓内正常 `sw.js`。首页仍最后上传。不得在本单执行退役。
4. **精准刷新**：双域 `/`、`/index.html`、`/sw.js`、`/sw-retire.js` 共 8 个 URL，固定版本 CLI，失败重试一次，必须有 `RefreshTaskId`，否则非零退出。复用 OSS key 的阿里云 CLI 环境别名，不打印凭证。
5. **发布后验真**：双域上述对象轮询 Content-MD5 必须等于本地对应文件；退役模式 `/sw.js` 的期望值切到 `sw-retire.js`。两件 worker 另验 200、JavaScript MIME、Cache-Control 含 no-store。失败不得宣称完成。保留现有双域 HTTPS 预检。
6. **测试**：新增跨平台 `tests/smooth/verify-deploy.mjs` 等必要静态/模拟检查，覆盖正常与 retire 两模式、8 URL、上传顺序、禁止缓存、MD5 映射、CI 闸与失败分支；至少一项删关键保护的负对照必须变红。可做 YAML/shell 语法检查与本地模拟命令，不得访问真实 OSS/CDN。
7. 复跑既有 S3 9 项、S1 9 项、S2 24 项、UX 46 项与 `verify-source`；若 `verify-source` 的写域白名单需要纳入 `.github/workflows/deploy_oss.yml`，只做这一处必要同步并记录。C1 三件产品哈希不得变化。

不做：不 push、不 deploy、不刷新 CDN、不调用真实凭证、不做线上或真机验收、不新增 90 天缓存、不改其它缓存策略。完成后交 `sol-s5-report.md`、原始 stdout/stderr/JSON、命令退出码和候选 diff。报告三行头、地图影响、验证状态、改动清单、遗留风险、地图终态齐全。最终尾部复述 `DELIVERY-T1128-SMOOTH-S5`。
