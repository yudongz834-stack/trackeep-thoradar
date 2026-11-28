# T1128-SMOOTH-M3 · www 永久跳转短域＋两件 worker 退役入口（生产 CDN 配置）

- **干了什么（人话）**：在 PI 日常 Chrome 自建后台标签里，给 `www.thoradar.online` 配了两笔：①回源路径改写把 `/sw.js` 换成 OSS 上的退役件 `sw-retire.js`（老访客的 Service Worker 能退场）；②EdgeScript 规则把其余所有 www 路径 301 到 `https://thoradar.online` 同路径同查询（`?sw=0` 这类查询不丢）。公网逐条回读全过：新访客直接被跳到主域，老访客还能从 www 拿到退役 worker；主域四地址一字未动。
- **PI 怎么亲手验**：浏览器地址栏输入 `https://www.thoradar.online/index.html?sw=0` 回车，看到地址栏自动变成 `https://thoradar.online/index.html?sw=0`（查询串还在）且胸科雷达页面正常打开，就算对。
- **还剩什么坑**：没有阻断坑，已逐条核；剩三件明标未验——公网只从本机一个接入点实测（配置全局下发但未多地复测）、308 未用（本单用 301，契约允许二选一）、两张存盘截图按无视觉纪律未读图复核（顶栏账号区已裁掉）。另证书 `cert-6ycr7` 2027-02-17 到期仍是 M2 遗留、续期属另一单。

## 结论（三态归类）

**A 态：全部公开契约通过。** 详见下方终验表；控制台「已配置/启用」仅作辅助证据，未单独当验收。

## 目标线上契约对照（公开回读，2026-11-28 20:46–20:49 实跑）

| 契约 | 实测 | 判 |
|---|---|---|
| www `/` → 301/308 到主域同路径同查询 | `HTTP/1.1 301 Moved Permanently`，`Location: https://thoradar.online/` | ✅ |
| www `/index.html` 同上 | `301`，`Location: https://thoradar.online/index.html` | ✅ |
| www 带查询样本 | `https://www.thoradar.online/?sw=0` → `301`，`Location: https://thoradar.online/?sw=0`；`/some/path?x=1` → `301`，`Location: https://thoradar.online/some/path?x=1` | ✅ 查询未丢、未跳其它主机 |
| www `/sw.js` 例外：200、JS、no-store、退役 MD5 | `200`｜`application/javascript`｜`Cache-Control: no-store`｜body MD5 `xviHOEexQQLp0q41sv2uuA==`（hex `c6f88738…aeb8`，832 字节）｜`Content-MD5` 同值 | ✅ 非 3xx，直接给正文 |
| www `/sw-retire.js` 同上 | 同上四值逐项相同 | ✅ |
| （附加）www `/sw.js?x=1` | 200＋退役 MD5（例外按路径匹配，带查询同样给退役件） | ✅ 计划外加分项 |
| 主域 `/`、`/index.html` 不变 | 200＋`text/html`，body MD5 `f349a0827cba4634573fd530e33825c5`（与改前基线同值） | ✅ |
| 主域 `/sw.js` 仍为正常 worker | 200＋no-store，body MD5 `nrgKbeazqBXvILkgAlssIg==`（hex `9eb80a6d…2c22`，5846 字节，与任务书 Run 版本键一致） | ✅ |
| 主域 `/sw-retire.js` 为退役件 | 200＋no-store＋`xviHOEexQQLp0q41sv2uuA==` | ✅ |

- 每次请求的退出码、状态行、响应头逐条记在 `online-release/mimo-m3/final-verify.txt`；其中 3 件首跑撞上本机偶发网络失败（curl 28 超时 / schannel 35 握手败，M2 同款已判偶发），已单列 `final-verify-retry.txt` 复跑取证：www `/index.html` 301 Location 精确、主域 `/` 200、主域 `/sw.js` body MD5 `nrgK…` 全部复现成功。
- 未执行 CDN 刷新，配置自然传播：回源改写 20:21 前后落库、20:23:13 公网已见退役件；ES 规则约 20:42 发布、20:44:07 首见 301、20:45:20 确认稳定。

## 控制台变更事实（2026-11-28 本单实做）

访问路径：PI 日常 Chrome（CDP 直连）自建后台标签，用毕已关；PI 原有标签（RAM×2、thoradar.online、本地台）全程未动。

| 步骤 | 动作 | 落库证据 |
|---|---|---|
| ① worker 例外 | www 域名 → 回源配置 → 重写回源路径，新增规则：待重写的Path `^/sw[.]js$`（PCRE）→ 目标Path `/sw-retire.js`，执行规则=空 | 规则表回读该行，状态由「配置中」转生效；`console-after-backsrc-rewrite.txt/.png`；公网 20:23:13 起 www `/sw.js` 正文=退役件 |
| ② 301 跳转 | www 域名 → EdgeScript自定义策略，新增规则 `www_to_apex_redirect`（优先级 0、开关 启用、执行位置 请求处理开始、Break 关），经模拟环境发布后「发布所有规则到生产环境」 | 生产环境规则表回读该行（查看/删除）；`console-after-esprod.txt/.png`；公网 301 生效 |

EdgeScript 规则代码全文（3 行）：

```
if and(ne($uri, '/sw.js'), ne($uri, '/sw-retire.js')) {
    rewrite(concat('https://thoradar.online', $uri), 'redirect', 301)
}
```

