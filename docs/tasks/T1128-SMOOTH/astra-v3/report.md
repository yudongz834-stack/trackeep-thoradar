**干了什么**　独立复验 Sol S4。空日期和注释内的数据桩都被拒绝写入缓存，随后打开页面仍显示 2026-11-27、40 篇论文和 37 个雷达点。  
**PI 怎么亲手验**　点开[核验结果](verdict.txt)，看前两行是否各有 `preserved=true`、`bytes=539012`、`next=cache-storage` 和 `counter=40 / 40`。  
**还剩什么坑**　F2 冷缓存双请求与状态短闪、F3 回归工具缺父目录沿用 V2 记录。AICLS、POOLUP 的 R08 检索步仍未验，真机及线上表现也未验。

# T1128-SMOOTH-A3 独立复验报告

**④ Astra V3 通过，F4 的两个边界漏口可以关闭。本轮范围内未发现阻断项。** 浏览器实测窗口为 2026-11-28 13:00:17 至 13:04:37（UTC+8），各套件各一轮。环境为 Windows 11 Pro 10.0.26300 x64、Node v24.14.0、Chrome 158.0.8127.88、CDP 1.3。复核席为委任的 `codex-gpt`，未再派。[环境及原始输出](independent.json)

## 候选与样本

在独立工作树中先计算 SHA-256，再以 `fc.exe /b` 对照 Sol S4 施工树。下列三件文件在开跑前、跑完后均返回 `FC: no differences encountered`、退出码 0。两树 HEAD 均为 `73dd34e65fce6661d74e595afc03df68e7d3f44f`。可用 PowerShell 复核，例为 `Get-FileHash -Algorithm SHA256 index.html` 和 `fc.exe /b index.html ..\trackeep-thoradar-smooth-T1128\index.html`。[开跑前记录](baseline.txt) · [跑完后记录](postflight.txt)

| 文件 | S4 实测 SHA-256 |
|---|---|
| index.html | `33c50bef723b0a3f32b51bc2d5927ff4391bb58eb474996f1a7d9dff96bc1def` |
| sw.js | `e882e9e2eef0bf36781b8b03ecec23eb81221fa8b33272cdc9de3e368f76394f` |
| sw-retire.js | `5ae38f2ba965f4e1b1d340da2ba5fadd8b58af82a1e271a02ddff97ab5686199` |

独立脚本的运行副本只改了 `s3GuardBlock` 的一行日期表达式。用标准输入从原 `tests` 目录执行后，导入路径、样本、`preserved` 判据和五项内存变异均可原样使用。原件 SHA-256 为 `b4ebc7cc7ad5a4f49eff067cdb01ce48d514e75322b623a2accf2036c48b4fc5`，副本为 `5eb0d78289bcbbc36e05d0fcef84a481228d7fee512fda3e1fca73f5b95eeed1`。JSON 中的 `source` 与终端的 `NEON_V2_DONE` 均为原脚本标签，本轮候选由 JSON 内的三件哈希标识。[唯一适配 diff](anchor.diff) · [运行参数](independent.run.json)

## 两个原失败样本

| V2 原样本 | V2 实际写入 | S4 独立探针 | S4 下一次打开 |
|---|---|---|---|
| `empty-briefing-date` | `preserved=false`，374669 B | `preserved=true`，539012 B | CacheStorage，2026-11-27，页面计数 40 / 40，37 个雷达点 |
| `comment-wrapped-site-data-stub` | `preserved=false`，184 B | `preserved=true`，539012 B | CacheStorage，2026-11-27，页面计数 40 / 40，37 个雷达点 |

两项保留的缓存 SHA-256 均等于上表的健康 `index.html`。S3 的本次上游请求与 V2 当时写入的坏页逐项对应，空日期样本的 SHA-256 为 `f13cfb12bdf230aa2788ddea5e6e3c97529fd669576f8e7acb43b0549fbdfbe4`，注释样本为 `438c6d30e0336bc1b430df5c5870890928f92258c78606cfdd989076ef75bb1e`。[V2 原始探针](../neon-v2/neon-v2-verify.json) · [本轮独立探针](independent.json) · [S3 上游与缓存记录](s3.json)

