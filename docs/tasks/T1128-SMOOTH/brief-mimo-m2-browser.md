DELIVERY-T1128-SMOOTH-M2
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar；任务号=T1128-SMOOTH-M2；交付=在当前账号接入 `www.thoradar.online`、复用现有证书与主域回源、必要时精准修正 www CNAME，并完成公开回读。
轨道位置：胸科雷达顺畅改造·⑧ 真实发布 CDN/www 接入。
R级：R3（生产 CDN/DNS 配置变更；仅限本单精确白名单，不做 Git 发布）。
判级理由：M1 已由控制台和主控原图确认 www 未接入当前 CDN，四 URL TLS 握手失败；主域证书覆盖 www。要完成既定双域上线，需要新增 www 加速配置并可能修正其 CNAME。
签发：沿用 PI 已确认的 G14/G15：原话「你帮我做」「全部运行allow，不要我一直瘦点」「要不操作浏览器你让codex gpt 6.2 sol还有mimo 2.6 pro做？」及既定任务「若未接入，添加加速域名并恢复公网 TLS」。本单是该已授权 www 接入目标的续作，不冒称 PI 对购买、套餐、证书私钥或跨账号迁移作了新授权。
地形：只在 PI 日常 Chrome 自行新建 CDN/DNS 控制台标签；不得操作 Sol 的 RAM 标签 `48EFF9133344B0869DF5A6CE6D213FE5` 或 PI 原有标签。报告只写 `docs/tasks/T1128-SMOOTH/mimo-m2-browser-report.md` 与 `online-release/mimo-m2/`；临时脚本只用 `D:/claude-tmp/mimo-m2-*`。不改产品、工作流、测试、任务地图，不 commit/push/deploy。
领域卡：无
经验卡：无卡。
Run 版本键：岗位卡=builder-jobspec 现役正本；model=mimo-v2.6-pro[1m]；M1 报告=`mimo-m1-browser-report.md`；主控已逐张复核 M1 三张截图，确认主域一条、www 搜索零条、证书 SAN 含 www。

## 精确变更白名单
1. 当前账号 CDN 新增唯一域名 `www.thoradar.online`；业务类型和回源与主域一致：图片小文件，源站 `thoradar-online.oss-cn-shenzhen.aliyuncs.com`。优先使用主域的「复制配置」减少手工差异，但必须逐项回读，不带入主域专用刷新、访问控制或其它无关设置。
2. HTTPS 只复用已有证书 `cert-6ycr7`（控制台证书匹配域名为主域和 www），不得申请/购买证书、上传或读取私钥。HTTP→HTTPS、HTTP/2 与主域一致；不开 QUIC、OCSP 等额外可选项，除非它们原本随主域且为同等接入所必需并单独记录。
3. 这是既有后付费 CDN 上的一条 www 接入，可能按实际流量/HTTPS 请求产生与主域同类的使用量费用；不得购买资源包、套餐、DCDN、证书或任何预付费产品，不改计费方式。若控制台要求新付费/开通服务才能继续，停止报告。
4. 添加后读取控制台分配给 www 的 CNAME。若它与当前 `thoradar.online.w.kunlunaq.com.` 不同，且 `thoradar.online` 的 DNS 在当前阿里云账号可直接管理，只允许修改记录主机名恰好为 `www` 的那一条 CNAME：先保存旧值、TTL、记录类型和截图，再改为控制台分配值；不得改主域、MX、TXT、NS 或任何其它记录。若 DNS 不在当前账号、存在多个无法区分的 www 记录或需跨账号，停止在 DNS 前并报告准确待改值。
5. 不新增/删除其它域名，不修改主域配置，不执行 CDN 刷新，不触发 GitHub Actions，不演练退役。

## 执行与回退
1. 先读 M1 报告和 webaccess SKILL/CONFIG；按无视觉模型处理，只用 DOM 文本和可机读状态，不 Read 截图，截图只存证。直接 CDP 使用 `DevToolsActivePort`，结束只关自建标签。
2. 每个提交前回读：动作只影响 www、源站与证书符合白名单、没有购买项、没有主域或其它 DNS 记录被勾选。页面报「域名已存在/其他账号/备案不通过/需购买/需私钥」任一情况即停，不强行绕过。
3. 保存每一步前后状态和错误原文；报告和截图裁掉/隐去账号 ID、用户名、主体、联系方式与无关资源，不复制凭证。
4. 若新增 CDN 成功而 DNS 变更失败，不得假称完成；报告现有 CDN 配置、旧 DNS 值和应改新值。若新增后公开结果更坏且能安全回退，只停用/删除本单新建的 www 配置前先报告实际状态，不碰主域；不得为回退擅自删其它资源。
5. 配置生效需要传播，按实际状态合理轮询，不用一次失败判死。最终公开验证 `https://www.thoradar.online/`、`/index.html`、`/sw.js`、`/sw-retire.js`：TLS 成功、HTTP 200、MD5 分别与主域对应对象一致，worker JavaScript MIME 和 `no-store` 正确。另验证主域四 URL 未退化。记录退出码与响应头，不读正文中的个人数据。

## 验收与交付
- 终态必须明确三态之一：A 双域公开回读通过；B CDN 已接入但 DNS/传播未完成；C 在某一步停止且说明未提交或已提交的精确状态。
- 只有 www 四 URL TLS+200+MD5/MIME/no-store 全过且主域未退化，才可写「www 接入完成」。不把控制台「正常运行」单独当公网验收。
- 报告含三行头、结论、地图影响、验证状态、改动清单、遗留风险、地图终态；附回滚所需的旧 www CNAME/TTL（若有变更）和实际新值，隐去个人与账号信息。尾部复述 `DELIVERY-T1128-SMOOTH-M2`。
