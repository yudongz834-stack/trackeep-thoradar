DELIVERY-T1128-SMOOTH-S9
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar；任务号=T1128-SMOOTH-S9；交付=确认 `ThoradarCDNRefreshOnly` 是否已创建、避免重复创建、授予唯一实际发布子用户并双回读。
轨道位置：胸科雷达顺畅改造·⑧ 真实发布 RAM 阻断处理续作。
R级：R3（阿里云 RAM 最小权限创建/授权；不发布）。
判级理由：S8 提交创建后遇到安全验证，创建结果与授权均未确认；新开策略列表页当前无验证，需要先查证再续作。
签发：沿用 PI G14/G15 原话「你帮我做」「全部运行allow，不要我一直瘦点」「要不操作浏览器你让codex gpt 6.2 sol还有mimo 2.6 pro做？」。仅限 S8 已说明的最小权限，不扩大范围。
地形：只操作主控新建的 RAM 标签 `02478B1ABB4E3D9D0DC72BA41B53620E`（`https://ram.console.aliyun.com/policies`），不得操作 Mimo 的 CDN/DNS 标签或 PI 原有标签。报告只写 `docs/tasks/T1128-SMOOTH/sol-s9-browser-report.md` 与 `online-release/sol-s9/`；临时脚本只用 `D:/claude-tmp/sol-s9-*`，可只读参考 `sol-s8-console.mjs`。不改产品、工作流、测试、任务地图，不 commit/push/deploy。
领域卡：无
经验卡：无卡。
Run 版本键：岗位卡=builder-jobspec 现役正本；model=gpt-6.2-sol；失败 run=`46130068894`；S8 报告=`sol-s8-browser-report.md`。

## 已知事实与首要判据
1. S8 已在 Monaco 完整复制回读并 JSON.parse，白名单和源文件逐字相等后，提交 `ThoradarCDNRefreshOnly` 命名确认；下一次回读为 `security_challenge`。因此**创建可能已成功，也可能未写入，严禁不查就重复创建**。
2. 主控新建标签页已 `ready=complete`、`challenge=false`；这只代表当前列表页无验证，不代表后续提交不会再次触发。
3. 唯一允许策略：Effect=Allow，Action 仅 `cdn:RefreshObjectCaches`，Resource 仅 `<CDN_OWNER_ACCOUNT_ID>:domain/thoradar.online`。源文件 `D:/claude-tmp/thoradar-cdn-refresh-only.json`；报告不得复制账号 ID、用户名、主体或个人信息。
4. S8 的脱敏记录显示发布失败日志主体标识唯一且 owner 与策略文件一致；可用既有临时脚本和失败材料做精确匹配。不得因“看起来像”就授权错误用户，不得批量授权。

## 步骤
1. 在现有标签精确搜索 `ThoradarCDNRefreshOnly`。若已存在，打开详情并回读策略文本，白名单完全相等才继续；若内容不符，不修改、不授权，报告差异。若不存在，才按 S8 已验证的方法创建一次。
2. 如再次出现安全验证、短信、扫码、滑块或任何需要 PI 本人处理的挑战：立即停止，不读取/绕过验证，**保留该 RAM 标签页不要关闭**，报告 `security_challenge` 和已完成步骤。不要重复提交。
3. 创建/详情回读成功后，在 RAM 用户列表用失败日志中的唯一主体标识精确匹配实际发布 SubUser。若多个候选或无法机械确认，停止，不授权。
4. 只给该用户添加自定义策略 `ThoradarCDNRefreshOnly`，授权范围选账号级别，资源限制由策略自身限定；不得添加系统策略、CDNFullAccess、AdministratorAccess 或通配资源。
5. 成功后分别重新打开策略详情和该用户权限列表回读，确认策略内容、策略名称、授权对象三者一致。控制台 toast 不算最终回读。
6. 无安全挑战且完成后关闭本单 RAM 标签；若需留给 PI 验证则保持打开。不得执行 CDN 刷新、GitHub 重跑、push/deploy 或退役演练。

## 验收与交付
- 明确终态：A 策略创建+用户授权+双回读完成；B 策略存在但未授权；C 安全验证阻断；D 主体无法唯一确认。不得混报。
- 报告含三行头、结论、地图影响、验证状态、改动清单、遗留风险、地图终态，附脱敏回读证据和实际停止点。尾部复述 `DELIVERY-T1128-SMOOTH-S9`。
