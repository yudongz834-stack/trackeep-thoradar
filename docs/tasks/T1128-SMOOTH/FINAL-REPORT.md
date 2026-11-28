# T1128-SMOOTH 最终整合报告

**干了什么**　把经 Sol 施工、Neon 查错、Astra 独立复验的首页本地副本候选整合进主仓；复访可先打开本地当日首页、后台核新、下次打开新版，异常响应不得覆盖健康副本，并提供单机/退役退出。

**PI 怎么亲手验**　打开 `main-final/verify-s3.stdout.txt`，末行应为 `SUMMARY {"passed":9,"failed":0}`；再看 `astra-v3/verdict.txt` 前两行，两个原失败样本均为 `preserved=true`、`bytes=539012`、`next=cache-storage`。

**还剩什么坑**　本机候选已完成，但生产上线未完成：现行 `deploy_oss.yml` 尚未上传两件 worker，本轮未改 CI/CD，真机与线上未验。F2/F3 两个低危遗留未修，AICLS/POOLUP 的 R08 检索步仍未形成有效验证。

## 验证状态

| 验证者 / 范围 | 实测结果 | 原始证据 |
|---|---|---|
| Sol S4 施工 | 专项 9/9；S1 9/9；S2 24/24；UX 46/46 | `sol-s4-report.md`、`sol-s4/` |
| Sol S4 撤防 | 撤日期校验 7/2；撤脚本上下文校验 8/1，均按预期变红 | `sol-s4/no-date-guard.*`、`sol-s4/no-script-guard.*` |
| 主控隔离树复核 | S4 专项 9/9；官方数据/初始化/合并窗口/写域/语法 5/5 | `main-s4-rerun/` |
| Astra 新会话独立复验 | 独立对抗 12/12；两个原失败探针均保留 539012B 健康缓存；S3 9/9、S1 9/9、S2 24/24、UX 46/46 | `astra-v3/report.md`、`astra-v3/verdict.txt` |
| 主仓最终复跑 | S3 9/9；S1 9/9；S2 24/24；UX 46/46；源码/写域 5/5 | `main-final/` |
| 架构地图 | `arch-scan --write` 刷新 5 块；`--check` 返回“地图与代码一致（5 块）” | 根 `架构.md` 与本次命令输出 |
| 最终格式与语法 | `git diff --check` 通过；`node --check sw.js/sw-retire.js` 通过 | 主控最终命令输出；仅有既存行尾转换提示 |

Astra 的独立复验确认：`empty-briefing-date` 与 `comment-wrapped-site-data-stub` 都从 V2 的 `preserved=false` 变为 `preserved=true`，下一次打开均由 Cache Storage 显示 2026-11-27、40 篇、37 个雷达点；合法零篇仍能更新。MIME 与 503 撤防变红；其余旧变异被 S4 的脚本上下文校验纵深接住，未把它们误报为“全部撤防都变红”。主控只将 Astra 报告已有的两个章节标题补成验收槽位名，未改实测数据。

## 改动清单

- `index.html`：+123/-10。新增生产域/本机显式门禁、缓存状态提示、后台消息处理、单机退出和多日档案失败持续提示；官方 `SITE_DATA`、`PAPERS` 初始化、`mergePapers/inWindow` 经源码检查逐段一致。
- `sw.js`：新增。仅处理同源 GET 的 `/` 与 `/index.html` 导航；本地先开、后台 `no-store` 核新、下次生效；写入前校验状态/basic/MIME/完整 HTML/真实内联脚本/`SITE_DATA` JSON/有效日期/论文数组。
- `sw-retire.js`：新增。清理 `thoradar-shell-` 前缀缓存、注销并通知打开的阅读页。
- `tests/smooth/`：新增核心、异常、退出、源码检查及回归封装。
- `README.md`、`docs/架构地图.md`、根 `架构.md`：同步 OSS 发布链、本地副本职责、退出机制和未上线边界；机器地图已刷新。
- `docs/tasks/T1128-SMOOTH/`：保存任务书、合同、施工与独立复核原始证据。

最终三件 SHA-256：

```text
index.html  33c50bef723b0a3f32b51bc2d5927ff4391bb58eb474996f1a7d9dff96bc1def
sw.js       e882e9e2eef0bf36781b8b03ecec23eb81221fa8b33272cdc9de3e368f76394f
sw-retire.js 5ae38f2ba965f4e1b1d340da2ba5fadd8b58af82a1e271a02ddff97ab5686199
```

## 遗留风险与未验项

1. **F2 低危未修**：冷缓存未命中会多发一次首页请求，受控页面可能短暂显示“本地副本·核对更新中”后切回联网状态。
2. **F3 低危未修**：`tests/smooth/run-regressions.mjs` 在父目录不存在时仍可能 `ENOENT`；本轮最终验证直接运行各原脚本，未把封装问题掩盖为通过。
3. **R08 未有效验证**：AICLS/POOLUP 沿用 Neon V2 独立重跑，均为 39 PASS / 1 FAIL；基线与候选都因测试选词得到 `Mortality` 零结果，其余 38 步逐字一致。未改旧测试，不宣称 40/40。
4. **派遣闸自检未全绿**：真实派遣链已恢复并完成 Neon/Astra 任务，但旧自检仍为 61 PASS / 26 FAIL，含旧型号期望和不存在的 D:/dev 夹具路径；未为赶进度修改这些夹具。
5. **本轮明确未验**：iOS、真机、国内无代理直连、线上跨日、多标签完整生命周期、正常 SW 自身升级、90 天档案离线、UX3 合并、CDN 头与刷新收敛、生产发布。

## 地图终态与下一步

③.4 施工返修、④ 独立复验、⑤ 主仓整合检查均可收口；⑤.9 对外发布仍为 `not-authorized`。未 commit、未 push、未 deploy、未刷新 CDN。

若 PI 后续决定上线，须另行授权发布接线与线上验收：两件 worker 的上传及缓存头、双域精准刷新、退役流程、真机/iOS/国内直连与跨日观察。`git push`、deploy 和 CDN 刷新仍只能由 PI 当次亲手执行。
