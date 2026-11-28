干了什么｜在隔离工作树原地调整 ThorRadar 布局。两个目标视口的雷达盘从 420 px 扩到 477.7 和 620 px，并修好窄桌面筛选和雷达标签的裁切。
PI 怎么亲手验｜启动下方本地服务后，用隔离浏览器打开打印出的候选页。在 1422×800 点一个未选中的雷达点，右栏切到对应文章即通过。
还剩什么坑｜未跨两块物理屏幕拖窗验真，主控独立验收待做。901 px 桌面边界为容纳三栏，雷达盘缩至 284 px。

## 干了什么

从 `2acc32d354555db6f245cb1a25055b450a7c0c3d` 的现成 detached worktree 施工，席位版本键 `launcher=codex-gpt`、`model=gpt-6.2-sol`。先保存 HEAD 截图和几何数据，再改 CSS，最后用同一个本地服务、同一个隔离 Chrome 进程重新拍摄 HEAD 与候选。两版均加载 2026-11-28 的同一批内嵌数据，运行时 43 篇文章 ID 序列一致。

宽高比达到 5:3 的桌面在三栏中增加详情宽度并收紧外边距。1600 px 以上继续放宽三栏容器，雷达直径上限随之增加。雷达盘始终受舞台实际宽高约束。两个目标档主视图按钮从 30 px 增到 34 px。紧凑标题、沉浸标题和正文的字号来自原规则。

## 地图影响

- 正式入口仍为 `index.html`。概览保留队列、雷达、锁定详情，阅读保留队列和详情，个性化继续复用四个原分区。
- 900 px 及以下维持单栏顺序。901 px 以上的概览保留三栏，窄中栏允许收缩。阅读筛选在桌面按宽度排四格一行或两行两列，窄屏沿用纵排。
- 文件级比较确认 `index.html` 的 `<style>` 外内容逐字一致。三个脚本、`SITE_DATA` 单行、现有测试、CI 和两份 worker 零差异。[源文件核验](sol-evidence/source-check.stdout.txt)

## 验证状态

主屏物理参数为 2560×1600、Windows 150%。1422×800 是按相同浏览器缩放估算的 CSS 视口。副屏物理参数为 2560×1440、Windows 100%。2134×1073 是委任状提供的实测 CSS 视口，来自约 120% 的浏览器缩放。本次用 Chrome 158.0.8127.88、DPR 1 重放这两个尺寸和其它档位。390×844 使用 Chrome 移动视口模拟，其余均为桌面视口模拟。截图使用减少动态效果偏好，便于比较雷达几何。

概览列宽和盘径以 CSS px 计，列宽依次为队列、雷达区、详情。单栏行只列栏宽。候选十档页面横溢均为 0 px，每档默认概览的 36 个点均有鼠标命中位置，并实际点按 3 个未选点核对锁定状态。每档还点击展开与关闭筛选、展开刊源图例、滚至最后一个刊源并选中、点击清除。[同服务矩阵原始输出](sol-evidence/matrix.stdout.txt) · [HEAD 几何](sol-evidence/head/geometry.json) · [候选几何](sol-evidence/candidate/geometry.json)

