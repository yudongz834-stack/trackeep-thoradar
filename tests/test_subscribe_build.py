#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""订阅件回归（2026-11-10 照搬 AIHOT 四通道）：周报窗口/标签、RSS 转义、日报 API 形状。"""
import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import subscribe_build as sb  # noqa: E402


def _radar() -> dict:
    today = date.today().isoformat()
    old = (date.today() - timedelta(days=20)).isoformat()
    return {"generated_at": f"{today} 11:45", "count": 3, "papers": [
        {"pmid": "1", "briefing_date": today, "title_zh": "今日A", "score_total": 90,
         "category_label": "肺癌", "url": "https://p/1", "journal_abbr": "JTO", "tier": "S"},
        {"pmid": "2", "briefing_date": (date.today() - timedelta(days=2)).isoformat(),
         "title_zh": "本周B", "score_total": 80, "category_label": "食管", "url": "https://p/2"},
        {"pmid": "3", "briefing_date": old, "title_zh": "窗外C", "score_total": 99},
    ]}


class PeriodTests(unittest.TestCase):
    def test_weekly_window_excludes_outside(self):
        title, body = sb.compose_period(_radar(), "周报（测试）", 7)
        self.assertIn("今日A", body)
        self.assertIn("本周B", body)
        self.assertNotIn("窗外C", body, "窗外高分文不得混入")
        self.assertIn("周报（测试）", title)

    def test_feed_escapes_and_lists_recent(self):
        r = _radar()
        r["papers"][0]["title_zh"] = "A<B>&C"
        xml = sb.build_feed(r)
        self.assertIn("A&lt;B&gt;&amp;C", xml)
        self.assertIn("<rss version=\"2.0\">", xml)
        self.assertNotIn("窗外C", xml)

    def test_daily_api_shape(self):
        d = sb.build_daily_api(_radar())
        self.assertEqual(d["count"], 1)
        self.assertEqual(d["date"], date.today().isoformat())
        self.assertEqual(len(d["papers"]), 1)
        json.dumps(d, ensure_ascii=False)  # 可序列化


if __name__ == "__main__":
    unittest.main()
