# T1128-SMOOTH 重启续作点

## 最终状态：已发布并完成本机线上验收
- PI 已亲手提交并推送 `2c43373aec098375edb9500b2b12e02cb12f2b06`，触发工作流 `46148918001`；`smooth-verify` 与 `deploy-oss` 均成功。
- 真实主域 CDN 刷新任务号 `33911284451`，部署日志末行 `Publish verified on both domains`。证据：`online-release/deploy-46148918001.json`、`deploy-46148918001.log`。
- `thoradar.online` 是唯一正式网站；`www.thoradar.online` 普通路径 301 到短域同路径同查询，`/sw.js` 与 `/sw-retire.js` 始终返回退役 worker、JavaScript MIME、no-store。
- 主控独立公网 10/10：`online-release/canonical-public-final.json`。
- 隔离 Chrome 初跑 8/1，仅根地址 HEAD 连接超时，五项实际浏览器行为均通过；完整复跑 9/9：`online-release/canonical-browser-final.json`、`canonical-browser-final-retry.json`。
- 已验冷首访原生打开并预热、复访 Cache Storage、后台核新不重载阅读页、离线当日副本、单页 `?sw=0` 退出和无未捕获异常。临时浏览器与 profile 已清理。

## 以后注意
- 不重发本次发布，不重复应用 S11/S12/S13 补丁；旧 S11 双域方案已废止。
- 真机/iOS、真实跨日和完整主域退役演练仍未完成，不得冒称已验。
- 完整主域退役会改变公开网站行为，必须由 PI 当次明确触发，不能夹在正常日报发布中。
- 公网有间歇连接失败；失败证据与成功复跑都保留，不宣称各地网络永远稳定。
- 发布日志中一次桶创建 403 后按既有流程跳过，随后现有桶上传、CDN 刷新和公网验真均成功；不要把它改写成“全程没有任何错误行”。
