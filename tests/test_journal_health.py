#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D2 周检·逐刊目录健康分类·固定场景验收套件

对象＝tools/journal_qc.classify_journal_health（纯函数，不联网、不落盘）。
判据：
  B1 边界：距最后命中 ≥100 天→red；99/45→yellow（两端含）；44/0→green；
  B2 空档：空 dict / None → 空档标记 {"red": [], "yellow": [], "green": 0, "total": 0}；
  B3 容错：坏日期串（非日期/空串/None/首尾空白）不崩——计入 total，
      无法解析者归 red 待人工核；
  B4 形状：输出恰为 {"red": [...], "yellow": [...], "green": int, "total": int}；
      未来日期（时钟回拨/写错）不崩，按「其余」入 green。

运行：
  E:/Python/python.exe -X utf8 -I -m unittest discover -s tests -v
（或直接 python tests/test_journal_health.py）
"""
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from journal_qc import classify_journal_health  # noqa: E402

TODAY = date(2026, 10, 18)


def ago(days: int) -> str:
    """距 TODAY 往前 days 天的 ISO 日期串（合成台账用）。"""
    return (TODAY - timedelta(days=days)).isoformat()


class JournalHealthClassify(unittest.TestCase):

    # ---- B1 红/黄/绿边界：100/99/45/44 ----
    def test_b1_boundaries_100_99_45_44(self):
        state = {
            "At100": ago(100),   # 恰 100 天 → red（≥100）
            "At99": ago(99),     # 99 → yellow（黄上端含）
            "At45": ago(45),     # 45 → yellow（黄下端含）
            "At44": ago(44),     # 44 → green
            "Today": ago(0),     # 当日命中 → green
        }
        h = classify_journal_health(state, TODAY)
        self.assertEqual(h["red"], ["At100"])
        self.assertEqual(h["yellow"], ["At99", "At45"])   # 保持台账顺序
        self.assertEqual(h["green"], 2)
        self.assertEqual(h["total"], 5)

    # ---- B2 空 dict / None → 空档标记（台账尚未生成） ----
    def test_b2_empty_ledger_marker(self):
        for empty in ({}, None):
            h = classify_journal_health(empty, TODAY)
            self.assertEqual(h, {"red": [], "yellow": [], "green": 0, "total": 0})

    # ---- B3 坏日期串容错：不崩、计入 total、归 red 人工核 ----
    def test_b3_bad_date_strings_tolerated(self):
        state = {
            "Bad": "not-a-date",
            "Empty": "",
            "Null": None,
            "Padded": f" {ago(50)} ",   # 首尾空白要能剥掉 → yellow
            "Good": ago(10),
        }
        h = classify_journal_health(state, TODAY)
        self.assertEqual(h["total"], 5)                       # 坏串不蒸发，计入 total
        self.assertEqual(sorted(h["red"]), ["Bad", "Empty", "Null"])
        self.assertEqual(h["yellow"], ["Padded"])
        self.assertEqual(h["green"], 1)

    # ---- B4 输出形状 + 未来日期不崩 ----
    def test_b4_shape_and_future_date(self):
        h = classify_journal_health({"A": ago(200), "B": ago(60), "C": ago(1)}, TODAY)
        self.assertEqual(set(h), {"red", "yellow", "green", "total"})
        self.assertIsInstance(h["red"], list)
        self.assertIsInstance(h["yellow"], list)
        self.assertIsInstance(h["green"], int)
        self.assertIsInstance(h["total"], int)
        self.assertEqual(h, {"red": ["A"], "yellow": ["B"], "green": 1, "total": 3})
        # 未来日期（时钟回拨/写错）：days<0 属「其余」→ green，不崩
        h2 = classify_journal_health({"Future": (TODAY + timedelta(days=3)).isoformat()}, TODAY)
        self.assertEqual(h2["green"], 1)
        self.assertEqual(h2["total"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
