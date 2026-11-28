**干了什么**　在独立复核树核对 S3 候选三件哈希与施工树逐字节一致后，亲自重跑 V1 原脚本（实测因 S3 重构 `dataStart` 触发第 60 行 `Anchor mismatch`）、自建 V2 对抗与负对照套件（12/12 检查全过、4 项核心防护负对照全部变红）、S3 专项（6/6）、S1（9/9）、S2（24/24）、UX（46/46）及直跑 AICLS／POOLUP 两套旧回归（均为 39/40 且 38 步差分零候选差异，仅 R08 因测试选词失真未验），实证 V1 阻断项 F1 已修复且下次导航不再出现 `date: null / points: 0`。  
**PI 怎么亲手验**　打开 [neon-v2-verify.stdout.txt](neon-v2-verify.stdout.txt)，看第 4 行 `PASS adversarial-empty-markers-stub preserved=true nextDate=2026-11-27 nextPoints=37`、第 10 行 `PASS valid-zero-papers-accepted ... nextDate=2026-11-28 nextPapers=0`、以及第 15–18 行四项 `RED-CAUGHT`（其中 `neg-mut-s3-site-data-guard` 删去 S3 新校验后即刻复现 `nextDate=null nextPoints=0`），再看 [aicls_regress.stdout.txt](aicls_regress.stdout.txt) 与 [poolup_regress.stdout.txt](poolup_regress.stdout.txt) 末尾均显示「比对的 38 步里 38 步四样逐字一致且零新增调用，0 步有差异」。  
**还剩什么坑**　无本机候选阻断项；遗留三项低危非阻断问题（V1 的 F2 冷缓存双请求／状态短闪、V1 的 F3 `run-regressions.mjs` 缺父目录 `ENOENT`、V2 新观察 F4 `briefing_date: ""` 空串与注释内伪造有效 `SITE_DATA` 桩页可被放行），以及旧回归 R08 因测试失真未验与合同明示的真机／线上／90 天等未覆盖项。

## 结论、阻断项与未验项

- **复核结论**：**有条件通过**（针对本机候选口径，V1 唯一高危阻断项 F1 已实证关闭，零阻断项；带明确未验项与低危遗留记录，不授权直接对外发布）。
- **阻断项**：本机候选口径下**无阻断项**（0 项）。
- **未验项**：
  1. **旧回归 R08（AICLS / POOLUP）**：两套脚本直跑均以退出码 1 返回 `39 PASS / 1 FAIL / 0 SKIP`，失败项均为 R08；实测日志确认基线（`73dd34e`）与候选两侧结果逐字一致为 `{"query":"Mortality","list":0,"noQuery":1}`，属测试 `WORDPICK` 漏计 R07b 已激活 `state.quick` 导致的空对空失真，**不可写成 40/40 全绿，该步按未验记录**；除该失真判定外，38/38 步差分零候选产品差异。
  2. **合同明示本轮不覆盖项**：iOS、真机、国内无代理直连、线上跨日、多标签完整生命周期、正常 SW 自身升级全过程、90 天档案离线、UX3 合并、CDN 头与刷新收敛、生产发布。
  3. **既有主仓漂移**：主仓 `arch-scan.sh` 漂移（131 vs 326）只能在主仓整合后由派单方复跑核对。

## 按哪几条干的

- 执行 `T1128-SMOOTH-V2` 委任状与 [acceptance-contract.md](../acceptance-contract.md) v1。轨道位置＝胸科雷达顺畅改造·④ Neon V2 返修后独立复验；R 级＝R2；签发＝PI 原话「算了，现在直接执行吧，不重启了」（2026-11-28）及「加快速度」「快点，做快一点啦！」。
- 独立性纪律：新会话、只找错不施工；严格先核对候选哈希并亲自跑完全部套件与旧回归，**全部落盘后才读取** S3 报告（`sol-s3-report.md`）。
- 写域零越界：被审 S3 工作树 `D:/trackeep/trackeep-product/trackeep-thoradar-smooth-T1128`、主仓产品文件、旧测试、验收合同与任务地图零写入；产品文件复核前后 SHA-256 逐字节一致；所有负对照只在测试服务器内存中对 `sw.js` 变异，未改动磁盘正本；Chrome 均使用独立临时配置目录并在结束时正常退出，复核结束后复查无残留 Chrome 进程；未读凭证，未碰外部 AI/NCBI，未 push/deploy。

