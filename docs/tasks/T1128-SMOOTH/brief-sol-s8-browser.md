DELIVERY-T1128-SMOOTH-S8
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar；任务号=T1128-SMOOTH-S8；交付=RAM 最小权限策略创建、授予实际发布子用户、回读证据。
轨道位置：胸科雷达顺畅改造·⑧ 真实发布 RAM 阻断处理。
R级：R3（使用 PI 已登录的阿里云控制台，实际新增最小权限策略并授权；不做 Git 发布）。
判级理由：生产发布身份当前被 `cdn:RefreshObjectCaches` 隐式拒绝，必须由有权限的登录态完成最小授权；该动作改变云端权限，按生产变更处理。
签发：PI 原话「你帮我做」「全部运行allow，不要我一直瘦点」「要不操作浏览器你让codex gpt 6.2 sol还有mimo 2.6 pro做？」（2026-11-28）。本单允许 Sol 代做下述 RAM 控制台副作用，不扩展为全账号、全资源权限。
地形：只操作 PI 日常 Chrome 中主控自建的 RAM 标签页 `48EFF9133344B0869DF5A6CE6D213FE5`；不得操作其它已有标签。报告只写 `docs/tasks/T1128-SMOOTH/sol-s8-browser-report.md` 与 `online-release/sol-s8/`；临时脚本只用 `D:/claude-tmp/sol-s8-*`。不改产品、工作流、测试、任务地图，不 commit/push/deploy。
领域卡：无
经验卡：无卡。
Run 版本键：岗位卡=builder-jobspec 现役正本；model=gpt-6.2-sol；失败 run=`46130068894`；真实错误=`Forbidden.RAM`／`AuthAction=cdn:RefreshObjectCaches`／身份类型 SubUser。

## 目标与当前状态
1. 当前 RAM 创建自定义策略页已经切到「脚本编辑」，Monaco 编辑器存在；主控此前多次输入失败，**尚未提交策略，云端没有因这些失败产生变更**。不要重载丢失当前编辑器状态。
2. 唯一允许的策略正文在 `D:/claude-tmp/thoradar-cdn-refresh-only.json`。读取并原样使用，但报告、回复和证据不得复制主账号 ID、用户名、个人认证信息、登录凭证、密钥或完整诊断编码。可以记录动作、域名和占位符 `<CDN_OWNER_ACCOUNT_ID>`。
3. 权限必须恰好为 `Effect=Allow`、Action 仅 `cdn:RefreshObjectCaches`、Resource 仅该主账号下 `domain/thoradar.online`；不得选 `AliyunCDNFullAccess`、`*` 资源或其它管理动作。
4. 创建策略后，授予**实际发布使用的 RAM 子用户**。先通过现有 GitHub 工作流失败证据／控制台可读信息确认身份，不猜名字、不打印账号 ID；若存在多个候选且无法机械确认，停在该步并报告，不得批量授权。

## 操作方法
1. 先读 `D:/claude/skills/meta-web-access/SKILL.md` 与 `CONFIG.md`，遵守只操作自建标签、结束关闭自建标签、PHI/凭证零外发。Mimo 会另开 CDN 标签，你不要碰它的页面。
2. 可用 localhost:3456 CDP proxy；直接 CDP 时从 `%LOCALAPPDATA%/Google/Chrome/User Data/DevToolsActivePort` 取 WebSocket 路径，不依赖 `/json/version`。已有辅助脚本 `D:/claude-tmp/insert-ram-policy.mjs` 可参考但需自行核验，不要盲目运行后假定成功。
3. Monaco 需要真实激活与系统剪贴板粘贴；直接改 textarea 不会更新模型，`Input.insertText` 可能触发自动补括号。当前编辑器已激活，优先 `Browser.setClipboardContents`＋真实 Ctrl+A/Ctrl+V，再回读 Monaco 模型或可见文本。真实点击 `#policy-script-tab` 已证明可切换。
4. 提交前必须回读并 JSON.parse：只有一个完整对象，无多余括号，Action/Resource 与上述白名单完全相等，「确定」可用。校验不通过不得提交。
5. 创建后重新打开策略详情回读；授权后重新打开该子用户的权限列表回读。页面显示成功不等于回读验收成功。
6. 若遇短信/扫码/二次认证、账号主体/证件页面、收费或权限范围扩大，立即停手报告，不读取、不代填。

## 验收与交付
- 成功：最小策略已创建，且仅授予实际发布子用户；策略详情和用户权限列表均重新打开回读一致；证据去除账号 ID 和个人信息。
- 若只完成一部分，明确停在创建前／创建后未授权／授权后未回读哪一步，不冒称完成。
- 不执行 CDN 刷新、不重跑 GitHub Actions、不 push/deploy，不演练退役。
- 报告含三行头（干了什么／PI 怎么亲手验／还剩什么坑）、结论、地图影响、验证状态、改动清单、遗留风险、地图终态；附实际步骤、关键回读和失败点，尾部复述 `DELIVERY-T1128-SMOOTH-S8`。
