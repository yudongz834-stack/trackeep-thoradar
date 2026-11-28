**干了什么**　胸科雷达首页首次联网打开，安装后从本地副本先出屏。后台发现新版时保留当前阅读，下次导航使用新版。\
**PI 怎么亲手验**　打开候选第 1 轮的 stdout，定位 `PASS background-update-keeps-document-and-reading-state`，看页面日期仍为 `2026-11-27`、提示「有新版，下次打开生效」、`view` 仍为 `reading`，缓存日期已是 `2026-11-28`。[候选第 1 轮 stdout](sol-s1-candidate-01.stdout.txt)\
**还剩什么坑**　首例候选已通过本机施工自测，等待主控放行及后续独立复核。线上跨日、国内直连、iOS 和真机仍未验。

## 按哪几条干的

- 执行 T1128-SMOOTH-S1 委任状和任务书。轨道位置为胸科雷达顺畅改造 ③.2，R2，签发为 PI 2026-11-28 原话「算了，现在直接执行吧，不重启了」。施工席为 codex·GPT-6.2·Sol，岗位册 `jobspecs` v1.7 第一章施工席。轨道版本为 `T1128-SMOOTH v1`，基线为 `73dd34e65fce6661d74e595afc03df68e7d3f44f`。领域卡无，经验无卡。
- 按 `safety-redlines` v6.1 和本单红线，用临时 Chrome 配置和独立 CDP 上下文，HTTP 服务绑定回环地址，AI POST 和跨域请求都发往本地模拟端点。五轮浏览器进程正常退出，临时配置均已移除。
- 首页导航只使用一个规范缓存键 `/index.html`。安装和后台核新用 `cache: 'reload'`，后台请求保留实际入口；写入前校验响应状态、类型、HTML MIME、顺序正确的官方标记和 `</html>`。页面先监听再主动查询当前导航的核新状态。

## 地图影响

- 正式改动在 [index.html](../../../index.html) 和 [sw.js](../../../sw.js)。首页只新增顶栏状态、样式和尾部胶水。基线对比确认官方内嵌 `SITE_DATA` 区块相同，首页原代码仅增加 78 行。既有应用逻辑和个人 `localStorage` 键保持原样。[源文件检查原始 stdout](sol-s1-source-check.stdout.txt)
- Chromium 证据中，默认本机首页注册数和 Cache Storage 缓存名均为 0。启用后第二次导航报告 `cache-storage`，v1 的首次内容绘制分别为 76、68、92 ms，当时延迟 1500 ms 的新版响应仍未结束。收到 v2 后，页面保持原数据日期、文档标记和阅读视图，第三次从 `/` 导航读到 v2。390 × 844 的手机模拟视口中状态和日期均完整可见。
- AI POST 和跨域 GET 到达各自模拟服务器，CDP 均报告 `fromServiceWorker: false`。缺少 `</html>` 的 HTTP 200 响应保留了健康 v2。`?sw=0` 在回环地址注销了同源注册、清除了雷达前缀缓存并保留了其他缓存，下一次普通打开走原生网络。

## 遗留风险

- 本机显式开启限 `localhost`、`127.0.0.1` 和 `[::1]`。首页仅接管无查询参数的导航和单独的 `?sw=1`，其他查询参数组合走原生路径。`?sw=0` 执行一次注销与清理，生产域随后再次访问符合条件的首页时会按默认策略注册。
- 首例异常样本为带官方标记但缺少结尾的 HTML。完整异常矩阵、生命周期长时测试、既有回归套件和新版生产发布由后续阶段处理。施工测试用完整正式页面，v2 仅在本地 HTTP 响应中替换两处顶层日期，截断样本再删 `</html>`。

## 证据

入口 [PowerShell 复跑脚本](run-sol-s1.ps1)，浏览器驱动 [verify-s1.mjs](../../../tests/smooth/verify-s1.mjs)。在隔离工作树根目录运行。`RunId` 用来保存各轮独立的 JSON、stdout 和 stderr。

