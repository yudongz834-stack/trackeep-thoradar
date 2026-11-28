# T1128-SMOOTH C2 发布候选报告

**干了什么**　在最新 2026-11-28、43 篇日报上整合首页本地副本、正常／退役发布、主域精准刷新、双域 MD5 验真和兼容每日数据变化的 CI 验收。PI 已亲手 push 并触发 deploy；真实 OSS 上传已成功，CDN 刷新按真实账号地形修正后待重发验收。

**PI 怎么亲手验**　发布前查看 `release-candidate-check/` 的汇总；发布后由主控实测双域首访、复访本地先开、后台核新、当日副本与 `?sw=0` 退出。实际 push 和手动触发 `deploy_oss.yml` 唯 PI 亲手。

**还剩什么坑**　Astra V4 发现的少篇日报阻断已修复并由主控用原样本复验关闭；GitHub 托管 runner 和真实 OSS 上传已通过，CDN 刷新收敛、双域线上行为、真机/iOS 和完整退役演练尚未验证。F2/F3、R08 与派遣闸旧自检的既有遗留不因本轮消失。

## 地图影响

⑥ 发布接线与日报验收闸已整合到 `T1128-SMOOTH-RELEASE`，基底为 `28131f314f92a05227fd5923607d717c426da2c5`。⑦ 由独立树 `trackeep-thoradar-astra-v4` 复核同一候选。⑧ 只有在独立复核无阻断且 PI 亲手发布后才进入线上验收。

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
| 日报发布复演 | 26 个命令均符合预期；合法日报通过，旧数据基线、坏 JSON、非法日期、非数组论文、初始化／合并改动、未提交及暂存越权写入均判红 | `release-candidate-check/daily.stdout.txt`、`daily/` |
| 撤防负对照 | 去掉 JSON 解析、日历日校验或基线防错后，对应错误样本能穿过被撤防的检查，证明负对照有区分力 | `release-candidate-check/daily/mutation-*.json`、对应 stdout/stderr |
| 架构地图 | `arch-scan --check`：地图与代码一致（5 块） | `release-candidate-check/arch-check.stdout.txt` |
| 格式、语法与哈希 | `git diff --check`、两件 worker 的 `node --check` 通过；三件产品哈希见下 | 主控命令输出 |
| 密钥样式扫描 | 1139 个变更／证据文件，高置信度 OpenAI／Google／AWS／Aliyun 密钥样式命中 0；这不是全量安全审计 | 主控命令输出 |

主控第一次日报复演停在辅助脚本的汇总格式断言：脚本要求输出含 `/ 0 SKIP`，真实 UX 汇总为 `46 PASS / 0 FAIL` 且不列 SKIP。实际 UX 已 46/46 通过。辅助脚本随后改为匹配真实汇总格式并另行拒绝 `SKIP` 行；失败证据保留为 `release-candidate-check/daily-helper-fail*`，修正后的完整复演通过。这不是删测试或跳过 F8。

Astra V4 的 B1 只涉及验收脚本对数据量的错误假设，网站与两件 worker 未改。修复后：不超过 12 篇时必须全部直接显示、无「显示其余」钮，并实际点击末篇验证详情；超过 12 篇仍检查前 12 篇、展开钮和第 13 篇。条目太少时改在 660px 高度补测折叠后队列增容；没有雷达点时检查零伪标签和零伪热点，有点时仍检查点径、形状、鼠标和键盘。原 2 篇红样本变 46/46，43 篇保持 46/46，藏篇负对照仍红。按 PI「一决策一审、修复不再送审」规则，未再开复审循环。

## 改动清单

