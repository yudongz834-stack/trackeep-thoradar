# J3b 判断席任务书（cursor-grok4.7 · 第三会话，与 J3 同口径判断增量）

## 委任状（五行简化版）
- 轨道位置：trackeep-thoradar（胸科雷达）→ 一次性信源判断席 J3b（不进登记册）
- R 级：R1——只允许新建一个输出文件（下方指定路径）
- 判级理由：判断稿可整体丢弃，生产零改动
- 签发：Orchestrator（coordinator），2026-10-17 夜，PI 追加口径「基础科研、临床科研、转化科研都需要」

## 任务
对期刊增量 194 本逐刊判断「理论上是否可能发表**胸外科疾病相关**的基础/临床/转化研究」（肺癌、食管癌、纵隔、胸膜胸壁、气胸、肺结节等——基础机制、组学、转化、临床试验都算）。

**输入（只读）：**
`D:\trackeep-thoradar\design\sweep-delta194.csv`（194 行，列含 cas_name/jcr_subject/impact_factor/jcr_q 等）

**判断口径（本批含大量基础科研刊，比 J3 更宽）：**
- include = yes：期刊可能刊出与胸科疾病相关的基础机制、组学/基因组、转化、免疫微环境、数字/AI 方法学、临床研究——「Cancer Res/Oncogene 级别的基础肿瘤刊」一律 yes；综合生命科学旗舰（Cell/Nature 系若在列）理论上可发，也 yes
- include = no：与胸科疾病研究基本无交集（植物病理、纯数学、文学、艺术、食品、土壤等——本批有农林科学 22 本多为关键词撞名，大胆杀）
- relation：核心（胸部肿瘤基础/转化主战场）｜密切（大肿瘤、大外科学、呼吸、基因组学常见）｜相关（综合生命科学/泛医学，可能发）｜综合可发（顶刊综合）
- note：一句话理由

**输出（唯一允许写的文件）：**
`D:\trackeep-thoradar\design\sweep-judged-cursor-j3b.csv`——与输入同列＋末尾 3 列：include, relation, note；行序同输入；utf-8-sig。

**自验（完成前必做）：**
①行数=194（加表头 195）；②无空值；③stdout 打印 include=yes 计数与四档计数。

## 禁区
- 只写上述一个输出文件；禁改其他任何文件；禁 `git commit`／`git push`
- Python 一律 `E:/Python/python.exe -X utf8 -I`；bash 路径用正斜杠；不需要联网
