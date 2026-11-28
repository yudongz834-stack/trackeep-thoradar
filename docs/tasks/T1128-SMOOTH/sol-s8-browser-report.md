**干了什么**　把 `ThoradarCDNRefreshOnly` 的策略脚本粘贴到 RAM，回读验证后提交创建。控制台随后触发安全验证。  
**PI 怎么亲手验**　在阿里云 RAM「权限策略」中搜索并打开 `ThoradarCDNRefreshOnly`，详情只显示 `Allow`、`cdn:RefreshObjectCaches` 和 `domain/thoradar.online` 即可确认策略已创建。  
**还剩什么坑**　创建是否写入云端尚未确认，实际发布子用户的授权和权限列表回读均未执行。

## 结论与验证状态

本单停在**创建确认已提交，云端结果未回读**。点击命名窗口的「确定」后，下一次控制台回读返回 `security_challenge`。按委任状停止操作，未读取或处理验证内容。临时 RAM 标签页已关闭。

| 验收项 | 结果 |
| --- | --- |
| 发布失败基线 | run `46130068894` 对应的本地失败材料包含 `Forbidden.RAM`、`cdn:RefreshObjectCaches`、`SubUser` 和 `ImplicitDeny`。拒绝日志中的主体标识唯一，主账号与策略文件一致。 |
| 提交前策略正文 | 从 Monaco 全选复制回读，两次通过 `JSON.parse`、白名单及源文件文本比对。仅一条 `Allow`，一个动作 `cdn:RefreshObjectCaches`，一个资源 `acs:cdn:*:<CDN_OWNER_ACCOUNT_ID>:domain/thoradar.online`。脚本页和命名弹窗的「确定」各验证为可用后点击。 |
| 创建后详情 | 未回读。命名弹窗提交动作已发出，安全验证出现后无法确认是否创建。 |
| 授权主体与权限列表 | 未进入 RAM 用户列表做精确匹配，未执行授权，未打开授权后的权限列表。 |
| 真实发布 | 本轮未触发 CDN 刷新、GitHub Actions 重跑或部署，权限修复能否解除发布阻断仍待验。 |

域名级 ARN 格式与阿里云为该动作列出的资源类型一致。 [阿里云 RefreshObjectCaches 文档](https://www.alibabacloud.com/help/en/cdn/developer-reference/api-cdn-2018-05-10-refreshobjectcaches)

## 实际步骤与失败点

1. 直连 `DevToolsActivePort` 的 WebSocket 握手超时，切换到现有本机 CDP 代理。代理回读确认指定标签页在 RAM 策略创建路由，脚本编辑器仍在。
2. 代理的真实点击让 Monaco 获得页内焦点，Windows 前台窗口仍不匹配。通过桌面控制激活唯一匹配的 Chrome 窗口后，用系统剪贴板和真实键盘快捷键完成粘贴、复制与回读。Monaco 只渲染部分行，因此提交校验使用完整复制文本。
3. 提交已校验的脚本，在命名弹窗填入 `ThoradarCDNRefreshOnly` 并点击「确定」。安全验证拦截详情回读。关闭指定标签成功，关闭后代理无法再读取该目标。

[实际命令及脱敏输出](online-release/sol-s8/browser-observations.txt)

## 改动清单与地图终态

- 云端操作到策略创建确认，落库状态待 PI 核对。授权动作尚未发生。
- 本地交付本文及 `online-release/sol-s8/browser-observations.txt`。
- 任务地图第⑧项记录为 `in-progress-browser-repair`。本单的证据只能支持「创建结果待确认」，授权验收缺两项，分别是详情的最小权限回读及唯一发布子用户的权限列表回读。
- 遗留风险是重新进入控制台后可能仍需 PI 处理安全验证。先搜索策略名称确认是否已创建，再决定是否需要重新提交。

DELIVERY-T1128-SMOOTH-S8
我核验并提交了胸科雷达 CDN 最小权限策略，控制台安全验证阻断了创建回读和子用户授权。