| 视口 | HEAD → 候选列宽 | HEAD → 候选盘径 | 基线问题或候选变化 | 概览截图 |
| --- | --- | --- | --- | --- |
| 1422×800 | 280 / 724 / 350 → 270 / 702 / 390 | 420 → 477.7 | 展开刊源图例后盘径 371.7 → 379.7，控件仍可操作 | [HEAD](sol-evidence/head/1422x800-overview.png) · [候选](sol-evidence/candidate/1422x800-overview.png) |
| 2134×1073 | 280 / 1102 / 350 → 320.09 / 1159.91 / 460 | 420 → 620 | 容器宽 1800 → 2000，详情摘要行宽 302 → 412 | [HEAD](sol-evidence/head/2134x1073-overview.png) · [候选](sol-evidence/candidate/2134x1073-overview.png) |
| 1920×1080 | 280 / 1102 / 350 → 294 / 1143.61 / 422.39 | 420 → 620 | 详情摘要行宽 302 → 374.39 | [HEAD](sol-evidence/head/1920x1080-overview.png) · [候选](sol-evidence/candidate/1920x1080-overview.png) |
| 1366×768 | 280 / 668 / 350 → 270 / 646 / 390 | 420 → 445.7 | 页脚继续完整落在视口内 | [HEAD](sol-evidence/head/1366x768-overview.png) · [候选](sol-evidence/candidate/1366x768-overview.png) |
| 1180×900 | 240 / 579 / 315 → 相同 | 420 → 420 | 阅读展开时档位区原先伸出面板，现完整容纳 | [HEAD](sol-evidence/head/1180x900-overview.png) · [候选](sol-evidence/candidate/1180x900-overview.png) |
| 1024×768 | 240 / 423 / 315 → 相同 | 407 → 407 | 3 个标签越过舞台边界 → 0，阅读档位区裁切消除 | [HEAD](sol-evidence/head/1024x768-overview.png) · [候选](sol-evidence/candidate/1024x768-overview.png) |
| 901×1000 | 240 / 360 / 315 → 240 / 300 / 315 | 344 → 284 | 横溢 48 → 0，3 个标签越过舞台边界 → 0 | [HEAD](sol-evidence/head/901x1000-overview.png) · [候选](sol-evidence/candidate/901x1000-overview.png) |
| 900×1000 | 861 → 861 | 560 → 560 | 单栏，页面纵向滚动 | [HEAD](sol-evidence/head/900x1000-overview.png) · [候选](sol-evidence/candidate/900x1000-overview.png) |
| 768×1024 | 729 → 729 | 560 → 560 | 单栏，页面纵向滚动 | [HEAD](sol-evidence/head/768x1024-overview.png) · [候选](sol-evidence/candidate/768x1024-overview.png) |
| 390×844 | 370 → 370 | 370 → 370 | 2 个标签越过舞台边界 → 0，长刊名可换行 | [HEAD](sol-evidence/head/390x844-overview.png) · [候选](sol-evidence/candidate/390x844-overview.png) |

阅读五档均实际切换紧凑和沉浸、点文章、展开并关闭详情元数据。紧凑结论 12 px、沉浸结论 14 px，摘要桌面 12 px、390 px 档 12.5 px。各档字号前后一致，摘要可滚动到末尾。

| 视口 | 阅读摘要宽度（px） | 阅读截图 | 展开筛选截图 |
| --- | --- | --- | --- |
| 1422×800 | 322 → 342 | [HEAD](sol-evidence/head/1422x800-reading.png) · [候选](sol-evidence/candidate/1422x800-reading.png) | [HEAD](sol-evidence/head/1422x800-reading-filters.png) · [候选](sol-evidence/candidate/1422x800-reading-filters.png) |
| 2134×1073 | 322 → 412 | [HEAD](sol-evidence/head/2134x1073-reading.png) · [候选](sol-evidence/candidate/2134x1073-reading.png) | [HEAD](sol-evidence/head/2134x1073-reading-filters.png) · [候选](sol-evidence/candidate/2134x1073-reading-filters.png) |
| 1180×900 | 328 → 328 | [HEAD](sol-evidence/head/1180x900-reading.png) · [候选](sol-evidence/candidate/1180x900-reading.png) | [HEAD](sol-evidence/head/1180x900-reading-filters.png) · [候选](sol-evidence/candidate/1180x900-reading-filters.png) |
| 1024×768 | 273 → 273 | [HEAD](sol-evidence/head/1024x768-reading.png) · [候选](sol-evidence/candidate/1024x768-reading.png) | [HEAD](sol-evidence/head/1024x768-reading-filters.png) · [候选](sol-evidence/candidate/1024x768-reading-filters.png) |
| 390×844 | 336 → 336 | [HEAD](sol-evidence/head/390x844-reading.png) · [候选](sol-evidence/candidate/390x844-reading.png) · [HEAD 摘要](sol-evidence/head/390x844-reading-detail.png) · [候选摘要](sol-evidence/candidate/390x844-reading-detail.png) | [HEAD](sol-evidence/head/390x844-reading-filters.png) · [候选](sol-evidence/candidate/390x844-reading-filters.png) |

