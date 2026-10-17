审计时间：2026-10-18 03:18:46 +0800  
审计版本：`期刊表/Thoradar确定期刊-终版总表.xlsx`；37,550 字节；sheet「确定期刊」341 行（表头 1＋数据 **340**）×13 列，sheet「说明」14 行；SHA256 `e7bc229f1ba0921bddd608fc2d00b1da4fb17f720f15d05e9775722ec5da125a`  
结论：**PASS-with-notes**（八项清单全部实测通过、critical=0；但说明页身份对拍数「339 本」比实测 338 多 1，属上轮「旧文案残留」同类问题的复发，只是规模缩到 1；另 ISSN 口径句歧义、11 行小类别用中文标签与 JCR 原文不一致，故不判纯 PASS）

---

## 逐项清单结果

### 1. 行数与分档 —— 过

- 数据行实测 **340**；档位实测 **S=14 / A=178 / B=133 / C=15**，合计 340，与任务书预期及说明页第 4–5 行逐项一致。
- 与上轮 341 版相比净删 1 行（即 Cancer Communications 旧名行），A 档 179→178，其余三档不变，与任务书「删的行原为 A」一致。

### 2. 四维查重 —— 过

| 维度 | 规范化后重复组 | 冗余行 |
|---|---:|---:|
| 期刊全称 | 0 | 0 |
| PubMed 缩写 | 0 | 0 |
| NLM ID | 0 | 0 |
| P-ISSN | 0 | 0 |

规范化口径：去首尾空白、NFKC 兼容折叠、大小写折叠、标点/空白移除；NLM 纯数字 ID 先补零至至少 7 位（`0372553`、`0255562` 等前导零格式本轮无异常）。340 行对应 340 个唯一 NLM ID。

### 3. Cancer 裁并复核 —— 过

- 全表「Cancer Communications」作全称的行**恰有 1 行**（Excel 行 46），五字段实测：

| Excel 行 | 全称 | PubMed 缩写 | NLM ID | IF | 中科院分区 | 档位 | P-ISSN | E-ISSN |
|---:|---|---|---|---|---|---|---|---|
| 46 | Cancer Communications | Cancer Commun (Lond) | 101723675 | 28.4 | 1区 | A | 1000-467X | 2523-3548 |

- 与任务书裁定（BMC 现行刊身份、IF 28.4、Q1、1区、A）逐字段一致；其 IF 28.4 与 JCR 真值表 `CANCER COMMUNICATIONS` 精确相符（第 4 项全量对拍 0 不符覆盖此行）。
- 全表以「Cancer Commun (Lond)」作**全称**的行 = **0**；以任何形式（全称或缩写）含 cancer commun 的行仅上述 1 行，Wiley 旧刊（8916730／0955-3541）痕迹清零。

### 4. IF 全量对拍 —— 过

- IF 列实测：**311 行已填＋29 行「—」**，与任务书预期 311 及说明页「已填 311／查无 29」一致；5年IF 列 340/340 全为「—」。
- 匹配路径：JCR 真值表（10,200 条记录）按全称/简称大写规范化直配，未中再走任务书 11 条经审计别名。
- **311/311 已填 IF 与真值精确一致，不符 0**；「已填却查无真值」**0 行**（无 critical 情形）；「真值可查却留 —」**0 行**；同一刊多路命中且 IF 冲突 **0 行**。
- 别名 11 条逐一核对结果：**9 条实际走别名路线命中且 IF 全部一致**——JAMA→65.4、BMJ→55.1、British Journal of Surgery→BJS 9.4、Lancet Child Adolesc Health→13.4、Lancet Healthy Longev→20.5、Lancet Reg Health Eur→15.7、Lancet Reg Health Southeast Asia→6.4、Lancet Reg Health West Pac→9.4、Nat Aging→25；其余 2 条（Cell Metab、Cell Rep Med）无需别名——其全称恰与 JCR「简称」列直配命中，IF 同样一致（说明页「别名 9 本」与此吻合）。

### 5. 类别空格清零 —— 过

- 「期刊大类别」空格 **0**，「期刊小类别」空格 **0**（340/340 两列全填）。
- 抽样：固定种子 20261018，在有 JCR 记录的行中随机抽 10 本，小类别与 JCR「主要学科」列 **10/10 一致**（J HEART LUNG TRANSPLANT、SURGERY、CANCER IMAGING、INT J TUBERC LUNG DIS、LANGENBECKS ARCH SURG、SURG CLIN NORTH AM、EUR J CANCER、J Genet Genomics、CA-CANCER J CLIN、MOL ONCOL）。全量口径：311 行有 JCR 学科真值，其中 300 行小类别与真值完全一致。
- 另 11 行小类别为中文标签（综合/医学综合/肿瘤学/数字健康/呼吸系统），与 JCR 原文不同（明细见发现项 minor-2）；业务判断正误按任务书口径不在验收判据内。

### 6. ISSN 列与身份对拍 —— 过（含 2 本已知开口）

- NLM ID 空值 **0**；P-ISSN、E-ISSN 两列无空白单元格（无记录处以「—」占位）。
- 取值分布：P 列真 ISSN 246＋「—」94；E 列真 ISSN 337＋「—」3；双路全真 **243**、仅 Print（P 真 E「—」）**3**、仅电子（P「—」E 真）**94**、两路皆无 **0**；P=E 同值 **4 本**，与任务书「4 本纯电子刊 P=E」一致。
- 两份 identity JSON 合并 376 条记录、340 个唯一 NLM ID；主表 340 行中 **338 行**可按 NLM ID 命中记录，**338/338 的 `issn_l` 均 ∈ {P-ISSN, E-ISSN}，例外 0**。
- 例外清单（与上轮相同，身份链开口）：**Nature（行 11，0410462）、Science（行 14，0404511）** 两刊在两份 JSON 中无记录，无法经该来源对拍 ISSN；说明页已声明其由 coordinator eutils 直验。

