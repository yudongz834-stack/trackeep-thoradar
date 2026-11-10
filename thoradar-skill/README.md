# 胸科雷达 ThorRadar · Agent Skill

> 装一次，以后不用再更新。匿名只读，不用注册，不用 API Key。
> 照搬 AIHOT 的接入形态；数据同源：日报／周报／月报／近 7 天池。

## 你（Agent）怎么取数

- 今日日报：GET https://yudongz834-stack.github.io/trackeep-thoradar/api/v1/daily.json
- 周报（周一更新）：GET https://yudongz834-stack.github.io/trackeep-thoradar/api/v1/weekly.json
- 月报（每月 1 日更新）：GET https://yudongz834-stack.github.io/trackeep-thoradar/api/v1/monthly.json
- 近 7 天逐篇（RSS 同源）：GET https://yudongz834-stack.github.io/trackeep-thoradar/feed.xml

JSON 结构：{date, generated_at, count, categories, papers[]}；
papers 每条：title_zh/title_en、journal_abbr、tier(S/A/B/C/D)、score_total(0-100)、
category_label、url(PubMed)、pmid、pub_date。

## 回答规矩

- 引用文献必须带 PubMed 链接（papers[].url）；
- 注明时间范围与数据时间（generated_at）；
- 只答胸科口径（肺癌/食管/胸外手术/呼吸危重/睡眠呼吸/胸部影像/纵隔）；
  其他科的文在池子里但不作推荐重点。