- `index.html`：保留最新 43 篇官方数据和 C1 缓存状态／注册／退出逻辑，SHA-256=`27ba018a9a3b4936ec734820af8cb505262bd55f41ae382047615f0a58d7c706`。
- `sw.js`：本地先开、后台核新、异常拒写，SHA-256=`e882e9e2eef0bf36781b8b03ecec23eb81221fa8b33272cdc9de3e368f76394f`。
- `sw-retire.js`：清前缀缓存、注销并通知客户端，SHA-256=`5ae38f2ba965f4e1b1d340da2ba5fadd8b58af82a1e271a02ddff97ab5686199`。
- `.github/workflows/deploy_oss.yml`：新增 `smooth-verify` 闸；正常／退役上传两件 worker，worker 禁止缓存，首页最后上传；实测本账号只管理主域 CDN，故仅刷新主域 4 个地址，双域 8 个地址仍逐一验 MD5，`www` 陈旧同样判红；worker 另验 MIME 与 `no-store`。
- `tests/smooth/`：新增发布模拟、官方数据解析、CI 基线准备与日报负对照；保留 S1/S2/S3 和源码检查。
- `tests/ux/ux_probe.mjs`：新增可选 `--base-html`，默认 `--base` 行为不变；CI 使用「父提交界面＋当前 SITE_DATA」，不拿当前提交自比制造空差分。B1 修复后按实际篇数、条目空间和雷达点数量选择有效验收行为，不删 F8，也不把少篇或无点场景当成必然失败。
- `README.md`、`docs/架构地图.md`、根 `架构.md`：同步缓存职责、发布链、日报验收与未验边界；机器块已刷新。
- `docs/tasks/T1128-SMOOTH/`：保存施工、复核、复演和失败证据。

## 遗留风险

1. **真实发布部分验证**：GitHub runner 和 OSS 上传已通过；CDN 刷新、Content-MD5 双域响应和传播收敛仍待成功发布后确认。
2. **线上行为未验**：双域冷首访、复访本地先开、后台核新、离线当日副本和 `?sw=0` 必须在发布后实测。
3. **明确不冒称**：真机/iOS、国内无代理直连、线上跨日、完整退役演练未做；桌面设备模拟不等于真机。
4. **F2 低危未修**：冷缓存未命中会多发一次首页请求，状态可能短闪。
5. **F3 低危未修**：`run-regressions.mjs` 在干净父目录可能 `ENOENT`；本轮直接运行各原脚本。
6. **R08 未有效验证**：AICLS/POOLUP 沿用 Neon V2 各 39 PASS / 1 FAIL，检索选词得到零结果；不宣称 40/40。
7. **派遣旧自检未全绿**：真实派遣可工作，但旧自检 61 PASS / 26 FAIL 含过时型号和失效夹具路径，未为赶进度改绿。
8. **S6 收工路径曾写错**：调度器因 `--expect` 指向外层而重发，主控已停止并按 PID 验尸；最终报告和 rerun 证据已收回，产品哈希未变。

## 地图终态与 PI 发布动作

⑥ 已完成本机候选；⑦ Astra V4 已完成，B1 修复已由主控用原样本和负对照关闭；⑧ 等 PI 亲手发布。以下命令仅供 PI 亲手执行，主控没有执行：

```bash
git -C "D:/trackeep/trackeep-product/trackeep-thoradar" add -- .github/workflows/deploy_oss.yml README.md 架构.md docs/架构地图.md index.html sw.js sw-retire.js tests/smooth tests/ux/ux_probe.mjs docs/tasks/T1128-SMOOTH && git -C "D:/trackeep/trackeep-product/trackeep-thoradar" diff --cached --check && git -C "D:/trackeep/trackeep-product/trackeep-thoradar" commit -m "T1128: accelerate repeat visits with verified local shell" && git -C "D:/trackeep/trackeep-product/trackeep-thoradar" push origin T1128-SMOOTH-RELEASE:main && gh --repo yudongz834-stack/trackeep-thoradar workflow run deploy_oss.yml --ref main
```

只推分支不会上线；以上命令推到 `main` 并手动触发发布。发布后主控再查工作流结果并做线上验收，不能把触发成功当作网站已经更新。
