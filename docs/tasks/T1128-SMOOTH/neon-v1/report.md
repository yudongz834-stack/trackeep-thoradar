**干了什么**　在独立复核树对胸科雷达首页缓存候选（`index.html`、`sw.js`、`sw-retire.js`）核对哈希并亲自重跑 S1（9/9）、S2（24/24）、UX 原脚本（46/46），自建 Chrome/CDP 异常对抗套件（含 3 类必测异常、1 类空标记坏壳越界探测、白名单绕过与域名门禁）及 3 项内存负对照（3/3 变红），揪出 1 项健康缓存可被空标记坏壳覆盖的真实缺口，并完成 AICLS/POOLUP R08 源码与原始日志判读。  
**PI 怎么亲手验**　打开 [neon-v1-verify.stdout.txt](neon-v1-verify.stdout.txt)，看第 1–4 行与第 6–8 行：必测三类异常全部 `PASS` 且原哈希保留，第 4 行 `FAIL adversarial-empty-markers-stub` 实证 156 字节空标记页面覆盖了 539KB 健康缓存（`preserved=false`，横幅误报「有新版，下次打开生效」），第 6–8 行三项负对照全部 `RED-CAUGHT` 变红。  
**还剩什么坑**　有两项硬缺口未清：① `sw.js` 的 `fetchShell` 仅查起止标记顺序与 `</html>`，不校验标记间存在有效 `SITE_DATA`，156 字节空标记壳可覆盖健康缓存导致下次打开 0 信号；② 受 11:41:06 硬预算及 `run-regressions.mjs` 在新工作树缺父目录报错（`ENOENT`）限制，未在本复核树独立重跑完 AICLS 与 POOLUP 两套回归，且两者 R08 检索步骤仍属测试失真未验。

## 结论与阻断项

- **复核结论**：**部分复核**（不予直接放行；含 1 项缓存污染实测缺口与 2 套旧回归未独立重跑）。
- **阻断项**：
  1. **[高危·合同不变量 4 违例]** `sw.js` 仅凭 `DATA_START`→`DATA_END` 顺序与 `</html>` 收尾放行写入，未校验标记间存在合法 `SITE_DATA` 或基本页面载荷；HTTP 200 + `text/html` 的 156 字节空标记坏壳已实测覆盖 539,012 字节健康缓存，并使下次导航从 `cache-storage` 渲染出 `date: null, points: 0`。
  2. **[未独立复跑·证据缺口]** `tests/aicls/aicls_regress.mjs` 与 `tests/poolup/poolup_regress.mjs` 未在本复核树完成独立重跑（`run-regressions.mjs` 因未传 `{ recursive: true }` 建目录而报 `ENOENT` 退出码 1，随后到达 11:41:06 硬预算终点）。此外，施工侧两套 39/40 中的 R08 实证为测试选词失真导致检索步未形成有效差分，不得写成产品全绿。

## 按哪几条干的

- 执行 `T1128-SMOOTH-V1` 委任状与 [acceptance-contract.md](../acceptance-contract.md) v1。轨道位置＝胸科雷达顺畅改造·④ Neon V1 独立复验；R 级＝R2；签发＝PI 原话「算了，现在直接执行吧，不重启了」（2026-11-28）及组合指定 agy Gemini 4 Neon 协助和验证。
- 正式身份＝agy·Gemini 4·Neon·独立复核席（执行档 `gemini-4-neon`），未参与 S1/S2 设计与施工；严格先核哈希、先读验收合同并跑完独立实测与对抗脚本，再读取施工报告与 R08 原始日志。
- 写域零越界：被审工作树 `D:/trackeep/trackeep-product/trackeep-thoradar-smooth-T1128` 与主仓产品文件零写入（复核前后三件 SHA-256 逐字节一致）；所有负对照只在测试服务器内存中变异 `sw.js`，未修改磁盘正本；Chrome 均使用独立临时配置目录并在结束时正常关闭，复核结束后无本会话残留 Chrome 进程；未读真实钥匙，未访问真实 AI/NCBI 服务，未 push/deploy/刷新 CDN。

## 主动查错与发现项（按严重度）

> 说明：以下发现项为本次复核已实证的下限，不代表缺陷总数。

### F1（高危 / 阻断）— 空标记坏壳可绕过 `fetchShell` 校验并污染健康缓存
- **位置**：`sw.js:16-20`
- **具体输入**：向已预热 `v1`（539,012 字节，SHA-256 `33c50bef...`）的受控页面导航 `/index.html`，源站对后台核新返回 `HTTP 200`、`Content-Type: text/html; charset=utf-8`、正文为 156 字节坏壳：
  ```html
  <!doctype html><html><head><title>Stub</title></head><body><!-- /*__THORADAR_DATA_START__*//*__THORADAR_DATA_END__*/ --><p>Corrupted shell</p></body></html>
  ```
