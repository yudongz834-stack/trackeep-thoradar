**干了什么**　补齐了胸科雷达首页副本的异常保护、退役退出和多日档案降级。读取中保留当前页面，核到的新版在下次打开时生效。\
**PI 怎么亲手验**　打开第 2 轮 stdout，找到 `PASS archive-warning-persists-with-controlled-shell-on-mobile`。看 390×844 的 `persistent` 里仍有「实际只显示 2026-11-27 当日副本／历史档案不可用」，且 `recovered` 的提示已隐藏。[第 2 轮原始输出](sol-s2-matrix-02.stdout.txt)\
**还剩什么坑**　AICLS 与 POOLUP 各有一项 R08 在基线和候选两边都搜到 0 篇，检索步骤仍未获得可判定证据。本机候选待 Neon 新会话复核，线上与真机未验。

## 按哪几条干的

- 执行 T1128-SMOOTH-S2 委任状和验收合同 v1。轨道位置为胸科雷达顺畅改造 ③.4，R2，理由是新增 Service Worker 异常与退役生命周期。签发为 PI 2026-11-28 原话「算了，现在直接执行吧，不重启了」，主控首例 9/9 后于 11:08 放行。施工席为 codex·GPT-6.2·Sol，岗位卡为现役 builder-jobspec，轨道版本为 T1128-SMOOTH v1，基线为 `73dd34e65fce6661d74e595afc03df68e7d3f44f` 加已放行 S1。领域卡无，经验无卡。
- 按委任状和 `safety-redlines` v6.1，在指定隔离工作树施工。Chrome 使用独立临时配置，S2 各场景关闭各自隔离上下文。测试服务监听回环地址，AI POST 与跨域请求经过本地模拟。原有 UX、AICLS、POOLUP 和 S1 测试脚本沿用原件。

## 地图影响

- [sw.js](../../../sw.js) 以 `event.resultingClientId || event.clientId` 关联页面，安装和后台核新共用写入校验。只有 HTTP 200、basic、HTML MIME 正确、官方标记依序出现且 HTML 完整收尾的响应可以写入。核新及安装使用 `cache: 'no-store'`，请求跳过 HTTP 缓存且不向其写回。缓存打不开时走网络，写入失败时保留健康内容。
- [sw-retire.js](../../../sw-retire.js) 立即 `skipWaiting()`，激活后清理 `thoradar-shell-` 缓存、注销并通知打开的页面。测试服务器在已注册的 `/sw.js` URL 返回退役脚本，以复现浏览器更新已有注册。触发退役后，原阅读页和选中条目保持，下一次普通打开由源站返回 v2。重装前用 `force-cache` 实际读到了旧 HTTP 副本，重装仍向源站拉取 v2 并写入 Cache Storage。`?sw=0` 保留单机注销和前缀清理。
- [index.html](../../../index.html) 在启用缓存、退出或持有本站 worker 时显示日期和状态。默认本机状态节点留在顶栏以外并隐藏，零注册、零缓存。历史档案请求失败后，顶栏保留实际日期和降级提示，覆盖 1440×900 桌面与 390×844 手机视口。提示在切到阅读视图后仍可见，重新选单日或成功拉取档案时收起。源文件检查确认官方 `SITE_DATA`、`PAPERS` 初始化及 `mergePapers/inWindow` 文本与基线一致，比较统一了行尾。档案请求保持原网络路径。[源文件检查 JSON](sol-s2-source.json)

## 遗留风险