原独立脚本在保住缓存时会将 `extraProbes[].nextSnap` 留空。S3 已逐项验证下一次导航的数据日期和论文数。为直接核对页面显示，复核席另用同哈希样本做了两次 DOM 观察。两次都由 CacheStorage 返回 `/index.html`，状态条显示「数据 2026-11-27 · 本地副本 · 暂未核实更新」，页面计数器显示「40 / 40」。[浏览器原始输出](render.stdout.txt) · [导航与 DOM 读数](render.json)

空标记、坏 JSON、错误的日期类型和论文类型均保留健康缓存。合法零篇更新则写入 374679 B，下一次导航显示 2026-11-28、0 篇、0 个雷达点。[独立脚本 stdout](independent.stdout.txt) · [S3 九项 JSON](s3.json)

## 撤防结果

| 旧脚本中的内存变异 | 实测 | 缓存与判读 |
|---|---|---|
| `mut-mime` | RED-CAUGHT | 错误 MIME 的响应替换了缓存，状态条报「有新版」 |
| `mut-status-503` | RED-CAUGHT | HTTP 503 响应替换了缓存，状态条报「有新版」 |
| `mut-marker-order-naive` | SURVIVED | 哈希仍为健康页。S4 在读数据前拦住倒序标记，该朴素变异在 V2 已被后续内容校验拦住 |
| `mut-marker-order-orderless` | SURVIVED | 哈希仍为健康页。双向切片保留，但倒序后的起始标记前已有脚本内容，先被 S4 的脚本上下文校验拒绝 |
| `mut-s3-site-data-guard` | SURVIVED | 哈希仍为健康页。空标记在 HTML 注释内，S4 在进入已撤掉的声明与 JSON 校验前就拒绝该样本 |

前两项变异均写入 SHA-256 为 `e83acf8ff52b04fef144cad2dd763ee1d3ff94c0c0ac315634394fb87c11403b` 的响应。其余三项的 `cachedHashAfter` 与健康页全值相同，状态条均为「暂未核实更新」。[逐项原始输出](independent.stdout.txt) · [含完整哈希的判断](verdict.txt)

| Sol 留下的专项工人 | 退出码 | 通过 / 失败 | 失败项的实际后果 |
|---|---:|---:|---|
| `no-date-guard.sw.js` | 1 | 7 / 2 | 空日期和不存在的 2026-02-29 分别写入 374669 B、175 B，下一次读到的论文数均为 0 |
| `no-script-guard.sw.js` | 1 | 8 / 1 | 仅注释样本变红，缓存变为 184 B，下一次日期与论文数均读到 null |

两个工人均直接从 Sol S4 的证据目录读取。实测工人 SHA-256 分别为 `e78a336372a349e3e561293572cbee4a28fc9994259ab18ca37716f052239e2f`、`7976934b55d8d3d865d8752e143242df64a0295f666c8a893b9157a9b9518de9`。两次跑的都是同一套九项断言。[日期撤防 JSON](no-date-guard.json) · [上下文撤防 JSON](no-script-guard.json)

## 验证状态：实测命令、退出码与日志

工作目录为 `D:/trackeep/trackeep-product/trackeep-thoradar-neon-v1`。下表用 `E` 表示该目录下的 `astra-v3`，`M` 表示 `../trackeep-thoradar-smooth-T1128/docs/tasks/T1128-SMOOTH/sol-s4`。每行的「参数」均记录实际工作目录、完整 argv、标准输入来源、起止时间和进程退出码。独立脚本单独从 `tests` 目录运行。