- **实际结果**：`sw.js` 接受该响应并覆盖 `thoradar-shell-v1` 中的 `/index.html`（缓存哈希变为 `11e2ff0add51cd0cf4f21b39010925b11df3fe7c0d388906c0c56468a3a16b74`，长度 `156` 字节），向当前页推送 `"数据 2026-11-27 · 有新版，下次打开生效"`；紧接着下一次导航 `/index.html` 从 `cache-storage` 渲染出 `date: null, points: 0, banner: null`（整页失效，且状态条消失）。证据见 [neon-v1-verify.json](neon-v1-verify.json) 中 `adversarial-empty-markers-stub`。
- **违反合同原因**：违反验收合同不变量 4（任何错误、截断、劫持响应不得覆盖健康缓存）与不变量 1（`SITE_DATA` 唯一真相）；只要异常构建/代理页面包含空注释标记或截断的 `SITE_DATA`（但保留了两个注释标记和 `</html>`），即可将正常离线副本覆盖为白屏坏页。

### F2（低危 / 体验与冗余请求）— 缓存未命中时的双请求与状态短暂误闪
- **位置**：`sw.js:81-99`、`index.html` 尾部脚本（`controller` 分支）
- **具体输入**：SW 已激活并控制页面但 `thoradar-shell-v1` 中无 `/index.html` 副本（如零配额冷启动或首次安装拉取失败后的第二次导航）。
- **实际结果**：`event.respondWith` 发起一次 `fetch(request)`，同时 `refreshTail` 中的 `checkForUpdate` 立即对同一 `request.url` 发起第二次 `fetchShell`（`cache: 'no-store'`），导致单次导航触发两次源站全量 HTML 请求；且页面初始化时因 `controller` 非空先显示 `本地副本 · 核对更新中`，待消息回执后才切回 `联网打开` 或 `联网打开 · 本地副本不可用`。
- **合同关联**：未破坏页面可用性（S2 零配额用例已过），但存在短暂状态不诚实与双倍首屏带宽消耗。

### F3（低危 / 测试工具链缺陷）— `run-regressions.mjs` 在干净工作树中因缺父目录报错
- **位置**：`tests/smooth/run-regressions.mjs:12`
- **具体输入**：在无 `docs/tasks/T1128-SMOOTH/` 目录的独立工作树中直接运行 `node tests/smooth/run-regressions.mjs`。
- **实际结果**：`await mkdir(directory)` 未传 `{ recursive: true }`，立即抛出 `Error: ENOENT`（退出码 1）。证据见 [run-regressions.stderr.txt](run-regressions.stderr.txt)。

### 必测三类异常与白名单/门禁核查结果（均通过）
| 查错项 | 输入条件 | 实际结果 | 判定 |
|---|---|---|---|
| 标记倒序 (`reversed-markers`) | HTTP 200、`text/html`、完整 HTML 但 `DATA_END` 在 `DATA_START` 前 | 拒绝覆盖；缓存仍为 `33c50bef...`（539,012B）；横幅 `数据 2026-11-27 · 本地副本 · 暂未核实更新` | **PASS** |
| 错误 MIME (`json-mime-valid-html`) | HTTP 200、`Content-Type: application/json`、完整官方标记 HTML | 拒绝覆盖；缓存仍为 `33c50bef...`；横幅 `暂未核实更新` | **PASS** |
| 非 200 状态 (`status-503-valid-html`) | HTTP 503、`text/html`、完整官方标记 HTML | 拒绝覆盖；缓存仍为 `33c50bef...`；横幅 `暂未核实更新` | **PASS** |
| 导航白名单与绕过 (`whitelist-and-bypass`) | `/?foo=bar`、`/index.html?sw=1&extra=1`、非导航 `fetch('/index.html')`、`/data/radar_latest.json`、`POST /api/ai-probe` | 全部 `fromServiceWorker: false` | **PASS** |
| 生产域名门禁 (`production-domain-gate`) | `https://thoradar.online` / `https://www.thoradar.online` 允许；`http://thoradar.online`、`https://evil-thoradar.online`、`https://thoradar.online.evil.com`、`http://127.0.0.1:8080` 拒绝 | 6/6 与预期一致 | **PASS** |
| 默认零注册/零缓存、多日持续降级、退出与重装 | `verify-s1.mjs`（9/9）、`verify-s2.mjs`（24/24）、`ux_probe.mjs`（46/46）亲自重跑 | 全部通过，零未捕获页面/Worker 异常 | **PASS** |

