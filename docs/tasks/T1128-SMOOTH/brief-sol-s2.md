DELIVERY-T1128-SMOOTH-S2
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar-smooth-T1128；任务号=T1128-SMOOTH-S2；交付=首页缓存完整本机候选、异常/退出/回归证据与施工回执。
轨道位置：胸科雷达顺畅改造·③.4 Sol S2 异常、退出与回归。
R级：R2
判级理由：在已放行首例上补 Service Worker 异常与退役生命周期，仍属架构级变更；仅本机候选，不含生产发布。
签发：PI 原话「算了，现在直接执行吧，不重启了」（2026-11-28）；主控首例复跑 9/9 后于 11:08 放行 S2。
地形：在 S1 的 `index.html`、`sw.js`、`tests/smooth/` 上续作，新增根 `sw-retire.js`；邻接 `ensureRollingData()` 的多日降级、既有 UX/AICLS/POOLUP 差分与默认本地零注册入口。
领域卡：无
经验卡：无卡（与 S1 相同）。
Run 版本键：岗位卡=builder-jobspec 现役正本；轨道版本=T1128-SMOOTH v1；基线版本=`73dd34e`＋已放行 S1。

## 目标与写域
只许改隔离工作树内：`index.html`、`sw.js`、新建 `sw-retire.js`、`tests/smooth/`、`docs/tasks/T1128-SMOOTH/`。其余一切只读。禁改既有测试、验收合同、基线、CI/CD、部署工作流、任务地图和官方数据语义。

## 必做
1. 保留 S1 九项核心行为。`clientId` 使用 `event.resultingClientId || event.clientId`；安装拉到合法新版时可更新健康缓存，不得因已有旧副本而跳过更新；缓存打开/写入失败不得阻断网站。
2. 补真实 Chrome/CDP 异常矩阵：离线、404、500、认证劫持 HTML、截断、缺官方数据起/止标记、错误 Content-Type，均不得覆盖健康缓存；断网仿真若拦不到 SW 请求，用测试服务器实际断开连接，不能把仿真失效误判成产品结果。
3. 低配额写失败保留健康副本；零配额冷启动、禁用 ServiceWorker/CacheStorage 均回退原生网站且无未捕获异常。
4. 新增自毁版 `sw-retire.js`：立即 `skipWaiting`，激活时清 `thoradar-shell-` 前缀缓存并 `unregister()`，通知客户端；测自毁后下一次打开走网络取当前版、重装不复活旧 HTTP 副本。保留 `?sw=0` 单机退出。
5. 多日档案不在本轮新增缓存。`ensureRollingData()` 拉取失败时，在支持的页面和降级页面都持续明示「实际只显示 <实际日期> 当日副本／历史档案不可用」，直到成功或重新选择单日；不能用短暂 toast 代替。不得改变 `PAPERS/mergePapers/inWindow` 语义。
6. 默认本地无 `?sw=1` 时零注册、零缓存，且既有 UX/AICLS/POOLUP 默认测试不应因新增静态 DOM 产生差分。若状态条造成差分，调整实现为受控或降级时按需显示/创建，或移到不参与旧快照的位置；不得修改旧测试、删断言或放宽预期。
7. 手机 390×844 与桌面均能看到数据日期及核新/降级状态；正常更新不刷新阅读；不得引入测试 meta、调试全局、调试消息或无关痕迹。
8. 至少重复核心矩阵两轮，保留每项原始 stdout/stderr、机器 JSON、环境/时间/重复次数/种子（无随机种子则写无）、目标 SHA-256。保留或补充负对照：删除缓存命中返回、允许截断写入、移除自毁清理应分别让对应测试变红；只改测试服务器内存中的响应，不改被审正本。

## 回归
亲自运行并保存原始输出：
- `node tests/ux/ux_probe.mjs --target index.html --base 73dd34e --label sol-s2`
- `node tests/aicls/aicls_regress.mjs --target index.html --baseline 73dd34e --label sols2`
- `node tests/poolup/poolup_regress.mjs --target index.html --baseline 73dd34e --label sols2`
不得修改这些脚本。若出现已知 R08 选词无判别力或其它失败，原样报告，不得用临时副本的全绿替代正式结果。

## 非目标与停止
仍不做 90 天缓存、UX3、CI/CD、iOS/真机/国内直连/线上跨日；不 push、不 deploy、不刷新 CDN。硬预算终点 11:41:06，到时未完成必须标未完，不得删测试赶绿。需要越写域、改旧测试或真实凭证时停手上报。

## 交付
`docs/tasks/T1128-SMOOTH/sol-s2-report.md`、完整测试脚本、原始输出和机器 JSON。报告三行头、「按哪几条干的」「地图影响」「遗留风险」「证据」「地图终态」齐全，列明通过数/失败数及未验项。最终尾部复述 `DELIVERY-T1128-SMOOTH-S2`。
