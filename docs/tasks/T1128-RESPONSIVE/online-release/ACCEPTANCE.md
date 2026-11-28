# T1128-RESPONSIVE 线上验收

**结论：响应式候选已上线，主控线上验收通过。**

- PI 发布提交：`c3c49d4c4dcd25d2a9efc2ac809f356a3e2659c8`。
- 工作流：`46156893720`；`smooth-verify` 与 `deploy-oss` 均成功。
- 主域 CDN 刷新任务：`33911709559`；日志末行 `Publish verified on both domains`。证据：`deploy-46156893720.json`、`deploy-46156893720.log`。
- 新首页 Git blob Content-MD5：`Urkv8Ixj5WPB4NVyESmg4g==`，主域根路径和 `/index.html` 均一致。

## 主控独立线上结果

| 范围 | 结果 | 证据 |
|---|---|---|
| 公网文件与域名合同 | 10/10：主域四地址、www 四跳转、www 两退役 worker | `public-final.json`、`verify-public-final.mjs` |
| 主域本地副本行为 | 9/9：四头信息、冷首访、复访、后台核新不重载、离线、`?sw=0`、无异常 | `browser-final.json` |
| 线上响应式布局 | 4/4：1422×800、2134×1073、901×1000、390×844 | `live-viewports.json`、`verify-live-viewports.mjs` |
| 线上截图目检 | 两块目标屏新版布局已核；雷达利用空间、正文未缩、无裁切 | `live/1422x800-overview.png`、`live/2134x1073-overview.png` |

线上实测盘径：1422 为 477.703px、2134 为 620px、901 为 284px、390 为 370px；四档均无横向页面溢出、无出界标签，43 篇数据和 36 个雷达点完整。

## 边界

- 本轮仍未做两块物理屏之间拖窗、真机/iOS 或所有设备验收；线上尺寸为真实网站在隔离 Chrome 中的视口重放。
- 部署日志仍有一次既有“桶创建 403 后跳过”的错误行，随后现有桶上传、刷新和公网验真全部成功，不写成日志零错误。
- `www` 永久跳转和退役入口未退化，个人 localStorage 未清理。