```powershell
pwsh -NoProfile -File docs/tasks/T1128-SMOOTH/run-sol-s1.ps1 -RunId candidate-01
pwsh -NoProfile -File docs/tasks/T1128-SMOOTH/run-sol-s1.ps1 -RunId candidate-02
pwsh -NoProfile -File docs/tasks/T1128-SMOOTH/run-sol-s1.ps1 -RunId candidate-03
pwsh -NoProfile -File docs/tasks/T1128-SMOOTH/run-sol-s1.ps1 -RunId negative-local-return -Mutation no-local-return
pwsh -NoProfile -File docs/tasks/T1128-SMOOTH/run-sol-s1.ps1 -RunId negative-truncated -Mutation allow-truncated
git diff --check
node --check sw.js
node --check tests/smooth/verify-s1.mjs
```

同一候选独立重复三轮，每轮 9 项通过。两轮负对照只在 HTTP 服务器内存中删对应代码。删除缓存命中返回后，Chrome 响应来源为 `http-cache`，本地副本用例变红。删除结尾校验后，截断页覆盖了 v2，保护用例变红。两轮各仅对应项失败，均返回 1。

| 测试轮次 | 原始结果 | 机器 JSON | stdout | stderr |
| --- | --- | --- | --- | --- |
| 候选 1 | 9 通过，0 失败 | [JSON](sol-s1-candidate-01.json) | [stdout](sol-s1-candidate-01.stdout.txt) | [stderr](sol-s1-candidate-01.stderr.txt) |
| 候选 2 | 9 通过，0 失败 | [JSON](sol-s1-candidate-02.json) | [stdout](sol-s1-candidate-02.stdout.txt) | [stderr](sol-s1-candidate-02.stderr.txt) |
| 候选 3 | 9 通过，0 失败 | [JSON](sol-s1-candidate-03.json) | [stdout](sol-s1-candidate-03.stdout.txt) | [stderr](sol-s1-candidate-03.stderr.txt) |
| 删除本地返回 | 3 通过，1 预期失败 | [JSON](sol-s1-negative-local-return.json) | [stdout](sol-s1-negative-local-return.stdout.txt) | [stderr](sol-s1-negative-local-return.stderr.txt) |
| 删除结尾校验 | 7 通过，1 预期失败 | [JSON](sol-s1-negative-truncated.json) | [stdout](sol-s1-negative-truncated.stdout.txt) | [stderr](sol-s1-negative-truncated.stderr.txt) |

```text
SUMMARY {"passed":9,"failed":0,"endedAt":"2026-11-28T03:01:36.778Z"}
SUMMARY {"passed":9,"failed":0,"endedAt":"2026-11-28T03:02:37.458Z"}
SUMMARY {"passed":9,"failed":0,"endedAt":"2026-11-28T03:02:52.075Z"}
SUMMARY {"passed":3,"failed":1,"endedAt":"2026-11-28T03:03:03.850Z"}
SUMMARY {"passed":7,"failed":1,"endedAt":"2026-11-28T03:03:17.037Z"}
```

实测窗口为北京时间 2026-11-28 11:01:30.599 至 11:03:17.037。运行环境为 Windows 11 Pro x64 `10.0.26300`、Chrome `158.0.8127.88`、CDP `1.3`、Node `v24.14.0`。逐轮开始和结束时刻、服务器和 CDP 原始数据、各测试文件 SHA-256 均记录在 JSON。

| 目标文件 | SHA-256 |
| --- | --- |
| `index.html` | `923eca1f843037339b73d440587b075b59b3cc1a7f6867571c49f6cd608bfd6f` |
| `sw.js` | `6d783246bcaba218ccaf98a2de8d450094b7949c970954f48b11ebcdb29ec898` |
| `tests/smooth/verify-s1.mjs` | `6c93edebe199b9d502e72d42b729bc2dc96ee313307b6341fd5fa92f85c84dc4` |

## 地图终态

任务地图读取结果为 ③.2 `ready`，③.3 主控放行 `pending`，③.4 S2 和 ④ V1 独立复核 `pending`。S1 候选及证据已落在委任状指定的隔离目录，交由派遣方复核和回填。地图仍由派遣方维护。[唯一任务地图](/D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/task-map.md)
