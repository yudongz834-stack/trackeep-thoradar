# T1128-SMOOTH C2 发布候选报告

**干了什么**　在最新 2026-11-28、43 篇日报上完成本地副本加速、主域唯一正式地址、`www` 永久跳转和旧客户端退出迁移。PI 已亲手提交并推送 `2c43373aec098375edb9500b2b12e02cb12f2b06`，触发工作流 `46148918001`；真实 OSS 上传、主域 CDN 刷新和发布后验证均成功。

**最终线上验收**　工作流 `smooth-verify` 与 `deploy-oss` 均成功，真实刷新任务号 `33911284451`，日志末行 `Publish verified on both domains`。主控独立公网检查 10/10：主域 4 地址 MD5/MIME 正确，www 4 个普通路径样本 301 到短域同路径同查询，www 两 worker 为退役版且 JS/no-store。隔离 Chrome 复跑 9/9：冷首访原生打开并预热、复访 Cache Storage、后台核新不重载阅读页、离线当日副本、单页 `?sw=0` 退出及无未捕获异常均通过。

**还剩什么坑**　真机/iOS、真实跨日和完整主域退役演练未做。公网仍有间歇连接超时：最终浏览器初跑 8/1 的根地址 HEAD 失败已保留，完整复跑 9/9；不冒称各地网络永远稳定。发布日志保留一次“桶创建 403 后跳过并继续使用现有桶”的记录，实际上传、刷新与验真均成功。F2/F3、R08 与派遣闸旧自检的既有遗留不因本轮消失。

## 地图影响

⑥ 发布接线与日报验收闸已整合并随 `2c43373` 发布。⑦ Astra V4 完成旧候选复核；G18 改向后 Astra A5 完成唯一独立复核，S13 按原样本关闭三项。⑧ M3 生产跳转、旧客户端迁移、真实工作流、主域刷新和最终线上复核均已完成；本任务进入已发布状态。

## 验证状态

| 范围 | 主控实测 | 原始证据 |
|---|---|---|
| 发布静态检查与正常／退役模拟 | 18 PASS / 0 FAIL | `release-candidate-check/deploy.stdout.txt`、`deploy.json` |
| S3 异常缓存 | 9 PASS / 0 FAIL | `release-candidate-check/s3.stdout.txt`、`s3.json` |
| S1 本地先开与后台更新 | 9 PASS / 0 FAIL | `release-candidate-check/s1.stdout.txt`、`s1.json` |
| S2 异常、退出与不拦截边界 | 24 PASS / 0 FAIL | `release-candidate-check/s2.stdout.txt`、`s2.json` |
| 最新 43 篇首页完整 UX | 46 PASS / 0 FAIL，F8a–F8d 均执行 | `release-candidate-check/ux.stdout.txt`、`ux.stderr.txt` |
| Astra V4 独立复核 | 发布模拟 18/18、S3 9/9、S1 9/9、S2 24/24、43 篇 UX 46/46；删 MD5 与错退役映射均判红。发现 B1：合法 2 篇日报被 UX 强制要求第 13 篇等条件阻断 | `astra-v4/report.md`、`astra-v4/evidence/` |
| B1 少篇日报修复 | 原 2 篇样本完整 UX 46/46；43 篇完整 UX 46/46；故意只显示 2 篇中的 1 篇时 F9a 判红；发布模拟 18/18 | `release-candidate-check/b1-fix/small.stdout.txt`、`full43.stdout.txt`、`small-negative.stdout.txt`、`deploy.stdout.txt` |
| 当前线上双域浏览器验收（改向前） | 18 PASS / 0 FAIL：双域 8 个 HEAD 的 MD5/MIME/no-store，加每域冷首访原生打开并预热、复访 Cache Storage、后台核新不重载阅读页、离线当日副本、单页 `?sw=0` 退出与无未捕获异常 | `online-release/online-verify-current-v4.json`、`online-verify-current-v4.stdout.txt`、`online-verify-current.mjs` |
| G18 单域最终发布模拟与源码检查 | 32 PASS / 0 FAIL；源码 5/5。A5 的 CRLF/Git blob、错主机和首页 MIME 原样本均关闭；八组撤防均判红 | `online-release/main-s13-deploy.json`、`main-s13-source.json`、`sol-s13-a5-repair-report.md`、`astra-v5/report.md` |
| M3 生产跳转与独立公网复核 | www 根/index/带查询/任意路径均 301 到短域同路径同查询；www 两 worker 为退役 MD5、JS/no-store；主域四地址未退化。主控初跑 9/10，唯一连接超时，补跑取得正确 301 | `mimo-m3-canonical-report.md`、`online-release/canonical-public-current.json`、`canonical-public-current-retry.txt` |
| 最终真实发布 | PI 推送 `2c43373` 并触发 run `46148918001`；smooth-verify、deploy-oss 成功，主域刷新任务 `33911284451`，主域四地址、www 三跳转和两退役入口均在 runner 验真，末行 `Publish verified on both domains` | `online-release/deploy-46148918001.json`、`deploy-46148918001.log` |
| 最终独立公网复核 | 10 PASS / 0 FAIL：主域四地址 MD5/MIME/no-store，www 四跳转样本与两退役入口；`/index.html` 第一次网络失败后第二次成功，尝试次数保留 | `online-release/canonical-public-final.json`、`verify-canonical-public-final.mjs` |
| 最终主域浏览器验收 | 初跑 8/1，仅根地址 HEAD 三次连接超时，五项实际浏览器行为全过；完整复跑 9/9。冷首访、复访本地先开、后台核新不重载、离线、单页退出、无异常全过；浏览器和 profile 已清理 | `online-release/canonical-browser-final.json`、`canonical-browser-final-retry.json`、`online-verify-current.mjs` |
| 真实旧 www 客户端迁移 | 旧缓存打开→worker 注销、壳缓存清空、个人标记保留→下次到短域同查询且 43 篇。原始探针 3/1，缺记 redirectResponse；与独立 301 联合裁定 4/0，原红保留 | `online-release/www-legacy-migration-v3.json`、`www-legacy-migration-review.json`、`adjudicate-www-legacy.mjs` |
| 日报发布复演 | 26 个命令均符合预期；合法日报通过，旧数据基线、坏 JSON、非法日期、非数组论文、初始化／合并改动、未提交及暂存越权写入均判红 | `release-candidate-check/daily.stdout.txt`、`daily/` |
| 撤防负对照 | 去掉 JSON 解析、日历日校验或基线防错后，对应错误样本能穿过被撤防的检查，证明负对照有区分力 | `release-candidate-check/daily/mutation-*.json`、对应 stdout/stderr |
| 架构地图 | `arch-scan --check`：地图与代码一致（5 块） | `release-candidate-check/arch-check.stdout.txt` |
| 格式、语法与哈希 | `git diff --check`、两件 worker 的 `node --check` 通过；三件产品哈希见下 | 主控命令输出 |
| 密钥样式扫描 | 1139 个变更／证据文件，高置信度 OpenAI／Google／AWS／Aliyun 密钥样式命中 0；这不是全量安全审计 | 主控命令输出 |