## F1 修复复验与主动查错（按严重度）

> 说明：以下发现项为本次独立复核已实证的下限，不代表缺陷总数。

### 1. V1 原阻断项 F1 复验结果 — **已修复（关闭）**
- **V1 原脚本原样运行证据**：在独立复核树原样执行 `node tests/neon-v1-verify.mjs .../neon-v1-verify-verbatim.json`，立即以退出码 `1` 报错：
  `Error: Anchor mismatch: html.indexOf(DATA_END, start + DATA_START.length) === -1`（位置 `tests/neon-v1-verify.mjs:60`）。
  原因：S3 将 `sw.js:17-19` 重构为 `const dataStart = start + DATA_START.length; const end = html.indexOf(DATA_END, dataStart);`，属测试脚本字符串替换锚点漂移，并非产品缺陷。原脚本保持未改，原始报错已保存至 [neon-v1-verify-verbatim.stderr.txt](neon-v1-verify-verbatim.stderr.txt)。
- **V2 独立对抗复验（`tests/neon-v2-verify.mjs`）＋ S3 专项独立重跑（`tests/smooth/verify-s3.mjs`）**：
  - V1 四类异常（倒序 `reversed-markers`、错误 MIME `json-mime-valid-html`、HTTP 503 `status-503-valid-html`、156B 空标记坏壳 `empty-markers-stub`）**全部拒绝覆盖**，缓存保持健康 `v1`（539,012B，SHA-256 `33c50bef...`），横幅诚实显示 `数据 2026-11-27 · 本地副本 · 暂未核实更新`。
  - **下一次导航专项确认**：对全部 9 类非法样本在拒绝覆盖后均紧接着执行下一次 `/index.html` 导航，均命中 `cache-storage` 并渲染 `nextDate=2026-11-27, nextPoints=37`、状态条正常，**不再出现 V1 的 `date: null / points: 0`**。
  - S3 新增样本独立重跑与自建双验：缺 `SITE_DATA`（标记外另放合法声明）、坏 JSON（尾逗号）、`briefing_date` 类型错（数字 `20261128`）、`papers` 类型错（对象 `{}`）及自加 `const SITE_DATA = null;` **全部拒绝覆盖**；合法零篇版（`briefing_date: "2026-11-28", papers: []`，374,679B）**正确放行**，横幅提示「有新版，下次打开生效」，下次导航从 `cache-storage` 正常渲染 `2026-11-28` 且 `papers: 0`（未被误拒）。

### 2. 独立内存负对照结果（4/4 核心防护变红，另实证 1 项纵深防御）
只在 `tests/neon-v2-verify.mjs` 服务器内存中对 `sw.js` 变异，磁盘正本零改动：

| 负对照变异 | 输入样本 | 结果 | 实测现象与判定 |
|---|---|---|---|
| `mut-marker-order-naive`（仅将 `indexOf(DATA_END, dataStart)` 改为 `indexOf(DATA_END)`） | `reversed-markers` | **SURVIVED（纵深防御）** | `end < dataStart` 时 `html.slice(dataStart, end)` 返回空串 `""`，被 S3 新增的 `SITE_DATA` 校验二次拦住，缓存未污染 |
| `mut-marker-order-orderless`（移除标记先后约束：改 `indexOf(DATA_END)` 且按无序区间切片） | `reversed-markers` | **RED-CAUGHT（变红）** | `hashChanged=true`，横幅误报「有新版，下次打开生效」，证明倒序防护真实有效 |
| `mut-mime`（移除 `mime !== 'text/html'`） | `json-mime-valid-html` | **RED-CAUGHT（变红）** | `hashChanged=true`，横幅误报「有新版，下次打开生效」 |
| `mut-status-503`（将 `response.status !== 200` 改为 `response.status < 200`） | `status-503-valid-html` | **RED-CAUGHT（变红）** | `hashChanged=true`，横幅误报「有新版，下次打开生效」 |
| `mut-s3-site-data-guard`（移除 S3 `sw.js:23-31` 的 `SITE_DATA` 解析与类型校验） | `empty-markers-stub`（156B） | **RED-CAUGHT（变红）** | `hashChanged=true`，横幅误报「有新版」，且下一次导航立刻复现 `nextDate=null, nextPoints=0` |

