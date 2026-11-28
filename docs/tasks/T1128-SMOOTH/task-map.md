# T1128-SMOOTH 唯一任务地图

契约 C1（已准）：PI 原话「算了，现在直接执行吧，不重启了」（2026-11-28）；前序组合原话「我想让codex gpt 6.2 sol全程施工，agy gemini 4 neon协助和验证，你做最后检查。先定这个施工组合」。
当前授权边界：C1 本机候选已完成。C2 续作＝PI 在知悉「核心修复完成、线上交付未完成」后原话「继续做」（2026-11-28），授权发布接线、退役流程、CI 验证闸与上线验收准备；实际 push、deploy、CDN 刷新和退役演练仍唯 PI 当次亲手。R2 施工／R3 发布。
开工时刻：2026-11-28 10:41:06（本机 `date`）；C1 硬预算终点 11:41:06 已结束，C2 不冒称一小时内完成。
C2 当前发布基底：`origin/main=28131f314f92a05227fd5923607d717c426da2c5`；本地分支 `T1128-SMOOTH-RELEASE` 已保留缓存改动并同步最新日报（43 篇），详见 `release-contract.md` 与 `release-sync-check/`。

| 轨道位置 | 状态 | 授权态 | 依赖 | 役中违例计数 | 结果指针 |
|---|---|---|---|---:|---|
| ③.1 基线、隔离工作树与任务书 | completed | C1 已准 | 无 | 0 | `brief-sol-s1.md`；HEAD `73dd34e`；工作树 `D:/trackeep/trackeep-product/trackeep-thoradar-smooth-T1128` |
| ③.2 Sol S1 首例：本地先开、后台更新、下次生效 | completed | C1 已准 | ③.1 | 0 | `sol-s1-report.md`；Sol 三轮 9/9＋两项负对照；主控复跑 `main-s1-rerun.json` 9/9 |
| ③.3 主控首例放行 | completed | C1 已准 | ③.2 | 0 | 主控 2026-11-28 11:08 放行；亲自复跑 9/9，写域/语法/diff-check 通过 |
| ③.4 Sol S2/S3/S4 异常、退出、回归与发现项返修 | completed | C1 已准 | ③.3 | 0 | S4 `sol-s4-report.md`：专项 9/9、S1 9/9、S2 24/24、UX 46/46；日期与脚本上下文撤防分别 7/2、8/1；主控复跑专项 9/9、源码/写域 5/5；sw SHA-256 `e882e9e2eef0bf36781b8b03ecec23eb81221fa8b33272cdc9de3e368f76394f` |
| ④ Neon V1 新会话独立复验 | completed-with-findings | C1 已准 | ③.4 | 0 | `neon-v1/report.md`：S1 9/9、S2 24/24、UX 46/46、指定异常与三项负对照通过；F1 空标记毒壳阻断，F2/F3 低危；两套旧回归未独立复跑，R08 失真未验 |
| ④ Neon V2 新会话独立复验 | completed-with-findings | C1 已准 | S3 | 0 | `neon-v2/report.md`：F1 已关，正式 12/12、4 项核心负对照变红；F4 两探针 `preserved=false`，F2/F3 未修；AICLS/POOLUP 各 39/40，R08 未形成有效检索验证 |
| ④ Astra V3 新会话独立复验 | completed | PI 2026-11-28 要求继续做完全活，并提示 agy 额度可能用尽 | S4 | 0 | `astra-v3/report.md`、`verdict.txt`：独立对抗 12/12，两个原失败探针均 `preserved=true`、健康缓存 539012B；S3 9/9、S1 9/9、S2 24/24、UX 46/46；本轮范围内无阻断项 |
| ⑤ 主控最终整合检查并写回主工作树 | completed-local-candidate | C1 已准 | Astra V3 | 0 | `FINAL-REPORT.md`：三件产品文件与 `tests/smooth` 已整合；主仓 S3 9/9、S1 9/9、S2 24/24、UX 46/46、源码/写域 5/5；`arch-scan --check` 5 块一致；F2/F3、R08、闸旧自检 61/26 和未上线边界如实保留 |
| ⑤.9 对外发布 | superseded-by-c2 | C2 续作另立⑥–⑧ | ⑤ | 0 | C1 未执行任何发布动作 |
| ⑥ Sol S5/S6 发布接线、CI 验证闸与退役模式 | completed-local-candidate | C2「继续做」 | ⑤ | 0 | S5/S6 已整合最新 43 篇候选；主控 `release-candidate-check/`：发布模拟 18/18、S3 9/9、S1 9/9、S2 24/24、UX 46/46；日报复演 26 步均符合预期，坏 JSON/非法日期/越权写入/旧基线判红；三件产品哈希保持合同值；不碰线上 |
| ⑦ Astra V4 发布候选独立复核＋B1 修复 | completed-with-repair | C2「继续做」 | ⑥ | 0 | `astra-v4/report.md`：发布与负对照通过，发现合法 2 篇日报被 UX 阻断；主控只修 `tests/ux/ux_probe.mjs`，按「一决策一审、修复不再送审」不复开外审。`release-candidate-check/b1-fix/`：原 2 篇样本 46/46、43 篇 46/46；故意藏掉 1 篇时 F9a 判红；发布模拟 18/18；三件产品哈希未变 |
| ⑧ PI 亲手发布＋Sol/Mimo 控制台修复＋主控线上验收 | completed | PI 已亲手执行前序 push/deploy；最终提交、推送、触发发布、CDN 刷新和主域退役仍唯 PI | ⑦ | 0 | 托管 runner 全闸与真实 OSS 上传通过；`www` 不属本账号导致整批刷新失败，主域随后证实缺 `cdn:RefreshObjectCaches`。Sol S7 `sol-s7-report.md` 另查实 `www` 公网 TLS 握手失败；主域 4 地址刷新、双域 8 地址验真不变，传播等待增至至少 370 秒，主仓 18/18。Sol S8 提交最小策略后遇安全验证，创建与授权未冒称完成；主控新开列表页无验证；S9 查重零条后仅提交一次，随后再次安全验证；PI 已亲手完成，主控回读到策略详情路由且无挑战。S10 RAM 子项已完成双回读：最小 Action/Resource、唯一发布 SubUser、账号级仅新增目标策略，用户权限 1→2 且原行不变；真实刷新待重发。Mimo M1 已回读当前账号仅主域、www 搜索零条、现有证书覆盖 www，主控逐图复核；www 四 URL 仍 TLS 失败。M2 已完成 www 同账号 CDN 接入、复用证书和 www 专用 CNAME，公开双域八 URL 全过且主域未退化。S11 旧双域补丁已交回但**未应用**：本地 18/18、两组负对照均 16/18 判红；RAM 增加 www 资源遇安全验证，云端未改。派遣闸因报告落在隔离树退出 12，主控已取回 `sol-s11-dual-domain-report.md` 与证据。G18 已拍板短域唯一＋www 跳转，旧 S11 不应用、www 刷新权限不扩。S12 已整合主树并复跑 27/27，七组撤防均判红，报告/补丁/证据在 `sol-s12-canonical-report.md` 与 `online-release/sol-s12/`；Astra A5 已完成唯一复核并发现 Git blob MD5、错主机用例、首页 MIME 三项；S13 已按原样本修复并整合，主控发布模拟 32/32、源码 5/5，证据 `online-release/main-s13-deploy.json`、`main-s13-source.json`，不再送复审。M3 已使 www 普通路径 301 到短域同路径同查询，两 worker 始终返回退役版、JS/no-store，主域四地址未退化；主控公网初跑 9/10，唯一连接超时补跑取得正确 301，证据 `mimo-m3-canonical-report.md`、`online-release/canonical-public-current.json`、`canonical-public-current-retry.txt`。真实旧 www 客户端已验旧缓存打开、注销清壳、个人标记保留及下次跳短域；原始探针 3/1 保留，与独立 301 联合裁定 4/0，测试 profile 已删除，证据 `online-release/www-legacy-migration-v3.json`、`www-legacy-migration-review.json`。PI 已亲手提交并推送 `2c43373`，触发工作流 `46148918001`；smooth-verify 与 deploy-oss 成功，主域刷新任务 `33911284451`，runner 末行 `Publish verified on both domains`。主控独立公网 10/10、浏览器完整复跑 9/9；初跑 8/1 的根地址 HEAD 连接超时保留，五项实际浏览器行为初跑已通过。证据 `online-release/deploy-46148918001.json`、`deploy-46148918001.log`、`canonical-public-final.json`、`canonical-browser-final.json`、`canonical-browser-final-retry.json`。真机/iOS、真实跨日和完整主域退役仍未验 |

规则：并行写默认禁止；Sol 只在隔离工作树施工，Neon/Astra 只读复验；任务地图只由派单方回填。退回或重派必须保留原因。
