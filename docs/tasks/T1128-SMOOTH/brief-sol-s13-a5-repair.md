DELIVERY-T1128-SMOOTH-S13
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar；任务号=T1128-SMOOTH-S13；交付=Astra A5 三项发现的原样修复与区分力验证。
轨道位置：胸科雷达顺畅改造·⑧ 单正式域名发布候选返修。
R级：R2（本地工作流/测试修复；不真实外呼、不发布）。
判级理由：A5 独立复核发现 Git blob 验真偏差、错主机回归缺口和首页 MIME 放行。按一决策一审，修复不再送审，但必须用 A5 原样本关闭。
签发：PI G18 单域方案及 A5 报告 `astra-v5/report.md`；不扩大线上授权。
地形：主树已整合 S12。代码在隔离副本施工，可写 `.github/workflows/deploy_oss.yml`、`tests/smooth/verify-deploy.mjs`、`tests/smooth/deploy-mock.mjs`、`docs/tasks/T1128-SMOOTH/release-contract.md` 与本单证据。不得改三件产品、官方数据、其它测试或任务地图。最终报告直接写主树 `docs/tasks/T1128-SMOOTH/sol-s13-a5-repair-report.md`，补丁与证据由主控整合。
领域卡：无
经验卡：无卡。
Run 版本键：model=gpt-6.2-sol；A5=`astra-v5/report.md`、`focused.json`、`skip-host.diff`、`audit.txt`；S12 主控 27/27=`online-release/main-s12-deploy.json`。

## A5 必须关闭的三项
1. **高：MD5 必须绑定发布提交的 Git blob。** 工作流不能用检出文件 `openssl dgst ... "$source"` 直接算期望。改为从同一 `HEAD:<path>` 的原始字节计算，并保证 git 读取失败会判红。模拟器健康响应也要以 Git blob 为源，不得继续让检出 CRLF 与期望值相互掩盖。
2. **中：错主机必须有专门回归。** 新增 `https://other.invalid/?from=www` 或等价响应，正本必须判红；若撤掉主机比较，套件也必须因该场景放行而判红。保留既有错路径和丢查询。
3. **首页 MIME：短域根/index 必须是 text/html。** 正确 MD5＋`application/octet-stream` 必须重试后判红；www 跳转不以 HTML MIME 判断，worker 仍 JS/no-store。同步合同。

## 强制验证
1. 新增一个“CRLF 检出仍按 Git blob 验真”的场景：故意让检出首页/worker 与 blob 换行不同，健康响应来自 Git blob。旧逻辑必须失败，新逻辑通过；不能用把两边都改成 CRLF 的方式制造绿。
2. 跑完整发布模拟，保存实际汇总。跑 A5 的错主机和首页 MIME 原样本，以及既有 wrong-md5、www-active-worker、302、www 塞回刷新、六分钟传播等负对照，证明没有为修 A5 放松其它闸。
3. 至少做一个撤掉 Git blob 读取的变异，证明 CRLF 场景会抓住；做一个撤掉主机比较的变异，证明错主机场景会抓住；做一个首页 octet-stream 样本证明判红。
4. `git diff --check`、三件产品无 diff、补丁在主树 `git apply --check`。不做真实浏览器/CDN/RAM，不 commit/push/deploy。
5. 报告含三行头、结论、地图影响、验证状态、改动清单、遗留风险、地图终态；逐项对应 A5 发现给原样本结果，不把模拟称为线上验收。尾部复述 `DELIVERY-T1128-SMOOTH-S13`。