### 3. 遗留与新观察（均属低危非阻断）

#### F2（V1 遗留·低危 / 体验与冗余请求）— 冷缓存未命中双请求与状态短暂误闪
- **现状核查**：`index.html` SHA-256 与 V1 完全相同（`33c50bef...`），`sw.js:93-112` 在缓存未命中时仍同时执行 `fetch(request)` 与 `refreshTail` 内的 `checkForUpdate(entry.cache, request.url, entry.displayed)`，且 `index.html` 在 `controller` 非空时先显示「本地副本 · 核对更新中」再切回「联网打开」。按任务书约定登记为低危遗留，不掩盖 F1 修复结果，未自行施工。

#### F3（V1 遗留·低危 / 测试工具链）— `tests/smooth/run-regressions.mjs` 缺父目录报 `ENOENT`
- **现状核查**：`tests/smooth/run-regressions.mjs:12` 仍为 `await mkdir(directory);`（未传 `{ recursive: true }`），文件哈希与 S2 一致（`ddaf9a9b...`）。按任务书约定登记为低危遗留，本次旧回归已绕过该封装直接运行原脚本。

#### F4（V2 新观察·低危边界）— `fetchShell` 允许空串 `briefing_date` 与注释包裹合法 `SITE_DATA` 的桩页
- **位置**：`sw.js:23-31`
- **实测证据**（见 [neon-v2-verify.json](neon-v2-verify.json) `extraProbes`）：
  1. `empty-briefing-date`：将 `briefing_date` 置为 `""`（空串）、`papers: []`（374,669B），因 `typeof "" === 'string'` 为真，被 `fetchShell` 放行覆盖缓存（`preserved=false`）。
  2. `comment-wrapped-site-data-stub`：184B 桩页 `<!doctype html><html><body><!-- /*__THORADAR_DATA_START__*/ const SITE_DATA = {"briefing_date":"2026-11-28","papers":[]}; /*__THORADAR_DATA_END__*/ --><p>Comment stub</p></body></html>`，因未校验声明处于 `<script>` 非注释上下文及应用主体 DOM，被 `fetchShell` 放行覆盖缓存（`preserved=false, bytes=184`）。
- **定级理由**：现实中的故障源站、认证劫持页、截断构建或空标记壳不会主动伪造符合正则且通过 `JSON.parse` 与字段类型检查的 `const SITE_DATA = {"briefing_date":...,"papers":[]}`，故列为低危边界观察而非阻断项；后续迭代若加固，可补充 `briefing_date` 非空日期格式校验及应用关键标识检查。

## 既有回归直跑核查（AICLS / POOLUP / UX）

- **UX（`tests/ux/ux_probe.mjs --target index.html --base 73dd34e --label neonv2`）**：退出码 `0`，**46 PASS / 0 FAIL**；19 键×3 视图官方面逐键差分 0 格不一致，8 幕状态面与详情卡内容逐字一致，运行期零异常。
- **AICLS（`node tests/aicls/aicls_regress.mjs --target index.html --baseline 73dd34e --label neonv2`）**：退出码 `1`，**39 PASS / 1 FAIL / 0 SKIP**。
  - 原始差分汇总：`比对的 38 步里 38 步四样逐字一致且零新增调用，0 步有差异`。
  - 唯一失败项 `R08`：基线与施工后均为 `{"query":"Mortality","list":0,"noQuery":1}`（测试选词未计入 R07b 的 `quick:"rct"`，导致空对空失真）。**无候选产品差异；R08 按未验记录**。
- **POOLUP（`node tests/poolup/poolup_regress.mjs --target index.html --baseline 73dd34e --label neonv2`）**：退出码 `1`，**39 PASS / 1 FAIL / 0 SKIP**。
  - 原始差分汇总：`比对的 38 步里 38 步四样逐字一致且零新增调用，0 步有差异`。
  - 唯一失败项 `R08`：同样为基线与施工后均为 `{"query":"Mortality","list":0,"noQuery":1}`。**无候选产品差异；R08 按未验记录**。
- **与 S3 报告交叉核对**：S3 `sol-s3-report.md` 所列 `index.html`、`sw.js`、`sw-retire.js`、`verify-s3.mjs` 及 156B 样本 SHA-256 与本席实测完全一致，S1/S2/S3/UX/AICLS/POOLUP 结论均被本席独立复现；未发现施工侧隐瞒或虚报。