### 独立负对照结果（3/3 变红，全部有效）
只在测试服务器内存中对 `sw.js` 移除对应防护，磁盘文件未改动：
1. `mut-marker-order`（将 `indexOf(DATA_END, start + DATA_START.length)` 改为 `indexOf(DATA_END)`）＋ `reversed-markers` → 健康缓存被覆盖（`hashChanged=true`），横幅变为 `"有新版，下次打开生效"` → **RED-CAUGHT（变红）**。
2. `mut-mime`（移除 `mime !== 'text/html'`）＋ `json-mime-valid-html` → 健康缓存被覆盖（`hashChanged=true`），横幅变为 `"有新版，下次打开生效"` → **RED-CAUGHT（变红）**。
3. `mut-status-503`（将 `response.status !== 200` 改为 `response.status < 200`）＋ `status-503-valid-html` → 健康缓存被覆盖（`hashChanged=true`），横幅变为 `"有新版，下次打开生效"` → **RED-CAUGHT（变红）**。

## R08 原始证据判读（AICLS / POOLUP）

对 `tests/aicls/aicls_regress.mjs:90-92,133-136`、`tests/poolup/poolup_regress.mjs:90-92,133-136` 及施工原始输出（`sol-s2-regressions-final/aicls.stdout.txt:33-37`、`poolup.stdout.txt`、`sol-s2-report.md`）逐行核查后的判断：

- **判定归属**：**测试失真＋该步未验（不是产品差异）**；**绝不可把 39/40 写成产品全绿**。
- **直接机制**：
  1. 在 R07 关掉一个档位、R07b 选中快筛（`state.quick` 非 `'all'`）后，当前列表仅剩 1 篇（`noQuery: 1`）。
  2. R08 选词器 `WORDPICK` 计算 `base` 时仅过滤 `tierOk(p) && journalOk(p)`，**漏掉了 R07b 已激活的 `state.quick`**，导致挑出的词 `Mortality` 虽在全量窗内命中多篇，却与当前唯一在列文章完全不匹配。
  3. 原始日志显示基线（`73dd34e`）与候选两边结果逐字相同：`{"query":"Mortality","list":0,"noQuery":1}`，触发脚本「防空对空闸」报错 `场景失真：这一步之后概览列表是空的（基线 0 篇、施工后 0 篇）——筛选逻辑没真正被比到`。
- **附注**：检查施工树旧目录 `sol-s2-regressions-final` 时还可见早期 R01 因 `thoradar.view.v1` 残留产生 38/40，最终交付采用的是 `sol-s2-legacy-evidence` 的 39/40；本复核树尚未独立重跑这两套脚本。

## 地图影响

- 本复核未修改被审工作树、主仓产品文件、既有测试、验收合同及任务地图。
- 仅在独立复核树新增自建复核脚本 `D:/trackeep/trackeep-product/trackeep-thoradar-neon-v1/tests/neon-v1-verify.mjs`，并将全部原始输出与本报告落盘于 `D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/neon-v1/`。
- 主仓 `arch-scan.sh` 既有漂移（131 vs 326）未在本复核中改动，按验收合同留待主仓整合后复跑。

## 遗留风险与未跑项

- **本复核未跑项（因 11:41:06 硬预算截断）**：
  - 未在独立复核树完成 `tests/aicls/aicls_regress.mjs` 与 `tests/poolup/poolup_regress.mjs` 的独立重跑；
  - 未重复运行 S1/S2 第二轮（本复核各自独立重跑 1 轮）；
  - 未单独重跑 `tests/smooth/verify-source.mjs`（但已手动对 `index.html` 与 `73dd34e` 执行 `git diff` 并保存 [index-diff.patch](index-diff.patch)，确认仅增 177 行 diff，未动 `SITE_DATA`、`PAPERS/mergePapers/inWindow` 与既有 `localStorage` 键）。
- **合同明示本轮不覆盖项**：iOS、真机、国内无代理直连、线上跨日、多标签完整生命周期、正常 SW 自身升级全过程、90 天档案离线、UX3 合并、CDN 头与刷新收敛、生产发布。

## 证据

- **来源**：独立复核工作树 `D:/trackeep/trackeep-product/trackeep-thoradar-neon-v1`（只读对照被审树 `D:/trackeep/trackeep-product/trackeep-thoradar-smooth-T1128`）。
- **复核时间窗口**：2026-11-28 11:37:39+08:00 至 2026-11-28 11:41:40+08:00（硬预算终点 11:41:06 后即刻停测并收口落盘）。
- **运行环境**：Windows 11 Pro (`Microsoft Windows NT 10.0.26300.0`, x64)、Node `v24.14.0`、Chrome `158.0.8127.88`（CDP `1.3`）。
- **重复次数与种子**：各独立重跑套件 1 轮；随机种子：无。
- **基线与候选 SHA-256（复核前后一致，与任务书及被审树完全匹配）**：
  - 基线提交：`73dd34e65fce6661d74e595afc03df68e7d3f44f`
  - `index.html`：`33c50bef723b0a3f32b51bc2d5927ff4391bb58eb474996f1a7d9dff96bc1def`
  - `sw.js`：`f8a4e2bc4d5d81964475580c012e825281f409a171782640ad5cbc68a07bca24`
  - `sw-retire.js`：`5ae38f2ba965f4e1b1d340da2ba5fadd8b58af82a1e271a02ddff97ab5686199`

