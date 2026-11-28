DELIVERY-T1128-SMOOTH-A4
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar-astra-v4；任务号=T1128-SMOOTH-A4；交付=正常/退役发布与日报 CI 闸的独立复核。
轨道位置：胸科雷达顺畅改造·⑦ Astra V4 发布候选独立复核。
R级：R2（真实发布另属 R3，唯 PI 亲手）。
判级理由：部署工作流、CDN 刷新、退役映射与 CI 验收链需要未参与施工的新会话亲自复验。
签发：PI 原话「继续做」「要加快脚步，不能拖沓，认证完成」（2026-11-28）；只复核既定发布范围，不扩新需求。
地形：派单方会从主仓 `T1128-SMOOTH-RELEASE` 同步最终候选到本独立树。复核写域仅 `astra-v4/` 自有适配与主仓同名证据目录；不得改产品、工作流、施工测试、合同或任务地图，不得真实外呼 OSS/CDN。
领域卡：无
经验卡：无卡。
Run 版本键：岗位卡=verifier-jobspec 现役正本；发布基底=`28131f314f92a05227fd5923607d717c426da2c5`；首页预期 SHA-256=`27ba018a9a3b4936ec734820af8cb505262bd55f41ae382047615f0a58d7c706`；worker=`e882e9e2...394f`、退役版=`5ae38f2b...6199`。

## 优先复核（先做前四项）
1. 先核对首页为 2026-11-28、43 篇及三件产品哈希，记录工作流和测试件哈希；不同步或仍是旧 40 篇候选就停报。
2. 亲自跑 `tests/smooth/verify-deploy.mjs`：正常/退役两模式、8 URL、上传顺序、no-store、MD5 映射、失败分支必须通过。亲自跑 Sol 的删 MD5 负对照，另造至少一项自己的发布变异（例如 retire 映射错文件、漏一个刷新 URL 或 worker 变可缓存），证明会红；只改自有副本，不动正本。
3. 复核 S6 日报闸：合法日报数据允许变化但坏 JSON/非法日期必须红；CI 写域不能拿历史日报文件当越权；UX 基线必须是「父提交界面＋当前 SITE_DATA」，不能直接把当前提交当基线制造空差分。亲自跑日报 source+UX 场景，并检查 F8a–F8d 真执行。默认本地 source/UX 行为不得被削弱。
4. 复核工作流确实先跑 verify-deploy/source/S1/S2/S3/UX 再部署，同一 revision、无 continue-on-error；退役模式把 `sw-retire.js` 映射到真实 `/sw.js`，正常模式可恢复。
5. 再复跑最新日报上的 S3 9 项、S1 9 项、S2 24 项、UX 46 项（本地基线 `28131f3`）与默认 `verify-source` 的适用入口。AICLS/POOLUP 沿用 V2 各 39/40、R08 失真未验，不重复耗时，不冒充本轮新跑。
6. 所有测试完成并落盘后再读 Sol S5/S6 报告，交叉核对。记录命令、退出码、环境、跑次/种子、哈希和原始 stdout/stderr/JSON。浏览器只用独立临时配置，按 PID 验尸。
7. 不 push/deploy/CDN，不访问真实凭证、AI/NCBI，不做线上或退役演练。发现会发旧日报、发错 worker、假绿或无法每日发布的问题列阻断；其它观察单列。

交付 `D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/astra-v4/report.md`，三行头、结论/阻断/未验、地图影响、验证状态、改动清单、遗留风险、地图终态齐全。最终尾部复述 `DELIVERY-T1128-SMOOTH-A4`。优先出结论，不扩做额外审计。
