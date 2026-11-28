DELIVERY-T1128-SMOOTH-S6
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar-smooth-T1128；任务号=T1128-SMOOTH-S6；交付=兼容每日数据更新的 CI 源码与 UX 验收闸。
轨道位置：胸科雷达顺畅改造·⑥ Sol S6 日报发布闸返修。
R级：R2（实际发布另属 R3，唯 PI 亲手）。
判级理由：S5 已实证固定 `73dd34e` 基线会阻止正常日报发布；须修测试与 CI，不得跳过验收。
签发：PI 原话「继续做」（2026-11-28）及 `release-contract.md` 的基底更新记录。
地形：写域仅 `.github/workflows/deploy_oss.yml`、`tests/smooth/`、必要的 `tests/ux/ux_probe.mjs` 测试辅助入口、`docs/tasks/T1128-SMOOTH/`；不改三件产品文件，不碰真实 OSS/CDN。
领域卡：无
经验卡：无卡。
Run 版本键：岗位卡=builder-jobspec 现役正本；S5 `verify-source` 固定基线、`verify-deploy` 18 项与 `reproduce-daily` 红证据；远端日报=`28131f314f92a05227fd5923607d717c426da2c5`。

## 已裁定的问题
正常日报会改变 `SITE_DATA` 和 data/feed 等 16 文件，这不是越权，也不能让每天自动发布永久红。主控已把最新日报与缓存改动合并，43 篇上 S1/S2/S3/UX 全过。当前 S5 CI 仍固定 `73dd34e`：源码 official-data/write-scope 会红，UX F8 会因论文内容差分变红。必须修根因，禁止删除这些测试或固定改成另一个很快过期的提交号。

## 要求的机制
1. **CI 源码检查**：支持明确的 CI 模式。当前 `SITE_DATA` 必须独立解析并校验真实日期和 `papers` 数组（允许正常日报变化）；`PAPERS` 初始化、`mergePapers/inWindow` 仍与基线核对。CI 的写域检查针对本 runner 干净 checkout 后新生成的未提交改动，不能把历史提交里的日报文件当未授权写入。默认本地模式仍保持原严格对照，不削弱 C1 检查。
2. **CI UX 基线**：取 `github.sha` 的第一父提交作为界面基线，但把该基线的 `SITE_DATA` 块替换为当前同版官方数据后再跑 UX。这样 F8 比较的是界面/程序差异，不是每天论文内容差异。可在 `tests/ux/ux_probe.mjs` 增加可选基线 HTML 入口；默认 `--base` 原行为不变。不得把基线直接设为当前提交来制造空差分。
3. 工作流使用同一 `github.sha`、全历史，显式准备上述基线，保持 S1/S2/S3 和 `verify-deploy` 原顺序及部署依赖。不能把 UX 或 source 步骤删掉、continue-on-error 或跳过 F8。
4. 加真实正例与负对照：变化的合法日报可通过 CI 数据校验；坏 JSON/非法日期仍红；基线 HTML 必须含父提交界面与当前数据，若夹带父提交旧数据或错块应红。默认本地 `verify-source` 和 UX 入口行为不变。
5. 复跑 S5 发布模拟 18 项、默认 `verify-source`、S1/S2/S3 与 UX，并模拟一个含日报数据的 CI 场景证明 source+UX 都能过。保留原 `reproduce-daily` 红证据，新证据不得覆盖旧文件。
6. 三件产品哈希不变；不 push/deploy/CDN、不访问真实凭证或线上服务。结果输出到 temp 或任务证据目录，避免测试自身污染写域。

交付 `sol-s6-report.md`、原始 stdout/stderr/JSON、diff 与退出码，报告三行头、地图影响、验证状态、改动清单、遗留风险、地图终态齐全。最终尾部复述 `DELIVERY-T1128-SMOOTH-S6`。
