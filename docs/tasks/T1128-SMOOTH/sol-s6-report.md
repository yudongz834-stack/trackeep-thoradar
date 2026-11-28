**干了什么**　修复日报发布闸。真实日报的 16 文件更新在干净 checkout 上通过源码检查和完整 UX，F8 仍能抓到旧日报基线。\
**PI 怎么亲手验**　打开[日报 UX 复跑原始输出](sol-s6/rerun/daily-final/ux-ci-daily.stdout.txt#L107)，看到 `PASS F8a` 至 `PASS F8d` 和 `SUMMARY 46 PASS / 0 FAIL` 即为本机复演通过。\
**还剩什么坑**　⑦ 独立复核和 GitHub 托管 runner 待验证，⑧ 线上发布与验收待 PI 亲手执行。

## 地图影响

⑥ S6 已交付隔离工作树与[六文件增量补丁](sol-s6/daily/candidate.diff)。补丁以 S5 施工候选为输入，能在原 S5 工作树正向应用，`git apply --check` 返回 `0`。本次只写 `.github/workflows/deploy_oss.yml`、`tests/smooth/`、`tests/ux/ux_probe.mjs` 和本任务证据。无写域偏差。主控可用该增量叠加 S5，C2 三件产品有逐件开工与收尾哈希。[正向补丁检查](sol-s6/patch-forward.run.json) · [反向检查及 `diff --check`](sol-s6/daily/daily.runs.json) · [产品哈希及日报文件清单](sol-s6/daily/daily-case.json)

按委任状、C2 发布验收合同和用工法的写审分离、证据要求与收卷规则施工。源码改动和本机复跑属于施工，独立验收归⑦。[C2 发布验收合同](/D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/release-contract.md)

## 改动清单

- `verify-source.mjs` 增加 `[--ci]`。CI 从独立提取的 `SITE_DATA` 块解析 JSON，校验 `briefing_date` 的实际日历日期和 `papers` 类型。`PAPERS` 初始化及 `inWindow`、`mergePapers` 仍与 C1 基线比较。本地默认入口继续逐字对照 C1 数据，并把差异与未跟踪文件纳入写域检查。
- CI 写域从 checkout 的 `HEAD` 起算，分别检查暂存区、工作树和未忽略的未跟踪文件。精确允许任务书授权的 UX 探针文件。提交里的日报数据、API 和 feed 不计入本次 runner 的写入。
- `prepare-ci-ux-baseline.mjs` 校验输入 SHA 等于 `HEAD`，以及受测首页等于该提交的首页。取 `HEAD^1` 的 HTML，只替换数据标记间的块，验证输出的父提交前后文和当前数据，再写到 runner 临时目录。`ux_probe.mjs --base-html` 使用该文件。原有 `--base` 继续读指定提交，默认仍为 `main`。
- 工作流与静态检查同步。验证 checkout 用全历史，验证与部署均锁定 `github.sha`。发布模拟、源码、S1、S2、S3、UX 的原顺序保留，准备基线在 UX 前执行。部署继续依赖整个 `smooth-verify`，发布 Bash 未改。[源码和工作流增量](sol-s6/daily/candidate.diff)

## 验证状态

Windows 11 `10.0.26300`、Node `24.14.0`、Chrome `158.0.8127.88`。浏览器用隔离 profile 与回环服务，发布模拟使用合成参数及假命令。命令和退出码见[本地套件记录](sol-s6/core.runs.json)、[日报复演记录](sol-s6/daily/daily.runs.json)和[YAML 检查记录](sol-s6/yaml.run.json)。

| 验证 | 通过／失败 | 退出码 | 原始证据 |
| --- | ---: | ---: | --- |
| S5 发布静态与 Bash 模拟 | 18／0 | 0 | [stdout](sol-s6/deploy.stdout.txt) · [stderr](sol-s6/deploy.stderr.txt) · [JSON](sol-s6/deploy.json) |
| C1 默认 `verify-source` | 5／0 | 0 | [stdout](sol-s6/source-local.stdout.txt) · [stderr](sol-s6/source-local.stderr.txt) · [JSON](sol-s6/source-local.json) |
| S1 | 9／0 | 0 | [stdout](sol-s6/s1.stdout.txt) · [stderr](sol-s6/s1.stderr.txt) · [JSON](sol-s6/s1.json) |
| S2 | 24／0 | 0 | [stdout](sol-s6/s2.stdout.txt) · [stderr](sol-s6/s2.stderr.txt) · [JSON](sol-s6/s2.json) |
| S3 | 9／0 | 0 | [stdout](sol-s6/s3.stdout.txt) · [stderr](sol-s6/s3.stderr.txt) · [JSON](sol-s6/s3.json) |
| C1 旧 `--base 73dd34e` UX | 46／0 | 0 | [stdout](sol-s6/ux-local.stdout.txt) · [stderr](sol-s6/ux-local.stderr.txt) · [F8 JSON](sol-s6/ux-local-measurements/f8-diff.json) |
| 43 篇日报 `verify-source --ci` | 5／0 | 0 | [stdout](sol-s6/daily/source-ci-daily.stdout.txt) · [stderr](sol-s6/daily/source-ci-daily.stderr.txt) · [JSON](sol-s6/daily/source-ci-daily.json) |
| 43 篇日报完整 UX | 46／0 | 0 | [stdout](sol-s6/daily/ux-ci-daily.stdout.txt) · [stderr](sol-s6/daily/ux-ci-daily.stderr.txt) · [F8 JSON](sol-s6/daily/ux-ci-measurements/f8-diff.json) |
| 同日报走默认 `verify-source` | 3／2 | 1 | [stdout](sol-s6/daily/source-local-daily.stdout.txt) · [JSON](sol-s6/daily/source-local-daily.json) |
| 旧父提交数据直喂 F8 | 1／3 | 1 | [stdout](sol-s6/daily/ux-ci-stale-parent.stdout.txt) · [stderr](sol-s6/daily/ux-ci-stale-parent.stderr.txt) · [F8 JSON](sol-s6/daily/ux-stale-measurements/f8-diff.json) |

用 `28131f314f92a05227fd5923607d717c426da2c5` 的 16 文件更新构造日报提交，首页与 C2 发布候选字节一致。临时父提交加了一枚无渲染效果的 `<meta>`，使测试能区分父提交 HTML 与当前 HTML。复演脚本独立逐段比较父提交前后文和当前数据块。基线记录显示父数据哈希 `6d4a6663…`、当前日报数据哈希 `1b624d90…`，日期 `2026-11-28`，43 篇。复演前后 `git status --porcelain=v1 -uall` 均为空。产品哈希在 C1、C2 各自开工与收尾逐件相等。[复演脚本](sol-s6/replay-ci.mjs) · [生成基线原始输出](sol-s6/daily/prepare-baseline.stdout.txt) · [快照与哈希](sol-s6/daily/daily-case.json)

### 负对照

| 改动 | 原始结果 | 退出码 |
| --- | --- | ---: |
| 损坏 JSON、使用 `2026-02-29` 或把 `papers` 改为对象 | [JSON 失败](sol-s6/daily/source-bad-json.stdout.txt) · [日期失败](sol-s6/daily/source-invalid-date.stdout.txt) · [数组失败](sol-s6/daily/source-invalid-papers.stdout.txt) | 各 1 |
| 改初始化段、改合并函数 | [初始化失败](sol-s6/daily/source-initialization-change.stdout.txt) · [合并失败](sol-s6/daily/source-merge-change.stdout.txt) | 各 1 |
| 未提交的 `feed.xml` 写入 | [工作树失败](sol-s6/daily/source-dirty-feed.stdout.txt) · [暂存区失败](sol-s6/daily/source-staged-feed.stdout.txt) | 各 1 |
| 生成基线时夹带父提交旧数据、替换错块或直接使用当前 HTML | [旧数据失败](sol-s6/daily/prepare-old-data.stderr.txt) · [错块失败](sol-s6/daily/prepare-wrong-block.stderr.txt) · [当前提交自比失败](sol-s6/daily/prepare-self-baseline.stderr.txt) | 各 1 |
| 传入非 checkout 的 SHA | [SHA 失败](sol-s6/daily/prepare-wrong-sha.stderr.txt) | 1 |

临时撤掉 `JSON.parse` 后，同一个坏 JSON 用例从退出 `1` 变成 `0`，证实负对照覆盖真实解析。临时撤掉基线产物断言后，故意输出旧父提交数据的命令退出 `0`，独立的三段对照仍拒绝该文件。两处变异都用备份恢复，临时 worktree 已移除。[撤掉解析的 stdout](sol-s6/daily/mutation-no-json-parser.stdout.txt) · [撤掉基线断言的 stdout](sol-s6/daily/mutation-no-baseline-guard.stdout.txt) · [命令与退出码](sol-s6/daily/daily.runs.json)

S5 原 `reproduce-daily` 脚本及红证据保留在原位置。新复演用 `sol-s6/` 独立路径。浏览器收尾日志里的 30 个 PID 已逐个复查，全部返回 `status=not-found`。[S5 原红证据](/D:/trackeep/trackeep-product/trackeep-thoradar-smooth-T1128/docs/tasks/T1128-SMOOTH/sol-s5/daily.run.json) · [S5 文件哈希](sol-s6/s5-red-hashes.json) · [PID 原始复查](sol-s6/process-recheck.stdout.txt) · [复查命令](sol-s6/process-recheck.run.json)

### 本轮复跑

沿用隔离树里已交付的六文件候选，复跑发布模拟、默认源码检查、S1/S2/S3 和旧 `--base` UX，六条命令均退出 `0`。复跑生成的补丁与原补丁 SHA-256 相同，正向和反向应用检查均退出 `0`。[命令与退出码](sol-s6/rerun/core.runs.json) · [发布模拟 stdout](sol-s6/rerun/deploy.stdout.txt) · [补丁应用检查](sol-s6/rerun/patch.runs.json) · [补丁哈希](sol-s6/rerun/patch-hashes.json)

完整日报复演确认 F8 四项均 `PASS` 且整卷无跳项。撤掉日历校验时，同一个 `2026-02-29` 用例从退出 `1` 变成 `0`。暂存及未暂存的 `feed.xml` 改写均判红，清理后 checkout 恢复干净。C1 与 C2 三件产品的开工和收尾哈希分别逐件一致。[日报命令与退出码](sol-s6/rerun/daily-final/daily.runs.json) · [非法日期 stdout](sol-s6/rerun/daily-final/source-invalid-date.stdout.txt) · [日期撤防 stdout](sol-s6/rerun/daily-final/mutation-no-calendar-check.stdout.txt) · [产品哈希](sol-s6/rerun/daily-final/daily-case.json)

首次复跑时，UX 已退出 `0`，复演脚本却错误地要求汇总行包含 `0 SKIP`。已按实际汇总格式修正断言并逐行检查跳项，完整复跑退出 `0`。两次输出均保留。复跑日志中记录的 PID 已逐个复查，全部返回 `status=not-found`。[首次复跑 stderr](sol-s6/rerun/replay.stderr.txt) · [修正后复跑 stdout](sol-s6/rerun/replay-final.stdout.txt) · [原始 PID 复查](sol-s6/rerun/process-recheck.stdout.txt)

## 遗留风险

- GitHub 托管 runner 尚未执行。真实 OSS/CDN 响应、刷新权限及缓存传播留到实际发布验收。
- 日报复演使用本地提交拓扑，包含真实日报的 16 文件和临时父页标记。S6 补丁以 S5 接线已在场为前提。`HEAD^1` 缺失时，准备基线步骤会判红。

## 地图终态

按 C2 基底 `28131f314f92a05227fd5923607d717c426da2c5` 的唯一任务地图收卷。⑥ S6 施工及本机证据已交付，待⑦独立复核对表后销单。⑧ 由 PI 在复核放行后亲手发布。地图由主控回填，本次以 SHA-256 `614f338a73bb389d00c92c2819371508a5c041509009a980f9be4c33f6641529` 版为引用。[唯一任务地图](/D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/task-map.md)

DELIVERY-T1128-SMOOTH-S6
已修复日报发布的源码与 UX 验收闸，并交付真实日报复演、负对照和增量补丁。
