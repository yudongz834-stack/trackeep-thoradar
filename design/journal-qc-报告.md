# 期刊库质检报告（OpenAlex 对拍 + PubMed 年发文量）

- 跑批时间：2026-11-07 07:08:59
- 总数：197 本（config/journals_taxonomy.json vv4.4-precision 全量）
- PubMed 窗口：2025/10/01 – 2026/10/17（约 365 天，[ta] 按缩写匹配）
- 脚本：D:\tmp\journal_qc.py（支持断点续跑，已成功条目跳过）

## 汇总

- OpenAlex 命中：191/197（96%）；未命中 1 本
- 名字宽松比对不一致：26 本（见下）
- PubMed vol_365 取到：197/197；为 0 的 1 本
- 异常条目（含 error）：5 本（见异常清单）

### 名字不一致清单

| 我们 title | OpenAlex display_name | nlm_id |
|---|---|---|
| Trends Cancer | Trends in cancer | 101665956 |
| Lancet Reg Health Eur | The Lancet Regional Health - Europe | 101777707 |
| Cell Rep Med | Cell Reports Medicine | 101766894 |
| CHEST | CHEST Journal | 0231335 |
| Lancet Reg Health West Pac | The Lancet Regional Health - Western Pacific | 101774968 |
| Lancet Reg Health Am | The Lancet Regional Health - Americas | 9918232503006676 |
| Lancet Reg Health Southeast Asia | The Lancet Regional Health - Southeast Asia | 9918419282806676 |
| International Journal of Chronic Obstructive Pulmonary Disease | International Journal of COPD | 101273481 |
| COPD | COPD Journal of Chronic Obstructive Pulmonary Disease | 101211769 |
|  | European Journal of Cardio-Thoracic Surgery | 8804069 |
| Nat Rev Clin Oncol | Nature Reviews Clinical Oncology | 101500077 |
| Cancer Communications | 癌症：英文版 | 101723675 |
| Nat Rev Cancer | Nature reviews. Cancer | 101124168 |
| Sci Robot | Science Robotics | 101733136 |
| Nat Nanotechnol | Nature Nanotechnology | 101283273 |
| Nat Mach Intell | Nature Machine Intelligence | 101740243 |
| Nat Methods | Nature Methods | 101215604 |
| Nat Biotechnol | Nature Biotechnology | 9604648 |
| Nat Biomed Eng | Nature Biomedical Engineering | 101696896 |
| Cell Host Microbe | Cell Host & Microbe | 101302316 |
| Mol Cell | Molecular Cell | 9802571 |
| Sci Signal | Science Signaling | 101465400 |
| J Clin Invest | Journal of Clinical Investigation | 7802877 |
| Nat Microbiol | Nature Microbiology | 101674869 |
| Nat Metab | Nature Metabolism | 101736592 |
| Nat Aging | Nature Aging | 101773306 |

### vol_365 最高 15 本

| title | vol_365 | tier |
|---|---|---|
| The thorax | 1888987 | B |
| Respirology | 1888987 | C |
| The esophagus | 1888987 | D |
| Chronic obstructive pulmonary diseases | 1888987 | D |
| Pediatric pulmonology | 1888987 | C |
| Nature communications | 13391 | A |
| Frontiers in Immunology | 9820 | C |
| Frontiers in public health | 7437 | D |
| Advanced science | 6700 | B |
| Proceedings of the National Academy of Sciences of the United States of America | 5037 | B |
| Nature | 4682 | S |
| iScience | 4213 | C |
| Frontiers in pharmacology | 4130 | D |
| Science advances | 3636 | B |
| Environmental research | 3472 | C |

### OpenAlex 未命中清单

- Chinese medical journal pulmonary and critical care medicine（query_issn=2097-1982）

### 异常清单（error 非空）

- The thorax（9918333279706676）：openalex: no issn available
- Respirology（101688533）：openalex: no issn available
- The esophagus（101769674）：openalex: no issn available
- Chronic obstructive pulmonary diseases（101665139）：openalex: no issn available
- Pediatric pulmonology（9918881164606676）：openalex: no issn available

## 阵地周报

### 阵地周报（近 7 天 · 锚 2026-11-06）

- 口径：命中率＝命中篇数/在册数（每刊产出，年检按此从低到高裁）；上榜率＝命中篇数/近窗入库总篇数。
- 类目：1 胸部肿瘤与胸外科｜2 肿瘤临床｜3 外科与重症医学｜4 影像、病理与检验｜5 感染与免疫｜6 邻科临床｜7 公共卫生与人群健康｜8 基础与转化医学｜9 综合医学与多学科｜10 医学AI与数字医学｜待定=待审定。

| 类目 | 在册数 | 命中篇数 | 命中率 | 上榜率 |
|---|---|---|---|---|
| 1 | 17 | 108 | 635.29% | 42.69% |
| 10 | 6 | 3 | 50.00% | 1.19% |
| 11 | 50 | 0 | 0.00% | 0.00% |
| 2 | 25 | 22 | 88.00% | 8.70% |
| 3 | 7 | 6 | 85.71% | 2.37% |
| 4 | 10 | 7 | 70.00% | 2.77% |
| 5 | 14 | 29 | 207.14% | 11.46% |
| 6 | 2 | 2 | 100.00% | 0.79% |
| 7 | 3 | 8 | 266.67% | 3.16% |
| 8 | 34 | 53 | 155.88% | 20.95% |
| 9 | 29 | 15 | 51.72% | 5.93% |

- 信噪观察（10 类）：在册 6 本仅命中 3 篇（命中率 50.00%），低产出属预期（默认折叠类）；年检按命中率裁汰。
- 信噪观察（8 类）：在册 34 本仅命中 53 篇（命中率 155.88%），低产出属预期（默认折叠类）；年检按命中率裁汰。

### 期刊目录健康（data/journal_health.json）

- 红档（≥100 天未命中，疑改名/停刊/检索键失效，人工核）：0 本
- 黄档（45–99 天，低频刊/季刊可能正常）：0 本
- 绿档（<45 天）：1506 本
- 结论：全部健康。