## 地图影响

- 本复核对被审 S3 工作树（`D:/trackeep/trackeep-product/trackeep-thoradar-smooth-T1128`）、主仓产品文件、既有测试、验收合同及唯一任务地图**零写入**。
- 仅在独立复核树新增 `D:/trackeep/trackeep-product/trackeep-thoradar-neon-v1/tests/neon-v2-verify.mjs`（保留 `tests/neon-v1-verify.mjs` 原样未动），并将全部原始输出与本报告落盘于 `D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/neon-v2/`。
- `tests/smooth/verify-source.mjs` 在本独立复核树跑出 `4 PASS / 1 FAIL`（唯一失败的 `write-scope` 仅报出复核自有脚本 `tests/neon-v1-verify.mjs` 与 `tests/neon-v2-verify.mjs`；`official-data`、`official-paper-initialization`、`official-window-and-merge`、`node-syntax-and-git-diff-check` 全部通过）。

## 遗留风险

- **R08 未验**：两套旧回归检索步（R08）因既有测试脚本选词缺陷仍未形成有效覆盖；虽其余 38 步全量逐字一致且本次改动未触碰搜索／筛选逻辑，仍不得表述为「旧回归 40/40 全绿」。
- **低危未修项**：F2（冷缓存双请求与短闪）、F3（`run-regressions.mjs` 缺父目录 `ENOENT`）、F4（空串 `briefing_date` 与注释包裹有效 `SITE_DATA` 桩页边界）。
- **本机口径以外风险**：iOS、真机、无代理网络、线上跨日、多标签复杂并发、正常 SW 升级、90 天离线档案、CDN 缓存头收敛均未在本轮实测，后续进入生产发布前须另行验收并由 PI 亲手执行发布动作。

## 证据

- **来源**：独立复核工作树 `D:/trackeep/trackeep-product/trackeep-thoradar-neon-v1`（只读核对 S3 施工树 `D:/trackeep/trackeep-product/trackeep-thoradar-smooth-T1128`）。
- **复核时间窗口**：2026-11-28 12:24:03+08:00 至 2026-11-28 12:29:21+08:00。
- **运行环境**：Windows 11 Pro（`Microsoft Windows NT 10.0.26300.0`，x64）、Node `v24.14.0`、npm `11.9.0`、git `2.53.0.windows.2`、Chrome `158.0.8127.88`（CDP `1.3`）。
- **重复次数与种子**：S1、S2、S3、UX、AICLS、POOLUP、V1 原样、`verify-source` 各独立运行 1 轮；`neon-v2-verify` 运行 2 轮（第二轮补充 `mut-marker-order-orderless` 负对照并覆盖留存最终版）；随机种子：无（`null`）。
- **基线与候选 SHA-256（复核前后逐字节一致，与 S3 施工树完全匹配）**：
  - 基线提交：`73dd34e65fce6661d74e595afc03df68e7d3f44f`
  - `index.html`：`33c50bef723b0a3f32b51bc2d5927ff4391bb58eb474996f1a7d9dff96bc1def`
  - `sw.js`：`900061dd45ad04e9f9c4391e5d2756f8b080a4bc4144ede9b913b6deabb5aa8b`
  - `sw-retire.js`：`5ae38f2ba965f4e1b1d340da2ba5fadd8b58af82a1e271a02ddff97ab5686199`
  - `tests/smooth/verify-s1.mjs`：`6c93edebe199b9d502e72d42b729bc2dc96ee313307b6341fd5fa92f85c84dc4`
  - `tests/smooth/verify-s2.mjs`：`9266fc7518314073d3694d809cca0e7c6e057daa2c7fcb80bdb0d2a7d460ea48`
  - `tests/smooth/verify-s3.mjs`：`585a9f3803238cfb18b80a490948f9e661fd6792dae09838c53d38f98a030ac7`
  - `tests/smooth/run-regressions.mjs`：`ddaf9a9b81c428244c485855ef2545035ce5dbfa586eefbaf8b596b15dbe3d6c`
  - `tests/smooth/verify-source.mjs`：`c6cdfd0a7c315217278bbf44351bcbdbc0397c102f0eb03769e9cf4215215574`
  - V1 156B 空标记毒壳样本：`11e2ff0add51cd0cf4f21b39010925b11df3fe7c0d388906c0c56468a3a16b74`

