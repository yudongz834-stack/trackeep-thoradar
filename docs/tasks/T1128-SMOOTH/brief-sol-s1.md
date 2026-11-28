DELIVERY-T1128-SMOOTH-S1
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar-smooth-T1128；任务号=T1128-SMOOTH-S1；交付=首例可运行代码、原始测试输出与施工回执。
轨道位置：胸科雷达顺畅改造·③.2 Sol S1 首例。
R级：R2
判级理由：新增 Service Worker 生命周期并改变首页导航读取路径，属于架构级变更；本单仅本机候选，不含生产发布。
签发：PI 原话「算了，现在直接执行吧，不重启了」（2026-11-28）；组合原话「我想让codex gpt 6.2 sol全程施工，agy gemini 4 neon协助和验证，你做最后检查。先定这个施工组合」。
地形：动 `index.html` 尾部注册胶水、新增根 `sw.js` 与 `tests/smooth/`；入口为 `/` 和 `/index.html`，邻接官方内嵌 `SITE_DATA`、AI/NCBI 请求和现有本地回归；同仓原型不在正式树，参考件仅在 `D:/trackeep/trackeep-workbench/smooth-prototype/`。
领域卡：无
经验卡：所属正式仓无 `.trackeep/experience.md`，如实记「无卡」。
Run 版本键：岗位卡=builder-jobspec（按现役正本）；轨道版本=T1128-SMOOTH v1；基线版本=trackeep-thoradar `73dd34e`。

## 本单目标
在隔离工作树完成最小但真实的首例：首页第二次打开由本地副本先出屏，后台核对新版；当前阅读不自动刷新，提示「有新版，下次打开生效」；下一次导航使用新版。首次访问仍走原生网络。

## 写域白名单（其余一切只读）
- `D:/trackeep/trackeep-product/trackeep-thoradar-smooth-T1128/index.html`
- `D:/trackeep/trackeep-product/trackeep-thoradar-smooth-T1128/sw.js`（新建）
- `D:/trackeep/trackeep-product/trackeep-thoradar-smooth-T1128/tests/smooth/`（新建施工自测与证据）
- `D:/trackeep/trackeep-product/trackeep-thoradar-smooth-T1128/docs/tasks/T1128-SMOOTH/`（新建本单证据与回执）

禁改：现有 `tests/ux/`、`tests/aicls/`、`tests/poolup/`、验收基线、`.github/`、部署工作流、复核配置、官方 `SITE_DATA/PAPERS/mergePapers/inWindow` 语义、个人 `localStorage` 键名。不得把 workbench 文件当正式送达物；可参考其逻辑，但正式代码必须在上述工作树内形成并实测。

## 必须守住
1. 保留单文件 `index.html` 和内嵌 `SITE_DATA`，不建第二份官方数据真相。
2. SW 只处理同源 GET、`request.mode==='navigate'`、`/` 与 `/index.html`；AI、NCBI、POST、跨域、个性化 API 和其它路径全部原生放行。
3. 生产默认只在 HTTPS 且主机为 `thoradar.online` 或其子域时注册；本机默认零注册，仅显式 `?sw=1` 开启专属测试；`?sw=0` 注销本 origin 的 SW 并清 `thoradar-shell-` 前缀缓存。
4. 缓存命中立即返回；后台以实际入口 URL、`cache:'reload'` 核新，规范缓存键统一为 `/index.html`。安装也用 `reload`，不得复活更旧 HTTP 副本。
5. 正常更新不 `skipWaiting`、不 `clients.claim`、不自动 `location.reload()`。页面监听器安装后主动查询状态，避免更新消息丢失。
6. 写缓存前校验 `response.ok`、`type==='basic'`、Content-Type 含 `text/html`、官方数据起止标记和完整 `</html>`。任何异常不得覆盖健康缓存。
7. 桌面和手机均能看到实际数据日期与核新状态；不得把旧副本标成最新。不得留下测试 meta、`window.__swMessages`、调试消息或其它半成品痕迹。
8. 现有个人 `localStorage` 不改名、不迁移；不打印、不传输、不提交任何钥匙；测试只用假钥匙。

## 非目标
本单不做 90 天档案缓存、不修改 `radar_latest.json` 流程、不做 UX3 合并、不做 iOS/真机/国内直连/线上跨日验收、不做 CI/CD 修改，不 push、不 deploy、不刷新 CDN。

## 首例完成判据
用完整正式页面和真实 Chrome/CDP，从本地测试服务器实跑并保留原始输出：
- 默认 `/index.html` 无 `?sw=1`：注册数 0、缓存键 0，页面正常。
- 显式 `?sw=1`：安装后第二次导航命中本地副本；模拟 1500ms 慢网与 v2，当前仍显示 v1 且出现「有新版，下次打开生效」，内存标记不变、未自动刷新；第三次导航显示 v2。
- AI POST 与跨域请求不被 SW 拦截；至少一个异常 HTML 不覆盖健康缓存。
- 测试结果含来源、开始/结束时间、基线 commit、操作系统/浏览器版本、重复次数、目标文件 SHA-256；失败如实保留。

## 预算与停止条件
总役硬预算为 2026-11-28 11:41:06；本首例是基础放行点，不得为赶时间删测试或退出机制。
出现以下任一情况立即停手上报：需要改验收基线/既有测试/CI；需要真实钥匙或登录态；需要对外网络发布；写域不足；同一核心用例连续 2 次失败且根因未明；发现会改官方数据语义的需求。
本单只完成首例即停，主控核首例后再发 S2，不自行扩做完整异常矩阵。

## 回滚与交付
只改隔离工作树；主控可移除该工作树，不影响主仓。不得用 `git checkout` 恢复文件；如需还原用动手前 `cp` 备份。
交付到 `docs/tasks/T1128-SMOOTH/`: `sol-s1-report.md`、测试脚本、机器 JSON、原始 stdout/stderr。回执开头三行依次为：干了什么／PI 怎么亲手验／还剩什么坑。另含「按哪几条干的」「地图影响」「遗留风险」「证据」「地图终态」；地图终态引用 `D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/task-map.md`，不得改任务地图。
最终输出尾部复述 `DELIVERY-T1128-SMOOTH-S1`。
