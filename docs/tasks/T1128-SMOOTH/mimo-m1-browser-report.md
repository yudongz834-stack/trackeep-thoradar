# T1128-SMOOTH-M1 · www.thoradar.online CDN 归属/HTTPS 控制台诊断报告

- **干了什么（人话）**：在 PI 日常 Chrome 里开了自己的 CDN 控制台标签，查清 `www.thoradar.online` **不在当前阿里云账号**（域名列表共 1 个域名、搜 www 为 0 条、DCDN 未开通），并回读到主域证书 `cert-6ycr7` 本身已覆盖 `www`；按任务书第 4 条**零变更**，只出卡点与最小后续处理单。
- **PI 怎么亲手验**：打开 `docs/tasks/T1128-SMOOTH/online-release/mimo-m1/02-search-www-nohit.png`，看到域名搜索 `www.thoradar.online` 的结果行是「没有数据」就算对（或浏览器进 CDN 控制台「域名管理」搜 `www.thoradar.online`，同样 0 条）。
- **还剩什么坑**：`www` 的归属只查到「不在本账号」，它是否配置在别的阿里账号无法从本控制台核实（未验）；根治需要新增域名或跨账号处理，都超出本单授权，等 PI 拍板后另开单。

## 结论（三态归类）

**只查明原因未改**。`www.thoradar.online` 不在当前账号 CDN 域名列表，任务书修复分支（第 3 条）不成立；继续所需的最小动作＝新增加速域名（或跨账号迁移），属第 4 条明令禁止提交的变更，故未做任何配置改动、未执行 CDN 刷新、未触发工作流、未演练退役。

## 控制台事实（本次独立回读，未采信旧报告）

访问路径：PI 日常 Chrome（CDP 直连 `DevToolsActivePort`）自建后台标签，只读。

| 项 | 回读内容 |
|---|---|
| CDN 域名列表 `/domain/list` | 共有 1 个域名：`thoradar.online`｜图片小文件｜CNAME 已配置｜`thoradar.online.w.kunlunaq.com`｜正常运行｜HTTPS 已开启｜源站 `thoradar-online.oss-cn-shenzhen.aliyuncs.com`｜创建 2026-11-20 23:37:56 |
| 搜索 `www.thoradar.online` | 「没有数据」，分页计「共有 0 个域名」 |
| 边缘安全加速（DCDN）域名列表 | 本账号未开通 DCDN（跳转开通/购买页），排除 `www` 挂在 DCDN |
| 主域 HTTPS 配置页 | 证书匹配域名 `thoradar.online,www.thoradar.online`｜品牌 DigiCert Inc｜类型 云盾证书｜证书名 `cert-6ycr7`｜到期 2027-02-17 07:59:59｜协议重定向 HTTP→HTTPS｜TLSv1.0–1.3 均开启｜HSTS 关闭｜HTTP/2 配置区存在 |
| 账号身份 | 已隐去（仅主账号，无 RAM 子用户标识出现在操作路径上） |

- 变更前后状态：**无变更**（全程只读，无 before/after 可对照）。
- 未读取/未输出：账号 ID、AccessKey、证书私钥、无关域名（列表仅 1 行且为本案主域）。
- Sol 的 RAM 标签（`48EFF9133344B0869DF5A6CE6D213FE5`）与 PI 原有标签全程未操作，收尾只关自建标签。

## 公开验证（带退出码，2026-11-28 本单实跑）

`curl -sS -I -o /dev/null -w "%{http_code}" --max-time 20/25`（Windows schannel）：

| URL | http | exit | 判读 |
|---|---|---|---|
| `https://www.thoradar.online/` | 000 | 35 | TLS 握手失败（SEC_E_ILLEGAL_MESSAGE） |
| `https://www.thoradar.online/index.html` | 000 | 35 | 同上 |
| `https://www.thoradar.online/sw.js` | 000 | 35 | 同上 |
| `https://www.thoradar.online/sw-retire.js` | 000 | 35 | 同上 |
| `https://thoradar.online/` | 200 | 0 | 通过 |
| `https://thoradar.online/index.html` | 200 | 0 | 通过 |
| `https://thoradar.online/sw.js` | 200 | 0 | 通过（首跑 1 次 exit=28 超时，随即重跑 3 次全 200，判偶发，未复现为持续故障） |
| `https://thoradar.online/sw-retire.js` | 200 | 0 | 通过 |

