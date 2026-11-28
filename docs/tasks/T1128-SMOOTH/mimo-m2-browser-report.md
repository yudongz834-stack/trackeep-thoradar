# T1128-SMOOTH-M2 · www.thoradar.online CDN/www 接入（真实发布）

- **干了什么（人话）**：在 PI 日常 Chrome 自建后台标签里，把 `www.thoradar.online` 加进了当前账号的 CDN（图片小文件、回源 OSS 与主域同源），复用已有证书 `cert-6ycr7` 开好 HTTPS＋HTTP→HTTPS＋HTTP/2，用主域「复制配置」补齐缓存与过滤参数，再把 DNS 里主机名恰好 `www` 的那一条 CNAME 从主域 CNAME 改成 www 专用 CNAME；公网 `www` 四 URL 已 TLS＋200＋MD5 与主域逐一对上，主域未退化。
- **PI 怎么亲手验**：浏览器地址栏进 `https://www.thoradar.online/`，看到胸科雷达页面正常打开（证书锁形为 DigiCert、签发给 thoradar.online/www.thoradar.online）就算对；再开 `docs/tasks/T1128-SMOOTH/online-release/mimo-m2/07-domain-list-final.png`，看到域名列表两行（www 与主域）都是「正常运行｜HTTPS 已开启」也算对。
- **还剩什么坑**：证书 `cert-6ycr7` 2027-02-17 到期（续期机制属另一单）；公网抽测 HTTP 版本为 1.1（两域一致，HTTP/2 控制台已开但本机 curl 未协商 h2，未实测 ALPN——标「未验」）；`www` 是否在其它阿里账号还有残留配置跨账号不可见（未验）。

## 结论（三态归类）

**A 态：双域公开回读通过。** `www` 四 URL TLS 成功＋HTTP 200＋MD5 与主域对应对象一致＋worker JavaScript MIME 与 `no-store` 正确，主域四 URL 未退化，HTTP→HTTPS 两域同为 301。控制台侧 www「已配置／正常运行／HTTPS 已开启」，仅作为辅助证据，不单独当验收。

## 控制台变更事实（每步回读，2026-11-28 本单实做）

访问路径：PI 日常 Chrome（CDP 直连 `DevToolsActivePort`）自建后台标签，用毕已关（只关自建，Sol RAM 标签与 PI 原有标签全程未动）。

| 步骤 | 动作 | 提交前回读／提交后落库证据 |
|---|---|---|
| ① 新增加速域名 | `www.thoradar.online`｜加速区域 仅中国内地（与主域一致）｜业务类型 图片小文件｜源站 OSS `thoradar-online.oss-cn-shenzhen.aliyuncs.com`（主/权重 10/端口 80，与主域逐格一致） | 添加成功页＋域名列表出现第 2 行；无「域名已存在／其他账号／备案不通过／需购买／需私钥」任何停止条件 |
| ② HTTPS | 证书来源=数字证书管理服务，复用已有 `cert-6ycr7`（匹配域名 `thoradar.online,www.thoradar.online`，DigiCert，到期 2027-02-17）；未申请/购买/上传证书，未触碰私钥 | 强刷 HTTPS 页回读：HTTPS证书 已开启＋证书名 cert-6ycr7（推荐配置页曾显示「已开启」但没落库，以详情页回读为准补做） |
| ③ 协议/可选项 | 协议重定向=HTTP -> HTTPS；HTTP/2=开；OCSP Stapling=关；HSTS=关；TLSv1.0–1.3 全开；QUIC=关（未动） | 逐项强刷回读，与主域同页对照一致；QUIC 页单查开关为关 |
| ④ 复制配置（主域→www） | 先 6 项批量复制报错 `[https] is not supported`（InvalidArgName.ValueNotSupported，整批未落、无部分生效）；改为只复制「缓存过期时间＋过滤参数」两项成功 | www 缓存规则回读=`/ 目录 1个月 优先遵循源站=开启 权重99`，与主域同格；性能优化页「忽略参数」两域同显（保留指定参数/是/保留回源参数=是） |
| ⑤ 回源 | 未改（新域按 OSS 源站自动生成默认回源HOST=源站域名 `thoradar-online.oss-cn-shenzhen.aliyuncs.com`，与主域显式配置同值） | www 回源配置页回读与主域逐项一致；指定源站回源HOST 两边均空 |
| ⑥ Gzip | 手动开启（第一批复制失败被减掉的项）；中途一次误点开「HTML优化」，当即关回 | 强刷性能优化页：HTML/CSS/JS/图像处理=关、Gzip=开、Brotli=关，与主域开关表逐位相同 |
| ⑦ DNS | 只改主机名恰好 `www` 的一条 CNAME（见下方回滚栏）；`@`、两条 TXT、NS/MX 等 4 条记录里其余 3 条零变动 | 变更确认框明细=「修改记录 1 条：www CNAME …改为…」；改后记录表回读＋更新时间 2026-11-28 19:03:58 |

- 无任何购买／套餐／资源包／DCDN／证书采购操作；HTTPS 请求数按既有后付费计费口径自然计量（白名单第 3 条已预告），未改计费方式。
- 未执行 CDN 刷新、未触发 GitHub Actions、未演练退役、未改主域任何配置、未新增/删除其它域名。
- 报告与截图已隐去账号 ID、用户名、主体、联系方式；两条 TXT 记录值不在本报告复制。

## 公开验证（带退出码与响应头，2026-11-28 18:59 生效后 19:04–19:10 实跑）

`curl -sS -I --max-time 25`（Windows schannel）＋正文 `md5sum`：