### 执行命令与退出码汇总

| 套件 / 命令 | 退出码 | 原始结果 | 证据文件 |
|---|---:|---|---|
| `node tests/neon-v1-verify.mjs .../neon-v1-verify-verbatim.json` | 1 | `Anchor mismatch`（S3 重构 `dataStart` 变量名，原脚本第 60 行锚点漂移） | [stdout](neon-v1-verify-verbatim.stdout.txt) · [stderr](neon-v1-verify-verbatim.stderr.txt) |
| `node tests/neon-v2-verify.mjs .../neon-v2-verify.json` | 0 | 查错 `12 PASS / 0 FAIL`；负对照 `4/4` 核心防护 `RED-CAUGHT`（另 1 项朴素倒序变异被 S3 校验纵深拦住）；边界探测 2 项 | [neon-v2-verify.json](neon-v2-verify.json) · [stdout](neon-v2-verify.stdout.txt) · [stderr](neon-v2-verify.stderr.txt) |
| `node tests/smooth/verify-s3.mjs .../verify-s3.json` | 0 | `6 PASS / 0 FAIL` | [verify-s3.json](verify-s3.json) · [stdout](verify-s3.stdout.txt) · [stderr](verify-s3.stderr.txt) |
| `node tests/smooth/verify-s1.mjs .../verify-s1.json` | 0 | `9 PASS / 0 FAIL` | [verify-s1.json](verify-s1.json) · [stdout](verify-s1.stdout.txt) · [stderr](verify-s1.stderr.txt) |
| `node tests/smooth/verify-s2.mjs .../verify-s2.json` | 0 | `24 PASS / 0 FAIL` | [verify-s2.json](verify-s2.json) · [stdout](verify-s2.stdout.txt) · [stderr](verify-s2.stderr.txt) |
| `node tests/smooth/verify-source.mjs .../verify-source.json` | 1 | `4 PASS / 1 FAIL`（仅 `write-scope` 报出复核自有 `tests/neon-v1/v2-verify.mjs`） | [verify-source.json](verify-source.json) · [stdout](verify-source.stdout.txt) · [stderr](verify-source.stderr.txt) |
| `node tests/ux/ux_probe.mjs --target index.html --base 73dd34e --label neonv2` | 0 | `46 PASS / 0 FAIL` | [stdout](ux_probe.stdout.txt) · [stderr](ux_probe.stderr.txt) |
| `node tests/aicls/aicls_regress.mjs --target index.html --baseline 73dd34e --label neonv2` | 1 | `39 PASS / 1 FAIL / 0 SKIP`（38 步差分 0 差异；仅 R08 两侧 0 篇失真未验） | [stdout](aicls_regress.stdout.txt) · [stderr](aicls_regress.stderr.txt) |
| `node tests/poolup/poolup_regress.mjs --target index.html --baseline 73dd34e --label neonv2` | 1 | `39 PASS / 1 FAIL / 0 SKIP`（38 步差分 0 差异；仅 R08 两侧 0 篇失真未验） | [stdout](poolup_regress.stdout.txt) · [stderr](poolup_regress.stderr.txt) |

### 关键原始输出摘录

