DELIVERY-T1128-SMOOTH-S10
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar；任务号=T1128-SMOOTH-S10；交付=已创建最小策略的正文回读、唯一发布子用户授权、用户权限列表回读。
轨道位置：胸科雷达顺畅改造·⑧ 真实发布 RAM 阻断处理最终续作。
R级：R3（RAM 授权；不发布）。
判级理由：PI 已完成安全验证，策略详情路由已可见，需要完成最小权限与授权验收。
签发：PI 原话「验证好」（2026-11-28），确认已亲手完成 S9 留下的安全验证；沿用 G14/G15 浏览器代操作与最小权限边界。
地形：只操作 RAM 标签 `02478B1ABB4E3D9D0DC72BA41B53620E`，不得操作 Mimo 的 CDN/DNS 标签或 PI 原有标签。报告只写 `docs/tasks/T1128-SMOOTH/sol-s10-browser-report.md` 与 `online-release/sol-s10/`；临时脚本只用 `D:/claude-tmp/sol-s10-*`，可只读参考 S8/S9。不得改代码、测试、工作流、任务地图，不 commit/push/deploy。
领域卡：无
经验卡：无卡。
Run 版本键：岗位卡=builder-jobspec 现役正本；model=gpt-6.2-sol；失败 run=`46130068894`；S9=`sol-s9-browser-report.md`。

## 当前已核实状态
1. PI 验证后，主控只读回读：`challenge=false`、`policyVisible=true`，URL 已为 `https://ram.console.aliyun.com/policies/detail?policyType=Custom&policyName=ThoradarCDNRefreshOnly`。这证明策略详情可打开；**不再创建策略**。
2. 尚需验证策略正文恰好为：Effect=Allow，Action 仅 `cdn:RefreshObjectCaches`，Resource 仅 `<CDN_OWNER_ACCOUNT_ID>:domain/thoradar.online`。若正文不符，停止，不授权、不修改，报告差异。
3. 失败日志主体标识唯一且 owner 与策略源文件一致；用 S8/S9 临时材料精确匹配实际发布 SubUser。报告、日志、截图不得展开账号 ID、用户名、个人主体或联系方式。

## 步骤与验收
1. 在当前详情页回读策略正文并 JSON.parse/白名单全等校验，保存脱敏证据。
2. 进入 RAM 用户列表，按失败日志唯一主体标识机械匹配。多个候选或无法确认就停止，不批量授权。
3. 仅给该用户添加自定义策略 `ThoradarCDNRefreshOnly`，账号级授权，资源由策略自身限制；不加系统策略、CDNFullAccess、AdministratorAccess 或通配资源。
4. 提交后重新打开该用户权限列表，确认只有本次新增的这一条目标授权；再回策略详情确认内容未变。toast 不等于回读。
5. 若再遇安全验证/短信/扫码，停止并保留标签，不重复提交授权。完成后无挑战则关闭本单 RAM 标签。
6. 不执行 CDN 刷新、GitHub 重跑、push/deploy、退役演练。

报告含三行头、结论、地图影响、验证状态、改动清单、遗留风险、地图终态；终态只能是 A 双回读完成／B 策略正文异常／C 主体不唯一／D 新安全挑战，并附脱敏证据。尾部复述 `DELIVERY-T1128-SMOOTH-S10`。
