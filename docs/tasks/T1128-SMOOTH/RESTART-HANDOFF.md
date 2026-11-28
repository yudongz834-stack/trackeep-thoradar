# T1128-SMOOTH 重启续作点

## 当前决定
- G18 已由 PI 拍板：`thoradar.online` 为唯一正式网站，`www.thoradar.online` 永久跳转并保留路径/查询。
- 不应用旧 S11 双域刷新补丁，不增加 www 每日刷新权限。
- www `/sw.js` 与 `/sw-retire.js` 始终返回退役 worker、JavaScript MIME、no-store，供旧客户端清缓存和注销；普通路径才 301/308 到短域。
- 主域正常加速不变；完整主域退役演练未授权。

## 发布前候选已齐
- 分支 `T1128-SMOOTH-RELEASE`，公开 HEAD 仍为 `af3f2775855bb99aeb5c3262cb2738a889b60d70`；最终候选已保存在工作树，尚未提交、未推送。
- S13 已整合主树：主控发布模拟 32/32、源码 5/5，Astra A5 三项均按原样本关闭。证据：`online-release/main-s13-deploy.json`、`main-s13-source.json`、`sol-s13-a5-repair-report.md`。
- Mimo M3 已完成生产配置：www 普通路径 301 到短域同路径同查询，两 worker 均为退役 MD5、JS/no-store，主域未退化。派遣身份闸退出 8，不记闸全绿；实际结果以 `mimo-m3-canonical-report.md` 和主控公网证据为准。
- 主控公网初跑 9/10，唯一失败是 `www/?from=www` 连接超时；补跑取得正确 301。证据：`online-release/canonical-public-current.json`、`canonical-public-current-retry.txt`。
- 真实旧 www 客户端迁移已完成：旧缓存打开、worker 注销、壳缓存清空、个人标记保留，下次到短域且数据完整。原始探针 3/1 未改，缺记重定向事件；与独立 301 联合裁定 4/0。证据：`online-release/www-legacy-migration-v3.json`、`www-legacy-migration-review.json`。
- 临时旧客户端 Chrome profile 和测试 Chrome 已清理，不需要重启后恢复。

## 重启后只做这些
1. 先 `git status --short --branch`，确认未提交候选仍在；不要重复应用 S11/S12/S13 补丁。
2. 最终发布命令见 `RELEASE-REPORT.md` 末节；只交给 PI 亲手执行，主控不得代为提交、推送或触发部署。
3. PI 发布后检查真实工作流和 CDN 刷新回执，不能把“触发成功”当作“网站已更新”。
4. 发布后核对主域四地址、www 三个跳转样本和两个退役入口，再复测主域冷首访、复访本地先开、后台核新、离线和 `?sw=0`。
5. 真机/iOS、真实跨日和完整主域退役演练仍未完成；完整主域退役会改变公开网站行为，必须由 PI 当次明确触发。
6. 如需浏览器调试，自动 Allow 守窗可用 `pwsh -NoProfile -ExecutionPolicy Bypass -File D:/claude-tmp/allow-clicker.ps1`；只操作本任务新建标签，不碰 PI 原标签。
