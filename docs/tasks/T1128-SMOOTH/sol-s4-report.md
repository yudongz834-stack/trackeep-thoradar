**干了什么**　胸科雷达拒绝把空日期、无效日历日期和 HTML 注释里的伪 `SITE_DATA` 写进首页缓存。两个 Neon 样本之后重新打开，仍读到健康版的 40 篇。合法零篇版仍能更新。  
**PI 怎么亲手验**　打开[专项原始输出](sol-s4/after.stdout.txt)，搜索 `PASS comment-wrapped-site-data-stub`，看到 `before` 和 `after` 均为 539012 字节、SHA-256 相同，且 `nextPage.papers` 为 40。  
**还剩什么坑**　本机施工验证已过，主控仍需安排 Neon 新会话复验。旧 Neon 脚本里的源码变异锚点需要随候选更新，两项旧变异还需要能单独触发原保护的样本。

## 地图影响

T1128-SMOOTH-S4 对应③.4 的 R2 返修。施工在指定隔离工作树完成。`sw.js` 的缓存写入校验要求数据标记位于同一真实内联脚本内，正式页面生成的数据块仍位于脚本开头。日期须通过 `YYYY-MM-DD` 格式与 UTC 日历往返校验。安装预取和后台核新共用这两项检查。施工测试在原六项上追加两个 Neon 样本和 `2026-02-29`。候选 `index.html` SHA-256 为 `33c50bef723b0a3f32b51bc2d5927ff4391bb58eb474996f1a7d9dff96bc1def`，与开工前一致。[worker 差异](sol-s4/worker.diff.txt) [候选专项 JSON](sol-s4/after.json)

S3 基线接受了两个 Neon 样本，分别拿 374669 B 和 184 B 替换 539012 B 的健康副本。S4 对两个样本都记录 `unavailable`，缓存前后字节数和 SHA-256 相同，下次从 Cache Storage 读取 `2026-11-27` 的 40 篇。非法闰日结果相同。合法零篇版写入后，下次从 Cache Storage 读到 `2026-11-28` 的 0 篇。[基线 JSON](sol-s4/before.json) [候选专项 JSON](sol-s4/after.json)

## 遗留风险

- S4 的新上下文保护也能拦住旧 Neon 试卷中用于倒置标记和空数据块的样本。本机重放中，三个旧变异仍被拒绝，其中两项在 S3 曾使样本进入缓存。S4 各自撤掉日期和脚本上下文校验后，专项对应样本均实际覆盖了健康缓存。[Neon V2 重放原始输出](sol-s4/neon-v2.stdout.txt) [日期负对照](sol-s4/no-date-guard.json) [脚本上下文负对照](sol-s4/no-script-guard.json)
- 验证使用本机 Chrome 隔离配置和回环测试服务。线上、CDN 和真机未验。映射到候选工作树的 Neon V2 本机重放使用适配器，仅在内存更新一处依赖 S3 源码的变异锚点。两个探针均报 `preserved=true`，12 项正式检查均过。独立签收仍由主控安排。[重放适配器](sol-s4/replay-neon-v2.mjs) [Neon V2 重放 JSON](sol-s4/neon-v2.json)

## 证据

Windows 11 Pro x64 `10.0.26300`、Node `v24.14.0`、Chrome `158.0.8127.88`。基线和候选专项、负对照均使用同一施工脚本，跑次各 1，无随机种子。开工实测基线与委任状哈希一致。候选 SHA-256 为 `e882e9e2eef0bf36781b8b03ecec23eb81221fa8b33272cdc9de3e368f76394f`。逐一复查测试进程记录中的 PID，健在 Chrome 数为 0。[哈希原始输出](sol-s4/hashes.stdout.txt) [PID 复查原始输出](sol-s4/process-recheck.stdout.txt)

```powershell
$e = 'docs/tasks/T1128-SMOOTH/sol-s4'
node tests/smooth/verify-s3.mjs "$e/before.json" "$e/s3-baseline.sw.js"
node tests/smooth/verify-s3.mjs "$e/after.json"
node tests/smooth/verify-s3.mjs "$e/no-date-guard.json" "$e/no-date-guard.sw.js"
node tests/smooth/verify-s3.mjs "$e/no-script-guard.json" "$e/no-script-guard.sw.js"
node tests/smooth/verify-s1.mjs "$e/s1.json" none
node tests/smooth/verify-s2.mjs "$e/s2.json" none
node tests/ux/ux_probe.mjs --target index.html --base 73dd34e --label sol-s4
node "$e/replay-neon-v2.mjs" "$e/neon-v2.json"
```

| 验证 | 通过 / 失败 | 退出码 | 原始证据 |
| --- | --- | ---: | --- |
| S3 基线，扩展专项 | 6 / 3，两个 Neon 样本和非法闰日变红 | 1 | [stdout](sol-s4/before.stdout.txt) · [stderr](sol-s4/before.stderr.txt) · [JSON](sol-s4/before.json) |
| S4 候选，扩展专项 | 9 / 0，包含 S3 原六项 | 0 | [stdout](sol-s4/after.stdout.txt) · [stderr](sol-s4/after.stderr.txt) · [JSON](sol-s4/after.json) |
| 撤回日期校验到原字符串检查 | 7 / 2，空日期和非法闰日变红 | 1 | [stdout](sol-s4/no-date-guard.stdout.txt) · [stderr](sol-s4/no-date-guard.stderr.txt) · [JSON](sol-s4/no-date-guard.json) |
| 删除脚本上下文校验 | 8 / 1，注释包装样本变红 | 1 | [stdout](sol-s4/no-script-guard.stdout.txt) · [stderr](sol-s4/no-script-guard.stderr.txt) · [JSON](sol-s4/no-script-guard.json) |
| S1 | 9 / 0 | 0 | [stdout](sol-s4/s1.stdout.txt) · [stderr](sol-s4/s1.stderr.txt) · [JSON](sol-s4/s1.json) |
| S2 | 24 / 0 | 0 | [stdout](sol-s4/s2.stdout.txt) · [stderr](sol-s4/s2.stderr.txt) · [JSON](sol-s4/s2.json) |
| UX | 46 / 0 | 0 | [stdout](sol-s4/ux.stdout.txt) · [stderr](sol-s4/ux.stderr.txt) · [运行记录](sol-s4/ux.run.json) · [量测 JSON](sol-s4/ux-measurements/) |
| Neon V2 本机重放 | 正式 12 / 0，两探针均保留缓存 | 0 | [stdout](sol-s4/neon-v2.stdout.txt) · [stderr](sol-s4/neon-v2.stderr.txt) · [JSON](sol-s4/neon-v2.json) |

## 地图终态

③.4 的 S4 候选与施工证据已交付，待独立复验。实读主控地图显示③.4 `in-progress-s4`，④ Neon V2 `completed-with-findings`，⑤ `blocked-on-s4`，⑤.9 `not-authorized`。地图由派单方回填。[唯一任务地图](/D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/task-map.md)

DELIVERY-T1128-SMOOTH-S4
已交付两处首页缓存校验修复及基线复现、负对照和回归证据。
