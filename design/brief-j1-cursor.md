# J1 填表席任务书（cursor-grok4.7）

## 委任状（五行简化版）
- 轨道位置：trackeep-thoradar（胸科雷达）→ 一次性信源整备席 J1（不进登记册）
- R 级：R1——只允许新建一个输出文件（下方指定路径），其余一切文件只读
- 判级理由：单文件产出可整体丢弃，生产零改动
- 签发：Orchestrator（coordinator），2026-10-17 夜，PI 口谕「组队完成，派遣 cursor-grok4.7 去做」

## 任务
把期刊候选名册填成 PI 模板结构的填充稿 xlsx。

**输入（全部只读）：**
1. 名册（60 本，PI 自官方两表先行圈定；种子名册文件已按 PI 令剔除，仅存于建库 git 历史）
   列：full_name, pubmed_abbr, major, minor, relation, forced_tier
2. 中科院 2025 分区表（查档数据源）：`D:\trackeep-thoradar\期刊表\2025年中科院大类分区期刊排名汇总表.xlsx`
   （多 sheet 按大类；「医学」1962 行、「综合」100 行是主用的两个；列＝序号/刊名/ISSN/分区）
3. 模板结构参考（只看表头列名，勿改此文件，它是只读的）：
   `D:\trackeep-thoradar\期刊表\Thoradar确定期刊.xlsx`
   列＝期刊全称/期刊PUBMEDE名称/期刊大类别/期刊小类别/期刊IF/期刊5年IF/JCR分区/与胸科关系程度

**定档规则：**
1. S 档＝以下 12 本固定（这是精选门槛名单）：NEJM、The Lancet、JAMA、Nature Medicine、Lancet Oncology、JAMA Oncology、Annals of Oncology、Journal of Clinical Oncology、Cancer Cell、Cancer Discovery、Journal of Thoracic Oncology、Lancet Respiratory Medicine
2. 非 S 的按中科院分区：1区→A、2区→A、3区→B、4区→C、查不到/未分级→C
3. CSV 里 forced_tier 有值的（6 本）强制 C（量控层，最终以用户档位过滤器实现质量分层）
4. 档位优先级：forced ＞ S 名单 ＞ 分区规则

**输出（唯一允许写的文件）：**
`D:\trackeep-thoradar\期刊表\Thoradar确定期刊-填充稿-cursor.xlsx`
- 沿模板 8 列，末尾追加 2 列：「中科院2025分区」「入库档位」（S/A/B/C）
- 模板列填不出的（IF/5年IF/JCR 分区我们暂无数据源）一律写「—」，**禁止编造数字**
- 排序：按档位 S→A→B→C，同档按刊名字母序
- 档位列按 S/A/B/C 淡色区分（如 F5E8E1/FAF9F5/F5F3EC/DFDACB），表头加粗
- 期刊大类别/小类别用 CSV 的 major/minor；与胸科关系程度用 CSV 的 relation

**自验（完成前必做）：**
重新打开你写的 xlsx：①总行数=60；②分档统计打印；③抽查 3 本在「医学」sheet 里能对上分区。统计结果写进 stdout。

## 禁区
- 只写上述一个输出文件；PI 的两份原件只读；禁改仓库其他任何文件
- 禁 `git commit`／`git push`
- Python 一律 `E:/Python/python.exe -X utf8 -I`（openpyxl 3.1.5 可用）；bash 路径用正斜杠
