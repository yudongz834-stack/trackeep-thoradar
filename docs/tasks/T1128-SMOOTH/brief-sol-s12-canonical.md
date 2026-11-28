DELIVERY-T1128-SMOOTH-S12
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar；任务号=T1128-SMOOTH-S12；交付=单正式域名发布工作流、www 跳转与退役 worker 验真、全套模拟和负对照。
轨道位置：胸科雷达顺畅改造·⑧ 单正式域名发布接线。
R级：R2（本地发布工作流/测试；真实 CDN 由 Mimo 另单，push/deploy 唯 PI）。
判级理由：PI 已将方案从双域独立内容改为短域唯一、www 永久跳转；旧 S11 双域刷新补丁不适用。
签发：PI 方案选择「短域唯一，www 跳转（推荐）」（2026-11-28，G18）。不加 www 刷新权限，不应用旧 S11，主域正常加速不变，www worker 保留退役入口。
地形：可写 `.github/workflows/deploy_oss.yml`、`tests/smooth/verify-deploy.mjs`、必要的 `tests/smooth/deploy-mock.mjs`、`docs/tasks/T1128-SMOOTH/release-contract.md`、`docs/tasks/T1128-SMOOTH/sol-s12*` 与 `online-release/sol-s12/`。不得改三件产品、官方数据、其它测试或任务地图。代码和测试证据在隔离副本施工；**最终报告直接写主树唯一预期路径 `docs/tasks/T1128-SMOOTH/sol-s12-canonical-report.md`**，避免再发生报告位置导致的重发。不得写主树其它文件；补丁由主控整合。
领域卡：无
经验卡：无卡。
Run 版本键：model=gpt-6.2-sol；主树当前只有 S7 等待补丁，旧 S11 未应用；M3 目标线上契约见 `brief-mimo-m3-canonical.md`。

## 目标发布模型
1. OSS 上传顺序不变；主域 `/sw.js` 正常模式等于 `sw.js`、主域退役模式等于 `sw-retire.js`，首页最后上传，worker no-store。
2. CDN 刷新只含主域四地址，**不得包含 www**。S7 前两次 5 秒、随后 40 秒、至少 370 秒等待不变。
3. 发布后验真分两类：
   - 主域根/index/两 worker：HTTP 200、对应 Git MD5，worker JS/no-store。
   - www 根和 `/index.html`：301 或 308，Location 必须是短域同路径；另加一个带 `?from=www` 样本，查询不得丢失。不得再要求 www 首页与主域同 MD5。
   - www `/sw.js` 和 `/sw-retire.js`：无论正常还是主域退役发布，始终 200、**退役 worker MD5**、JS/no-store，不得跟随跳转。www 的正常缓存入口永久退役，用于旧客户端迁移。
4. `Publish verified on both domains` 可保留，但其含义变为短域内容＋www 跳转/迁移全通过。双源站预检可保留，不得替代公网验证。

## 本地施工与测试
1. 不应用 S11 双域补丁。更新工作流和测试注释/合同，清楚记录主域刷新、www 跳转、www 两 worker 永远退役。
2. 修改 mock 模拟上述新现实；正常和退役都断言一次刷新请求恰好主域四地址，www 跳转不写刷新请求。不得删除现有上传顺序、错误、MIME/no-store、传播等待检查。
3. 至少保留/新增这些负对照，均须真的判红：
   - 把 www 塞回刷新请求。
   - www 根/index 错返 200 同内容，或错误 Location/非永久状态/丢查询。
   - www `/sw.js` 错映射为正常 worker 而非退役 worker。
   - 既有 wrong-md5 撤防仍能抓错误放行。
4. 六分钟传播场景继续有效；www `/sw.js` 陈旧或变成普通内容必须不能误判为退役 MD5。
5. 跑完整发布模拟并保存真实汇总（项数由新增测试决定，不硬凑 18）。保存正本 stdout/stderr/JSON、各变异命令/退出码/汇总。确认三件产品无 diff、`git diff --check`、主树 `git apply --check`。
6. 不做真实浏览器操作、不改 CDN/RAM、不刷新、不 commit/push/deploy。若 M3 未回，不冒称线上可发布；本地和云端状态分开。

## 交付
报告含三行头、结论、地图影响、验证状态、改动清单、遗留风险、地图终态，附完整增量补丁。尾部复述 `DELIVERY-T1128-SMOOTH-S12`。