### 执行命令与退出码汇总
| 套件 / 命令 | 退出码 | 原始结果 | 证据文件 |
|---|---:|---|---|
| `node tests/smooth/verify-s1.mjs .../verify-s1.json` | 0 | `9 PASS / 0 FAIL` | [verify-s1.json](verify-s1.json) · [stdout](verify-s1.stdout.txt) · [stderr](verify-s1.stderr.txt) |
| `node tests/smooth/verify-s2.mjs .../verify-s2.json` | 0 | `24 PASS / 0 FAIL` | [verify-s2.json](verify-s2.json) · [stdout](verify-s2.stdout.txt) · [stderr](verify-s2.stderr.txt) |
| `node tests/ux/ux_probe.mjs` | 0 | `46 PASS / 0 FAIL` | [stdout](ux_probe.stdout.txt) · [stderr](ux_probe.stderr.txt) |
| `node tests/smooth/run-regressions.mjs` | 1 | 未跑完（`ENOENT` 缺父目录） | [stdout](run-regressions.stdout.txt) · [stderr](run-regressions.stderr.txt) |
| `node tests/neon-v1-verify.mjs .../neon-v1-verify.json` | 0 | 查错 `5 PASS / 1 FAIL`（空标记坏壳复现）；负对照 `3/3 RED-CAUGHT` | [neon-v1-verify.json](neon-v1-verify.json) · [stdout](neon-v1-verify.stdout.txt) · [stderr](neon-v1-verify.stderr.txt) |
| `git diff 73dd34e -- index.html` | 0 | 177 行 diff | [index-diff.patch](index-diff.patch) |

### 关键原始输出摘录
```text
# verify-s1.mjs
SUMMARY {"passed":9,"failed":0,"endedAt":"2026-11-28T03:38:57.455Z"}

# verify-s2.mjs
SUMMARY {"passed":24,"failed":0}

# ux_probe.mjs
==== UX PROBE [run] SUMMARY 46 PASS / 0 FAIL ====

# neon-v1-verify.mjs (独立对抗 + 负对照)
PASS adversarial-reversed-markers preserved=true banner="数据 2026-11-27 · 本地副本 · 暂未核实更新" hash=33c50bef723b0a3f32b51bc2d5927ff4391bb58eb474996f1a7d9dff96bc1def
PASS adversarial-json-mime-valid-html preserved=true banner="数据 2026-11-27 · 本地副本 · 暂未核实更新" hash=33c50bef723b0a3f32b51bc2d5927ff4391bb58eb474996f1a7d9dff96bc1def
PASS adversarial-status-503-valid-html preserved=true banner="数据 2026-11-27 · 本地副本 · 暂未核实更新" hash=33c50bef723b0a3f32b51bc2d5927ff4391bb58eb474996f1a7d9dff96bc1def
FAIL adversarial-empty-markers-stub preserved=false banner="数据 2026-11-27 · 有新版，下次打开生效" hash=11e2ff0add51cd0cf4f21b39010925b11df3fe7c0d388906c0c56468a3a16b74
PASS whitelist-and-bypass
RED-CAUGHT neg-mut-marker-order input=reversed-markers banner="数据 2026-11-27 · 有新版，下次打开生效" hashChanged=true
RED-CAUGHT neg-mut-mime input=json-mime-valid-html banner="数据 2026-11-27 · 有新版，下次打开生效" hashChanged=true
RED-CAUGHT neg-mut-status-503 input=status-503-valid-html banner="数据 2026-11-27 · 有新版，下次打开生效" hashChanged=true
PASS production-domain-gate
NEON_DONE {"checksPassed":5,"checksFailed":1,"negCaughtRed":3,"negTotal":3}
```

## 地图终态

[task-map.md](../task-map.md) 当前仍显示 ④ Neon V1 独立复验 `in-progress`、⑤ 主控最终整合检查 `pending`、⑤.9 对外发布 `not-authorized`（地图只由派单方回填，本席零写入）。本复核结论为**部分复核**并提交阻断项 F1 与 AICLS/POOLUP 未独立重跑事实，交由派单方裁决是否退回加固 `fetchShell` 与补跑两套旧回归。

DELIVERY-T1128-SMOOTH-V1
