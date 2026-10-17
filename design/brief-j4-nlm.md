# J4 核验席任务书（agy-Gemini3.8 · 增量身份核验）

## 委任状（五行简化版）
- 轨道位置：trackeep-thoradar（胸科雷达）→ 一次性信源核验席 J4（不进登记册）
- R 级：R1——只允许新建两个输出文件（下方指定路径），其余一切只读
- 判级理由：草稿与报告可整体丢弃，生产 config/ 不动
- 签发：Orchestrator（coordinator），2026-10-17 夜，PI 组队令（J2 前序已收 60 本，本席核增量）

## 任务
对增量期刊 316 本逐刊做 NLM Catalog 身份核验（规程与 J2 完全一致）。

**输入（只读）：**
`D:\trackeep-thoradar\design\nlm-verify-delta.csv`——316 行，列：input_name, input_abbr（abbr 常为空，空就只按刊名查）

**做法（同 J2）：**
- esearch `db=nlmcatalog`（`刊名[Title]`，有 abbr 加 OR ISSN 双路）→ esummary 取 NlmUniqueID / ISO Abbreviation / ISSN(L)
- 限速 0.4 秒/请求；单刊重试 3 次；连续 3 轮全败熔断，剩余标 unreachable 不崩
- 不抓文献；禁 NCBI_API_KEY；只准访问 eutils.ncbi.nlm.nih.gov

**输出（仅允许写这两个文件）：**
1. `D:\trackeep-thoradar\design\identity-draft-gemini-j4.json`——对象数组，字段同 J2：
   `{"input_name","input_abbr","nlm_found","nlm_id","iso_abbr","issn_l","verify_status":"match|diff|unreachable","note"}`
2. `D:\trackeep-thoradar\design\identity-draft-gemini-j4-报告.md`——**必须落盘此文件**（J2 前车之鉴）：三计数统计＋diff/unreachable 明细表＋点评（尤其：哪些刊 NLM 根本没收录＝不进 PubMed，引擎抓不到，要点名）

**自验（完成前必做）：**
①json.load 恰好 316 对象；②报告文件存在且三计数之和=316；③stdout 打印三计数。

## 禁区
- 只写上述两个文件；禁改其他文件；禁 git；Python 用 `E:/Python/python.exe -X utf8 -I`；bash 路径正斜杠
