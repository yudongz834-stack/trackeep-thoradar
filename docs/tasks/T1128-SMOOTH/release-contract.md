# T1128-SMOOTH C2 发布验收合同

签发：PI 在知悉「核心修复完成、线上交付未完成」后原话「继续做」（2026-11-28）。本合同覆盖发布接线、CI 验证闸、正常/退役部署与线上验收准备；实际 push、deploy、CDN 刷新和退役演练唯 PI 当次亲手。

**基底更新（主控实测）**：`git fetch` 发现远端由 `73dd34e` 前进到 `28131f314f92a05227fd5923607d717c426da2c5`，为 2026-11-28 日报 16 文件更新。主仓已用 stash→新分支→stash pop 保留本地候选并同步该远端基底；当前首页含 `briefing_date=2026-11-28`、43 篇，SHA-256=`27ba018a9a3b4936ec734820af8cb505262bd55f41ae382047615f0a58d7c706`。C1 首页哈希仅用于 Sol S5 的「不得改产品」检查，不得再把旧首页当作最终发布内容。最新基底上 S3 9/9、S1 9/9、S2 24/24、UX 46/46 已复跑通过（`release-sync-check/`）。CI 的源码检查必须兼容正常日报数据变化，不得继续机械要求与旧 `73dd34e` 数据逐字一致。

## 不变量
1. 发布接线不得改缓存程序：worker `e882e9e2...394f`、退役版 `5ae38f2b...6199` 保持不变。Sol S5 的输入首页为 C1 哈希 `33c50bef...1def`；最终发布首页必须采用上述最新日报与缓存改动合并版 `27ba018a...c706`，不得回退到旧 40 篇。
2. 不改 `SITE_DATA/PAPERS/mergePapers/inWindow`，不新增 90 天缓存，不改其它对象现有缓存策略。
3. OSS 首页保持 `max-age=60, s-maxage=3600` 并最后上传。两域的 `/sw.js` 与 `/sw-retire.js` 公网响应均须 `200`、JavaScript MIME、`Cache-Control: no-store`，直接验证响应，禁止跟随跳转。
4. `thoradar.online` 为唯一正式域（PI 2026-11-28 G18 签发）。主域根路径、`/index.html` 和两件 worker 发布后均须返回 `200`，以 `Content-MD5` 对照发布提交 `HEAD:<path>` 的原始 Git blob 字节。读取 blob 或计算摘要失败即判红。主域根路径与 `/index.html` 的响应 MIME 必须为 `text/html`。主域 `/sw.js` 在正常模式对应 `sw.js`，退役模式对应 `sw-retire.js`，正常部署可恢复。主域 `/sw-retire.js` 始终对应 `sw-retire.js`。
5. CDN 仅刷新 `https://thoradar.online` 的 `/`、`/index.html`、`/sw.js`、`/sw-retire.js`。刷新失败或无 `RefreshTaskId` 判红。公网验真最多 12 次，先等两次 5 秒，再每次等 40 秒，第 12 次累计等待 370 秒。
   - `www.thoradar.online` 的 `/`、`/index.html` 和 `/?from=www` 必须返回 `301` 或 `308`，`Location` 必须精确指向 `https://thoradar.online` 的同路径、同查询。跳转按状态和 `Location` 验收。
   - `www` 的 `/sw.js` 与 `/sw-retire.js` 在正常、退役两种发布模式中均须匹配发布提交 `HEAD:sw-retire.js` 的 `Content-MD5`，用于旧客户端退出旧缓存。发布时无需刷新 `www`，两条 worker 例外与普通路径永久跳转由 M3 的 CDN 配置提供。
   - 双域源站预检仅检查 SNI 与根路径 `200`。`Publish verified on both domains` 表示主域四个对象与 `www` 三个跳转、两个退役入口均通过公网验真。
6. CI 必须先跑发布静态检查、源码不变量、S1/S2/S3 与 UX，再允许部署；不拿已知 R08 失真测试充数。
7. 任何真实凭证不得打印、传输到测试或提交；静态/模拟测试只用假命令和假应答。

## 独立复核与发布边界
- Sol 只在隔离树改 `.github/workflows/deploy_oss.yml`、`tests/smooth/`、`docs/tasks/T1128-SMOOTH/`。
- Astra 新会话独立复核，亲自跑静态/模拟测试、至少一项撤防负对照与核心回归，不执行真实部署。
- 线上首访/复访/后台更新/离线/单页退出在 PI 发布后由主控用隔离浏览器实测；桌面模拟不得冒充真机/iOS。
- 退役演练会改变公开网站行为，必须另由 PI 当次亲手触发，不在正常发布中自动演练。
