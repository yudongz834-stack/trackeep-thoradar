# J2 核验席任务书（agy-Gemini3.8）

## 委任状（五行简化版）
- 轨道位置：trackeep-thoradar（胸科雷达）→ 一次性信源核验席 J2（不进登记册）
- R 级：R1——只允许新建两个输出文件（下方指定路径），其余一切文件只读
- 判级理由：草稿与报告皆可整体丢弃，生产字典 config/ 不动
- 签发：Orchestrator（coordinator），2026-10-17 夜，PI 口谕「派遣 agy-Gemini3.8 去做」

## 任务
对期刊候选名册 60 本逐刊做 **NLM Catalog 身份核验**，产出引擎字典的身份草稿＋差异报告。

**输入（只读）：**
`D:\trackeep-thoradar\design\roster-journals.csv`
列：full_name, pubmed_abbr, major, minor, relation, forced_tier

**做法：**
- 用 NCBI E-utilities 查 NLM Catalog：esearch `db=nlmcatalog`（`期刊名[Title]` 或 ISSN 检索，建议「刊名 OR ISSN」双路）→ esummary 取 NlmUniqueID / ISO Abbreviation / ISSN(L)
- 无 API key：限速 **0.4 秒/请求**，单刊重试 3 次；连续 3 轮全败触发熔断，剩余刊标 unreachable，程序不崩
- 不抓文献数据，只查期刊身份；禁用 NCBI_API_KEY

**输出（仅允许写这两个文件）：**
1. `D:\trackeep-thoradar\design\identity-draft-gemini.json`——逐刊对象数组：
   `{"input_name", "input_abbr", "nlm_found": true/false, "nlm_id", "iso_abbr", "issn_l", "verify_status": "match|diff|unreachable", "note"}`
   判 match＝NLM 找到唯一且 ISO abbr 与 input_abbr 大小写不敏感一致；找到但缩写不一致＝diff；没找到或接口失败＝unreachable（附 note）
2. `D:\trackeep-thoradar\design\identity-draft-gemini-报告.md`——统计（match/diff/unreachable 三计数）＋diff 与 unreachable 逐刊明细表＋你对可疑匹配的点评

**自验（完成前必做）：**
①JSON 可被 json.load 且恰好 60 个对象；②报告三计数之和=60；③stdout 打印三计数。

## 禁区
- 只写上述两个文件；禁改仓库其他任何文件（尤其 config/、tools/）
- 禁 `git commit`／`git push`
- 禁外部 CDN 类联网下载；只准访问 eutils.ncbi.nlm.nih.gov
- Python 一律 `E:/Python/python.exe -X utf8 -I`；bash 路径用正斜杠
