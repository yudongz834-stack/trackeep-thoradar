#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""胸科雷达 MCP 订阅（stdio 版·照搬 AIHOT「填一个地址多出一排工具」的工具面）。

匿名只读，不要 Key。读的与 RSS/API/Skill 同一份数据。
接法（Claude Code 等支持 MCP 的客户端）：
  claude mcp add thoradar -- E:/Python/python.exe D:/trackeep-thoradar/tools/mcp_server.py
协议：MCP stdio JSON-RPC（initialize / tools/list / tools/call），stdlib 零依赖。
"""
import json
import sys
import urllib.request

API = "https://thoradar.online/api/v1"

TOOLS = [
    {"name": "thoradar_daily", "description": "胸科雷达今日日报：今日新收文献（中文标题/期刊/档次/分数/分类/PubMed 链接）。",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "thoradar_weekly", "description": "胸科雷达周报（每周一更新）：近 7 天精选 Top15＋分类分布。",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "thoradar_monthly", "description": "胸科雷达月报（每月 1 日更新）：上月精选 Top15＋分类分布。",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "thoradar_search", "description": "在近 7 天池里按关键词查文献（题名/分类/期刊模糊匹配）。",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string", "description": "关键词，如 肺癌 / esophageal / 睡眠呼吸"}},
                     "required": ["query"]}},
]


def _get_json(path: str) -> dict:
    with urllib.request.urlopen(API + path, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _brief(p: dict) -> dict:
    return {k: p.get(k) for k in ("title_zh", "title_en", "journal_abbr", "tier",
                                  "score_total", "category_label", "url", "pmid", "pub_date")}


def call_tool(name: str, args: dict) -> str:
    if name == "thoradar_daily":
        d = _get_json("/daily.json")
        return json.dumps({"date": d.get("date"), "generated_at": d.get("generated_at"),
                           "count": d.get("count"), "categories": d.get("categories"),
                           "papers": [_brief(p) for p in (d.get("papers") or [])[:30]]},
                          ensure_ascii=False)
    if name in ("thoradar_weekly", "thoradar_monthly"):
        d = _get_json("/" + name.replace("thoradar_", "") + ".json")
        return json.dumps({"period": d.get("period"), "generated_at": d.get("generated_at"),
                           "count": d.get("count"), "papers": [_brief(p) for p in (d.get("papers") or [])[:20]]},
                          ensure_ascii=False)
    if name == "thoradar_search":
        q = (args.get("query") or "").lower()
        d = _get_json("/daily.json")
        rows = [p for p in (d.get("papers") or [])
                if q in (str(p.get("title_zh") or "") + str(p.get("title_en") or "")
                         + str(p.get("category_label") or "") + str(p.get("journal_abbr") or "")).lower()]
        return json.dumps({"query": args.get("query"), "hits": [_brief(p) for p in rows[:20]]},
                          ensure_ascii=False)
    return json.dumps({"error": "unknown tool"}, ensure_ascii=False)


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        mid, method = msg.get("id"), msg.get("method")
        if method == "initialize":
            resp = {"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "thoradar", "version": "1.0.0"}}}
        elif method == "tools/list":
            resp = {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
        elif method == "tools/call":
            try:
                text = call_tool(msg["params"]["name"], msg.get("params", {}).get("arguments") or {})
                resp = {"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": text}]}}
            except Exception as e:  # noqa: BLE001 工具错误回执不吞
                resp = {"jsonrpc": "2.0", "id": mid, "result": {
                    "content": [{"type": "text", "text": f"error: {e}"}], "isError": True}}
        elif method == "notifications/initialized":
            continue
        else:
            resp = {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found"}}
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
