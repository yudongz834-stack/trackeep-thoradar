审计时间：2026-10-18 01:37:37 +0800  
审计版本：`期刊表/Thoradar确定期刊-终版总表.xlsx`；30,236 字节；sheet「确定期刊」342 行（表头 1＋数据 **341**）×11 列，sheet「说明」12 行；SHA256 `1c48953dd6fa41bb55d195e0af7727ddf03c6125bab95598cc8fb9ff91d36a23`  
结论：**PASS-with-notes**（上一轮两项 critical 已消除，本轮 critical=0；主表行数、分档、规则、已填 IF/JCR、三维查重及旗舰在位均通过。说明页仍残留「376本全验」旧文案，Nature/Science 缺 identity JSON 核验记录，另有少量全称显示不统一，故不判纯 PASS）

---

## 逐项清单结果

### 1. 行数与分档 —— 过

- 数据行实测 **341**；档位实测 **S=14 / A=179 / B=133 / C=15**，合计 341，与本轮预期及说明页第 4–5 行一致。
- S 档 14 本逐一核对如下；14 行均为「S／1区」，与说明页固定名单一致：

| Excel 行 | 期刊全称 | PubMed 缩写 | NLM ID | 核对 |
|---:|---|---|---|---|
| 2 | Annals of Oncology | Ann Oncol | 9007735 | S／1区 ✓ |
| 3 | Cancer Cell | Cancer Cell | 101130617 | S／1区 ✓ |
| 4 | Cancer Discovery | Cancer Discov | 101561693 | S／1区 ✓ |
| 5 | JAMA | JAMA | 7501160 | S／1区 ✓ |
| 6 | JAMA Oncology | JAMA Oncol | 101652861 | S／1区 ✓ |
| 7 | Journal of Clinical Oncology | J Clin Oncol | 8309333 | S／1区 ✓ |
| 8 | Journal of Thoracic Oncology | J Thorac Oncol | 101274235 | S／1区 ✓ |
| 9 | Lancet Oncology | Lancet Oncol | 100957246 | S／1区 ✓ |
| 10 | Lancet Respiratory Medicine | Lancet Respir Med | 101605555 | S／1区 ✓ |
| 11 | Nature | NATURE | 0410462 | S／1区 ✓ |
| 12 | Nature Medicine | Nat Med | 9502015 | S／1区 ✓ |
| 13 | New England Journal of Medicine | N Engl J Med | 0255562 | S／1区 ✓ |
| 14 | Science | SCIENCE | 0404511 | S／1区 ✓ |
| 15 | The Lancet | Lancet | 2985213R | S／1区 ✓ |

- **上一轮 critical-1 已关闭**：全称、PubMed 缩写、NLM ID 三维均未再发现重复；34 行冗余已清零，当前 341 行对应 341 个唯一 NLM ID。详细证据见第 5 项。
- **上一轮 critical-2 已关闭**：Excel 行 32 已矫正为 **British Journal of Surgery / Br J Surg / 0372553 / 1区 / A**，五字段全部符合本轮预期。identity JSON 对应记录亦为 `0372553`、`iso_abbr=Br J Surg`；中科院真值表「医学」第 193 行为 British Journal of Surgery、ISSN 0007-1323、**1区**。

### 2. 档位规则抽样 —— 过（并做了全量复算）

- 抽样方法：固定种子 **20261018**，按 S/A/B/C 分层，每层随机抽 5 本，共 **20 本**；20/20 表内档位与规则复算一致。
- 说明页另明示 6 本强制 C：Cancers、Frontiers in Oncology、Scientific Reports、Journal of Thoracic Imaging、Esophagus、Mediastinum。下表的「3区→C」均属该明示例外，不是误判。

