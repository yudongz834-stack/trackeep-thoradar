# T1128-BRANDING 线上验收

**结论：Thoradar 品牌与页脚精简已上线，主控线上验收通过。**

- PI 发布提交：`19d8005f617d23cca745911d2ce8deec10edad78`。
- 工作流：`46165264331`；预检与部署均成功。
- 主域 CDN 刷新任务：`33912124596`；日志末行 `Publish verified on both domains`。
- 新首页 Content-MD5：`rC5sZ6dh1b23k0NTPM5VaA==`。

## 主控结果

| 范围 | 结果 | 证据 |
|---|---|---|
| 公网文件与域名 | 首轮 9/1，仅 www 任意路径连接超时；保留原始结果，完整复跑 10/10 | `public-final-attempt1.json`、`public-final.json` |
| 本地副本行为 | 9/9：冷首访、复访、后台核新不重载、离线、`?sw=0`、无异常 | `browser-shell-final.json` |
| 线上中英文品牌 | 8/8：四档视口×中英文，品牌/标题/副标题精确对应，顶栏不重叠、页面不横溢、页脚删除、备案可见 | `browser-final.json`、`verify-brand-browser.mjs` |
| 线上截图目检 | 1422 中文与 390 英文截图确认新文案和页脚 | `screens/` |

线上中文为 `Thoradar`＋`胸科医学文献 · 每日扫描与个性化追踪`；英文为 `Thoradar`＋`Thoracic Medical Literature · Daily Scanning and Personalized Tracking`。旧页脚不再出现，快捷键与备案链接保留。

## 边界
- 公网仍有间歇连接失败，首轮 9/1 未删改，复跑全绿不冒称网络永远稳定。
- 部署日志仍有既有建桶 403 后跳过的记录，随后上传、刷新和验真成功。
- 线上尺寸为真实网站在隔离 Chrome 中重放，未做物理双屏拖窗或真机/iOS 验收。
