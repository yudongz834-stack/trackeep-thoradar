# T1128-READABILITY 本地候选验收报告

**结论：PI 认可的首屏可读性与正式用语已落入正式 `index.html`，最终本地回归通过。当前仅为未提交候选，未提交、未推送、未部署、未刷新 CDN。**

基线：`2826461b93d0ae7d099746e12544bfbaaf960f93`。PI 于 2026-11-29 原话「按这版改」，放行正式源代码施工与完整回归，不含发布。

## 改动

- Thoradar：桌面 17→24px；手机 15→22px。副标题：桌面 9→12px；390px 手机 8→10.5px。
- 主 Tab：桌面约 12.5px、36px 高；选中项深色底、浅色字，未选项文字加深。过滤按钮 12px、36px 高并加强边框与文字。
- 901–1100px 保留三个放大的 Tab，隐藏 `01/02/03` 小编号；1351–1400px 收紧顶栏间距，避免常见屏宽出现内部裁切。
- 首屏用语：`文献队列 / Literature queue`、`每日新文献 / Daily new research`、`胸科文献雷达 / Thoracic literature radar`、`文献 / PAPERS`、`数据日期 / DATA DATE`；搜索框统一为 `检索文献… / Search the literature…`。
- 首屏及中英文翻译表中的 `signal / 信号` 用户措辞改为 `paper / 文献`；例如 `Click a paper to select`、`点选文献查看详情`。医学正文里的专业用词不作替换。
- `tests/ux/ux_probe.mjs` 同步新合同：主 Tab 期望高度改为 36px；仅将本次认可的旧／新措辞精确归一后比较，其余 HTML、数据和状态仍逐字对拍，并单列认可差异。没有删除或跳过检查。

最终 tracked diff：`index.html` 81 行新增、48 行删除；`tests/ux/ux_probe.mjs` 19 行新增、10 行删除。`git diff --check` 通过。完整差异见 `source.diff`。

## 最终验证

| 范围 | 结果 | 证据 |
|---|---|---|
| 静态源代码与数据完整性 | **28/28**；`SITE_DATA` 与基线一致；`mergePapers`、`inWindow`、`render`、`gatePause`、`classifyScheme` 逐字一致（统一换行后）；worker 与发布工作流未改 | `verify-content.mjs`、`content-check.json` |
| 中英文与尺寸专项 | **候选 110/110**；10 组候选＋10 组基线行合计 20/20。覆盖 1422、2134、1366、1180、1024、901、900、390；无横溢、顶栏重叠、控件内部文字裁切或页面异常 | `verify-readability.mjs`、`browser-check.json`、`screens/` |
| 完整 UX | **46 PASS / 0 FAIL**；三视图、筛选、阅读可达性、雷达、页脚、数据与状态差分全部通过 | `ux.stdout.txt`、`ux-screens/` |
| 缓存与异常内容 | **S1 9/9、S2 24/24、S3 9/9，共 42/42**；冷首访、本地副本、核新、退役及异常 HTML/JSON 等合同通过 | `final-cache-s1.json`、`final-cache-s2.json`、`final-cache-s3.json` |
| 发布模拟 | **32/32**；安装与发布 shell 语法检查均为 0，只模拟，不部署 | `deploy-mock.json`、`deploy-mock.stdout.txt` |
| 旧界面负对照 | 旧 30px Tab 按预期 **2 PASS / 2 FAIL**，F11a/F11c 判红 | `ux-negative.stdout.txt`、`ux-negative.exit.txt` |
| 未认可措辞变异对照 | 同时改动两个实际展示版本后按预期 **3 PASS / 1 FAIL**，F8a 判红 | `ux-mutation.stdout.txt`、`ux-mutation.exit.txt` |
| 正式树截图目检 | 1422 中文、1422 英文、901 英文、390 英文均与认可效果一致 | `screens/final-formal-*.png` |

## 发现、返修与对照有效性

1. 第一轮 UX 为 42 PASS / 4 FAIL：两项仍要求旧 30px Tab，两项要求文案逐字不变。按新合同更新后重跑，最终 46/46；原始记录保留在 `ux-attempt1.stdout.txt`。
2. 静态检查首轮发现全局中文替换误碰 `SITE_DATA` 中一处医学正文“信号”。已按基线恢复整行官方数据，确认 `SITE_DATA` 完全一致，并重跑 UX、专项浏览器和缓存测试。首轮 22/3 记录保留在 `content-check-attempt1.json`、`content-attempt1.stdout.txt`。
3. 专项浏览器首轮候选 110/110，但“旧用词应被判出”的负对照未触发；原因是测试表达式中的 `\b` 被外层模板字符串吞成退格。修正后旧界面能够判出旧用词，901px 旧布局也能判出内部裁切；原始记录保留在 `browser-check-attempt1.json`、`browser-attempt1.stdout.txt`。
4. 第一次未认可措辞变异只改了未被当前场景使用的提示版本，返回 4/4，记为无效对照而未记通过。随后同时改动两个实际展示版本，F8a 按预期判红；原始记录保留在 `ux-mutation-attempt1.*`。
5. 最终差异审查恢复了四句被全局替换波及的代码注释，避免把技术上的“停止信号”误写为“停止文献”。恢复后重新执行最终全套 UX、专项浏览器和 S1/S2/S3；`render`、`gatePause`、`classifyScheme` 也加入逐字不变校验。

## 边界

- 官方 `SITE_DATA`、数据合并与时间窗语义、三视图功能、worker、发布配置和 CDN 均未改。
- 真机/iOS、物理双屏拖窗、真实跨日和完整主域退役演练不在本轮；桌面设备模拟不冒称真机。
- 当前线上仍是上一发布版。提交、推送、部署与工作流内 CDN 刷新仍需 PI 当次明确放行并由 PI 亲手操作。
