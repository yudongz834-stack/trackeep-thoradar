# J3 判断席任务书（cursor-grok4.7 · 与 J1 同模型不同会话）

## 委任状（五行简化版）
- 轨道位置：trackeep-thoradar（胸科雷达）→ 一次性信源判断席 J3（不进登记册）
- R 级：R1——只允许新建一个输出文件（下方指定路径）
- 判级理由：判断稿可整体丢弃，生产零改动
- 签发：Orchestrator（coordinator），2026-10-17 夜，PI 口谕「把表里所有可能涉及胸科的杂志都填进去」

## 任务
对期刊超集 280 本逐刊判断「这本期刊**理论上是否可能发表胸外科疾病相关内容**」（肺癌、食管癌、纵隔肿瘤、胸壁/胸膜、气胸、肺结节、胸外科术式等临床与转化研究）。

**输入（只读）：**
`D:\trackeep-thoradar\design\sweep-superset.csv`
280 行，列：cas_name, jcr_abbr, issn, cas_zone, cas_sheet, jcr_subject, impact_factor, jcr_q

**判断口径（宽进，PI 原话「所有可能涉及胸科的都要」）：**
- include = yes：期刊定位下出现胸科内容有现实可能——胸外科/呼吸/肿瘤/影像主战场刊当然是 yes；儿外科、移植、麻醉与围术期、重症、老年、病理、检验、流行病学、数字医学等有胸科交集的也是 yes
- include = no：定位与胸科基本无交集（纯血液、皮肤、口腔、妇产、精神、眼科等专科）
- relation 四档：核心（胸外科/胸部肿瘤主战场）｜密切（外科/肿瘤/呼吸/影像大类常见胸科内容）｜相关（综合医学、泛肿瘤/外科，偶尔发）｜综合可发（顶级综合刊，理论上可发重磅试验）
- note：一句话理由（如「胸部外科手术方法学主刊」）

**输出（唯一允许写的文件）：**
`D:\trackeep-thoradar\design\sweep-judged-cursor.csv`
——与输入同列，末尾追加 3 列：include, relation, note；行序与输入一致；编码 utf-8-sig。

**自验（完成前必做）：**
①行数=280（加表头 281）；②include/relation 无空值；③stdout 打印 include=yes 计数与四档 relation 计数。

## 禁区
- 只写上述一个输出文件；禁改其他任何文件；禁 `git commit`／`git push`
- Python 一律 `E:/Python/python.exe -X utf8 -I`；bash 路径用正斜杠
- 不需要联网（判断基于你自己的期刊知识＋CSV 内数据）