### 7. 说明页一致性 —— 主统计过；一处旧计数残留（minor）

| 说明页声明 | 实测 | 结果 |
|---|---|---|
| 总本数 340 | 340 | ✓ |
| S=14 A=178 B=133 C=15 | S=14 A=178 B=133 C=15 | ✓ |
| IF 已填 311／查无 29 | 311／29 | ✓ |
| 经审计别名 9 本 | 别名路线命中 9 本 | ✓ |
| ISSN 双全 243／仅 Print 3 | 243／3 | ✓ |
| 339 本经 identity JSON 对拍 | **338**（340 行仅 Nature/Science 无记录） | ✗ 差 1 |

- 上轮「376本全验」旧文案已改写，总本数、分档、IF 口径均已同步到本轮实测；唯「339 本」仍是 341 行时代的旧数——删掉的 Cancer 旧名行恰是有 JSON 记录的行，对拍数应同步减为 338。属同一类（修主表后说明页计数未全量同步）的复发，规模从 376 缩到差 1。

### 8. 回溯抽查 —— 过

- **34 行重复**：本轮四维（全称/缩写/NLM ID/P-ISSN）规范化查重全部 0 碰撞、0 冗余（第 2 项），旧 33 组碰撞无回潮。
- **BJS 错误**：Excel 行 32 实测 `British Journal of Surgery / Br J Surg / NLM 0372553 / 1区 / A / IF 9.4 / Q1 / P 0007-1323 / E 1365-2168`，身份、分区、档位、IF 全部正确；IF 9.4 与 JCR `BJS-BRITISH JOURNAL OF SURGERY` 精确一致，ISSN 与中科院真值表「医学」区 0007-1323 记录互洽。仍为修复态。

---

## 发现项分级

### critical（影响字典正确性）

**无。** 340 行零重复、已填 IF 311/311 全真、无「查无却填值」、Cancer 裁并与 BJS 修复均复核在位。

### minor（显示/说明/核验链瑕疵）

1. **说明页「339 本经 identity JSON 对拍」为旧计数**：实测 338/340（仅 Nature/Science 无记录）。上一轮同类问题（376 残留）整改时漏改了这一处随删行联动的数字。
2. **11 行小类别用中文标签、与 JCR「主要学科」原文不一致**：Nature Medicine（医学综合/Multiple）、NEJM 与 The Lancet（综合/MEDICINE, GENERAL & INTERNAL）、ESMO Open（肿瘤学/ONCOLOGY）、JAMA Network Open（医学综合）、Lancet Digital Health 与 npj Digital Medicine（数字健康/Multiple）、MedComm（医学综合）、Signal Transduct Target Ther（肿瘤学/Multiple）、JTO Clin Res Rep（呼吸系统/Multiple）、Scientific Reports（综合/MULTIDISCIPLINARY SCIENCES）。说明页声称「小类别＝JCR 主要学科列」，这 11 行是人工中文改写，口径说明与实际不完全相符；正误不在验收判据内，仅标口径。
3. **说明页 ISSN 句歧义**：「双全 243 本，3 本仅 Print，0 本无记录留『—』」未提 94 本纯电子刊 P 列实为「—」，读者易误以为全表无「—」；建议补「94 本仅电子（P=—）」。
4. **Nature/Science 身份核验链开口**（沿自上轮）：两刊 ISSN/缩写不能经 identity JSON 对拍，仅有说明页声明的 eutils 直验，无可回放证据文件。

### 建议

1. 说明页所有计数（总本数、分档、IF、对拍数、ISSN 分布）由脚本从主表自动生成，根治「修主表忘改说明」这一已复发两次的失效模式。
2. 11 行中文小类别若要保留，说明页口径句改为「JCR 主要学科列，其中 11 行按中文惯例改写」；或统一回写 JCR 原文。
3. 将 Nature/Science 的 eutils 直验留痕（查询返回原文存 design/ 目录），把身份链开口关闭。

## 未覆盖开口清单

- 29 本 IF 为「—」的刊仅核实「在给定 JCR 真值表中三条路线均查无」，未联网验证表外是否有新收录；中科院分区真值表本轮未重跑全量对拍（任务书本轮未列入，沿用上轮 330/341 定位、0 不符的结论，删行不涉及分区字段变更）。
- 「与胸科关系程度」「期刊大/小类别」业务判断正误不在验收判据内（任务书明示），未终审。
- The Lancet 的 NLM 新旧两说（2985213R vs 446079）仍按给定 identity JSON 取 `2985213R`，未做外部终裁，与说明页差异清单声明一致。
- 4 本 P=E 同值刊按任务书声明视为 NLM 原样，本轮仅核实同值事实，未向 NLM 复核。
- 按禁区要求全程未联网；所有结论仅基于任务书及指定本地真值文件。

## 只读与证据完整性

- 全程只读加载 xlsx/json；未执行 git；未联网；Python 经 stdin 执行（`E:/Python/python.exe -X utf8 -I -`），未落任何临时脚本文件。
- 本轮唯一写入文件即本报告：`design/终表审计2-kimi.md`。
