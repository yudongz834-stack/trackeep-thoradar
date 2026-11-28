DELIVERY-T1128-SMOOTH-V2
键字段：目标目录=D:/trackeep/trackeep-product/trackeep-thoradar-neon-v1；任务号=T1128-SMOOTH-V2；交付=S3 修复独立复验与旧回归补跑证据。
轨道位置：胸科雷达顺畅改造·④ Neon V2 返修后独立复验。
R级：R2
判级理由：复核 Service Worker 缓存污染阻断项的修复；只验本机候选，不发布。
签发：PI 原话「算了，现在直接执行吧，不重启了」（2026-11-28）及「加快速度」「快点，做快一点啦！」；只做返修复验，不扩需求。
地形：被审 S3 工作树零写入；独立树 `D:/trackeep/trackeep-product/trackeep-thoradar-neon-v1`；重点为空标记无 SITE_DATA 的 156B 毒壳及 V1 全部对抗样本。
领域卡：无
经验卡：无卡。
Run 版本键：岗位卡=verifier-jobspec 现役正本；轨道版本=T1128-SMOOTH v1；候选版本=S3 当前落盘哈希（复核方亲自计算并与施工树核对）。

## 独立性与写域
新会话，只找错不施工。先亲自跑，再读 S3 总结。只可写独立树和 `D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/neon-v2/`；被审 S3 树、主仓产品文件、旧测试、验收合同、任务地图零写入。不得改测试预期来放行。

## 必做
1. 从 V1 复制 `tests/neon-v1-verify.mjs` 到本独立树（主控已复制也可），原样运行：四类异常（倒序、错误 MIME、503、空标记坏壳）必须全部拒绝覆盖；三项负对照仍须变红。特别确认下一次导航不再出现 `date:null / points:0`。
2. 查 S3 新增的缺 SITE_DATA、坏 JSON、字段类型错与合法零篇样本；合法零篇不得被误拒。亲自重跑 S1、S2 和 UX，保存原始输出。
3. 直接运行旧回归，不经过已发现 ENOENT 的封装：
   `node tests/aicls/aicls_regress.mjs --target index.html --baseline 73dd34e --label neonv2`
   `node tests/poolup/poolup_regress.mjs --target index.html --baseline 73dd34e --label neonv2`
   保存退出码和原始输出。R08 若仍因两侧 0 篇失真，明确写未验，不把 39/40 写成全绿；检查除该步外是否还有候选差异。
4. V1 的 F2 冷缓存双请求/状态误闪、F3 测试封装目录创建问题若未修，按低危遗留记录，不因此掩盖 F1 修复结果，也不自行施工。
5. 记录时间、环境、候选哈希、重复次数与种子；发现项是下限。只交报告和证据，不改产品。

## 交付
`D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/neon-v2/report.md` 和原始输出。结论=通过/有条件通过/不通过/部分复核，列阻断项和未验项。报告三行头、地图影响、遗留风险、证据、地图终态齐全。尽快完成，不扩做真机/线上/90 天。最终尾部复述 `DELIVERY-T1128-SMOOTH-V2`。
