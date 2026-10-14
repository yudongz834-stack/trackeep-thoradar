# 胸科雷达 ThorRadar

胸部肿瘤文献每日雷达：每天早上自动抓取 PubMed 新入库的胸部肿瘤文献，期刊定级、预筛、
LLM 精评（PICO 提取 + 反阳性偏倚条款）、四元组数值核验，产出单页网站与中文每日简报。
设计思路受 [AIHOT](https://github.com/KKKKhazix/AIHOT) 启发，引擎为面向生物医学文献的独立实现。

## 快速使用

- **只看网站**：双击 `index.html` 即可（数据内嵌，无需服务器）。
- **本地跑流水线**：
  ```bash
  python thoradar_engine.py --self-test   # 离线自测
  python thoradar_engine.py               # 正式运行（无 LLM_API_KEY 自动走启发式模式）
  ```
- **全自动**：推到 GitHub 后配置 Secrets（见下），每天北京时间 07:30 自动更新（GitHub Pages 托管 `index.html`）。

## 环境变量（GitHub Secrets 或本地环境变量）

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `LLM_API_KEY` | 否 | OpenAI 兼容接口密钥；不填则降级启发式模式（卡片会如实标注） |
| `LLM_BASE_URL` / `LLM_MODEL` | 否 | 默认 DeepSeek `deepseek-chat` |
| `LLM_PRICE_IN` / `LLM_PRICE_OUT` | 否 | 每百万 token 单价（美元），用于成本估算 |
| `MAX_DAILY_COST_USD` | 否 | LLM 成本熔断，默认 0.10 |
| `NCBI_API_KEY` | 否 | [免费申请](https://www.ncbi.nlm.nih.gov/account/)，限速 3→10 req/s |

密钥永不入库（`.gitignore` 已挡 `.env`）；工作流通过 Secrets 注入。

## 诚实边界（读数据前必读）

- 四元组核验是**确定性文本比对**（数值存在性 + 语境锚定），能拦编造数字与明显错配；
  **不能**识别「同一数值安到不同人群」的高级张冠李戴。卡片核验状态为 ⚠ 或用于临床决策前，请点开英文原摘要人工复核。
- 评分（AI 或启发式）只用于排序，不构成临床建议。
- 期刊字典（`config/journals_taxonomy.json`）与 IF 值为静态快照，会过时；未收录期刊按 B 级处理。

## 目录

```
index.html                  单文件网站（数据经标记区间注入，勿手改 SITE_DATA 块）
thoradar_engine.py          每日流水线引擎（采集→定级→预筛→精评→核验→产出）
config/journals_taxonomy.json  期刊五重索引字典（S/A/B 三级）
data/curated_literature.json   当日精选数据（引擎写）
data/daily_briefing_*.md       每日简报 Markdown（引擎写）
data/archive/                  按日归档
.github/workflows/daily_thoradar.yml  每日定时流水线（含静默断粮熔断闸）
```

## 免责声明

本站为文献检索与学习辅助工具，所有内容摘要由自动流程生成，可能存在错误；
不构成医疗建议，临床决策请以原文与指南为准。