| URL | TLS exit | http | Content-Type | Cache-Control | body MD5 | 与主域一致 |
|---|---|---|---|---|---|---|
| `https://www.thoradar.online/` | 0 | 200 | text/html | public, max-age=60, s-maxage=3600 | f349a082…25c5 | YES |
| `https://www.thoradar.online/index.html` | 0 | 200 | text/html | public, max-age=60, s-maxage=3600 | f349a082…25c5 | YES |
| `https://www.thoradar.online/sw.js` | 0 | 200 | application/javascript | **no-store** | 9eb80a6d…2c22 | YES |
| `https://www.thoradar.online/sw-retire.js` | 0 | 200 | application/javascript | **no-store** | c6f88738…aeb8 | YES |
| `https://thoradar.online/`（4 URL） | 0×4 | 200×4 | 同上对应 | 同上对应 | 同上 4 值 | 基准，未退化 |

- HTTP→HTTPS：`http://www.thoradar.online/` → 301 `Location: https://www.thoradar.online/`；主域同款 301（exit 0）。
- 完整响应头另存 `online-release/mimo-m2/apex-www-sw-headers.txt`（两域 sw.js 均带 `Cache-Control: no-store`＋`Content-MD5` 一致）；全程日志 `baseline-m2.txt`／`verify-public.txt`／`final-verify.txt`。
- 公共 DNS（DoH dns.alidns.com）：`www.thoradar.online` CNAME → `www.thoradar.online.w.kunlunaq.com.`（TTL 600，新值已生效）；`thoradar.online` → `thoradar.online.w.kunlunaq.com.`（未动）。
- 基线对照（改前 18:23）：www 四 URL 全 TLS 失败 exit=35；主域四 URL 200（`index.html` 首跑 1 次 exit=28 超时，3/3 复跑全 200，判偶发未复现）。

## 地图影响 / 地图终态

- **地图影响**：无。不改产品、工作流、测试、任务地图，未 commit/push/deploy。
- **地图终态**：`docs/tasks/T1128-SMOOTH/task-map.md`、`RELEASE-REPORT.md` 等工作树既有改动系开工前已存在，本单未审未动；本单新增件仅本报告与 `online-release/mimo-m2/` 证据目录。

## 验证状态

- **已验**：新增域名表单逐项（区域/类型/源站）、HTTPS 证书名与到期（详情页强刷回读）、协议重定向/HTTP2/OCSP/HTLS/QUIC 逐开关、缓存规则与忽略参数两域对照、回源 HOST 两域对照、DNS 四条记录改前改后全量回读（仅 www 一条变化）、公网 8 组 URL 的 TLS/状态码/响应头/MD5、HTTP→HTTPS 301、DoH 新 CNAME、截图 7 张落盘。
- **未验（明标）**：公网 ALPN/HTTP2 实际协商（本机 curl 两域均回 1.1，无差异但未见 h2）；`www` 在其它阿里账号是否有残留配置（跨账号不可见）；证书 2027-02-17 到期的续期机制（另一单）；HTTPS 请求数计费出账首日数额（按后付费口径待账单体现）。

## 改动清单

- 生产配置：CDN 新增 1 个加速域名 `www.thoradar.online`（含 HTTPS/重定向/HTTP2/缓存/过滤参数/Gzip 如上表）；DNS 修改 1 条记录（www CNAME）。主域、其它域名、其它 DNS 记录、工作流、测试零改动。
- 文件：新增 `docs/tasks/T1128-SMOOTH/mimo-m2-browser-report.md`、`online-release/mimo-m2/`（截图 7 张＋`baseline-m2.txt`／`verify-public.txt`／`final-verify.txt`／`apex-www-sw-headers.txt`）；临时驱动 `D:/claude-tmp/mimo-m2-cdp.mjs`（含可信点击/键入扩展，会话后按惯例留置，不入库）。
- 浏览器：自建后台标签 2 个（施工 1 个、QUIC 复查 1 个），用毕均已关。

## 回滚所需旧值（回滚动作用）

| 项 | 旧值（改前） | 新值（现值） |
|---|---|---|
| DNS 记录 | 主机记录 `www`｜类型 CNAME｜线路 默认｜记录值 **`thoradar.online.w.kunlunaq.com`**｜TTL **10 分钟（600 秒）**｜权重 1｜启用 | 记录值 **`www.thoradar.online.w.kunlunaq.com`**（TTL/类型/权重/状态未动） |

- DNS 回滚＝把上表记录值改回旧值即可（改前截图 `05-dns-records-before.png`、改后 `06-dns-records-after.png`）。
- 若需整体回退 www：CDN 域名列表停用/删除本单新建的 `www.thoradar.online` 即可（白名单允许范围）；主域任何配置本单未动，无需回滚。

## 遗留风险

1. 证书 `cert-6ycr7` 到期 2027-02-17，两域共用；续期机制未查（另一单）。
2. www 接入后按实际流量/HTTPS 请求数产生与主域同类的后付费用量费用（白名单第 3 条预告口径）；未买资源包抵扣（白名单禁止）。
3. 若其它阿里账号还留有 `www` 旧配置，跨账号归属冲突仍不可见（M1 遗留同款，未复现为故障）。
4. 复制配置对含 https 属性的项批量报错 `[https] is not supported`（阿里控制台缺陷/限制），本单以手动对齐绕过；后续批量复制同类项会再踩（已留证）。

---

DELIVERY-T1128-SMOOTH-M2
本单把 `www.thoradar.online` 接入当前账号 CDN 并复用 `cert-6ycr7` 开好 HTTPS/HTTP2/HTTP→HTTPS、用主域复制配置对齐缓存与过滤参数、精准把 www 一条 CNAME 改到 `www.thoradar.online.w.kunlunaq.com`，公网 www 四 URL TLS+200+MD5/MIME/no-store 与主域逐一对上且主域未退化，DNS 旧值已留档可回滚。