- AICLS 和 POOLUP 正式结果均为 39 通过、1 失败、0 跳过。R08 两套脚本都选中 `Mortality`，基线与候选均为 `list: 0, noQuery: 1`，原脚本判场景失真。该步骤尚未形成有效检索差分。UX 正式结果为 46 通过、0 失败。
- Chrome 的 CDP 字面 `quotaSize: 0` 试跑仍可写，因此正式矩阵使用 1 字节总上限复现零可写空间。冷启动后 CDP 报告总上限 1 字节，已有注册占 3,908 字节，Cache Storage 占 0 字节，尝试写入 1 字节获原生 `QuotaExceededError`。API 不可用和拒绝访问用 CDP 文档注入及本地 worker 响应模拟，覆盖网页与 worker 的降级分支。[字面零试跑](sol-s2-matrix-pilot2.json) [正式配额证据](sol-s2-matrix-01.json) [CDP 配额接口](https://chromedevtools.github.io/devtools-protocol/tot/Storage/#method-overrideQuotaForOrigin)
- 本机试验验证了 worker 核新不会把普通首页写入浏览器 HTTP 缓存。若普通导航此前已经被服务器的长 TTL 缓存，退役后走的是浏览器原生 HTTP 缓存策略。线上缓存头、CDN 收敛、线上跨日、国内直连、iOS、真机、多标签完整生命周期、常规 worker 升级激活全过程、90 天离线档案、UX3 和生产发布均未验。安装阶段更新健康缓存已验。验收合同记载的主仓架构地图漂移待主控整合阶段处理。

## 证据

Windows 11 Pro x64 `10.0.26300`，Node `v24.14.0`，Chrome `158.0.8127.88`，CDP `1.3`，种子无。核心和异常矩阵各独立重复两轮，开始、结束时刻和来源逐轮记录在 JSON。S1 脚本自带的随机文档标识仅用于判断是否换页，未用于生成输入或选择用例。CDP 离线时 worker 请求仍抵达回环服务器，两轮均由测试服务器实际断开 socket。另有独立用例在 CDP 联网时复测物理断开。两轮均保留健康副本的完整 SHA-256，且无未捕获页面或 worker 异常。

```powershell
pwsh -NoProfile -File docs/tasks/T1128-SMOOTH/run-sol-s2.ps1 -Suite s1 -RunId core-final-01
pwsh -NoProfile -File docs/tasks/T1128-SMOOTH/run-sol-s2.ps1 -Suite s1 -RunId core-final-02
pwsh -NoProfile -File docs/tasks/T1128-SMOOTH/run-sol-s2.ps1 -RunId matrix-01
pwsh -NoProfile -File docs/tasks/T1128-SMOOTH/run-sol-s2.ps1 -RunId matrix-02
pwsh -NoProfile -File docs/tasks/T1128-SMOOTH/run-sol-s2.ps1 -Suite s1 -RunId mutation-local-return -Mutation no-local-return
pwsh -NoProfile -File docs/tasks/T1128-SMOOTH/run-sol-s2.ps1 -Suite s1 -RunId mutation-truncated -Mutation allow-truncated
pwsh -NoProfile -File docs/tasks/T1128-SMOOTH/run-sol-s2.ps1 -RunId mutation-retire -Mutation no-retire-cleanup
node tests/smooth/verify-source.mjs docs/tasks/T1128-SMOOTH/sol-s2-source.json
node tests/smooth/run-regressions.mjs sol-s2-legacy-evidence
```

| 本机候选 | 原始结果 | 证据 |
| --- | --- | --- |
| S1 核心第 1 轮 | 9 通过，0 失败 | [JSON](sol-s2-core-final-01.json) · [stdout](sol-s2-core-final-01.stdout.txt) · [stderr](sol-s2-core-final-01.stderr.txt) |
| S1 核心第 2 轮 | 9 通过，0 失败 | [JSON](sol-s2-core-final-02.json) · [stdout](sol-s2-core-final-02.stdout.txt) · [stderr](sol-s2-core-final-02.stderr.txt) |
| S2 矩阵第 1 轮 | 24 通过，0 失败 | [JSON](sol-s2-matrix-01.json) · [stdout](sol-s2-matrix-01.stdout.txt) · [stderr](sol-s2-matrix-01.stderr.txt) |
| S2 矩阵第 2 轮 | 24 通过，0 失败 | [JSON](sol-s2-matrix-02.json) · [stdout](sol-s2-matrix-02.stdout.txt) · [stderr](sol-s2-matrix-02.stderr.txt) |
| 源文件、写域和语法 | 5 通过，0 失败 | [JSON](sol-s2-source.json) · [stdout](sol-s2-source.stdout.txt) · [stderr](sol-s2-source.stderr.txt) |

负对照只改回环测试服务器内存中的响应。去掉缓存命中返回，提前出屏用例变红。允许截断写入，健康副本保护用例变红。去掉自毁清理，前缀缓存仍在，退役用例变红。三次都返回 1。

| 负对照 | 原始结果 | 证据 |
| --- | --- | --- |
| 去掉缓存命中返回 | 3 通过，1 预期失败 | [JSON](sol-s2-mutation-local-return.json) · [stdout](sol-s2-mutation-local-return.stdout.txt) · [stderr](sol-s2-mutation-local-return.stderr.txt) |
| 允许截断写入 | 7 通过，1 预期失败 | [JSON](sol-s2-mutation-truncated.json) · [stdout](sol-s2-mutation-truncated.stdout.txt) · [stderr](sol-s2-mutation-truncated.stderr.txt) |
| 去掉自毁清理 | 1 通过，1 预期失败 | [JSON](sol-s2-mutation-retire.json) · [stdout](sol-s2-mutation-retire.stdout.txt) · [stderr](sol-s2-mutation-retire.stderr.txt) |

既有回归的封装只设置各套临时目录并捕获输出，实际执行如下命令。UX 原生量测 JSON 在 [ux-measurements](sol-s2-legacy-evidence/ux-measurements/)。

```powershell
node tests/ux/ux_probe.mjs --target index.html --base 73dd34e --label sol-s2
node tests/aicls/aicls_regress.mjs --target index.html --baseline 73dd34e --label sols2
node tests/poolup/poolup_regress.mjs --target index.html --baseline 73dd34e --label sols2
```

| 既有回归 | 原始结果 | 证据 |
| --- | --- | --- |
| UX | 46 通过，0 失败，退出 0 | [JSON](sol-s2-legacy-evidence/ux.json) · [stdout](sol-s2-legacy-evidence/ux.stdout.txt) · [stderr](sol-s2-legacy-evidence/ux.stderr.txt) |
| AICLS | 39 通过，1 失败，退出 1 | [JSON](sol-s2-legacy-evidence/aicls.json) · [stdout](sol-s2-legacy-evidence/aicls.stdout.txt) · [stderr](sol-s2-legacy-evidence/aicls.stderr.txt) |
| POOLUP | 39 通过，1 失败，退出 1 | [JSON](sol-s2-legacy-evidence/poolup.json) · [stdout](sol-s2-legacy-evidence/poolup.stdout.txt) · [stderr](sol-s2-legacy-evidence/poolup.stderr.txt) |

| 目标文件 | SHA-256 |
| --- | --- |
| `index.html` | `33c50bef723b0a3f32b51bc2d5927ff4391bb58eb474996f1a7d9dff96bc1def` |
| `sw.js` | `f8a4e2bc4d5d81964475580c012e825281f409a171782640ad5cbc68a07bca24` |
| `sw-retire.js` | `5ae38f2ba965f4e1b1d340da2ba5fadd8b58af82a1e271a02ddff97ab5686199` |
| `tests/smooth/verify-s1.mjs` | `6c93edebe199b9d502e72d42b729bc2dc96ee313307b6341fd5fa92f85c84dc4` |
| `tests/smooth/verify-s2.mjs` | `9266fc7518314073d3694d809cca0e7c6e057daa2c7fcb80bdb0d2a7d460ea48` |

## 地图终态

③.4 的施工候选和证据已落在指定隔离工作树。地图仍显示 ③.4 `in-progress`、④ Neon 独立复核和 ⑤ 主控整合 `pending`、⑤.9 发布 `not-authorized`，由派遣方回填。正式回归所留 R08 红项随候选提交复核。[唯一任务地图](/D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/task-map.md)
