**干了什么**　回读了 RAM 自定义策略 `ThoradarCDNRefreshOnly` 的当前版本，只为失败日志精确匹配的发布子用户新增了一条账号级授权，并完成了两项回读。\
**PI 怎么亲手验**　在发布子用户的 RAM「权限管理 → 个人权限」里点开账号级 `ThoradarCDNRefreshOnly`，策略内容只显示对 `thoradar.online` 的缓存刷新权限即对。\
**还剩什么坑**　真实发布链路仍待独立验证，本单验收覆盖 RAM 授权。

## 结论

**A 双回读完成。** 指定 RAM 标签完成全部核验后已关闭。控制台未出现新的安全验证。

## 验证状态

| 验收项 | 脱敏回读 |
| --- | --- |
| 策略正文 | 授权前后分别打开策略详情的「策略内容 → 源代码」。两次均从当前版本读取完整 JSON，`JSON.parse` 通过，字段集合一致。版本为 `1`，唯一语句为 `Allow`，唯一动作是 `cdn:RefreshObjectCaches`，唯一资源是 `acs:cdn:*:<CDN_OWNER_ACCOUNT_ID>:domain/thoradar.online`。 |
| 发布主体 | 从失败 run `46130068894` 的 `Forbidden.RAM` 材料提取出唯一的 `SubUser` UID。所属账号与策略源文件一致。RAM 用户列表只有一个精确匹配的详情链接，打开后，页面的用户 UID 字段与详情路由的 `userId` 均与日志精确相等。阿里云将此错误字段对 RAM 用户定义为 UID。 [阿里云 RAM 鉴权失败字段说明](https://www.alibabacloud.com/help/zh/ram/support/how-to-troubleshoot-an-access-denied-error) |
| 授权提交 | 从该用户详情打开新增授权。保留账号级别，筛选自定义策略，精确选中 `ThoradarCDNRefreshOnly` 一条，点击确认一次。 |
| 用户权限回读 | 从用户列表重新打开同一 UID 的用户，再进入「权限管理 → 个人权限」。无筛选、无其他页。总数由 1 变为 2，既有行比对一致，唯一新增行的策略类型为 Custom，资源范围为账号级。 |
| 标签关闭 | 关闭指令成功。延迟复查浏览器目标列表，指定标签已消失。 |

[操作命令与脱敏原始输出](online-release/sol-s10/browser-observations.txt)

## 改动清单

- 云端新增一条直接授权，将现有自定义策略 `ThoradarCDNRefreshOnly` 绑定到精确匹配的发布子用户。
- 本地交付本报告及 `online-release/sol-s10/browser-observations.txt`。

## 地图影响与终态

第⑧项的 RAM 最小权限子项达到 **A 双回读完成**。现有任务地图记录为 `in-progress-browser-repair`，派遣方可据本报告回填 RAM 子项实证。

## 遗留风险

真实发布 run 是否会通过 CDN 刷新步骤，仍待另行验证。

DELIVERY-T1128-SMOOTH-S10
我回读了最小策略正文，仅为精确匹配的发布子用户授权一次，并在重新打开的用户权限列表和策略详情中完成双回读。
