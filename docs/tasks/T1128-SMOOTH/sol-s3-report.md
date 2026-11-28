**干了什么**　修复了胸科雷达首页缓存写入校验。156 B 的空标记损坏页和另外四个坏样本均被拒绝，合法零篇版在下次打开时正常显示。  
**PI 怎么亲手验**　点击专项原始输出，看到 `PASS neon-empty-markers-stub` 一行的 `before` 和 `after` 都是 `539012` 字节且 SHA-256 相同，就验到了健康副本被保留。[专项原始输出](sol-s3-recheck/after.stdout.txt)  
**还剩什么坑**　AICLS 和 POOLUP 的 R08 仍因基线与候选均搜到零篇而无法判定。S3 施工自测完毕，待独立复核和主控整合。

## 地图影响

T1128-SMOOTH-S3 对应胸科雷达顺畅改造 ③.4 的 R2 返修。指定隔离工作树里已有 S3 候选和首轮证据，本轮核对基线后，使用同一版专项脚本复跑旧版、新版和删减版，并补齐正式回执。岗位卡为 `builder-jobspec`，轨道版本为 `T1128-SMOOTH v1`，委任席位为 `codex-gpt`，点名档位为 `gpt-6.2-sol`。

`sw.js` 的 `fetchShell` 在现有 HTTP 200、`basic`、HTML MIME、标记顺序及 `</html>` 收尾检查后，提取两个标记之间的 `const SITE_DATA = …` 声明，用 `JSON.parse` 验证 JSON 对象并检查 `briefing_date` 是字符串、`papers` 是数组。安装预取与后台核新共用该函数。相对 S2 的生产代码差异限于这一处。[worker 差异](sol-s3-recheck/worker.diff.txt) [源文件检查](sol-s3-recheck/source.json)

Neon 的 156 B 样本与独立证据中的 SHA-256 完全一致。旧版在收到 HTTP 200、`text/html` 响应后将 539,012 B 的健康副本换成了这 156 B，下次从 Cache Storage 读到损坏壳。候选版对五个异常输入均报告 `unavailable`，健康副本的长度和 SHA-256 在刷新前后完全一致，下次打开仍从 Cache Storage 显示 `2026-11-27` 的 40 篇。零篇用例更新为 `2026-11-28`，下次打开从 Cache Storage 读出 `papers.length === 0`。缺块用例在结束标记外放置了一个合法声明，验证了声明必须位于标记之间。[Neon 独立样本](/D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/neon-v1/neon-v1-verify.json:141) [基线 JSON](sol-s3-recheck/before.json) [候选 JSON](sol-s3-recheck/after.json)

## 遗留风险

- AICLS 和 POOLUP 各有一项 R08 原样失败。两套脚本都挑中 `Mortality`，基线和候选均报告 `list: 0, noQuery: 1`，因此这项检索差分仍未验证。[AICLS 原始输出](sol-s3-recheck-regressions/aicls.stdout.txt) [POOLUP 原始输出](sol-s3-recheck-regressions/poolup.stdout.txt)
- 验证环境为本机 Chrome 和回环测试服务。线上、CDN 和真机未验。独立复核由主控另行验收。

## 证据

Windows 11 Pro x64 `10.0.26300`，Node `v24.14.0`，Chrome `158.0.8127.88`，CDP `1.3`，无随机种子。专项正式复跑从北京时间 `2026-11-28 11:58:20` 开始，最后一套既有回归于 `12:00:37` 结束。各套精确 UTC 起止、命令、哈希及逐项结果在 JSON。旧三项负对照通过既有测试设施返回变异响应。S3 负对照只从临时 worker 文件删掉数据块检查，保留原来的 HTTP、MIME、标记与收尾检查。删除代码原文、变异 SHA-256 与实际退出码留在运行记录。[S3 负对照运行记录](sol-s3-recheck/no-data-validation.run.json) [既有回归汇总输出](sol-s3-recheck/legacy.stdout.txt)

```powershell
$e = 'docs/tasks/T1128-SMOOTH/sol-s3-recheck'
$baseline = 'D:/trackeep/trackeep-product/trackeep-thoradar-neon-v1/sw.js'
node tests/smooth/verify-s3.mjs "$e/before.json" $baseline
node tests/smooth/verify-s3.mjs "$e/after.json"
pwsh -NoProfile -File "$e/run-no-data-validation.ps1"
node tests/smooth/verify-s1.mjs "$e/s1.json" none
node tests/smooth/verify-s2.mjs "$e/s2.json" none
node tests/smooth/verify-s1.mjs "$e/s1-no-local-return.json" no-local-return
node tests/smooth/verify-s1.mjs "$e/s1-allow-truncated.json" allow-truncated
node tests/smooth/verify-s2.mjs "$e/s2-no-retire-cleanup.json" no-retire-cleanup
node tests/smooth/verify-source.mjs "$e/source.json"
node tests/smooth/run-regressions.mjs sol-s3-recheck-regressions
```

