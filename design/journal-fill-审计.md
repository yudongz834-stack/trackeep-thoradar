# 期刊终表二轮补全 · 审计留痕（coordinator，2026-10-18）

对应交付：`期刊表/Thoradar确定期刊-终版总表.xlsx`（340 行 ×13 列）＋ `design/journals-taxonomy-DRAFT.json`
生成链：`D:\tmp\journal_assemble.py`（重写版）；ISSN 缓存 `D:\tmp\nlm_issn_cache.json`（NLM efetch 331＋ta 路 10）

## 1. 行数变化：341 → 340（Cancer Communications 裁并）

问题：终表同时存在两行——
- 「Cancer Commun (Lond)」NLM **101723675**（E 2523-3548）＝ BMC 现行刊
- 「Cancer Communications」NLM **8916730**（P 0955-3541）＝ Wiley 旧刊（已停刊）

NLM 记录正文核实为两家（ISSN 完全不同）。**裁定**：删旧名行；保留行钉 BMC 身份
（全称 Cancer Communications / 缩写 Cancer Commun (Lond)＝PubMed TA / NLM 101723675 /
IF 28.4 Q1 / ONCOLOGY / 1区 / A）。分档 S14/A178/B133/C15（被删行原为 A）。
注：一轮审计查重未抓到此对——两行名字、缩写、NLM ID 三维全不同，ISSN 维度当时未查。
判例：**改名刊的新旧两个 NLM 实体会让三维查重漏过，必须加 ISSN 维度**。

## 2. IF 回填：302 → 311

三路查找：全称 → 简称 → 审计别名表。别名表 11 条（人工逐一核对为同一刊的改名/连字符/全称缩写差）：

| 我们的写法 | JCR 真身 | IF |
|---|---|---|
| JAMA | JAMA-JOURNAL OF THE AMERICAN MEDICAL ASSOCIATION | 65.4 |
| BMJ | BMJ-British Medical Journal | 55.1 |
| British Journal of Surgery | BJS-British Journal of Surgery | 9.4 |
| Lancet Child Adolesc Health | Lancet Child & Adolescent Health | 13.4 |
| Lancet Healthy Longev | Lancet Healthy Longevity | 20.5 |
| Lancet Reg Health Eur | Lancet Regional Health-Europe | 15.7 |
| Lancet Reg Health Southeast Asia | Lancet Regional Health-Southeast Asia | 6.4 |
| Lancet Reg Health West Pac | Lancet Regional Health-Western Pacific | 9.4 |
| Nat Aging | Nature Aging | 25 |
| Cell Metab | Cell Metabolism | 37 |
| Cell Rep Med | Cell Reports Medicine | 14 |

（Cell Metab/Cell Rep Med 属简称直配，别名表冗余兜底。）
其余 29 本 IF 留「—」：真值表确无（Mediastinum/NEJM AI/Proteomes/Acta Oncologica 等已逐一验证缺席）。
全量对拍：311 个 IF 与 JCR 精确一致（差 0）；无「查无却填值」。

## 3. 类别补全：小类别空 62→0，大类别空 26→0

- 小类别＝JCR「主要学科」列直配；JCR 真查无的 **24 本**由 coordinator 依刊物性质判定（JCR 学科风格字符串）：
  Acta Oncologica→ONCOLOGY；Am J Med Genet A/C→GENETICS & HEREDITY；Am J Cancer Res、Cancer Causes & Control、
  Clin Oncol (R Coll Radiol)、Infectious Agents and Cancer、Int J Clin Oncol、Lung Cancer-Targets and Therapy→ONCOLOGY；
  Application of Clinical Genetics、Clinical Genetics、J Hum Genet、Mol Genet Genomics→GENETICS & HEREDITY；
  Biomarker Insights→MEDICINE, RESEARCH & EXPERIMENTAL；Biotechnol Genet Eng Rev→BIOTECHNOLOGY & APPLIED MICROBIOLOGY；
  Cell Immunol→IMMUNOLOGY；Heart Lung Circ→CARDIAC & CARDIOVASCULAR SYSTEMS；JMIR Cancer→HEALTH CARE SCIENCES & SERVICES；
  J Imaging、Ultrason Imaging→RADIOLOGY, NUCLEAR MEDICINE & MEDICAL IMAGING；
  Proteome Science、Proteomes、Proteomics Clin Appl→BIOCHEMISTRY & MOLECULAR BIOLOGY；NEJM AI→MULTIDISCIPLINARY SCIENCES。
- 大类别＝学科→大类映射（已填 279 行众数承袭原席判断＋固定兜底表，脚本内 STATIC_SUBJ2MAJOR）。
- 业务判断正误不在独立审计判据内（与一轮口径同）；审计只验「空格清零＋与声明的来源一致」。

## 4. P/E-ISSN：新增两列

- 主路：NLM efetch 批量（db=nlmcatalog，341 ID 分 7 批）→ 331 记录解析 Print/Electronic；
- 补路：10 本老式记录（R 后缀与新式 16 位 ID）efetch 不吐 → PubMed ta 路线取现行记录 IS 行（Lancet 0140-6736/1474-547X 等 10/10 补齐）；
- 特例：4 本纯电子刊 P=E 同值（Cell Genomics/Lancet Reg Health Am/SEA/NEJM AI）系 NLM 原样；Cancer Communications 钉 BMC 身份（1000-467X/2523-3548）。
- 诚实边界：ISSN 是「刊」的属性，取自现行记录；NLM ID 两说问题（Lancet 2985213R vs 446079）不受此影响，仍挂 identity_check 终裁。

## 5. 引擎假数修复（同族问题，一并收口）

- `if_val` 兜底 0.0 → None；briefing 与 index.html 六处渲染改「—」；
- zone 缺省硬编「JCR Q2」→ 无值不显示（消灭第二个假默认）。
- 引擎自测 8/8、回归 5/5 全绿。

## 6. 复核记录（coordinator 全量复算，非抽样）

行 340；四维（全称/简称/NLM ID/P-ISSN）碰撞 0；IF 不符 0；关键列空格 0；JSON 与表同步 340。
独立复审：Kimi K3 二轮审计（brief-audit2-kimi.md → 终表审计2-kimi.md）。