| 实际命令（路径缩写见上） | 退出码 | 判读 | 原始证据 |
|---|---:|---|---|
| `node --input-type=module - E/independent.json < E/neon-v2-s4.mjs` | 0 | 12/12，另核两项探针、五项撤防 | [参数](independent.run.json) · [stdout](independent.stdout.txt) · [stderr](independent.stderr.txt) · [JSON](independent.json) |
| `node tests/smooth/verify-s3.mjs E/s3.json` | 0 | 9/9 | [参数](s3.run.json) · [stdout](s3.stdout.txt) · [stderr](s3.stderr.txt) · [JSON](s3.json) |
| `node tests/smooth/verify-s3.mjs E/no-date-guard.json M/no-date-guard.sw.js` | 1 | 7/2，预期的两个失败 | [参数](no-date-guard.run.json) · [stdout](no-date-guard.stdout.txt) · [stderr](no-date-guard.stderr.txt) · [JSON](no-date-guard.json) |
| `node tests/smooth/verify-s3.mjs E/no-script-guard.json M/no-script-guard.sw.js` | 1 | 8/1，预期的一个失败 | [参数](no-script-guard.run.json) · [stdout](no-script-guard.stdout.txt) · [stderr](no-script-guard.stderr.txt) · [JSON](no-script-guard.json) |
| `node tests/smooth/verify-s1.mjs E/s1.json` | 0 | 9/9 | [参数](s1.run.json) · [stdout](s1.stdout.txt) · [stderr](s1.stderr.txt) · [JSON](s1.json) |
| `node tests/smooth/verify-s2.mjs E/s2.json` | 0 | 24/24 | [参数](s2.run.json) · [stdout](s2.stdout.txt) · [stderr](s2.stderr.txt) · [JSON](s2.json) |
| `node tests/ux/ux_probe.mjs --target index.html --base 73dd34e --label astrav3` | 0 | 46/46 | [参数](ux.run.json) · [stdout](ux.stdout.txt) · [stderr](ux.stderr.txt) · [状态面差分](ux-measurements/f8-diff.json) |
| `node astra-v3/read-render.mjs E/render.json` | 0 | 2/2，下一次导航的可见日期、计数和雷达点 | [参数](render.run.json) · [stdout](render.stdout.txt) · [stderr](render.stderr.txt) · [JSON](render.json) |
| `python astra-v3/validate_evidence.py` | 0 | 逐字段对读 V2、两套本轮探针、撤防和回归记录 | [完整输出](verdict.txt) |

## 改动清单、清理与终态

八次运行都使用独立临时 Chrome 配置，测试 HTTP 服务绑定回环地址。主浏览器 PID 分别为独立脚本 47212、S3 36916、日期撤防 51064、脚本撤防 48604、S1 46852、S2 69688、UX 55956、DOM 观察 55720。收尾按本次 Node 进程的子树记录 Chrome 的 PID、启动时间与配置路径，再执行 `Get-Process -Id <PID>` 和 `Test-Path -LiteralPath <profile>`。八个配置目录均已消失，逐 PID 核对无同一测试进程存活。终查中已有号码被系统重用，记录为 `creationMatch=False`。UX 原生清理行与逐 PID 原始结果均已留档。[终查原始输出](process-recheck.txt) · [UX 原生清理输出](ux.stdout.txt)

- **沿用与未验。** `index.html` 的完整哈希与 V2 相同。AICLS、POOLUP 沿用 V2 各 39/40。两套的 R08 在基线和候选上都因选词导致空结果，检索效果仍未验证。F2 冷缓存双请求及状态短闪、F3 回归工具遇到缺失父目录时报错，沿用 V2 的低危记录。合同范围以外的 iOS/真机、国内无代理直连、线上跨日、多标签完整生命周期、正常 SW 自身升级、90 天离线、UX3 合并、CDN 及生产发布未验。[V2 AICLS](../neon-v2/aicls_regress.stdout.txt) · [V2 POOLUP](../neon-v2/poolup_regress.stdout.txt) · [V2 遗留记录](../neon-v2/report.md) · [验收合同](../acceptance-contract.md)
- **地图影响。** ④ 的验收条件已满足，③.4 的 S4 返修可关，⑤ 可由 Orchestrator 开始最终整合检查。任务地图由派单方回填，本席交付终态为「独立复验通过」。⑤ 尚待整合。⑤.9 仍为 `not-authorized`。[任务地图](../task-map.md)
- **写域。** 复核自有程序及原始运行副本位于独立工作树的 `astra-v3/`。主仓仅交付本证据目录。UX 的临时输出根另留一份基线 HTML 与九份测量 JSON。浏览器配置已清除。[UX 输出位置](ux.run.json)

DELIVERY-T1128-SMOOTH-A3
独立复验确认 Sol S4 已修复两个缓存漏口，两项撤防和既有核心回归均得到预期结果。
