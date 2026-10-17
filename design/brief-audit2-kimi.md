# 审计席任务书第二轮（Kimi K3 · 二轮补全增量独立审计）

## 委任状（五行简化版）
- 轨道位置：trackeep-thoradar → 一次性审计席（不进登记册）
- R 级：R1——只允许新建一个报告文件 `D:\trackeep-thoradar\design\终表审计2-kimi.md`
- 判级理由：纯只读审计＋一份报告
- 签发：Orchestrator（coordinator），2026-10-18；上一轮你已独立审计过终表（PASS-with-notes），本轮审增量

## 背景（30 秒）
你上轮审的是 341 行版。此后 coordinator 做了二轮补全，被审对象已重写：
- **行数 341→340**：发现「Cancer Communications」存在新旧两个 NLM 实体（Wiley 旧刊 8916730/Print 0955-3541，已停刊 vs BMC 现行刊 101723675/Print 1000-467X/E 2523-3548＝JCR IF 28.4 真身）。裁定：删旧名行「Cancer Commun (Lond)」（该行 NLM 本就是 101723675 但与 Wiley 行并存）；保留行钉 BMC 身份（全称 Cancer Communications，PubMed 缩写 Cancer Commun (Lond)，NLM 101723675，IF 28.4，Q1，ONCOLOGY，1区，A）。
- **新增 2 列**：P-ISSN、E-ISSN（NLM efetch 批量；10 本老式记录走 PubMed ta 路线取现行记录 ISSN；4 本纯电子刊 P=E 同值系 NLM 原样）。
- **IF 回填**：302→311（全称/简称/经审计别名三路；别名表 11 条人工核对：JAMA→JAMA-JOURNAL OF THE AMERICAN MEDICAL ASSOCIATION、BMJ→BMJ-British Medical Journal、British Journal of Surgery→BJS-British Journal of Surgery、Lancet Child Adolesc Health→Lancet Child & Adolescent Health、Lancet Healthy Longev→Lancet Healthy Longevity、Lancet Reg Health Eur→Lancet Regional Health-Europe、Lancet Reg Health Southeast Asia→Lancet Regional Health-Southeast Asia、Lancet Reg Health West Pac→Lancet Regional Health-Western Pacific、Nat Aging→Nature Aging、Cell Metab→Cell Metabolism、Cell Rep Med→Cell Reports Medicine）。
- **类别补全**：小类别空 62→0（JCR「主要学科」列直配＋24 本 JCR 真查无者由 coordinator 依刊物性质判定）；大类别空 26→0（学科→大类映射：已填行众数＋固定兜底表）。分档统计变为 S=14/A=178/B=133/C=15（删的行原为 A）。

## 你审什么
被审对象：`D:\trackeep-thoradar\期刊表\Thoradar确定期刊-终版总表.xlsx`（现 340 数据行 ×13 列，sheet「确定期刊」＋「说明」）
对照真值（全部只读）：
- `期刊表\2025年中科院大类分区期刊排名汇总表.xlsx`（分区真值）
- `期刊表\最新IF 2025 全.xlsx`（IF/Q/主要学科真值）
- `design\identity-draft-gemini.json`＋`identity-draft-gemini-j4.json`（NLM 身份真值）

## 审计清单（逐项过，给出 过/不过＋证据）
1. **行数与分档**：数据行=340；S=14/A=178/B=133/C=15。
2. **四维查重**：全称/简称/NLM ID/P-ISSN 四维零碰撞（规范化含大小写折叠、标点去除、纯数字 ID 补零）。
3. **Cancer 裁并复核**：表中恰有一行 Cancer Communications；其五字段（缩写 Cancer Commun (Lond)／NLM 101723675／IF 28.4／1区／A）与任务书一致；全表不再存在「Cancer Commun (Lond)」作全称的行。
4. **IF 全量对拍**：已填 IF（预期 311）与 JCR 真值逐行精确一致；别名行（上表 11 条）单独列出核对；查无刊的 IF 必须为「—」（发现任何「真值表查无却填值」＝critical）。
5. **类别空格清零**：大类别/小类别两列空格=0；抽 10 本新填小类别对 JCR 主要学科；「与胸科关系程度」「期刊大/小类别」的**业务判断正误不在验收判据内**（同上轮口径）。
6. **ISSN 列**：P/E-ISSN 与 identity JSON 的 issn_l 至少一路相容（逐刊核对 issn_l ∈ {P, E} 或记录例外清单）；NLM ID 空=0。
7. **说明页一致性**：总本数 340、分档统计、IF 已填/空数与主表实测一致（上轮的旧文案残留问题本轮不得复现）。
8. **回溯抽查**：你上轮 FAIL 轮抓的 34 行重复与 BJS 错误——确认在当前版仍是修复态。

## 输出（唯一允许写的文件）
`D:\trackeep-thoradar\design\终表审计2-kimi.md`：
- 头部三行：审计时间 / 审计版本（文件大小+行数）/ 结论（PASS / PASS-with-notes / FAIL）
- 逐项清单结果＋证据数字
- 发现项分级：critical / minor / 建议
- 未覆盖开口清单

## 禁区
- 只写上述一个报告文件；被审对象与真值只读；禁 git；禁联网
- Python 用 `E:/Python/python.exe -X utf8 -I`（openpyxl 可用）；bash 路径正斜杠