个性化复测三档，四个分区用鼠标逐一切换，再回概览。1422×800 [HEAD](sol-evidence/head/1422x800-personal.png) · [候选](sol-evidence/candidate/1422x800-personal.png)，2134×1073 [HEAD](sol-evidence/head/2134x1073-personal.png) · [候选](sol-evidence/candidate/2134x1073-personal.png)，390×844 [HEAD](sol-evidence/head/390x844-personal.png) · [候选](sol-evidence/candidate/390x844-personal.png)。

- 仓库完整 UX 回归维持 `46 PASS / 0 FAIL`。按现有 CI 的方式从首父准备同数据对照，HEAD 和候选各跑一次，未传 `--only`。官方面 57 格与 8 幕状态一致。[准备输出](sol-evidence/ux-prepare.stdout.txt) · [HEAD 回归](sol-evidence/ux-head.stdout.txt) · [候选回归](sol-evidence/ux-candidate.stdout.txt)
- 改坏对照实际删掉 `100cqh` 高度约束。1422×800 打开刊源图例时，探针报 `radar exceeds stage` 和 `radar overlaps its controls`，退出 1。用 `Copy-Item` 从备份恢复，前后 SHA-256 相同。[改坏原始输出](sol-evidence/mutation.stdout.txt) · [改坏截图](sol-evidence/mutation/1422x800-overview-legend.png) · [恢复原始输出](sol-evidence/mutation-restore.stdout.txt)
- 矩阵退出 0。`git diff --check` 退出 0，唯一有跟踪改动的是 `index.html`。任务目录原有的四份未跟踪文件保留在原处。[退出码](sol-evidence/matrix.exit.txt) · [源文件核验](sol-evidence/source-check.stdout.txt) · [最终 Git 状态](sol-evidence/git-status.stdout.txt)

## 改动清单

- `index.html` 调整概览网格、雷达舞台和标签、阅读筛选列、两档主视图按钮及长刊名换行。
- `sol-evidence/` 保存尺寸探针、源文件核验、改坏脚本、截图、几何数据和命令原始输出。`head-before-edit/` 是动 CSS 前首次拍摄。首跑把部分可滚动图例和移动端平滑滚动过程判为失败。复拍时补了滚动容器和实时命中检查，`head/` 与 `candidate/` 均用修正后的同一版探针。
- `sol-r1-report.md` 汇总本次交付。

## 还剩什么坑

双屏实机拖窗和主控独立重跑待完成。901 px 边界的雷达盘只剩 284 px，这是保持左栏 240 px、右栏 315 px 和页面零横溢的取舍。390 px 阅读仍需纵向滚到详情，沿用现有单栏顺序。

## 地图终态

候选留在指定隔离工作树，交付层级为 R2 待主控验收。提交、推送、部署、CDN 刷新均未执行。以下命令在隔离工作树根目录运行。

```powershell
$e = 'docs/tasks/T1128-RESPONSIVE/sol-evidence'
node "$e/responsive-probe.mjs" serve
node "$e/responsive-probe.mjs" compare
node "$e/source-check.mjs"
pwsh -NoProfile -File "$e/layout-mutation.ps1"
```

`serve` 打印候选和 HEAD 的本地 URL。`compare` 使用单独的隔离浏览器和端口，可另开终端重跑。完整 UX 回归的命令和对照准备见 [运行记录](sol-evidence/commands.txt)。

DELIVERY-T1128-RESPONSIVE-R1