主控第一次日报复演停在辅助脚本的汇总格式断言：脚本要求输出含 `/ 0 SKIP`，真实 UX 汇总为 `46 PASS / 0 FAIL` 且不列 SKIP。实际 UX 已 46/46 通过。辅助脚本随后改为匹配真实汇总格式并另行拒绝 `SKIP` 行；失败证据保留为 `release-candidate-check/daily-helper-fail*`，修正后的完整复演通过。这不是删测试或跳过 F8。

Astra V4 的 B1 只涉及验收脚本对数据量的错误假设，网站与两件 worker 未改。修复后：不超过 12 篇时必须全部直接显示、无「显示其余」钮，并实际点击末篇验证详情；超过 12 篇仍检查前 12 篇、展开钮和第 13 篇。条目太少时改在 660px 高度补测折叠后队列增容；没有雷达点时检查零伪标签和零伪热点，有点时仍检查点径、形状、鼠标和键盘。原 2 篇红样本变 46/46，43 篇保持 46/46，藏篇负对照仍红。按 PI「一决策一审、修复不再送审」规则，未再开复审循环。

线上验收脚本先经过三轮修正：第一轮沿用内部测试的封网 DNS 参数；第二轮把 `const SITE_DATA` 误读为 `globalThis.SITE_DATA`，并把单页退出误当永久退出；第三轮 `www` 全部行为通过、主域一次预热 15 秒超时。保留 `online-verify-current.json`、`-v2.json`、`-v3.json`，未删红证据。最终仅修验收脚本后，第四轮双域 18/18；主域那次预热超时未在第四轮复现，根因不能冒称已查明，记为偶发网络／预热风险。两个根地址在第四轮各有一次 HEAD 网络失败后重试成功，尝试次数留在 JSON。

G18 的唯一独立复核 A5 未直接放行：它复现了按检出字节而非 Git blob 验 MD5、缺少错主机用例和首页错误 MIME 放行。S13 已按原样本修复，主控复跑 32/32、源码 5/5，并比较整合文件与隔离候选一致；未再开复审循环。