| 验证 | 通过 / 失败 | 退出码 | 原始证据 |
| --- | ---: | ---: | --- |
| S3 修复前首轮 | 1 / 5 | — | [JSON](sol-s3-before.json) · [stdout](sol-s3-before.stdout.txt) · [stderr](sol-s3-before.stderr.txt) |
| S3 基线正式复跑 | 1 / 5 | 1 | [JSON](sol-s3-recheck/before.json) · [stdout](sol-s3-recheck/before.stdout.txt) · [stderr](sol-s3-recheck/before.stderr.txt) |
| S3 候选 | 6 / 0 | 0 | [JSON](sol-s3-recheck/after.json) · [stdout](sol-s3-recheck/after.stdout.txt) · [stderr](sol-s3-recheck/after.stderr.txt) |
| S3 删新校验 | 1 / 5 | 1 | [JSON](sol-s3-recheck/no-data-validation.json) · [stdout](sol-s3-recheck/no-data-validation.stdout.txt) · [stderr](sol-s3-recheck/no-data-validation.stderr.txt) |
| S1 核心 | 9 / 0 | 0 | [JSON](sol-s3-recheck/s1.json) · [stdout](sol-s3-recheck/s1.stdout.txt) · [stderr](sol-s3-recheck/s1.stderr.txt) |
| S2 异常矩阵 | 24 / 0 | 0 | [JSON](sol-s3-recheck/s2.json) · [stdout](sol-s3-recheck/s2.stdout.txt) · [stderr](sol-s3-recheck/s2.stderr.txt) |
| S1 去掉缓存命中返回 | 3 / 1 | 1 | [JSON](sol-s3-recheck/s1-no-local-return.json) · [stdout](sol-s3-recheck/s1-no-local-return.stdout.txt) · [stderr](sol-s3-recheck/s1-no-local-return.stderr.txt) |
| S1 放行截断 | 7 / 1 | 1 | [JSON](sol-s3-recheck/s1-allow-truncated.json) · [stdout](sol-s3-recheck/s1-allow-truncated.stdout.txt) · [stderr](sol-s3-recheck/s1-allow-truncated.stderr.txt) |
| S2 去掉退役清理 | 1 / 1 | 1 | [JSON](sol-s3-recheck/s2-no-retire-cleanup.json) · [stdout](sol-s3-recheck/s2-no-retire-cleanup.stdout.txt) · [stderr](sol-s3-recheck/s2-no-retire-cleanup.stderr.txt) |
| 源文件检查 | 5 / 0 | 0 | [JSON](sol-s3-recheck/source.json) · [stdout](sol-s3-recheck/source.stdout.txt) · [stderr](sol-s3-recheck/source.stderr.txt) |
| UX | 46 / 0 | 0 | [JSON](sol-s3-recheck-regressions/ux.json) · [stdout](sol-s3-recheck-regressions/ux.stdout.txt) · [stderr](sol-s3-recheck-regressions/ux.stderr.txt) · [量测 JSON](sol-s3-recheck-regressions/ux-measurements/) |
| AICLS | 39 / 1 | 1 | [JSON](sol-s3-recheck-regressions/aicls.json) · [stdout](sol-s3-recheck-regressions/aicls.stdout.txt) · [stderr](sol-s3-recheck-regressions/aicls.stderr.txt) |
| POOLUP | 39 / 1 | 1 | [JSON](sol-s3-recheck-regressions/poolup.json) · [stdout](sol-s3-recheck-regressions/poolup.stdout.txt) · [stderr](sol-s3-recheck-regressions/poolup.stderr.txt) |

| 文件 | SHA-256 |
| --- | --- |
| `index.html` | `33c50bef723b0a3f32b51bc2d5927ff4391bb58eb474996f1a7d9dff96bc1def` |
| S2 `sw.js` 基线 | `f8a4e2bc4d5d81964475580c012e825281f409a171782640ad5cbc68a07bca24` |
| S3 `sw.js` 候选 | `900061dd45ad04e9f9c4391e5d2756f8b080a4bc4144ede9b913b6deabb5aa8b` |
| S3 删校验的临时 worker | `0bee8f9201700624a076cb9b35d9250954130b63a464eec095c6f283e85ab14f` |
| `sw-retire.js` | `5ae38f2ba965f4e1b1d340da2ba5fadd8b58af82a1e271a02ddff97ab5686199` |
| `tests/smooth/verify-s3.mjs` | `585a9f3803238cfb18b80a490948f9e661fd6792dae09838c53d38f98a030ac7` |
| Neon 156 B 样本 | `11e2ff0add51cd0cf4f21b39010925b11df3fe7c0d388906c0c56468a3a16b74` |

## 地图终态

③.4 的 S3 修复与施工证据已交付，建议主控回填待独立复核。地图当前为 ③.4 `rework-in-progress`、④ `completed-with-findings`、⑤ `pending`、⑤.9 `not-authorized`。地图由主控回填。[唯一任务地图](/D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/task-map.md:12)

DELIVERY-T1128-SMOOTH-S3
已交付空标记损坏页的缓存写入修复，以及专项红绿、删校验负对照和既有回归证据。