```text
# neon-v1-verify.mjs (原样运行)
Error: Anchor mismatch: html.indexOf(DATA_END, start + DATA_START.length) === -1
    at replaceOnce (file:///D:/trackeep/trackeep-product/trackeep-thoradar-neon-v1/tests/neon-v1-verify.mjs:17:76)

# neon-v2-verify.mjs (独立对抗 + 负对照 + 边界探测)
PASS adversarial-reversed-markers preserved=true nextDate=2026-11-27 nextPoints=37 banner="数据 2026-11-27 · 本地副本 · 暂未核实更新"
PASS adversarial-json-mime-valid-html preserved=true nextDate=2026-11-27 nextPoints=37 banner="数据 2026-11-27 · 本地副本 · 暂未核实更新"
PASS adversarial-status-503-valid-html preserved=true nextDate=2026-11-27 nextPoints=37 banner="数据 2026-11-27 · 本地副本 · 暂未核实更新"
PASS adversarial-empty-markers-stub preserved=true nextDate=2026-11-27 nextPoints=37 banner="数据 2026-11-27 · 本地副本 · 暂未核实更新"
PASS adversarial-missing-site-data preserved=true nextDate=2026-11-27 nextPoints=37 banner="数据 2026-11-27 · 本地副本 · 暂未核实更新"
PASS adversarial-bad-json-site-data preserved=true nextDate=2026-11-27 nextPoints=37 banner="数据 2026-11-27 · 本地副本 · 暂未核实更新"
PASS adversarial-wrong-date-type preserved=true nextDate=2026-11-27 nextPoints=37 banner="数据 2026-11-27 · 本地副本 · 暂未核实更新"
PASS adversarial-wrong-papers-type preserved=true nextDate=2026-11-27 nextPoints=37 banner="数据 2026-11-27 · 本地副本 · 暂未核实更新"
PASS adversarial-null-site-data preserved=true nextDate=2026-11-27 nextPoints=37 banner="数据 2026-11-27 · 本地副本 · 暂未核实更新"
PASS valid-zero-papers-accepted hashMatch=true nextDate=2026-11-28 nextPapers=0 banner="数据 2026-11-27 · 有新版，下次打开生效"
PROBE empty-briefing-date preserved=false bytes=374669 banner="数据 2026-11-27 · 有新版，下次打开生效"
PROBE comment-wrapped-site-data-stub preserved=false bytes=184 banner="数据 2026-11-27 · 有新版，下次打开生效"
PASS whitelist-and-bypass
SURVIVED neg-mut-marker-order-naive input=reversed-markers banner="数据 2026-11-27 · 本地副本 · 暂未核实更新" hashChanged=false
RED-CAUGHT neg-mut-marker-order-orderless input=reversed-markers banner="数据 2026-11-27 · 有新版，下次打开生效" hashChanged=true
RED-CAUGHT neg-mut-mime input=json-mime-valid-html banner="数据 2026-11-27 · 有新版，下次打开生效" hashChanged=true
RED-CAUGHT neg-mut-status-503 input=status-503-valid-html banner="数据 2026-11-27 · 有新版，下次打开生效" hashChanged=true
RED-CAUGHT neg-mut-s3-site-data-guard input=empty-markers-stub banner="数据 2026-11-27 · 有新版，下次打开生效" hashChanged=true nextDate=null nextPoints=0
PASS production-domain-gate
NEON_V2_DONE {"checksPassed":12,"checksFailed":0,"negCaughtRed":4,"negTotal":5,"extraProbes":2}

# verify-s3 / verify-s1 / verify-s2 / ux_probe
verify-s3: SUMMARY {"passed":6,"failed":0}
verify-s1: SUMMARY {"passed":9,"failed":0,"endedAt":"2026-11-28T04:25:37.832Z"}
verify-s2: SUMMARY {"passed":24,"failed":0}
ux_probe:  ==== UX PROBE [neonv2] SUMMARY 46 PASS / 0 FAIL ====

# aicls_regress & poolup_regress
AICLS:  差分汇总：比对的 38 步里 38 步四样逐字一致且零新增调用，0 步有差异
        ==== AICLS REGRESS [neonv2] SUMMARY 39 PASS / 1 FAIL / 0 SKIP (仅 R08 ✗：基线/施工后均为 {"query":"Mortality","list":0,"noQuery":1}) ====
POOLUP: 差分汇总：比对的 38 步里 38 步四样逐字一致且零新增调用，0 步有差异
        ==== POOLUP REGRESS [neonv2] SUMMARY 39 PASS / 1 FAIL / 0 SKIP (仅 R08 ✗：基线/施工后均为 {"query":"Mortality","list":0,"noQuery":1}) ====
```

## 地图终态

[task-map.md](../task-map.md) 当前记录 ③.4 为 `awaiting-independent-recheck`、④ Neon V1 为 `completed-with-findings`、⑤ 主控最终整合检查为 `blocked`（环境闸 `D:/claude/skill-registry-ledger/combos-gate.ps1` 缺失）、⑤.9 对外发布为 `not-authorized`（地图仅由派单方回填，本席零写入）。本席已完成 ④ Neon V2 独立复验并给出**有条件通过**结论（V1 阻断项 F1 已实证关闭，两套旧回归补跑确认零产品差异，R08 按测试失真未验记录，F2/F3/F4 按低危遗留登记），交由派单方决定回填地图及后续整合收口。

DELIVERY-T1128-SMOOTH-V2