M3 的派遣回执出现 `mimo-v2.6-pro` 与辅助 flash 两个型号键，身份闸退出 8，故不宣称派遣全绿。实际生产配置以公开响应为准。旧客户端迁移的前两次失败是调试端口/旧端口文件问题；第三次已跑通核心迁移，但原始 3/1 仍保留。第四项缺的是 CDP `requestWillBeSent.redirectResponse` 采集，主控未改写原证据，而用最终地址和独立公网 301 联合裁定，详见 `www-legacy-migration-review.json`。

## 改动清单

- `index.html`：保留最新 43 篇官方数据和 C1 缓存状态／注册／退出逻辑，SHA-256=`27ba018a9a3b4936ec734820af8cb505262bd55f41ae382047615f0a58d7c706`。
- `sw.js`：本地先开、后台核新、异常拒写，SHA-256=`e882e9e2eef0bf36781b8b03ecec23eb81221fa8b33272cdc9de3e368f76394f`。
- `sw-retire.js`：清前缀缓存、注销并通知客户端，SHA-256=`5ae38f2ba965f4e1b1d340da2ba5fadd8b58af82a1e271a02ddff97ab5686199`。
- `.github/workflows/deploy_oss.yml`：`smooth-verify` 先于部署；正常／退役上传两件 worker，worker 禁止缓存，首页最后上传。只刷新主域 4 地址；主域按 `HEAD` Git blob 验 MD5 和 HTML/JS MIME，www 根/index/带查询样本验 301/308 到短域同路径同查询，www 两 worker 始终验退役 MD5、JS/no-store。S7 等待为前两次各 5 秒、随后每次 40 秒，末次前累计至少 370 秒；S13 新增 CRLF、Git 读取失败、错主机和首页 MIME 判红。
- `tests/smooth/`：新增发布模拟、官方数据解析、CI 基线准备与日报负对照；保留 S1/S2/S3 和源码检查。
- `tests/ux/ux_probe.mjs`：新增可选 `--base-html`，默认 `--base` 行为不变；CI 使用「父提交界面＋当前 SITE_DATA」，不拿当前提交自比制造空差分。B1 修复后按实际篇数、条目空间和雷达点数量选择有效验收行为，不删 F8，也不把少篇或无点场景当成必然失败。
- `README.md`、`docs/架构地图.md`、根 `架构.md`：同步缓存职责、发布链、日报验收与未验边界；机器块已刷新。
- `docs/tasks/T1128-SMOOTH/`：保存施工、复核、复演和失败证据。

## 遗留风险

1. **公网间歇失败仍存在**：最终独立公网检查有一次 `/index.html` 重试，浏览器初跑根地址 HEAD 三次超时；完整复跑 9/9。只证明本机当前入口最终可取到正确版本，不证明各地网络永远稳定。
2. **明确不冒称**：真机/iOS、真实跨日、完整主域退役演练未做；桌面设备模拟不等于真机。公网只从本机一个接入点实测，不等于多地域验收。
3. **部署日志有已知非阻断错误行**：现有桶创建返回 403 后按流程跳过，随后上传、CDN 刷新和全部公网验真成功；不写成“日志零错误”，后续可另评估是否去掉无必要的建桶尝试。
4. **F2 低危未修**：冷缓存未命中会多发一次首页请求，状态可能短闪。
5. **F3 低危未修**：`run-regressions.mjs` 在干净父目录可能 `ENOENT`；本轮直接运行各原脚本。
6. **R08 未有效验证**：AICLS/POOLUP 沿用 Neon V2 各 39 PASS / 1 FAIL，检索选词得到零结果；不宣称 40/40。
7. **派遣旧自检未全绿**：真实派遣可工作，但旧自检 61 PASS / 26 FAIL 含过时型号和失效夹具路径，未为赶进度改绿。
8. **S6 收工路径曾写错**：调度器因 `--expect` 指向外层而重发，主控已停止并按 PID 验尸；最终报告和 rerun 证据已收回，产品哈希未变。

## 地图终态

⑥ 本机候选、⑦ V4/A5 独立复核及修复、⑧ 发布与线上验收全部完成。正式发布提交为 `2c43373aec098375edb9500b2b12e02cb12f2b06`，真实工作流为 `46148918001`，主域刷新任务为 `33911284451`。主域唯一正文、www 永久跳转与旧客户端退役入口均已从 GitHub runner 和主控本机两个独立入口核实。

本机线上验收完成后，不再自动重发、不刷新 CDN、不执行主域退役。后续真机/iOS、真实跨日与完整主域退役分别另开验证；其中完整主域退役必须由 PI 当次明确触发。
