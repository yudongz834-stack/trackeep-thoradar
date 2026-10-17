# K3 设计任务书（胸科雷达原型 · 无方向限制版）

## PI 原话
「不做任何限制，让 K3 做几版原型我看看，只要求 trackeep 风格。」

## 你的任务
给「胸科雷达 ThorRadar」（胸部肿瘤文献每日雷达站，读者＝胸外科医生/研究者）做一版界面原型。**方向、布局、气质完全由你定，不设任何限制**——唯一硬要求是下方 Trackeep 风格 token（逐字用，不改值）。派出多席各做一版，方向由各席自己定，追求彼此不同。

## 唯一风格硬约束：Trackeep token 冻结块 v1（逐字）

```css
:root{--bg:#F0EEE6;--card:#FAF9F5;--card-2:#F5F3EC;--line:#DFDACB;--text:#1F1E1D;--text-2:#46433C;--muted:#7A7568;--accent:#D97757;--accent-dark:#BC5F3F;--accent-soft:#F5E8E1;--accent-on-soft:#A34A28;--success:#2F9E44;--success-soft:#E7F3EA;--success-on-soft:#2B7A3F;--warning:#E8590C;--warning-soft:#FCEBDD;--warning-on-soft:#A64309;--danger:#C92A2A;--danger-soft:#FBE7E7;--danger-on-soft:#B02525;--shadow-sm:0 1px 2px rgba(31,30,29,.05);--shadow-card:0 1px 2px rgba(31,30,29,.04),0 10px 30px -14px rgba(31,30,29,.12)}
html.dark{--bg:#26241f;--card:#302d27;--card-2:#2b2823;--line:#4a453d;--text:#ece7de;--text-2:#c5bfb2;--muted:#9c9488;--nav:#2b2823;--accent:#e08a6a;--accent-dark:#c9744f;--accent-soft:#3a2b23;--on-accent:#26241f;--accent-on-soft:#e8b49a;--success:#5cb974;--success-soft:#26372b;--success-on-soft:#8fd0a0;--warning-soft:#3a2f1e;--warning-on-soft:#e0a86a;--danger:#e07a7a;--danger-soft:#3a2626;--danger-on-soft:#e8a0a0;--shadow-sm:0 1px 2px rgba(0,0,0,.3);--shadow-card:0 1px 2px rgba(0,0,0,.3),0 10px 30px -14px rgba(0,0,0,.5);color-scheme:dark}
--font-sans:"Segoe UI Variable Text","Segoe UI","Noto Sans SC","Microsoft YaHei UI",system-ui,-apple-system,sans-serif;
--font-serif:"Georgia","Cambria","Palatino Linotype","Noto Serif SC",serif;
--font-mono:"Cascadia Mono","Consolas",ui-monospace,monospace;
```

## 素材（可自由取用）
- 真实数据：`D:/trackeep-thoradar/data/archive/2026-10-17.json`（36 篇今日文献）＋ `data/status.json`；字段语义可参考生产 `index.html` 渲染 JS。建议用真数据，原型才有真实感；怎么呈现由你。
- 背景常识：站名「胸科雷达 ThorRadar」，单文件静态站，GitHub Pages 托管，每天早上的胸科文献雷达。

## 交付与自验
1. 你的版本写到任务里指定的文件名（如 `design/k3-a.html`）——**单文件自包含，离线双击可开，禁外部 CDN/联网字体**。
2. 完稿后用 headless 浏览器截图自验：桌面 1440px＋手机 390px（headless Edge 最小布局宽约 489px，390 用 iframe 包裹法），截图存 `design/shots-k3/`（文件名带你的版本字母）。破版就修。
3. 写 5-10 行设计说明，存 `design/k3-<版本字母>-说明.md`。

## 禁区（不是设计限制，是家规）
- 只许写 `D:/trackeep-thoradar/design/` 目录；其他一切文件只读（含 index.html、thoradar_engine.py、data、.github）。
- 禁 `git commit`／`git push`。
- 禁出现任何个人/机构信息、禁出现「AIHOT」或其他品牌字样。
- 机器规则：Python 用 `E:/Python/python.exe -X utf8 -I`；bash 路径用正斜杠。