- 语法依据：控制台「HTTPS重定向」模板＋官方文档（`rewrite(url, flag, code)`，flag=redirect 时 code 可自定义 301/302/303/307/308；`concat()` 拼 URI；`and/ne` 组合条件）；查询保留行为以公网两例实测为准（`?sw=0`、`?x=1` 均原样带到 Location）。
- 未改主域任何配置；未动 DNS、证书、源站、缓存规则、过滤参数、计费；未购买任何资源/套餐；未执行 CDN 刷新；未 commit/push/deploy。
- 两张存盘截图（`console-after-*.png`）裁掉顶栏账号区；证据 txt 已把账号名替换为 `[账号]`。

## 地图影响 / 地图终态

- **地图影响**：无。不改产品、代码、测试、工作流、任务地图。
- **地图终态**：`docs/tasks/T1128-SMOOTH/task-map.md`、`RELEASE-REPORT.md` 等工作树既有改动系开工前已存在，本单未审未动；本单新增件仅本报告与 `online-release/mimo-m3/` 证据目录。临时驱动 `D:/claude-tmp/mimo-m3-cdp.mjs` 等按惯例留置临时区，不入库。

## 验证状态

- **已验**：上表 10 组契约逐条公网回读（状态码/Location/Content-Type/Cache-Control/Content-MD5/正文 MD5/退出码）；`/sw.js?x=1` 加分项；改前基线（`baseline-public.txt`，两域 10 URL 头＋8 URL 正文 MD5）与改后对比，主域四地址零漂移；本地 `sw-retire.js` MD5 与任务书 Run 版本键对账一致；控制台两侧规则表落库回读。
- **未验（明标）**：① 多地域/多节点一致性——本机仅一个接入点实测，配置为全局下发但未多地复测；② 308 状态码（本单用 301，契约允许 301/308 之一）；③ 截图内容按无视觉纪律未读图复核（仅机读 DOM 证据为准）；④ staging.myalicdn.com 模拟环境实测（需 hosts 绑定，按「不得伪造公网结果/不动本机配置」纪律跳过，直接生产发布后公网验证）；⑤ EdgeScript 每域 2 条额度的余量表现（现用 1 条）；⑥ 公网 ALPN/h2（M2 遗留未验，沿标）。

## 改动清单

- 生产配置（仅 `www.thoradar.online`）：① 回源配置·重写回源路径 +1 条（`^/sw[.]js$` → `/sw-retire.js`）；② EdgeScript自定义策略·生产环境 +1 条（`www_to_apex_redirect`，代码见上）。
- 文件：新增本报告与 `online-release/mimo-m3/`（`baseline-public.txt`、`verify-worker-exceptions.txt`、`poll-redirect.txt`、`final-verify.txt`、`final-verify-retry.txt`、`console-before-backsrc.txt`、`console-after-backsrc-rewrite.txt/.png`、`console-after-esprod.txt/.png`）。
- 浏览器：自建后台标签 2 个（第 1 个施工中被外部关闭，第 2 个用毕自关），PI 原有标签零接触。

## 可回滚的原配置（回滚动作用）

| 项 | 原配置（改前） | 现值 | 回滚动作 |
|---|---|---|---|
| 回源路径改写（www） | 无任何规则（空表） | 1 条：`^/sw[.]js$` → `/sw-retire.js` | 该行「删除」即回原状 |
| EdgeScript 规则（www） | 模拟/生产皆空（额度 2 条未占用） | 生产 1 条：`www_to_apex_redirect`（优先级 0、启用、请求处理开始） | 生产环境该行「开关」关掉可止血；「删除」即回原状 |

- 主域、DNS、证书、源站、缓存、计费本单零改动，无需回滚。
- 两笔都删后线上行为回到 M2 状态（www 双域同源同内容）。

## 遗留风险

1. 旧 www Service Worker 访客的退场依赖客户端更新机制：入口已保住（www `/sw.js` 长期给退役件，no-store 不缓存），清掉旧副本后下次访问即被 301；但长期不回访的浏览器何时更新属客户端行为，本单只保入口、不控客户端。
2. ES 规则排除清单只含 `/sw.js`、`/sw-retire.js` 两路径；将来 www 若要新增例外路径（如健康检查），须「复制规则到模拟环境」改代码后重发生产（生产环境不可直接改内容）。
3. ES 文档对 flag=redirect 的查询保留语义表述含糊（原文「仅改写 URI，不改参数」）；本单以公网两例实证查询原样保留，若阿里改版需复验。
4. 本机 curl 偶发超时/TLS 握手失败（网络抖动，M2 同款）：取证一律复跑至成功，单次失败不作数。
5. 证书 `cert-6ycr7` 2027-02-17 到期（M2 遗留），续期机制属另一单；www 与主域共用此证。
6. EdgeScript 属 CDN 自带功能（额度每域 2 条），本单未产生购买/新计费项；HTTPS 请求数仍按 M2 既有后付费口径自然计量。

---

DELIVERY-T1128-SMOOTH-M3
本单在 www.thoradar.online 上用回源路径改写保住 `/sw.js`／`/sw-retire.js` 两条退役 worker 入口（公网回读＝退役 MD5＋JS＋no-store），并用 EdgeScript 把其余所有路径 301 到 `https://thoradar.online` 同路径同查询（`?sw=0` 实测未丢），主域四地址未退化，两笔配置均可一键回滚。
