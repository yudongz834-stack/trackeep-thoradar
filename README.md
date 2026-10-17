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

## 数据职责（权威源与派生物）

| 文件 | 角色 | 规则 |
| --- | --- | --- |
| `data/archive/<date>.json` | **权威日档** | 保存当日抓到与发布的内容；当日重跑可覆写，**隔日永不回改**（撤稿/更正也不改它） |
| `data/status.json` | **出版状态覆盖层** | 记录每篇文献最新状态（ok/撤稿/更正/关注声明）与回查时间；展示与导出统一应用最新状态 |
| `data/daily_briefing_<date>.md` | 派生早报 | 引擎每日生成 |
| `index.html` | 派生视图 | 数据经标记区间注入（SITE_DATA 块勿手改） |
| 本地仓库 ↔ GitHub | 互为镜像 | 推送保持一致 |

## 诚实边界（读数据前必读）

- 全站**无人审校**：标题、结果陈述、疑点提示由程序与语言模型生成。数值核验为确定性文本比对（数值存在性＋句内语境锚），能拦编造数字；**语义核验（人群/终点错配）未上线，如实标注**。重要文献请点开 PubMed 原文。
- **失败降级**：核验未通过/异常，或文献存在撤稿·更正（影响未明）·关注声明时，卡片自动「解读暂停」，只呈现题录与官方链接。
- 期刊分区为 2025 年静态快照（字典内 `tiering.data_year`），页面标注「截至 2025」。
- 摘要仅展示开头两句＋官方链接（版权属出版商，本站不做全文再发布）。
- 评分只用于排序，不构成临床建议。
- 反馈：卡片「反馈」按钮复制预填报错文本（含文献 ID 与核验状态），贴群即可；反馈触发自动重查，不直接作为修改事实的依据。

## 目录

```
index.html                  单文件网站（数据经标记区间注入，勿手改 SITE_DATA 块）
thoradar_engine.py          每日流水线引擎（采集→定级→预筛→精评→核验→状态覆盖→产出）
config/journals_taxonomy.json  期刊字典（身份/分区分开记录版本与年份）
data/archive/<date>.json    权威日档（当日冷存，隔日不改）
data/status.json            出版状态覆盖层（撤稿/更正/关注声明＋回查时间）
data/daily_briefing_*.md    每日简报 Markdown（引擎写）
data/regression/            工程回归集与报告（--build-regression / --regression）
.github/workflows/daily_thoradar.yml  每日定时流水线（含静默断粮熔断闸）
```

## 免责声明

本站为文献检索与学习辅助工具，所有内容摘要由自动流程生成，可能存在错误；
不构成医疗建议，临床决策请以原文与指南为准。
