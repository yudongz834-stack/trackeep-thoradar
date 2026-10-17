# 胸科雷达 ThorRadar — 网站式门户界面设计说明（Agron · Web v2 终版）

> **设计席位**：Agron（界面设计师）  
> **任务依据**：`design/brief-v2-web.md`（PI 裁定「前两版是刊物排版，要 AIhot 那种网站式界面」）  
> **交付产物**：  
> - 核心原型：[`design/agron-web.html`](file:///D:/trackeep-thoradar/design/agron-web.html)（单文件自包含、离线双击可用、零外部 CDN）  
> - 自验截图：[`design/shots-web/`](file:///D:/trackeep-thoradar/design/shots-web/)（桌面 1440px 全视图、精选空态、趋势台账、主题卷宗、深色模式、手机 390px iPhone iframe 包裹法实测）  
> - 驱动数据：`data/archive/2026-10-17.json`（当日 36 篇）＋ `data/status.json`（实时出版状态）＋ `data/archive/2026-10-15.json`（双批次汇总基准）

---

## 一、核心定位修正：彻底告别「报刊排版」，建立「现代 Web 门户」

前两版（`agron-v1` 与 `agron-argon`）被 PI 明确否决的核心原因在于**视觉母体偏差**：
- **错在哪**：前两版将胸科雷达做成了大衬线报头、通栏长文章流与章节眉题的「学术晨刊/报纸」，缺乏当代互联网门户产品的交互格局与信息密度。
- **改在哪**：本版严格遵循任务书，解构并吸收原包骨架（`D:/tmp/thor-hot-ref/index.html`）的**现代 Web 门户组件范式**（Sticky 顶栏、渐变大卡英雄区、名次榜单、横滑 Pill 筛选、Sticky 侧栏部件堆、卡片 hover 动效与抽屉展开），同时全面穿上 **Trackeep 家族 token 冻结块皮肤**，彻底禁绝外部品牌痕迹（禁 AIHOT 字样），实现高度产品化、专业化的胸科肿瘤学术门户。

---

## 二、七项硬性结构指标实现台账

| 序号 | 任务书硬性结构要求 | 界面实现方案与关键设计决策 | 验收截图定位 |
| :--- | :--- | :--- | :--- |
| **1** | **Sticky 应用顶栏** | 吸顶常驻（`position: sticky; top: 0; z-index: 100`），毛玻璃底透感。<br>· **左侧**：TK 陶土品牌标 ＋「胸科雷达」＋ 副标；<br>· **中间**：4 大主导航（⭐精选 `0`、📰动态 `36`、📊趋势 `W42`、📁主题 `6`）带微胶囊实时计数徽章；<br>· **右侧**：集成搜索框（支持实时模糊检索）＋ 明暗主题切换钮（🌙深色 / ☀️浅色）。 | `shots-web/desktop-1440.png` |
| **2** | **英雄区（Hero）** | 采用 **Trackeep 暖陶土橙系渐变大底**（`linear-gradient(135deg, rgba(217,119,87,.08), rgba(245,232,225,.45))`），营造学术温度与门户视觉锚点。<br>· **主头条大卡（2/3 宽）**：当日综合评分最高文献（*Cancer Cell* · PMID 42887497），带实心赤陶「🔥 今日头条」角标、期刊徽章、NCT05364073 试验徽章、关键突破胶囊（💡 PACC 突变肺癌靶向进展）、作者中心与官方直达按钮；<br>· **次级推荐卡（1/3 宽并排 2 张）**：上下堆叠次高分文献（#2 JCOG2510 III期 RCT 与 #3 食管癌微创），悬浮上浮反馈。 | `shots-web/desktop-1440.png` |
| **3** | **今日热点 TOP 榜** | 5~8 条高分文献榜单组件，双列响应式网格：<br>· **名次徽章**：#1 采用深陶土渐变金、#2 采用深岩银灰、#3 采用琥珀铜橙、#4~#8 采用细线低调徽章；<br>· **条目要素**：单行标题＋期刊＋综合评分＋专科标签＋NCT 编号＋健康出版状态呼吸绿点；<br>· **交互联动**：点击榜单任意条目，主栏平滑滚动定位并高亮对应文献卡片。 | `shots-web/desktop-1440.png` |
| **4** | **主体双栏（左主栏）** | · **横向滚动分类 Pill 行**：支持横滑，含全部 (36)、局晚期靶向免疫 (13)、微创胸外 (13)、围术期新辅助 (5)、肺结节早筛 (2)、食管纵隔 (2)、胸外 AI (1) 实时真计数；<br>· **快捷筛选**：仅看 NCT 试验 (3)、仅看 RCT/III期 (8)、我的收藏夹；<br>· **Web 质感文献卡流**：卡圆角 12px，卡片四分离（`01 研究设计`、`02 实际结果`、`03 作者结论`、`04 AI 疑点` 2×2 矩阵，缺失留白说明）；支持三态警示横幅、前两句摘要抽屉、BibTeX / Obsidian 笔记导出。 | `shots-web/desktop-1440-full.png` |
| **5** | **主体双栏（右侧栏）** | 吸顶常驻小部件堆（`position: sticky; top: 76px`）：<br>① **今日漏斗**：真数字呈现 56 初抓 → 39 匹配 → 36 预筛 → 36 收录 → 0 精选（空缺）；<br>② **活跃注册试验**：提取当日 3 项注册临床试验（NCT05364073、NCT05786430、NCT03539484），支持一键反向过滤主流；<br>③ **趋势速览**：本周 W42 双批次条形图（10-15：60 篇 vs 10-17：36 篇）；<br>④ **出版状态全景播报**：4 格状态监视器（36 正常、0 撤稿、0 更正、0 关注）。 | `shots-web/desktop-1440-full.png` |
| **6** | **产品化 Footer** | 三栏布局（关于本站定位 / 数据标准与诚信机制 / 学术反馈协作）＋ 底部诚实红线警示声明行（标注「程序生成 · 无人审校」「分区截至 2025 年」「摘要仅供检索导读，版权属原出版机构」）。 | `shots-web/desktop-1440-full.png` |
| **7** | **移动端 390px 适配** | 采用**任务书强制要求之「手机 390 iframe 包裹法」**自验（iPhone 14/15 390×844px 真实物理视口）：<br>· 顶栏自适应折行：第一行品牌标＋搜索/深色钮，第二行导航页签平滑横滑；<br>· 英雄区与双栏在 ≤860px 自动折叠为单列流式网格，侧栏小部件顺畅排列在文献流下方；<br>· 分类 Pill 行支持单指轻滑，零任何横向越界溢出。 | `shots-web/mobile-390.png` |

---

## 三、内容与诚实规则逐条执行情况

1. **精选可为空（「今日空缺，不凑数」）**：
   - 真实数据中 `curated: 0`。界面切换至「⭐ 精选」导航时，绝不硬拽普通文章凑数，而是以 2px 赤陶外框呈现大尺寸提示卡：**「今日精选为空 · 严守规则不凑数」**；
   - 详尽陈述三道未越过的硬规则（顶级期刊、高循证设计、四元组零幻觉），并提供直达今日 8 篇 RCT 与 3 项 NCT 注册试验的快捷分流。
2. **卡片四分离与诚实留白**：
   - 启发式模式下，未接入大模型提取的字段严谨呈现斜体灰字：`（启发式收录：数值未提取，留白不硬写）`、`（信息不足留白，不硬写）`，坚决不捏造虚假结论。
3. **出版状态三态分明与「解读暂停」熔断**：
   - 完整预置撤稿（retracted · 红色）、更正启事（corrected · 橙色）、关注声明（concern · 黄色）三套独立告警横幅样式；命中即标明「解读暂停，请勿引用」，收回非题录内容。公开页严格遵照委任状砍除状态切换演练钮，纯正呈现生产态。
4. **版权与导读边界**：
   - 每篇文献英文摘要抽屉**通过正则表达式强制仅截取开头两句**，注明出版商版权归属，引导至 PubMed 官方页与 DOI 原文直达链接。
5. **规范标注与零虚构**：
   - 顶栏、卡片、抽屉及页脚醒目标注「程序生成 · 无人审校 · 期刊分区数据截至 2025」；
   - 全页文本无任何 `AIHOT` 外部字样；无假数据、无无来源徽章。

---

## 四、视觉规范（Trackeep 家族 Token 冻结块逐字落实）

本设计稿全量变量完整逐字承袭正本，零私自篡改色值：

```css
/* 亮色基底 */
:root {
  --bg: #F0EEE6;
  --card: #FAF9F5;
  --card-2: #F5F3EC;
  --line: #DFDACB;
  --text: #1F1E1D;
  --text-2: #46433C;
  --muted: #7A7568;
  --accent: #D97757;
  --accent-dark: #BC5F3F;
  --accent-soft: #F5E8E1;
  --accent-on-soft: #A34A28;
  --success: #2F9E44;
  --success-soft: #E7F3EA;
  --success-on-soft: #2B7A3F;
  --warning: #E8590C;
  --warning-soft: #FCEBDD;
  --warning-on-soft: #A64309;
  --danger: #C92A2A;
  --danger-soft: #FBE7E7;
  --danger-on-soft: #B02525;
  --shadow-sm: 0 1px 2px rgba(31,30,29,.05);
  --shadow-card: 0 1px 2px rgba(31,30,29,.04),0 10px 30px -14px rgba(31,30,29,.12);
}
/* 深色基底 */
html.dark {
  --bg: #26241f;
  --card: #302d27;
  --card-2: #2b2823;
  --line: #4a453d;
  --text: #ece7de;
  --text-2: #c5bfb2;
  --muted: #9c9488;
  --nav: #2b2823;
  --accent: #e08a6a;
  --accent-dark: #c9744f;
  --accent-soft: #3a2b23;
  --on-accent: #26241f;
  --accent-on-soft: #e8b49a;
  --success: #5cb974;
  --success-soft: #26372b;
  --success-on-soft: #8fd0a0;
  --warning-soft: #3a2f1e;
  --warning-on-soft: #e0a86a;
  --danger: #e07a7a;
  --danger-soft: #3a2626;
  --danger-on-soft: #e8a0a0;
  --shadow-sm: 0 1px 2px rgba(0,0,0,.3);
  --shadow-card: 0 1px 2px rgba(0,0,0,.3),0 10px 30px -14px rgba(0,0,0,.5);
  color-scheme: dark;
}
```

---

## 五、自验截图清单与索引

所有截图已存入目录 [`design/shots-web/`](file:///D:/trackeep-thoradar/design/shots-web/)：

1. **桌面主屏全景（1440px）**：[`desktop-1440.png`](file:///D:/trackeep-thoradar/design/shots-web/desktop-1440.png)
   - 验证：Sticky 顶栏、Hero 暖橙系大卡矩阵、TOP 8 榜单（三档名次徽章）、分类 Pill 筛选行与左侧漏斗。
2. **桌面全量文献卡流（1440px 纵向全长）**：[`desktop-1440-full.png`](file:///D:/trackeep-thoradar/design/shots-web/desktop-1440-full.png)
   - 验证：36 篇文献卡流、四分离网格留白、右侧 sticky 小部件完整堆叠（漏斗/试验/趋势/状态）、产品化三栏页脚。
3. **精选规则空态视图**：[`desktop-1440-curated.png`](file:///D:/trackeep-thoradar/design/shots-web/desktop-1440-curated.png)
   - 验证：「今日精选为空 · 严守规则不凑数」大卡、三条准入规则解析及直达分流按钮。
4. **深色模式全景**：[`desktop-1440-dark.png`](file:///D:/trackeep-thoradar/design/shots-web/desktop-1440-dark.png)
   - 验证：`html.dark` 全局色值转换，字体高对比度，卡片阴影加深沉浸。
5. **趋势分析视图（W42 / 10 月台账）**：[`desktop-1440-trend.png`](file:///D:/trackeep-thoradar/design/shots-web/desktop-1440-trend.png)
   - 验证：125 篇抓取与 96 篇真实入库台账、活跃期刊分布横向条形图。
6. **主题档案视图（6 大专科卷宗）**：[`desktop-1440-topic.png`](file:///D:/trackeep-thoradar/design/shots-web/desktop-1440-topic.png)
   - 验证：6 大专科专题卡片、实时篇数统计与一键反向筛选联动。
7. **移动端实测（iPhone 390px iframe 包裹法）**：[`mobile-390.png`](file:///D:/trackeep-thoradar/design/shots-web/mobile-390.png)
   - 验证：真机物理边框包裹实测，顶栏折行收纳，导航页签横滑，Hero 垂直规整堆叠。
8. **移动端纵向流实测**：[`mobile-390-scroll.png`](file:///D:/trackeep-thoradar/design/shots-web/mobile-390-scroll.png)
   - 验证：文献卡单列适配，侧栏小部件顺滑折叠到主栏下方，无任何水平横向溢出。

---

## 六、抗断流与工程合规总结

1. **高频落盘与增量控制**：严格遵守「单次生成 ≤ 80 行」，从 HTML 骨架、CSS 顶栏、Hero 区、TOP 榜、双栏网格、侧栏部件到交互逻辑，均分步渐增落盘，全程保持文件完整且离线双击可用。
2. **零 CDN 与离线自包含**：通过真实读取 `data/archive/2026-10-17.json` 与 `data/status.json` 内嵌至单文件，Windows 本地直接双击即可流畅运行所有前端交互（分类过滤、搜索、抽屉、收藏、BibTeX 导出、明暗切换）。
3. **生产零污染**：全量代码均限制于 `D:\trackeep-thoradar\design\`，完全符合 R1 判定标准，无 git 操作，无外部网络依赖。
