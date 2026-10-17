# Agron 任务书 v2 —— 网站式界面（AIhot 门户骨架 × Trackeep 皮肤）

## 委任状（五行简化版）

- 轨道位置：trackeep-thoradar（胸科雷达，已上线系统仓）→ 一次性界面设计席 Agron（延续）
- R 级：R1——只允许写 `D:\trackeep-thoradar\design\` 目录内新文件
- 判级理由：新增设计稿可整体丢弃，生产零改动
- 签发：Orchestrator（D:\workbench 主会话），2026-10-17；PI 裁定「前两版是刊物排版，要 AIhot 那种网站式界面」

## 一、这次错在哪（PI 原话）

PI：「我们要的是网站的那种界面……AIhot 那样。」
前两版（agron-v1 / agron-argon）做成了**报纸刊物排版**——大衬线标题、通栏文章流。
PI 要的是**现代 Web 门户产品**：顶栏、大卡英雄区、榜单、侧栏小部件、hover 动效。
结构学原包 `D:/tmp/thor-hot-ref/index.html`（它就是仿 AIhot 的骨架），皮肤用 Trackeep token。

## 二、硬性结构（一条不能少，这就是「网站那种」的定义）

1. **Sticky 应用顶栏**：左＝品牌标＋「胸科雷达」；中＝主导航（精选/动态/趋势/主题，页签式带计数徽章）；右＝搜索框＋深色切换。滚动时顶栏吸顶。
2. **英雄区（Hero）**：今日评分最高文献做**今日头条大卡**（占主栏 2/3 宽，带「今日头条」角标、关键结论胶囊、期刊徽章），右侧并排 2 张次级卡（次高评分）。整块用 Trackeep 陶土橙系渐变或 accent-soft 大底（原包用的是蓝色渐变，我们换成暖橙系）。
3. **今日热点 TOP 榜**：榜单组件，5-8 条，**第 1/2/3 名带名次徽章**（金/银/铜或橙系三档），条目=标题一句＋期刊＋评分＋状态点。
4. **主体双栏**：左主栏＝文献卡流＋**分类 pill 筛选行（带实时计数）**；右侧栏＝**sticky 小部件堆**：①今日漏斗（抓取→初筛→入库→精选，真数字）②活跃试验 ③趋势速览（本周条形）④出版状态播报（ok/撤稿/更正/关注计数）。
5. **Web 质感细节**：卡圆角 10-14px、hover 上浮＋shadow-card、pill/chip/徽章体系、按钮实心 accent 主按钮＋ghost 次按钮、入场淡入动效、数字等宽字体。
6. **产品化 Footer**：三栏（关于本站/数据说明/反馈渠道）＋诚实声明行。
7. **移动端 390px**：侧栏折到主栏下方、顶栏精简、pill 行横滑。

## 三、内容与诚实规则（照旧，一条不能破）

- 精选可为空（「今日空缺，不凑数」）；卡片四分离（研究设计/实际结果/作者结论/AI 疑点），信息不足留白注明；撤稿/更正/关注三态分明、命中即「解读暂停」；PubMed/DOI 官方链接必备；摘要仅开头两句；「程序生成·无人审校」「分区截至 2025」标注；禁 AIHOT 字样、禁假数据假徽章；**公开页不放状态切换演示钮**（预览需求砍掉）。
- 数据：真读 `data/archive/2026-10-17.json` + `data/status.json`（字段语义参考生产 index.html 渲染 JS）；自包含单文件、离线双击可用、零 CDN。

## 四、风格（唯一视觉硬约束：token 冻结块逐字，不改值）

```css
:root{--bg:#F0EEE6;--card:#FAF9F5;--card-2:#F5F3EC;--line:#DFDACB;--text:#1F1E1D;--text-2:#46433C;--muted:#7A7568;--accent:#D97757;--accent-dark:#BC5F3F;--accent-soft:#F5E8E1;--accent-on-soft:#A34A28;--success:#2F9E44;--success-soft:#E7F3EA;--success-on-soft:#2B7A3F;--warning:#E8590C;--warning-soft:#FCEBDD;--warning-on-soft:#A64309;--danger:#C92A2A;--danger-soft:#FBE7E7;--danger-on-soft:#B02525;--shadow-sm:0 1px 2px rgba(31,30,29,.05);--shadow-card:0 1px 2px rgba(31,30,29,.04),0 10px 30px -14px rgba(31,30,29,.12)}
html.dark{--bg:#26241f;--card:#302d27;--card-2:#2b2823;--line:#4a453d;--text:#ece7de;--text-2:#c5bfb2;--muted:#9c9488;--nav:#2b2823;--accent:#e08a6a;--accent-dark:#c9744f;--accent-soft:#3a2b23;--on-accent:#26241f;--accent-on-soft:#e8b49a;--success:#5cb974;--success-soft:#26372b;--success-on-soft:#8fd0a0;--warning-soft:#3a2f1e;--warning-on-soft:#e0a86a;--danger:#e07a7a;--danger-soft:#3a2626;--danger-on-soft:#e8a0a0;--shadow-sm:0 1px 2px rgba(0,0,0,.3);--shadow-card:0 1px 2px rgba(0,0,0,.3),0 10px 30px -14px rgba(0,0,0,.5);color-scheme:dark}
--font-sans:"Segoe UI Variable Text","Segoe UI","Noto Sans SC","Microsoft YaHei UI",system-ui,-apple-system,sans-serif;
--font-serif:"Georgia","Cambria","Palatino Linotype","Noto Serif SC",serif;
--font-mono:"Cascadia Mono","Consolas",ui-monospace,monospace;
```

## 五、交付与抗断流纪律

1. 交付 `design/agron-web.html`（不覆盖前两版）；截图存 `design/shots-web/`（桌面 1440 ＋ 手机 390 iframe 包裹法）；说明写 `design/agron-web-设计说明.md`。
2. **高频落盘**：先写骨架整文件，之后每完成一个区块用完整重写方式保存（任何时刻文件完整可打开，单次生成 ≤80 行）。
3. 顺序：CSS 与顶栏 → 英雄区 → TOP 榜 → 双栏主体 → 侧栏部件 → 趋势/主题层 → 交互 → 自验截图 → 说明。
4. 禁改 design 外文件、禁 git、禁联网抓数据。Python 用 `E:/Python/python.exe -X utf8 -I`；bash 路径用正斜杠。
