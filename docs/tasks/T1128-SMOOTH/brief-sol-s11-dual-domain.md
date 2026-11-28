DELIVERY-T1128-SMOOTH-S11
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar；任务号=T1128-SMOOTH-S11；交付=同一最小刷新权限精确覆盖双域、工作流恢复双域八地址刷新、发布模拟与负对照。
轨道位置：胸科雷达顺畅改造·⑧ 双域最终发布接线。
R级：R3（RAM 现有策略精确扩一个 www 资源＋本地发布工作流修改；不 push/deploy/真实刷新）。
判级理由：M2 已把 www 纳入同一 CDN 账号并验证公开八地址；若脚本只刷新主域，以后 www 日报会陈旧。直接恢复双域刷新又会被当前仅主域的 RAM 资源拒绝，两处必须同批闭环。
签发：沿用 PI G14/G15/G16 的连续代操作授权与既定要求「www 若迁入同一可管理账号，应恢复双域自动刷新并更新测试，避免未来日报 www 陈旧」。仅限同一刷新动作和两个精确域名，不扩大为其它权限或发布授权。
地形：本地只写 `.github/workflows/deploy_oss.yml`、`tests/smooth/verify-deploy.mjs`、必要的 `tests/smooth/deploy-mock.mjs`、`docs/tasks/T1128-SMOOTH/sol-s11*` 与 `online-release/sol-s11/`。不得改三件产品、官方数据、其它测试或任务地图。浏览器只新建自己的 RAM 标签，不碰 PI 原有/Mimo 标签，结束关闭；遇安全挑战保留。
领域卡：无
经验卡：无卡。
Run 版本键：岗位卡=builder-jobspec 现役正本；model=gpt-6.2-sol；基底工作树已有 S7 至少 370 秒等待补丁；S10 最小策略与唯一 SubUser 证据=`sol-s10-browser-report.md`；M2 双域接入=`mimo-m2-browser-report.md`。

## 已确认事实
1. `www.thoradar.online` 已在当前账号 CDN，专用 CNAME 已生效，HTTPS/回源与主域对齐。M2 和主控独立抽测均显示 www 首页 200 且 MD5 与 Git blob 一致；不是其它账号。
2. 现有自定义策略 `ThoradarCDNRefreshOnly` 只有 Action `cdn:RefreshObjectCaches`、Resource 主域。S10 已将它授予唯一实际发布 SubUser。
3. 当前本地工作流只刷新主域四地址，双域八地址验真；S7 等待已改前两次 5 秒、随后 40 秒，至少 370 秒，当前 18/18。

## A. RAM 精确续作
1. 新建 RAM 标签，打开现有 `ThoradarCDNRefreshOnly`，不得再创建第二个策略或新用户。读取 `D:/claude-tmp/thoradar-cdn-refresh-only.json` 获得同一主账号 ARN 形式；报告不得展开账号 ID。
2. 修改当前策略，使 JSON 仍只有一个 Statement、Effect=Allow、Action 数组仅 `cdn:RefreshObjectCaches`，Resource 数组恰好两项：`acs:cdn:*:<CDN_OWNER_ACCOUNT_ID>:domain/thoradar.online` 和 `acs:cdn:*:<CDN_OWNER_ACCOUNT_ID>:domain/www.thoradar.online`。不得加入 `*` 资源、其它动作或其它域名。
3. 若控制台生成新版本，确认新版本已成为当前/默认生效版本；只编辑不算生效。保存修改前正文到临时目录供回退，不入库、不打印账号 ID。
4. 重新打开策略详情，完整回读 JSON.parse 并机械全等校验两资源；再打开 S10 同一唯一 SubUser 权限列表，确认仍只绑定该自定义策略，原权限行不变，无新增其它策略。
5. 遇安全验证/短信/扫码立即停止云操作并保留标签，不重复提交；即使云侧被阻断，也继续完成下面本地修复，报告分开写云侧与本地终态。不得执行真实 CDN 刷新或发布。

## B. 本地双域发布修复
1. 将刷新 URL 集合改为现有 `urls` 的双域八地址，不再过滤主域；上传顺序、正常/退役 worker 映射、双域八地址验真、MIME/no-store 和至少 370 秒等待保持不变。更新过时的「www 不属本账号」注释。
2. `verify-deploy.mjs` 正常和退役场景必须断言一次刷新请求包含**恰好双域八地址且顺序与 urls 相同**，名称同步改为 eight owned CDN URLs。不得放松双域验真。
3. mock 按新现实允许双域刷新；不得删除失败场景、把错误改成成功或为赶绿调整预期。若无必要不改 mock。
4. 跑 `node tests/smooth/verify-deploy.mjs docs/tasks/T1128-SMOOTH/online-release/sol-s11/deploy.json`，需 18/18。保留 stdout/stderr。
5. 制作临时工作流变异，把刷新恢复成只主域四地址，用更新后的测试运行，正常+退役断言必须红；不得把变异覆盖正本。另保留至少一个既有错误场景证明仍能判红。记录变异命令、退出码和汇总。
6. `git diff --check` 针对本次代码；确认 `index.html`、`sw.js`、`sw-retire.js` 无 diff。不得 commit/push/deploy。

## 交付
报告含三行头、结论、地图影响、验证状态、改动清单、遗留风险、地图终态；分开列 RAM 云端状态（完成/挑战阻断）与本地状态（18/18＋负对照）。若 RAM 未完成，不得写双域发布可放行。尾部复述 `DELIVERY-T1128-SMOOTH-S11`。
