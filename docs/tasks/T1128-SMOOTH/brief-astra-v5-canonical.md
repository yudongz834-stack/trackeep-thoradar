DELIVERY-T1128-SMOOTH-A5
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar；任务号=T1128-SMOOTH-A5；交付=G18 单正式域名发布候选的独立只读复核。
轨道位置：胸科雷达顺畅改造·⑧ 单正式域名发布候选独立复核。
R级：R2（发布工作流与验收代码独立复核；只读产品，不写代码，不真实外呼云端）。
判级理由：主发布链和 CDN 验真规则改变，必须由未参与施工的新会话独立重跑和检查负对照。
签发：PI G18「短域唯一，www 跳转（推荐）」；按一决策一审，本单是该方向唯一独立复核，修复不再循环送审。
地形：主树已整合 Sol S12 并由主控复跑 27/27。复核写域仅 `docs/tasks/T1128-SMOOTH/astra-v5/` 与系统临时目录；不得改产品、工作流、测试、合同、旧证据或任务地图。真实 CDN/RAM 不在本单。
领域卡：无
经验卡：无卡。
Run 版本键：model=gpt-6.2-astra；被审报告=`sol-s12-canonical-report.md`；被审补丁=`online-release/sol-s12/canonical.patch`；主控结果=`online-release/main-s12-deploy.json`；S12 证据=`online-release/sol-s12/`。

## 独立判据
1. 主域四地址才是每日刷新对象，www 不得混入刷新；正常/退役上传顺序和主域 worker 映射不变。
2. 主域四地址按 Git blob MD5 验真；www 根/index/带查询样本必须是 301/308 到短域同路径同查询，不能 200 同内容、302、错主机或丢查询。
3. www `/sw.js` 与 `/sw-retire.js` 在两种发布模式下都必须直接 200 退役 MD5、JS/no-store，不能是正常 worker、HTML 或跳转。这个例外用于旧 www 客户端退出，不得误删。
4. S7 至少 370 秒传播等待仍有效；worker 上传失败必须阻止首页和刷新；坏 MD5/MIME/状态/网络错误均判红。
5. 本地模拟与真实线上状态分开；M3 未回前不得写生产放行。

## 你要做的事
1. 亲自阅读当前 `.github/workflows/deploy_oss.yml`、`tests/smooth/verify-deploy.mjs`、`deploy-mock.mjs` 和 `release-contract.md`，不要只信 Sol 摘要。检查上述逻辑和潜在漏判。
2. 用新输出路径在 `astra-v5/` 亲自跑当前发布模拟，记录退出码与完整汇总。
3. 至少选两组关键变异独立重跑：www 允许 200/302 或错 Location，www 使用正常 worker，或把 www 塞回刷新。确认失败确实来自对应断言，不是测试辅助错误。
4. 检查三件产品未改、补丁范围、报告链接和证据真实性。若发现问题，给文件/行号、最小复现和严重度；没有发现也要写已覆盖角度与未验范围。
5. 不做真实浏览器/CDN/RAM 操作，不触发发布，不 commit/push。最终报告直接写 `docs/tasks/T1128-SMOOTH/astra-v5/report.md`，含三行头、结论、发现项、验证状态、未验范围、地图影响，尾部复述 `DELIVERY-T1128-SMOOTH-A5`。
