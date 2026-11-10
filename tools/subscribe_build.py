#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""订阅件生成（照搬 AIHOT 四通道：RSS／REST API／Agent Skill／MCP 读同一份数据）。

产物（全静态、匿名只读、不要 Key，随 Pages 发布）：
  feed.xml                 RSS 2.0（近 7 天逐篇，阅读器可订）
  api/v1/daily.json        今日批次（日报同源）
  api/v1/weekly.json       周报（仅周一 --weekly 生成）
  api/v1/monthly.json      月报（仅每月 1 日 --monthly 生成）
  thoradar-skill/README.md Agent Skill 安装件（装一次免更新）

节奏（照搬 AIHOT）：日报每天；周报周一；月报每月 1 日。
--weekly / --monthly 生成对应件并推飞书卡片（经 push_notify 同一条线）。
"""
import json
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone, time as dtime
from email.utils import format_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import push_notify as pn  # noqa: E402  复用 _clip/MSG_LIMIT/send_feishu/日志

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = pn.SITE_URL


def _load() -> dict:
    return json.loads((DATA / "radar_latest.json").read_text(encoding="utf-8"))


def _window(radar: dict, days: int) -> list:
    """近 N 天批次（含今天；按 briefing_date 取窗）。"""
    papers = radar.get("papers", [])
    if not papers:
        return []
    end = max((p.get("briefing_date") or "") for p in papers)
    end_d = date.fromisoformat(end)
    start_d = end_d - timedelta(days=days - 1)
    return [p for p in papers
            if start_d <= date.fromisoformat(p.get("briefing_date") or "1970-01-01") <= end_d]


def compose_period(radar: dict, label: str, days: int) -> tuple:
    """周报/月报卡片：(title, body)。label 如 '周报 (11-03~11-09)'。"""
    rows = _window(radar, days)
    title = f"🫁 胸科雷达 · {label}"
    lines = [f"数据时间 {(radar.get('generated_at') or '')[:16]} · 窗内共 **{len(rows)}** 篇"]
    cats = Counter(p.get("category_label") or "其他" for p in rows)
    if cats:
        lines.append("分类分布：" + " ｜ ".join(f"{k} {v}" for k, v in cats.most_common(8)))
    lines.append("")
    top = sorted(rows, key=lambda p: -(p.get("score_total") or 0))[:15]
    lines.append(f"**窗内精选 Top{len(top)}**")
    for i, p in enumerate(top, 1):
        t = (p.get("title_zh") or p.get("title_en") or "(无题)")[:42]
        url = p.get("url") or f"https://pubmed.ncbi.nlm.nih.gov/{p.get('pmid', '')}/"
        lines.append(f"{i}. [{t}]({url})")
        lines.append(f"   {p.get('journal_abbr', '?')} · {p.get('tier', '')} · {p.get('score_total', 0)} 分")
    lines.append("")
    lines.append(f"[🌐 全量看板]({SITE}) · 由胸科专科判官自动筛选 ｜ 金雷达出品")
    return title, pn._clip("\n".join(lines).replace("*", ""))


def build_feed(radar: dict) -> str:
    """RSS 2.0：近 7 天逐篇（阅读器订阅面）。"""
    rows = sorted(_window(radar, 7), key=lambda p: p.get("briefing_date") or "", reverse=True)[:50]
    items = []
    for p in rows:
        t = (p.get("title_zh") or p.get("title_en") or "(无题)")
        url = p.get("url") or f"https://pubmed.ncbi.nlm.nih.gov/{p.get('pmid', '')}/"
        desc = f"{p.get('journal_abbr', '')} · {p.get('tier', '')} · {p.get('score_total', 0)} 分 · {p.get('category_label', '')}"
        try:
            dt = datetime.combine(date.fromisoformat(p.get("briefing_date")), dtime(8, 0),
                                  tzinfo=timezone(timedelta(hours=8)))
            pub = format_datetime(dt)
        except ValueError:
            pub = ""
        items.append(f"    <item>\n      <title>{_xml(t)}</title>\n      <link>{_xml(url)}</link>\n"
                     f"      <description>{_xml(desc)}</description>\n      <pubDate>{pub}</pubDate>\n"
                     f"      <category>{_xml(p.get('category_label') or '')}</category>\n    </item>")
    return ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<rss version=\"2.0\"><channel>\n"
            f"  <title>胸科雷达 ThorRadar</title>\n  <link>{SITE}</link>\n"
            "  <description>胸科医生的每日文献雷达——197 刊自动扫描、专科判官筛选</description>\n"
            + "\n".join(items) + "\n</channel></rss>\n")


def _xml(s) -> str:
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_daily_api(radar: dict) -> dict:
    rows = _window(radar, 1)
    return {"date": rows[0].get("briefing_date") if rows else "",
            "generated_at": radar.get("generated_at"), "count": len(rows),
            "categories": dict(Counter(p.get("category_label") or "其他" for p in rows)),
            "papers": rows}


SKILL_MD = """# 胸科雷达 ThorRadar · Agent Skill

