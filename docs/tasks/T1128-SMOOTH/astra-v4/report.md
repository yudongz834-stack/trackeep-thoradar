**干了什么**　独立复核了 11 月 28 日 43 篇候选。正常与退役发布模拟均通过；合法的 2 篇日报会被必经的 UX 闸拦下，⑦判阻断。  
**PI 怎么亲手验**　打开[两篇日报的阅读验证原始输出](evidence/ux-ci-small-f9.stdout.txt)，可见页面显示 2/2，随后报 `FAIL F9a` 和 `FAIL F9b`。  
**还剩什么坑**　每日发布认证仍有一项阻断。托管 runner、线上正常发布、退役和真机验收均待后续。

## 结论与阻断

**T1128-SMOOTH-A4 · R2 · ⑦不放行。** 本轮未复现 43 篇候选发旧首页、发错 worker 或摘要错误仍报成功。相同的部署工作流遇到篇数较少的合法日报会停止。模拟结果适用于本次核对的工作流和测试件。[开工哈希](evidence/inventory-before.json) · [收尾哈希](evidence/inventory-after.json)

**B1　日报不足 13 篇时，阅读验收要求出现第 13 篇。** 用历史提交 `7feecfac0534198244331e59bb22b4abefd5ebc4` 中 11 月 2 日的两篇文献、生成时间、日报日期和漏斗，保留候选的页面代码及现行期刊注册表，建立干净的日报提交。源码检查 5/5。基线生成后逐字等于目标页，两边都用相同的界面和数据。浏览器看到 2 篇，2 篇全部可读。完整 CI UX 仍报 **40 过、6 败，退出 1**。这是本地回放，历史日期用来标识样本。[样本来源与边界](evidence/small-oracle.json) · [源码检查](evidence/source-ci-small.json) · [完整 UX 输出](evidence/ux-ci-small.stdout.txt)

