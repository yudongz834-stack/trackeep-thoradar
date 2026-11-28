DELIVERY-T1128-SMOOTH-S7
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar-sol-cdn；任务号=T1128-SMOOTH-S7；交付=CDN 刷新失败的独立诊断、必要的本地修复和 PI 可执行处理单。
轨道位置：胸科雷达顺畅改造·⑧ 真实发布 CDN/RAM 阻断处理。
R级：R2（本地代码、测试和只读诊断；真实 RAM、OSS、CDN、push、deploy 不在本单授权内）。
判级理由：真实工作流已越过本机全部验证并完成 OSS 上传，当前需要修正发布配置诊断和最小授权方案；任何线上权限变更仍另属 R3。
签发：PI 原话「让codex gpt 6.2 sol看看怎么回事，让他操作」（2026-11-28）。本单把「操作」落实到隔离树代码、测试和公开只读诊断，不扩展为登录态、凭证或云端写权限。
地形：独立树基底 `af3f2775855bb99aeb5c3262cb2738a889b60d70`。可写 `.github/workflows/deploy_oss.yml`、`tests/smooth/`、`docs/tasks/T1128-SMOOTH/sol-s7*`；不得改首页、两件 worker、官方数据，不碰主仓工作树。
领域卡：无
经验卡：无卡。
Run 版本键：岗位卡=builder-jobspec 现役正本；model=gpt-6.2-sol；真实失败 run=`46129122449`、`46130068894`；当前主域刷新版发布模拟 18/18。

## 已确认事实（不要重新猜测或重复全套缓存测试）
1. `smooth-verify` 在真实 GitHub runner 已全部通过，真实 OSS 上传成功，两件 worker 和新首页已上传。
2. run `46129122449` 把双域 8 URL 放在同一刷新请求中，返回 `InvalidDomain.NotFound`：`www.thoradar.online` 不属当前 CDN 账号，整批失败。
3. 随后改成只向 `thoradar.online` 的 `/`、`/index.html`、`/sw.js`、`/sw-retire.js` 提交刷新，双域 8 URL 仍逐一验 MD5。run `46130068894` 返回 `Forbidden.RAM`，`AuthAction=cdn:RefreshObjectCaches`，发布用身份类型为 SubUser，属于隐式拒绝。不要引用账号 ID、EncodedDiagnosticMessage 或任何凭证。
4. 当前生产脚本保留了真实错误输出。主域刷新与双域验真的本地模拟 18/18；把 www 塞回刷新请求的负对照会红。
5. 真实 OSS 上传成功不等于 CDN 已更新；不得把当前线上状态称为验收通过。

## 你要做的事
1. 读当前工作流、`verify-deploy.mjs` 和上述事实，独立判断两个错误各自的根因，确认「主域刷新＋双域 MD5 验真」是否正确，尤其不得为迁就账号状态而放松 www 验证。
2. 用公开只读方式核对 RAM 最小权限：给出只许 `cdn:RefreshObjectCaches`、只覆盖 `thoradar.online` 的策略或控制台处理单。核对 `www` 的 DNS/公开响应，说明主域刷新后 www 是否可能共享更新；没有证据就明确留到实测，不猜。
3. 亲自跑发布模拟及至少一个针对本问题的负对照。若发现当前代码仍有实质问题，可在上述写域直接修复并跑全套 18 项；不要做无关重构，不要重复 S1/S2/S3/UX。
4. 给 PI 一份最短后续操作单：需要补什么 RAM 权限、授权后如何重发、www 若仍旧应如何处理。真实授权、真实刷新和重发只能由 PI 另行执行，本单不做。
5. 不 push、不 commit、不 deploy、不调用真实 OSS/CDN/RAM 写接口，不打开云端登录页，不读取或打印任何密钥。`gh` 只读日志可用，但报告不得复制账号 ID、诊断编码或个人信息。

交付 `D:/trackeep/trackeep-product/trackeep-thoradar-sol-cdn/docs/tasks/T1128-SMOOTH/sol-s7-report.md`，附命令、退出码、必要原始输出和 diff。报告含三行头、结论、地图影响、验证状态、改动清单、遗留风险、地图终态；最终尾部复述 `DELIVERY-T1128-SMOOTH-S7`。