公共 DNS（DoH `dns.alidns.com`，独立于本机代理假 IP）：

- `www.thoradar.online` CNAME → `thoradar.online.w.kunlunaq.com.`（TTL 600）
- `thoradar.online` CNAME → `thoradar.online.w.kunlunaq.com.`（TTL 600）

## 机制推断（标「我猜」）

我猜：`www` 的 DNS 指向**主域的** CDN CNAME，而 `www` 自己没有在任何已查位置（本账号 CDN、DCDN）配置成加速域名，边缘节点按 SNI=`www.thoradar.online` 找不到对应证书 → TLS 握手失败。依据三条：① DoH 显示两域共用同一 CNAME；② 域名列表/搜索均无 `www`；③ 主域证书匹配域名里含 `www`（证书本身覆盖，缺的是域名配置）。与 run `46129122449` 刷新 API 报 `InvalidDomain.NotFound` 也一致。**未经跨账号核实，不写成事实**。

## 最小后续处理单（供 PI 拍板，本单未执行任何一项）

1. **候选 A（证书现成，动 DNS）**：在本账号 CDN「添加域名」`www.thoradar.online`——业务类型/源站对齐主域（图片小文件，回源 `thoradar-online.oss-cn-shenzhen.aliyuncs.com`）；HTTPS 证书直接选已有 `cert-6ycr7`（匹配域名已含 `www`，**不需要**申请/购买证书、不需要私钥）；添加后把 `www` 的 CNAME 改成控制台给出的 `www` 专用 CNAME（当前错配到主域 CNAME 是嫌疑点）。涉及新增域名（可能计费/备案核验）＋ DNS 变更，均需 PI 拍板，另开施工单。
2. **候选 B（若 `www` 实在另一账号）**：先做账号归属核对（现象与刷新 API `InvalidDomain.NotFound` 吻合），由 PI 决定迁移或在该账号修复；迁移不在本单授权。
3. **双域自动刷新恢复**：待 `www` 归属落定后再改工作流（本单不动工作流、测试、真实发布）。

## 地图影响 / 地图终态

- **地图影响**：无。不改产品、工作流、测试、任务地图。
- **地图终态**：`docs/tasks/T1128-SMOOTH/task-map.md`、`RELEASE-REPORT.md` 等工作树既有改动系本单开工前已存在，本单未审未动；本单新增件仅本报告与 `online-release/mimo-m1/` 三张截图（`01-domain-list.png`／`02-search-www-nohit.png`／`03-https-cert.png`，已裁掉含账号名的顶栏）。

## 验证状态

- 已验：控制台归属（列表总数＋搜索 0 条＋DCDN 未开通）、主域证书匹配域名、公网四 URL TLS/HEAD（带退出码）、公共 DNS CNAME（DoH）、截图三张落盘。
- 未验（明标）：`www` 是否存在于其他阿里账号（跨账号不可见）；新增 `www` 域名的计费/备案影响（未做）；主域 `sw.js` 首跑超时的根因（重跑 3 次未复现，判偶发，未深挖）。

## 改动清单

- 配置/生产：**零改动**（未提交任何 CDN 变更、未刷新、未触发工作流/部署）。
- 文件：新增 `docs/tasks/T1128-SMOOTH/mimo-m1-browser-report.md`、`docs/tasks/T1128-SMOOTH/online-release/mimo-m1/*.png` 3 张；临时驱动 `D:/claude-tmp/mimo-m1-cdp.mjs`（会话后按惯例留置，不入库）。
- 浏览器：自建 CDN 标签 1 个（用毕已关）。

## 遗留风险

1. `www` 四 URL 公网 TLS 仍失败（本单只查明原因未改）——双域验真继续被阻断，直到 PI 在候选 A/B 里拍板。
2. 证书 `cert-6ycr7` 到期 2027-02-17（证书面板标注有效期 2 months，续期机制未查，属另一单）。
3. 若 `www` 在别的账号还有配置，两账号并存的归属冲突需 PI 定夺，本单不下结论。

---

DELIVERY-T1128-SMOOTH-M1
本单只查明原因未改：`www.thoradar.online` 不在当前阿里云账号 CDN 域名列表（搜索 0 条、DCDN 未开通），主域证书 `cert-6ycr7` 已覆盖 `www`，公网 `www` 四 URL TLS 握手失败（exit 35）现状已回读留证，零配置变更，最小后续处理单随报告交付。