| Excel 行 | 抽样期刊 | 真值分区 | 规则预期 | 表内档位 | 结果 |
|---:|---|---|---|---|---|
| 3 | Cancer Cell | 1区 | S（固定名单） | S | ✓ |
| 5 | JAMA | 1区 | S（固定名单） | S | ✓ |
| 7 | Journal of Clinical Oncology | 1区 | S（固定名单） | S | ✓ |
| 14 | Science | 1区 | S（固定名单） | S | ✓ |
| 15 | The Lancet | 1区 | S（固定名单） | S | ✓ |
| 45 | Cancer Biology & Medicine | 2区 | A | A | ✓ |
| 72 | EUROPEAN RESPIRATORY JOURNAL | 1区 | A | A | ✓ |
| 133 | Lancet Child Adolesc Health | 1区 | A | A | ✓ |
| 144 | MOLECULAR & CELLULAR PROTEOMICS | 2区 | A | A | ✓ |
| 155 | Nat Biotechnol | 1区 | A | A | ✓ |
| 209 | BMC Pulmonary Medicine | 3区 | B | B | ✓ |
| 242 | Diagnostic Pathology | 3区 | B | B | ✓ |
| 260 | International Journal of Chronic Obstructive Pulmonary Disease | 3区 | B | B | ✓ |
| 264 | JCO Global Oncology | 3区 | B | B | ✓ |
| 325 | Updates in Surgery | 3区 | B | B | ✓ |
| 328 | Cancers | 3区 | C（强制例外） | C | ✓ |
| 330 | Esophagus | 3区 | C（强制例外） | C | ✓ |
| 331 | Frontiers in Oncology | 3区 | C（强制例外） | C | ✓ |
| 338 | NEJM AI | 未收录 | C | C | ✓ |
| 342 | Trends Cancer | 未收录 | C | C | ✓ |

- **全量加强验证**：341 行中 **330 行**在给定中科院表定位成功（全称 304＋PubMed 缩写 1＋identity ISSN 24＋BMJ 别名 1），其余 **11 行**均为表内「未收录→C」；分区或档位不符 **0 行**。BMJ 对应真值表「医学」第 18 行 `BMJ-British Medical Journal / 1区`，与主表 A 一致。

### 3. 禁编造检查 —— 过

- IF 列：**302 行非负数字＋39 行「—」**；非法值 0（负数、NaN/无穷、非规定文本均未发现）。
- 5年IF 列：**341/341 全为「—」**。
- 已填的 **302/302 个 IF 与 `最新IF 2025 全.xlsx` 精确一致**，最大绝对差 **0.0**；同 302 行 JCR 分区对拍不符数 **0**。
- 名称未直接匹配 JCR 表的 39 行，IF 与 JCR 分区全部为「—」；不存在「有数值但无法回溯到给定 IF 真值表」的行，未发现可疑编造数字。

### 4. 身份数据对拍 —— 主表值过；JSON 覆盖完整性不过（minor）

- 与第 2 项相同的 20 本抽样：**19 本 NLM ID＋官方缩写均与两份 identity JSON 对拍一致**；Science 的表内 ID 为任务书指定的 `0404511`，但两份 JSON 均无该刊记录，记为覆盖开口而非错值。
- 全量 341 行中，**339 行 NLM ID 可在 identity JSON 找到记录，339/339 官方缩写对拍 0 不符**；未覆盖仅 **Nature（行11，0410462）**和 **Science（行14，0404511）**。
- 四本必查：

| 期刊 | 表内 NLM ID | 任务书期望 | JSON 对拍 |
|---|---|---|---|
| Nature | 0410462 | 0410462 | 无记录；仅能对到任务书期望值 |
| Science | 0404511 | 0404511 | 无记录；仅能对到任务书期望值 |
| BMJ | 8900488 | 8900488 | 一致 ✓ |
| CA-A CANCER JOURNAL FOR CLINICIANS | 0370647 | 0370647 | 一致 ✓ |

- NLM ID 空值 **0**；纯数字 ID 的前导零格式异常 **0**。上一轮 Nature/Science 去前导零问题已修复。

### 5. 重复检查 —— 过

| 检查维度 | 字面重复组 | 规范化后重复组 | 冗余行 |
|---|---:|---:|---:|
| 期刊全称 | 0 | 0 | 0 |
| PubMed 缩写 | 0 | 0 | 0 |
| NLM ID | 0 | 0 | 0 |

规范化口径含去首尾空白、大小写折叠、Unicode 兼容折叠及标点/空白移除；NLM 纯数字 ID 先补足至少 7 位前导零再查。上一轮 33 组碰撞、34 行冗余已清零。

### 6. 旗舰在位 —— 过

