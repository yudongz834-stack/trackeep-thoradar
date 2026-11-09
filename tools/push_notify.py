#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日报推送（通道①：企业微信群机器人；④飞书/TG 预留）。

产业级五件套：送达回执（push_log.json 台账）＋失败重试（3 发指数退避）＋
断粮告警（数据滞后 >2 天推送里明写）＋密钥掩码（日志只见尾 4 位）＋
发送失败不阻断发布（工作流侧只警告）。

用法：python3 tools/push_notify.py [--dry-run]
密钥：WECOM_WEBHOOK 环境变量（GitHub secret 同名注入）。
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LOG = DATA / "push_log.json"
SITE_URL = os.environ.get("SITE_URL", "https://yudongz834-stack.github.io/trackeep-thoradar/")
WECOM_LIMIT = 4096  # 企微 markdown 正文上限（字节）


def compose_digest(radar: dict) -> str:
    """从 radar_latest.json 组装企微 markdown 日报。"""
    papers = radar.get("papers", [])
    gen_at = (radar.get("generated_at") or "")[:16]
    days = papers and max((p.get("briefing_date") or "") for p in papers) or ""
    todays = [p for p in papers if p.get("briefing_date") == days]

    lines = [f"# 🫁 胸科雷达 · {days} 日报", ""]

    # 断粮告警：数据产物生成时间距今 >2 天（金雷达判例：推送正常≠内容正常）
    try:
        gen_date = date.fromisoformat((radar.get("generated_at") or "")[:10])
        lag = (date.today() - gen_date).days
    except ValueError:
        lag = -1
    if lag > 2:
        lines.insert(1, f"> ⚠️ **数据滞后 {lag} 天，管线可能断粮，下文仅供参考**")
    elif lag >= 0:
        lines.insert(1, f"> 数据时间 {gen_at}（正常）")

    lines.append(f"今日新收 **{len(todays)}** 篇（90 天池共 {radar.get('count', len(papers))} 篇）")
    cats = Counter(p.get("category_label") or p.get("category") or "其他" for p in todays)
    if cats:
        lines.append("分类速览：" + " ｜ ".join(f"{k} {v}" for k, v in cats.most_common(6)))
    lines.append("")

    top = sorted(todays, key=lambda p: -(p.get("score_total") or 0))[:8]
    if top:
        lines.append("**今日精选**")
        for i, p in enumerate(top, 1):
            title = (p.get("title_zh") or p.get("title_en") or "(无题)")[:42]
            url = p.get("url") or f"https://pubmed.ncbi.nlm.nih.gov/{p.get('pmid', '')}/"
            lines.append(f"{i}. [{title}]({url})")
            lines.append(f"   *{p.get('journal_abbr', '?')}* · {p.get('tier', '')} · {p.get('score_total', 0)} 分")
    else:
        lines.append("今日暂无新收录。")

    lines.append("")
    lines.append(f"[🌐 全量看板]({SITE_URL}) · 由胸科专科判官自动筛选")
    content = "\n".join(lines)
    if len(content.encode("utf-8")) > WECOM_LIMIT:        # 截到上限内（保标题保链接）
        content = content.encode("utf-8")[:WECOM_LIMIT - 32].decode("utf-8", "ignore") + "\n…"
    return content


def send_wecom(webhook: str, content: str) -> dict:
    """POST 企微机器人；3 发指数退避；回执进台账（密钥掩码）。"""
    payload = json.dumps({"msgtype": "markdown", "markdown": {"content": content}}).encode("utf-8")
    key_hint = "****" + webhook.rstrip("/").rsplit("=", 1)[-1][-4:]
    last = ""
    for attempt in range(3):
        try:
            req = urllib.request.Request(webhook, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            if body.get("errcode") == 0:
                return {"ok": True, "attempts": attempt + 1, "key": key_hint}
            last = f"errcode={body.get('errcode')} {body.get('errmsg', '')}"
        except Exception as e:  # noqa: BLE001 网络抖动重试
            last = str(e)
        time.sleep(2 * (attempt + 1))
    return {"ok": False, "attempts": 3, "key": key_hint, "error": last[:120]}


def log_push(entry: dict) -> None:
    rows = []
    if LOG.exists():
        try:
            rows = json.loads(LOG.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 台账损坏从零记
            rows = []
    entry.setdefault("ts", datetime.now().isoformat(timespec="seconds"))
    rows.append(entry)
    LOG.write_text(json.dumps(rows[-200:], ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> int:
    dry = "--dry-run" in sys.argv
    radar = json.loads((DATA / "radar_latest.json").read_text(encoding="utf-8"))
    content = compose_digest(radar)

    if dry:
        print(content)
        print(f"--- dry-run · {len(content.encode('utf-8'))} bytes · 不发送 ---")
        return 0

    webhook = os.environ.get("WECOM_WEBHOOK", "").strip()
    if not webhook:
        print("WECOM_WEBHOOK 未配置，跳过推送")
        return 0
    r = send_wecom(webhook, content)
    log_push({"channel": "wecom", **r})
    print(f"企微推送 {'成功' if r['ok'] else '失败'}（{r['attempts']} 发） {r.get('error', '')}")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
