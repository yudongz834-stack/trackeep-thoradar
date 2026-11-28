DELIVERY-T1128-SMOOTH-M3
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar；任务号=T1128-SMOOTH-M3；交付=www 永久跳转短域，且两件 worker 永久保留退役入口，公开回读。
轨道位置：胸科雷达顺畅改造·⑧ 单正式域名收敛。
R级：R3（生产 CDN 配置；不做 Git 发布、不刷新 CDN）。
判级理由：PI 已选短域唯一、www 跳转。若把 www 所有路径一刀切跳转，旧 Service Worker 无法更新并会把老访客困在缓存中，必须先保留 worker 退役通道。
签发：PI 在方案选择中选定「短域唯一，www 跳转（推荐）」（2026-11-28，G18）。允许本次 www CDN 跳转和旧客户端退出迁移；不授权主域退役、DNS 变更、购买或 RAM 扩展。
地形：只操作自行新建的 www CDN 控制台标签，不碰主域、RAM、DNS 和 PI 其它标签。报告只写 `docs/tasks/T1128-SMOOTH/mimo-m3-canonical-report.md` 与 `online-release/mimo-m3/`；临时脚本 `D:/claude-tmp/mimo-m3-*`。不改代码、测试、工作流、任务地图，不 commit/push/deploy。
领域卡：无
经验卡：无卡。
Run 版本键：model=mimo-v2.6-pro[1m]；M2 www 接入=`mimo-m2-browser-report.md`；当前 Git blob MD5：正常 `sw.js=nrgKbeazqBXvILkgAlssIg==`，退役 `sw-retire.js=xviHOEexQQLp0q41sv2uuA==`。

## 目标线上契约
1. `https://www.thoradar.online/`、`/index.html` 以及其它普通路径：返回 301（或 308）到 `https://thoradar.online` 的**同路径、同查询参数**，不得跳到其它主机，不得丢失 `?sw=0` 等查询。
2. 两个例外长期保留，不得被 301 覆盖：
   - `https://www.thoradar.online/sw.js` 必须 200、JavaScript、`Cache-Control:no-store`，正文 MD5 等于 **`sw-retire.js`** 的 `xviHOEexQQLp0q41sv2uuA==`。
   - `https://www.thoradar.online/sw-retire.js` 同样 200、JavaScript、no-store、上述退役 MD5。
3. 主域四地址不得变化：根/index 为当前首页 MD5，主域 `/sw.js` 仍为正常 worker MD5，主域 `/sw-retire.js` 为退役 MD5。
4. 这样新访客直接 301；已有旧 www worker 的访客仍能从 `/sw.js` 获得退役版，清掉旧副本后下次访问跳转。不得删除这个例外来追求表面简洁。

## 操作顺序（防半截迁移）
1. 先读 webaccess SKILL/CONFIG；无视觉，只用 DOM/机读状态，不 Read 截图。保存 www 当前配置与主域公开基线。
2. **先配置并公开验证两个 worker 例外**：www `/sw.js` 通过回源 URI 改写或等价机制直接返回 OSS 的 `sw-retire.js`，不是跨域 301/302；www `/sw-retire.js` 保持退役件。两件均 no-store、JS MIME。若控制台不能精确实现两条例外，停止，不进入普通路径跳转。
3. worker 例外公开回读成功后，才配置其它 www 路径的永久跳转。保留路径和查询，目标只能是 `https://thoradar.online`。不要改主域、源站、DNS、证书、计费或其它域名。
4. 若任一步只能做到“全域包括 worker 一起跳转”，立即停止并尽可能恢复到本单前状态；不得接受旧客户端无法升级的方案。已发生的部分变更逐项报告。
5. 不执行 CDN 刷新，等待控制台配置自然传播并轮询。不得用本机 hosts/代理规则伪造公网结果。
6. 最终验证：www 根/index/一个带查询样本为 301/308 且 Location 精确；www 两 worker 为退役 MD5+JS+no-store；主域四地址未退化。记录每次退出码、状态和响应头，报告截图裁掉账号/个人信息。结束关闭自建标签。

## 验收与交付
- 终态明确：A 全部公开契约通过；B 仅 worker 例外完成、跳转未做；C 无法支持例外且零跳转；D 部分变更待回滚。不得只凭控制台“已开启”报完成。
- 报告含三行头、结论、地图影响、验证状态、改动清单、遗留风险、地图终态，附可回滚的原配置。尾部复述 `DELIVERY-T1128-SMOOTH-M3`。
