# 期刊库质检报告（OpenAlex 对拍 + PubMed 年发文量）

- 跑批时间：2026-10-18 11:30:05
- 总数：340 本（config/journals_taxonomy.json v3.1.0 全量）
- PubMed 窗口：2025/10/01 – 2026/10/17（约 365 天，[ta] 按缩写匹配）
- 脚本：D:\tmp\journal_qc.py（支持断点续跑，已成功条目跳过）

## 汇总

- OpenAlex 命中：340/340（100%）；未命中 0 本
- 名字宽松比对不一致：36 本（见下）
- PubMed vol_365 取到：340/340；为 0 的 5 本
- 异常条目（含 error）：0 本（见异常清单）

### 名字不一致清单

| 我们 title | OpenAlex display_name | nlm_id |
|---|---|---|
| CHEST | CHEST Journal | 0231335 |
| Cancer Communications | 癌症：英文版 | 101723675 |
| Cancer Metabolism | Cancer & Metabolism | 101607582 |
| Cell Host Microbe | Cell Host & Microbe | 101302316 |
| Cell Rep Med | Cell Reports Medicine | 101766894 |
| Cellular Molecular Immunology | Cellular and Molecular Immunology | 101242872 |
| Environmental Epigenetics | Current Zoology | 101675941 |
| Experimental Hematology Oncology | Experimental Hematology and Oncology | 101590676 |
| J Clin Invest | Journal of Clinical Investigation | 7802877 |
| Journal of Hematology Oncology | Journal of Hematology & Oncology | 101468937 |
| Journal of Trauma and Acute Care Surgery | The Journal of Trauma: Injury, Infection, and Critical Care | 101570622 |
| Lancet Child Adolesc Health | The Lancet Child & Adolescent Health | 101712925 |
| Lancet Glob Health | The Lancet Global Health | 101613665 |
| Lancet Planet Health | The Lancet Planetary Health | 101704339 |
| Lancet Reg Health Am | The Lancet Regional Health - Americas | 9918232503006676 |
| Lancet Reg Health Eur | The Lancet Regional Health - Europe | 101777707 |
| Lancet Reg Health Southeast Asia | The Lancet Regional Health - Southeast Asia | 9918419282806676 |
| Lancet Reg Health West Pac | The Lancet Regional Health - Western Pacific | 101774968 |
| Nat Aging | Nature Aging | 101773306 |
| Nat Biomed Eng | Nature Biomedical Engineering | 101696896 |
| Nat Biotechnol | Nature Biotechnology | 9604648 |
| Nat Mach Intell | Nature Machine Intelligence | 101740243 |
| Nat Metab | Nature Metabolism | 101736592 |
| Nat Methods | Nature Methods | 101215604 |
| Nat Microbiol | Nature Microbiology | 101674869 |
| Nat Nanotechnol | Nature Nanotechnology | 101283273 |
| Sci Robot | Science Robotics | 101733136 |
| Sci Signal | Science Signaling | 101465400 |
| International Journal of Chronic Obstructive Pulmonary Disease | International Journal of COPD | 101273481 |
| JOURNAL OF DIGITAL IMAGING | Journal of Imaging Informatics in Medicine | 9100529 |
| LANGENBECKS ARCHIVES OF SURGERY | Langenbeck s Archives of Surgery | 9808285 |
| SURGEON-JOURNAL OF THE ROYAL COLLEGES OF SURGEONS OF EDINBURGH AND IRELAND | The Surgeon | 101168329 |
| Mol Cell | Molecular Cell | 9802571 |
| Nat Rev Cancer | Nature reviews. Cancer | 101124168 |
| Nat Rev Clin Oncol | Nature Reviews Clinical Oncology | 101500077 |
| Trends Cancer | Trends in cancer | 101665956 |

### vol_365 最高 15 本

| title | vol_365 | tier |
|---|---|---|
| Scientific Reports | 43825 | C |
| Frontiers in Immunology | 9820 | A |
| Frontiers in Oncology | 6179 | C |
| Nature | 4682 | S |
| Cancers | 4081 | C |
| JAMA Network Open | 2744 | A |
| ANNALS OF SURGICAL ONCOLOGY | 2734 | A |
| BMJ | 2570 | A |
| International Journal of Surgery | 2152 | A |
| International Immunopharmacology | 2102 | A |
| Science | 2066 | S |
| JAMA | 1967 | S |
| BMC CANCER | 1734 | B |
| Journal of Translational Medicine | 1730 | A |
| New England Journal of Medicine | 1465 | S |

### OpenAlex 未命中清单

（无）

### 异常清单（error 非空）

（无）
