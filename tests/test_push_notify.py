#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""推送模块回归（2026-11-09 通道①企微群机器人）：
组装（含断粮告警线）＋重试回执（3 发指数退避）＋台账落盘。
"""
import json
import sys
import unittest
import unittest.mock as mock
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import push_notify as pn  # noqa: E402


def _radar(days_ago: int = 0) -> dict:
    day = (date.today() - timedelta(days=days_ago)).isoformat()
    return {
        "generated_at": f"{day} 11:45", "anchor_date": day, "count": 10,
        "papers": [
            {"pmid": "1", "briefing_date": day, "title_zh": "肺癌免疫治疗进展", "url": "https://p/1",
             "journal_abbr": "JTO", "tier": "S", "score_total": 92, "category_label": "肺癌"},
            {"pmid": "2", "briefing_date": day, "title_zh": "食管癌微创手术", "url": "https://p/2",
             "journal_abbr": "Ann Surg", "tier": "A", "score_total": 88, "category_label": "食管"},
            {"pmid": "3", "briefing_date": "2026-10-01", "title_zh": "旧文", "score_total": 99},
        ],
    }


class ComposeDigestTests(unittest.TestCase):
    def test_digest_lists_today_top_sorted(self):
        c = pn.compose_digest(_radar())
        self.assertIn("今日新收 **2** 篇", c)
        self.assertIn("肺癌免疫治疗进展", c)
        i1, i2 = c.index("肺癌免疫治疗"), c.index("食管癌微创")
        self.assertLess(i1, i2, "精选应按分数降序")
        self.assertNotIn("旧文", c, "非今日批次不得混入")

    def test_digest_warns_when_stale(self):
        c = pn.compose_digest(_radar(days_ago=5))
        self.assertIn("数据滞后 5 天", c)
        self.assertIn("断粮", c)
        c2 = pn.compose_digest(_radar(days_ago=0))
        self.assertNotIn("断粮", c2)


class SendWecomTests(unittest.TestCase):
    def test_retry_then_success(self):
        import io
        calls = {"n": 0}

        def boom(req, timeout=20):
            calls["n"] += 1
            if calls["n"] < 3:
                raise OSError("net down")
            return io.BytesIO(b'{"errcode": 0, "errmsg": "ok"}')

        with mock.patch.object(pn.urllib.request, "urlopen", boom), \
             mock.patch.object(pn.time, "sleep"):
            r = pn.send_wecom("https://qyapi.weixin.qq.com/x?key=abcd1234", "hi")
        self.assertTrue(r["ok"])
        self.assertEqual(r["attempts"], 3)
        self.assertEqual(r["key"], "****1234", "密钥必须掩码只留尾 4 位")

    def test_three_failures_reported(self):
        with mock.patch.object(pn.urllib.request, "urlopen", mock.Mock(side_effect=OSError("down"))), \
             mock.patch.object(pn.time, "sleep"):
            r = pn.send_wecom("https://qyapi.weixin.qq.com/x?key=zz", "hi")
        self.assertFalse(r["ok"])
        self.assertEqual(r["attempts"], 3)
        self.assertIn("error", r)


if __name__ == "__main__":
    unittest.main()