| Excel 行 | 期刊 | 档位 | 中科院分区 | NLM ID | 结果 |
|---:|---|---|---|---|---|
| 33 | CA-A CANCER JOURNAL FOR CLINICIANS | A | 1区 | 0370647 | 在位 ✓ |
| 51 | Cell | A | 1区 | 0413066 | 在位 ✓ |
| 11 | Nature | S | 1区 | 0410462 | 在位 ✓ |
| 14 | Science | S | 1区 | 0404511 | 在位 ✓ |
| 28 | BMJ | A | 1区 | 8900488 | 在位 ✓ |
| 15 | The Lancet | S | 1区 | 2985213R | 在位 ✓ |
| 13 | New England Journal of Medicine | S | 1区 | 0255562 | 在位 ✓ |

CA、Cell、BMJ 为 A 而非 S，符合「S=14 本固定名单」的设计，不是降档错误。

### 7. 说明页一致性 —— 统计过；旧文案不过（minor）

- 说明页第 4 行「总本数 341」与实际 **341** 一致；第 5 行「S=14 A=179 B=133 C=15」与实测逐项一致。
- 说明页第 10 行仍写「NLM Catalog……**376本全验**」：376 是上一轮旧行数；当前主表为 341 行，且 identity JSON 直接覆盖为 339 行，Nature/Science 无记录。因此该句同时存在**旧计数**与**全验表述过满**两处显示/说明瑕疵。

---

## 发现项分级

### critical（影响字典正确性）

**无。** 上一轮「34 行重复入库」与「BJS 身份/分区/档位错误」两项 critical 均已修复并通过本轮复核。

### minor（显示/说明/核验链瑕疵）

1. **说明页第 10 行残留「376本全验」**：应至少改为当前 341 行口径，并如实区分 339 行有 identity JSON 记录、Nature/Science 无记录；否则读者会误认为 341 本均已有 JSON 身份证据。
2. **Nature/Science 身份核验链开口**：主表 `0410462/0404511` 与任务书期望一致，未发现错值，但两份 identity JSON 均无这两刊，不能宣称其已完成该来源的独立对拍。
3. **「期刊全称」仍有缩写/别名显示**：例如行 133 `Lancet Child Adolesc Health`、行 155 `Nat Biotechnol`、行 339 `Nat Rev Cancer`、行 342 `Trends Cancer`。这不影响本轮 NLM 唯一性及档位判定，但显示口径仍不统一。

### 建议

1. 说明页的总本数、分档数与身份覆盖数由当前主表/证据记录自动生成，避免修复主表后旧数字残留。
2. 后续补齐 Nature/Science 的可追溯身份证据，或在说明页明确其替代核验来源；保留「NLM ID 唯一性」硬约束，防止合并回潮。
3. 后续可单独做全称规范化；若补填目前 39 行的「—」IF/JCR，应先建立经审计的别名映射，仍坚持「查不到即—，不编造」。

## 未覆盖开口清单

- 以下 **11 本 C 档刊**只核实了「在给定中科院真值表中查无，故按未收录→C」：Diseases of the Esophagus、Interactive CardioVascular and Thoracic Surgery、JTO Clinical and Research Reports、Journal of Thoracic Disease、Journal of Thoracic Imaging、Mediastinum、Mol Cell、NEJM AI、Nat Rev Cancer、Nat Rev Clin Oncol、Trends Cancer。未联网验证该真值表之外的官方最新分区；其中 Journal of Thoracic Imaging、Mediastinum 同时还受强制 C 规则约束。
- 「与胸科关系程度」「期刊大/小类别」的业务判断不在本任务书验收判据内，未作正确性终审；PI 圈定种 60 本名册（已按 PI 令剔除）本轮用于基础名单及 6 本强制 C 核对。
- The Lancet 的 NLM 新旧两说（2985213R vs 446079）未做外部终裁；本轮按给定 identity JSON 采用 `2985213R`，与说明页已声明的差异清单一致。
- 按禁区要求未做外部联网核验；所有结论仅基于任务书及指定本地真值文件。

## 只读与证据完整性

- 本次仅以只读方式加载 xlsx/json/csv；未执行 git，未修改被审对象或真值文件。
- 审前、审后重新计算被审文件及 5 份真值文件的 SHA256，**6/6 全部一致**。
- 本轮唯一写入文件即本报告：`design/终表审计-kimi.md`。
