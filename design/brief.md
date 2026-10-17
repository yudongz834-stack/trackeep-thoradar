# Agron 委任状＋任务书（读完整份再动手）

## 委任状（五行简化版）

- 轨道位置：trackeep-thoradar（胸科雷达，已上线系统仓）→ 一次性界面设计席 Agron（不进登记册）
- R 级：R1——只允许在 `D:\trackeep-thoradar\design\` 目录内新建/修改文件
- 判级理由：新增设计稿可整体丢弃，生产文件零改动，风险可回收
- 签发：Orchestrator（D:\workbench 主会话），2026-10-17；PI 口谕「派遣 agy-gemini 4agron 设计网站界面，让他发挥，只要遵循我们的 trackeep 风格就好」

## 你是谁、做什么

你是 Agron，界面设计师。给「胸科雷达 ThorRadar」出一版**读者向**的网站界面，交付一个自包含 HTML 原型。**发挥空间给你**：布局、信息架构、视觉语言、动效都由你定，只要惊艳、像一个真正被认真设计过的刊物级网站。唯一风格硬约束是下方 Trackeep token 冻结块（逐字使用，不许改值）。

## 背景（PI 原话，为什么找你）

- 现上线界面被 PI 判「整个网站的界面都设计得不对」——它长得像工程师控制台，不是给人读的刊物。
- 上一版原型被 PI 判「画得太丑了，这根本就不像一个网站」。
- 本站真实定位：胸外科医生/研究者每天早上花十分钟扫一遍胸部肿瘤文献新动态的**阅读站**——像一本每天更新的专业刊物，不是仪表盘。
- 可参考的既有件（不必受它们束缚，PI 要看你的东西）：`D:\trackeep-thoradar\index.html`（现生产站，可看数据渲染字段含义）；`D:\trackeep-thoradar\prototype.html`（前人原型 v5，可看可超越）。

## 硬事实（内容要求，一条不能破）

1. **四层内容导航**：精选（编辑精选，允许为空——空就明说「今日空缺，不凑数」）／动态（当日全量文献流）／趋势（热点、日报、周报、月报）／主题（长期主题档案）。
2. **每篇文献卡片四分离**：研究设计／实际结果／作者结论／AI 疑点，分开呈现；信息不足留白，不硬写。
3. **状态三态分明**：撤稿／更正／关注声明——各自不同标记；命中任一即「解读暂停」，只留题录＋官方链接。
4. **官方链接必备**：PubMed／DOI。
5. **摘要只展示开头两句**（版权边界），完整内容走官方链接。
6. **诚实底线**：不准放假数据、假徽章、假统计、假「提交成功」；页面须标注「程序生成·无人审」类诚实声明；分区标注「截至 2025」。**禁止出现「AIHOT」或任何他人品牌字样。**
7. **手机端 390px 必须可读、不破版。**
8. 界面语言：中文（zh-CN）。

## 数据（用真的，不编）

- 读 `D:\trackeep-thoradar\data\archive\2026-10-17.json`（当日权威日档，papers 数组，字段自解释：pmid/title/journal/评分/四分离内容/链接/publish_state 等）＋ `D:\trackeep-thoradar\data\status.json`（出版状态覆盖层）。
- 字段语义拿不准就看 index.html 的渲染 JS。
- 原型＝静态自包含单文件 HTML，数据直接内嵌写死（生产的数据注入机制你不用实现），但**必须由真实日档数据驱动**，精选/动态/趋势各层都从这份真数据组织。

## 风格（唯一硬约束：Trackeep token 冻结块 v1，逐字用，不改值）

```css
/* trackeep 家族 token 冻结块 v1 —— 正本＝terminal-console/web/design-tokens.css */
:root{--bg:#F0EEE6;--card:#FAF9F5;--card-2:#F5F3EC;--line:#DFDACB;--text:#1F1E1D;--text-2:#46433C;--muted:#7A7568;--accent:#D97757;--accent-dark:#BC5F3F;--accent-soft:#F5E8E1;--accent-on-soft:#A34A28;--success:#2F9E44;--success-soft:#E7F3EA;--success-on-soft:#2B7A3F;--warning:#E8590C;--warning-soft:#FCEBDD;--warning-on-soft:#A64309;--danger:#C92A2A;--danger-soft:#FBE7E7;--danger-on-soft:#B02525;--shadow-sm:0 1px 2px rgba(31,30,29,.05);--shadow-card:0 1px 2px rgba(31,30,29,.04),0 10px 30px -14px rgba(31,30,29,.12)}
/* /trackeep 家族 token 冻结块 */

/* 深色块（承 trackeep-ui.css §1c） */
html.dark{
  --bg:#26241f;--card:#302d27;--card-2:#2b2823;--line:#4a453d;--text:#ece7de;--text-2:#c5bfb2;--muted:#9c9488;--nav:#2b2823;
  --accent:#e08a6a;--accent-dark:#c9744f;--accent-soft:#3a2b23;--on-accent:#26241f;--accent-on-soft:#e8b49a;
  --success:#5cb974;--success-soft:#26372b;--success-on-soft:#8fd0a0;
  --warning-soft:#3a2f1e;--warning-on-soft:#e0a86a;
  --danger:#e07a7a;--danger-soft:#3a2626;--danger-on-soft:#e8a0a0;
  --shadow-sm:0 1px 2px rgba(0,0,0,.3);--shadow-card:0 1px 2px rgba(0,0,0,.3),0 10px 30px -14px rgba(0,0,0,.5);
  color-scheme:dark;
}

/* 字体栈（家族同款） */
--font-sans:"Segoe UI Variable Text","Segoe UI","Noto Sans SC","Microsoft YaHei UI",system-ui,-apple-system,sans-serif;
--font-serif:"Georgia","Cambria","Palatino Linotype","Noto Serif SC",serif;
--font-mono:"Cascadia Mono","Consolas",ui-monospace,monospace;
```

## 交付

1. `D:\trackeep-thoradar\design\agron-v1.html`——单文件自包含，离线双击可用（**禁外部 CDN/联网字体**，图标用内联 SVG，字体用上方系统字体栈）。
2. **自验后才算完成**：用 headless 浏览器截图亲眼验渲染——桌面 1440px＋手机 390px（提示：headless Edge 有约 489px 最小布局宽度钳制，验 390px 用 iframe 包裹法），截图存 `design\shots\`。有破版就修，修到干净。
3. `D:\trackeep-thoradar\design\agron-设计说明.md`——一页：你的设计决策、四层各自怎么呈现、PI 三条反馈（像控制台／太丑／不像网站）你分别怎么解的。

## 禁止

- 禁改 `design\` 之外的任何文件（index.html、thoradar_engine.py、data、.github、prototype.html 全部只读）。
- 禁 `git commit`／`git push`。
- 禁联网抓新数据（用仓库现成日档）。
- 禁外部 CDN 依赖。

## 机器规则

- Python 一律 `E:/Python/python.exe -X utf8 -I`（裸 `python` 是坏桩）。
- bash 里 Windows 路径写正斜杠。
