#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日报推送（飞书通道＝主打；企微通道备用同接口）。

产业级五件套：送达回执（push_log.json 台账）＋失败重试（3 发指数退避）＋
断粮告警（数据滞后 >2 天推送里明写）＋密钥掩码（日志只见尾 4 位）＋
发送失败不阻断发布（工作流侧只警告）。

用法：python3 tools/push_notify.py [--dry-run]
密钥：FEISHU_WEBHOOK / WECOM_WEBHOOK 环境变量（GitHub secret 同名注入，
配哪个推哪个，都配双发）。发送强制直连不吃系统代理（金雷达实战教训）。
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
SITE_URL = os.environ.get("SITE_URL", "https://thoradar.online/")
MSG_LIMIT = 4096  # 企微 markdown／飞书卡片正文同此上限（字节），宁保守


def _compose_parts(radar: dict) -> tuple:
    """组装标题＋正文行（通道无关）。返回 (title, lines)。"""
    papers = radar.get("papers", [])
    gen_at = (radar.get("generated_at") or "")[:16]
    days = papers and max((p.get("briefing_date") or "") for p in papers) or ""
    todays = [p for p in papers if p.get("briefing_date") == days]
    title = f"🫁 胸科雷达 · {days} 日报"

    lines = []
    # 断粮告警：数据产物生成时间距今 >2 天（金雷达判例：推送正常≠内容正常）
    try:
        gen_date = date.fromisoformat((radar.get("generated_at") or "")[:10])
        lag = (date.today() - gen_date).days
    except ValueError:
        lag = -1
    if lag > 2:
        lines.append(f"⚠️ **数据滞后 {lag} 天，管线可能断粮，下文仅供参考**")
    else:
        lines.append(f"数据时间 {gen_at}（正常）")

    lines.append(f"今日新收 **{len(todays)}** 篇（90 天池共 {radar.get('count', len(papers))} 篇）")
    cats = Counter(p.get("category_label") or p.get("category") or "其他" for p in todays)
    if cats:
        lines.append("分类速览：" + " ｜ ".join(f"{k} {v}" for k, v in cats.most_common(6)))
    lines.append("")

    top = sorted(todays, key=lambda p: -(p.get("score_total") or 0))[:8]
    if top:
        lines.append("**今日精选**")
        for i, p in enumerate(top, 1):
            t = (p.get("title_zh") or p.get("title_en") or "(无题)")[:42]
            url = p.get("url") or f"https://pubmed.ncbi.nlm.nih.gov/{p.get('pmid', '')}/"
            lines.append(f"{i}. [{t}]({url})")
            lines.append(f"   {p.get('journal_abbr', '?')} · {p.get('tier', '')} · {p.get('score_total', 0)} 分")
    else:
        lines.append("今日暂无新收录。")

    lines.append("")
    # 「金雷达出品」＝关键词安全桥：金雷达机器人自定义关键词＝金雷达，缺词被拒(19024)。
    # PI 在机器人设置加「胸科雷达」关键词或建专属机器人后摘除此落款。
    lines.append(f"[🌐 全量看板]({SITE_URL}) · 由胸科专科判官自动筛选 ｜ 金雷达出品")
    return title, lines


def compose_digest(radar: dict) -> str:
    """企微 markdown 日报（含 # 标题行）。"""
    title, lines = _compose_parts(radar)
    content = "\n".join([f"# {title}", ""] + lines)
    return _clip(content)


def compose_feishu(radar: dict) -> tuple:
    """飞书卡片（标题进卡片头，正文 lark_md——无斜体无井号，去 *）。"""
    title, lines = _compose_parts(radar)
    body = _clip("\n".join(lines).replace("*", ""))
    return title, body


def _clip(content: str) -> str:
    if len(content.encode("utf-8")) > MSG_LIMIT:  # 截到上限内（保标题保链接）
        return content.encode("utf-8")[:MSG_LIMIT - 32].decode("utf-8", "ignore") + "\n…"
    return content


def _direct_post(url: str, payload: bytes) -> dict:
    """强制直连 POST（绕过系统代理——金雷达实战：requests 读系统代理反而误事）。"""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with opener.open(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _key_hint(url: str) -> str:
    return "****" + url.rstrip("/").rsplit("/", 1)[-1][-4:]


def _send(url: str, payload: bytes, ok_test) -> dict:
    """网络抖动 3 发指数退避；业务拒绝（对方明确说不行）立断不重试；回执掩码。"""
    last = ""
    for attempt in range(3):
        try:
            body = _direct_post(url, payload)
            if ok_test(body):
                return {"ok": True, "attempts": attempt + 1, "key": _key_hint(url)}
            return {"ok": False, "attempts": attempt + 1, "key": _key_hint(url),
                    "error": f"业务拒绝 {str(body)[:100]}"}   # 永久性错误重试无意义
        except Exception as e:  # noqa: BLE001 网络抖动重试
            last = str(e)
        time.sleep(2 * (attempt + 1))
    return {"ok": False, "attempts": 3, "key": _key_hint(url), "error": last[:120]}


def send_wecom(webhook: str, content: str) -> dict:
    payload = json.dumps({"msgtype": "markdown", "markdown": {"content": content}}).encode("utf-8")
    return _send(webhook, payload, lambda b: b.get("errcode") == 0)


def send_feishu(webhook: str, title: str, body: str) -> dict:
    """飞书自定义群机器人：卡片优先，卡片被拒（errcode≠0）降级纯文本。"""
    card = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {"title": {"tag": "plain_text", "content": title}, "template": "blue"},
            "elements": [{"tag": "markdown", "content": body}],
        },
    }
    r = _send(webhook, json.dumps(card).encode("utf-8"),
              lambda b: b.get("code") == 0 or b.get("StatusCode") == 0)
    if r["ok"]:
        return r
    text = json.dumps({"msg_type": "text", "content": {"text": f"{title}\n{body}"[:MSG_LIMIT]}}).encode("utf-8")
    r2 = _send(webhook, text, lambda b: b.get("code") == 0 or b.get("StatusCode") == 0)
    r2["fallback"] = "card→text"
    return r2


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

    if dry:
        title, body = compose_feishu(radar)
        print(title)
        print(body)
        print(f"--- dry-run · {len(body.encode('utf-8'))} bytes · 不发送 ---")
        return 0

    ok_all = True
    feishu = os.environ.get("FEISHU_WEBHOOK", "").strip()
    wecom = os.environ.get("WECOM_WEBHOOK", "").strip()
    if not feishu and not wecom:
        print("FEISHU_WEBHOOK / WECOM_WEBHOOK 均未配置，跳过推送")
        return 0

    if feishu:
        title, body = compose_feishu(radar)
        r = send_feishu(feishu, title, body)
        log_push({"channel": "feishu", **r})
        print(f"飞书推送 {'成功' if r['ok'] else '失败'}（{r['attempts']} 发） {r.get('error', '')}")
        ok_all = ok_all and r["ok"]
    if wecom:
        r = send_wecom(wecom, compose_digest(radar))
        log_push({"channel": "wecom", **r})
        print(f"企微推送 {'成功' if r['ok'] else '失败'}（{r['attempts']} 发） {r.get('error', '')}")
        ok_all = ok_all and r["ok"]
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