> 装一次，以后不用再更新。匿名只读，不用注册，不用 API Key。
> 照搬 AIHOT 的接入形态；数据同源：日报／周报／月报／近 7 天池。

## 你（Agent）怎么取数

- 今日日报：GET {site}/api/v1/daily.json
- 周报（周一更新）：GET {site}/api/v1/weekly.json
- 月报（每月 1 日更新）：GET {site}/api/v1/monthly.json
- 近 7 天逐篇（RSS 同源）：GET {site}/feed.xml

JSON 结构：{{date, generated_at, count, categories, papers[]}}；
papers 每条：title_zh/title_en、journal_abbr、tier(S/A/B/C/D)、score_total(0-100)、
category_label、url(PubMed)、pmid、pub_date。

## 回答规矩

- 引用文献必须带 PubMed 链接（papers[].url）；
- 注明时间范围与数据时间（generated_at）；
- 只答胸科口径（肺癌/食管/胸外手术/呼吸危重/睡眠呼吸/胸部影像/纵隔）；
  其他科的文在池子里但不作推荐重点。
"""


def build_skill_readme() -> str:
    return SKILL_MD.format(site=SITE.rstrip("/"))


INSTALL_PROMPT = """请安装胸科雷达 Skill：{site}/thoradar-skill/README.md
装完在你平时执行命令的环境里请求一次 {site}/api/v1/daily.json；连不上的话，告诉我要怎么给你开联网。
装完告诉我是否需要开启新会话。"""


def main() -> int:
    radar = _load()
    mode = sys.argv[1] if len(sys.argv) > 1 else ""

    if mode == "--weekly":
        d = radar.get("generated_at", "")[:10]
        d = date.fromisoformat(d) if d else date.today()
        monday = d - timedelta(days=d.weekday())
        label = f"周报（{monday.month:02d}-{monday.day:02d}~{(monday + timedelta(days=6)).month:02d}-{(monday + timedelta(days=6)).day:02d}）"
        title, body = compose_period(radar, label, 7)
        (ROOT / "api" / "v1").mkdir(parents=True, exist_ok=True)
        (ROOT / "api" / "v1" / "weekly.json").write_text(json.dumps(
            {"period": label, "generated_at": radar.get("generated_at"),
             "count": len(_window(radar, 7)), "papers": _window(radar, 7)},
            ensure_ascii=False, indent=1), encoding="utf-8")
        _push(title, body, "weekly")
    elif mode == "--monthly":
        d = radar.get("generated_at", "")[:10]
        d = date.fromisoformat(d) if d else date.today()
        first = d.replace(day=1)
        prev_last = first - timedelta(days=1)
        label = f"月报（{prev_last.year}-{prev_last.month:02d}）"
        title, body = compose_period(radar, label, 31)
        (ROOT / "api" / "v1").mkdir(parents=True, exist_ok=True)
        (ROOT / "api" / "v1" / "monthly.json").write_text(json.dumps(
            {"period": label, "generated_at": radar.get("generated_at"),
             "count": len(_window(radar, 31)), "papers": _window(radar, 31)},
            ensure_ascii=False, indent=1), encoding="utf-8")
        _push(title, body, "monthly")
    else:
        # 日常三件：feed + daily API + skill README
        (ROOT / "api" / "v1").mkdir(parents=True, exist_ok=True)
        (ROOT / "feed.xml").write_text(build_feed(radar), encoding="utf-8")
        (ROOT / "api" / "v1" / "daily.json").write_text(
            json.dumps(build_daily_api(radar), ensure_ascii=False, indent=1), encoding="utf-8")
        (ROOT / "thoradar-skill" ).mkdir(exist_ok=True)
        (ROOT / "thoradar-skill" / "README.md").write_text(build_skill_readme(), encoding="utf-8")
        print(f"订阅件生成：feed.xml {len(_window(radar, 7))} 篇 · daily.json · skill README")
        print("安装提示词（给同事/Agent）：\n" + INSTALL_PROMPT.format(site=SITE.rstrip("/")))
    return 0


def _push(title: str, body: str, kind: str) -> None:
    hook = pn.os.environ.get("FEISHU_WEBHOOK", "").strip()
    if not hook:
        print(f"{kind} 件已生成（FEISHU_WEBHOOK 未配，不推送）")
        return
    r = pn.send_feishu(hook, title, body)
    pn.log_push({"channel": "feishu", "kind": kind, **r})
    print(f"{kind} 飞书推送 {'成功' if r['ok'] else '失败'}（{r['attempts']} 发）{r.get('error', '')}")


if __name__ == "__main__":
    sys.exit(main())