其中 F9a 要求 `before.total > 12` 并出现展开钮，F9b 要求能选中第 13 篇。单独执行 F9 得到 **1 过、2 败**，F9c 的运行期异常检查通过。同一次完整回放里，F2c 因展开和收起时都看得到两条而失败，F10a–c 也因该样本的点位条件失败。仅 F9 的两条硬性要求已足以阻断。工作流 `deploy-oss` 依赖 `smooth-verify`，UX 的退出码 1 会拦住部署。验收还需同时覆盖少篇日报可发，以及有第 13 篇时该条确实可达。[F9 代码](../../../../tests/ux/ux_probe.mjs#L345) · [F9 单跑命令与退出码](evidence/ux-ci-small-f9.run.json) · [工作流依赖](../../../../.github/workflows/deploy_oss.yml#L60)

```text
[阅读可达性] 首屏条目 2/2，按钮「null」→ 展开 2/2｜第 13 篇 无 点击后 selected=pmid_42966824
FAIL F9a F9a 阅读默认仍为前 12 篇，且有明确入口显示其余
FAIL F9b F9b 真鼠标点「显示其余」后所有在筛文献可达
==== UX PROBE [ux-ci-small-f9] SUMMARY 1 PASS / 2 FAIL：F9a ✗  F9b ✗  F9c ✓ ====
```

## 候选与发布验证状态

基底 `28131f314f92a05227fd5923607d717c426da2c5`。直接解析首页得到 `briefing_date=2026-11-28`、`papers.length=43`。完整 SHA-256 如下。清单另含发布模拟、三套浏览器测试、UX、共享库、源码闸与基线生成器。[全量清单](evidence/inventory-before.json)

| 文件 | SHA-256 |
| --- | --- |
| index.html | `27ba018a9a3b4936ec734820af8cb505262bd55f41ae382047615f0a58d7c706` |
| sw.js | `e882e9e2eef0bf36781b8b03ecec23eb81221fa8b33272cdc9de3e368f76394f` |
| sw-retire.js | `5ae38f2ba965f4e1b1d340da2ba5fadd8b58af82a1e271a02ddff97ab5686199` |
| .github/workflows/deploy_oss.yml | `8dba459122bc2a7e42040fc493eb03146170989fbcfb88b6b383f5ff38485790` |

| 亲自执行的命令或对照 | 通过／失败 | 退出码 | 原始证据 |
| --- | ---: | ---: | --- |
| `node tests/smooth/verify-deploy.mjs <json>` | 18／0 | 0 | [stdout](evidence/deploy.stdout.txt) · [含子进程输出的完整调用轨迹](evidence/deploy.json) |
| 同一命令，末参传入删去 ` \|\| md5 != expected` 的 YAML | 16／2 | 1 | [stderr](evidence/deploy-no-md5.stderr.txt) · [命令](evidence/deploy-no-md5.run.json) |
| 同一命令，末参传入退役分支误选 `sw.js` 的 YAML | 15／3 | 1 | [stderr](evidence/deploy-retire-wrong.stderr.txt) · [轨迹](evidence/deploy-retire-wrong.json) |
| `node tests/smooth/verify-s3.mjs <json>` | 9／0 | 0 | [JSON](evidence/s3.json) · [stdout](evidence/s3.stdout.txt) |
| `node tests/smooth/verify-s1.mjs <json>` | 9／0 | 0 | [JSON](evidence/s1.json) · [stdout](evidence/s1.stdout.txt) |
| `node tests/smooth/verify-s2.mjs <json>` | 24／0 | 0 | [JSON](evidence/s2.json) · [stdout](evidence/s2.stdout.txt) |
| `node tests/ux/ux_probe.mjs --target index.html --base 28131f3…` | 46／0 | 0 | [命令](evidence/ux-local.run.json) · [stdout](evidence/ux-local.stdout.txt) |

另用 YAML 解析器读取两个 job，核对 Windows Node 24 先跑 deploy、source、S1、S2、S3，再准备父页并跑完整 UX。验证与部署 checkout 都锁 `github.sha`，所有步骤均未设置条件跳过或 `continue-on-error`。对正常、退役两段模拟轨迹独立计算本地 MD5，逐个比对双域的根、首页、活动 worker 和退役 worker，共 8 URL／模式。两种模式均先写两件 worker，再写首页；两个 worker 验证 HTTP 200、JavaScript MIME 和 `no-store`。退役时真实键名 `/sw.js` 对应退役字节，默认发布强制覆写该同名键为普通 worker，两种模式均有上传参数及摘要记录。[独立结构与逐 URL 对照](evidence/workflow-oracle.stdout.txt)

刷新报错、缺任务 ID、陈旧摘要、错误 MIME、可缓存 worker、404、HEAD 失败、源站 304、上传失败均按用例重试或中止。删 MD5 判定时，模拟发布对错误摘要返回 0，外层测试正确返回 1。独立映射变异触发 `Verification failed for https://thoradar.online/sw.js`。[原版各分支](evidence/deploy.stdout.txt) · [MD5 撤防输出](evidence/deploy-no-md5.stderr.txt) · [退役映射撤防输出](evidence/deploy-retire-wrong.stderr.txt)

## 日报闸与默认本地入口

私有 Git 历史回放了 11 月 27 日 40 篇到 28 日 43 篇的 16 个实际变更路径。15 个非首页文件逐一对上 `28131f3` 的 blob，首页取本次候选。父页单独放入不可见的 `a4-parent-only` 标记。独立按字节拼出「父页前段＋当期 SITE_DATA＋父页后段」，其 SHA-256 与生成器输出同为 `16ff94f4…c3835`；直接取当前页的 LF 规范化结果是 `275de4ac…8172`。标记仅在基线存在，基线保留了双方可辨的代码差异。[逐段核对及 16 路径](evidence/baseline-oracle.json) · [生成器原始输出](evidence/prepare-daily.stdout.txt)

| 场景 | 通过／失败及退出码 | 原始证据 |
| --- | --- | --- |
| 43 篇，干净 checkout 的 `verify-source --ci` | 5／0，退出 0；历史日报文件未被报越权 | [JSON](evidence/source-ci-daily.json) |
| 破坏 JSON、日期改为 `2026-02-30` | 各 4／1，均退出 1 | [坏 JSON](evidence/source-ci-bad-json.stdout.txt) · [非法日期](evidence/source-ci-bad-date.stdout.txt) |
| 未提交或暂存越权写 `feed.xml` | 两次均报 `write-scope`，退出 1；备份拷回后状态干净 | [工作树](evidence/source-ci-dirty.json) · [暂存区](evidence/source-ci-staged.json) · [恢复后状态命令](evidence/clean-after-negatives.run.json) |
| 43 篇的 CI 完整 UX，传入拼合基线 | 46／0，退出 0，零跳项；F8a–d 均有独立 PASS 行。8 幕状态串一致，点快筛、扇区、档位和时间窗在两边均改了状态 | [stdout](evidence/ux-ci-daily.stdout.txt) · [F8 实测 JSON](evidence/ux-ci-daily-measurements/f8-diff.json) |
| 默认 source，不传 `--ci` | 40 篇 C1 数据 5／0，退出 0；43 篇候选 3／2，退出 1，命中固定数据和历史写域 | [40 篇](evidence/source-local-old.stdout.txt) · [43 篇候选](evidence/source-local.stdout.txt) |
| 本地默认 UX 不传 `--base` 或 `--base-html`，单跑 F8 | 本地 `main=73dd34e` 的 40 篇与当前 43 篇产生真实差分，F8a–c 红、F8d 绿，退出 1 | [命令](evidence/ux-local-default-strict.run.json) · [stdout](evidence/ux-local-default-strict.stdout.txt) |

## 环境、改动清单与交叉核对

Windows 11 x64 10.0.26300，Node v24.14.0，Chrome 158.0.8127.88，Git 2.53.0.windows.2。表内每个具名场景各跑 1 次，使用固定输入，无随机种子。每次浏览器使用独立临时 profile 和回环服务。按日志记录的 49 个 PID 逐一执行 `Get-Process -Id`，49 个均返回 `ABSENT`。每条命令的工作目录、参数、UTC 起止、退出码保存在同名 `.run.json`，同名 `.stdout.txt`、`.stderr.txt` 保存原始流。[逐 PID 原始输出](evidence/pids-after.stdout.txt) · [复查命令](evidence/pids-after.run.json) · [环境](evidence/inventory-before.json)

本席写入独立树的 `docs/tasks/T1128-SMOOTH/astra-v4/`，包括自有取证脚本、私有 Git 副本、基线、变异 YAML 和证据。主仓同名目录收取报告与证据。产品、工作流及施工测试共 16 个文件，主仓与独立树哈希逐项相同，收尾也与开工相同。两次发布变异都以单独 YAML 路径传入；日报数据变异在私有副本使用备份拷回。[复演脚本](evidence/adapters.zip) · [两树逐项核对](evidence/handoff-check.json)

所有测试与 PID 记录落盘后，才阅读 Sol 两份报告。S5 的发布 18／0 和删 MD5 后 16／2 得到独立复现。S5 报出的旧数据固定基线红项在默认本地入口保留；S6 针对 11 月 28 日 16 文件日报的修复得到独立复现。两份报告所示的 43 篇绿单不能覆盖本次 2 篇回放，B1 单列为发布阻断。[S5 报告](../sol-s5-report.md) · [S6 报告](../sol-s6-report.md)

## 未验、遗留风险与地图终态

- 旧套件 AICLS、POOLUP 仅沿用 V2 各 39/40；R08 失真未验，本轮运行数均为 0。
- 本机已验证回环浏览器行为和假 OSS/CDN 命令。GitHub 托管 runner、生产 OSS/CDN 权限、真实缓存传播、线上正常与退役切换、真机及 iOS 均未验；本轮线上发布和退役演练次数为 0。
- 地图影响为⑥保留本机候选与原证据，⑦独立复核完成、结论阻断，B1 待修复复验，⑧待⑦放行后由 PI 亲手执行。任务地图由 Orchestrator 回填。[任务地图](../task-map.md)

DELIVERY-T1128-SMOOTH-A4
已独立核验正常与退役发布，并复现合法少篇日报被 UX 闸拦住的发布阻断。
