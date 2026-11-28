干了什么｜核对隔离工作树中的双域八地址刷新补丁，复跑 18 项发布模拟和两组负对照。RAM 控制台出现安全验证，现有策略尚未修改。\
PI 怎么亲手验｜打开本单的 `handoff-check/deploy.stdout.txt`，看到 `normal` 和 `retire` 两行 `PASS` 都写着 `refreshes eight owned CDN URLs`，且末行显示 18 项通过、0 项失败，即对。\
还剩什么坑｜RAM 标签已保留待 PI 处理安全验证。完成策略默认版本和发布子用户权限的回读前，双域发布暂缓放行。

# T1128-SMOOTH-S11 施工回执

按委任状 A、B 和法库安全红线执行。隔离工作树使用 `af3f2775855bb99aeb5c3262cb2738a889b60d70`，以主工作树当前三份发布文件的原样副本作为补丁基线。

## 结论

- **RAM 云端 · 安全验证阻断。** 本单前次执行新建专用 RAM 标签，首次页内读取返回 `{"op":"layout","challenge":true}`，退出码 3，随后保留标签。这次交付复验使用本地隔离副本，未重试控制台。策略编辑、默认版本和同一发布子用户的权限列表回读均待完成。本地模板已脱敏核对，策略目标仍为一个 `Allow`、`Action: ["cdn:RefreshObjectCaches"]` 和同一账号下 `domain/thoradar.online`、`domain/www.thoradar.online` 两项精确资源。S10 记录的两条现有权限行是续作的回读基线。
- **本地施工 · 18/18，负对照符合预期。** 正常和退役各提交一次刷新，`ObjectPath` 精确包含主域四项、`www` 四项，顺序与双域验真完全一致。测试记录显示第 12 次验真前累计模拟等待 370 秒。

## 验证状态

| 契约 | 节点 | 命令与原始输出 |
| --- | --- | --- |
| A.1–A.5 策略与发布子用户 | ⑧ RAM | [控制台观测](online-release/sol-s11/browser-observations.txt)，新建标签、首次读取和本地模板脱敏输出 |
| B.1–B.4 八地址刷新、验真和模拟 | ⑧ 发布接线 | [执行说明](online-release/sol-s11/local-verification.md)、[stdout](online-release/sol-s11/deploy.stdout.txt)、[stderr](online-release/sol-s11/deploy.stderr.txt)、[模拟 JSON](online-release/sol-s11/deploy.json)、[调用轨迹核验](online-release/sol-s11/trace-check.txt) |
| B.5 主域四地址负对照 | ⑧ 发布接线 | 退出码 1，16 项通过、2 项失败。正常和退役均在刷新参数全等断言处报告缺少四条 `www` URL。[stdout](online-release/sol-s11/apex-only.stdout.txt)、[stderr](online-release/sol-s11/apex-only.stderr.txt) |
| B.5 既有错误场景 | ⑧ 发布接线 | 正本的 `wrong-md5` 模拟发布进程退出 1。临时去掉 MD5 检查后，此发布进程退出 0，测试套件退出 1，并报告 `wrong-md5` 与陈旧内容轮询断言失败。[stdout](online-release/sol-s11/without-md5-gate.stdout.txt)、[stderr](online-release/sol-s11/without-md5-gate.stderr.txt)、[调用轨迹核验](online-release/sol-s11/trace-check.txt) |
| B.6 改动范围 | ⑧ 发布接线 | `git diff --check` 退出 0，主工作树和隔离工作树的三个产品文件均与 HEAD 无 diff，增量补丁在主工作树 `git apply --check` 退出 0。[Git 输出](online-release/sol-s11/scope-check.txt) |
| 本地复跑 | ⑧ 发布接线 | 正本退出 0，18/18。主域四地址和移除 MD5 检查两组变异各退出 1，均为 16/18。[正本](online-release/sol-s11/rerun/deploy.stdout.txt)、[主域变异](online-release/sol-s11/rerun/apex-only.stderr.txt)、[MD5 变异](online-release/sol-s11/rerun/without-md5-gate.stderr.txt)、[调用轨迹及范围复核](online-release/sol-s11/rerun/checks.txt) |
| 交付复验 | ⑧ 发布接线 | 复用既有隔离副本与 S11 补丁。正本退出 0，18/18。两组变异均退出 1，16/18。正常、退役各刷新一次，地址与验真同序，末次传播探测前累计等待 370 秒。[命令与退出码](online-release/sol-s11/local-verification.md)、[正本 stdout](online-release/sol-s11/handoff-check/deploy.stdout.txt)、[正本 stderr](online-release/sol-s11/handoff-check/deploy.stderr.txt)、[主域变异](online-release/sol-s11/handoff-check/apex-only.stderr.txt)、[MD5 变异](online-release/sol-s11/handoff-check/without-md5-gate.stderr.txt)、[调用轨迹](online-release/sol-s11/handoff-check/trace-check.txt)、[范围核验](online-release/sol-s11/handoff-check/scope-check.txt) |

## 改动清单

- `.github/workflows/deploy_oss.yml` 使用既有 `urls` 生成同一组八地址的 `ObjectPath`，并更新 CDN 账号归属注释。
- `tests/smooth/verify-deploy.mjs` 对正常和退役场景断言整条刷新请求的地址和顺序。已有 mock 支持两域，复用原实现。
- [增量补丁](online-release/sol-s11/dual-domain.patch) 只含上述两份代码的 S11 差异。本报告与证据均留在隔离工作树。

## 地图影响

⑧ 的本地发布接线已有回填证据，RAM 续作卡在安全验证。主工作树原有代码和任务地图由派遣方接收本单后处理。

## 地图终态

主工作树任务地图第 21 行是本单对应的⑧节点，本次读取的文件 blob 为 `0fed834852a3fdfdfe588b26faf1c1e9a1562d0f`，节点仍为 `in-progress-browser-repair`。[任务地图](../../../../../docs/tasks/T1128-SMOOTH/task-map.md)

## 遗留风险

真实发布和 CDN 刷新留待授权后的发布流程。本单本地证据仅覆盖模拟，当前出货闸仍取决于 RAM 安全验证以及 A.1–A.4 的实测。R3 独立复核回执由派遣方归口。

DELIVERY-T1128-SMOOTH-S11
我恢复了工作流的双域八地址刷新并完成模拟和负对照，RAM 安全验证阻断了策略变更和回读。
