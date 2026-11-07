#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""空数据守卫回归（2026-11-07 判例：限流跑产出 0 篇，注入把 13 篇好数据洗成空）。

守卫语义：papers 为空且线上现有数据非空 → 拒绝写入（index 保留旧数据）；
papers 为空且线上本来就是空（首启/连续空跑） → 照写；papers 非空 → 照写。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import thoradar_engine as eng  # noqa: E402

DATA_START = "/*__THORADAR_DATA_START__*/"
DATA_END = "/*__THORADAR_DATA_END__*/"


def _html_with(papers_json: str) -> str:
    return (f"<html><script>\n{DATA_START}\n"
            f'    const SITE_DATA = {{"generated_at":"x","papers":{papers_json}}};\n'
            f"{DATA_END}\n</script></html>")


class InjectGuardTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="thor_inject_"))
        self.path = self.tmp / "index.html"
        self._orig = eng.INDEX_HTML
        eng.INDEX_HTML = self.path

    def tearDown(self):
        eng.INDEX_HTML = self._orig
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _read(self) -> str:
        return self.path.read_text(encoding="utf-8")

    def test_empty_papers_never_clobbers_nonempty_site(self):
        """0 篇产出撞上非空线上数据：拒绝覆盖，index 一字不动。"""
        self.path.write_text(_html_with('[{"pmid":"1"}]'), encoding="utf-8")
        before = self._read()
        eng.inject_index_html([], {"fetched": 276, "journal_matched": 0}, "2026-11-07")
        self.assertEqual(self._read(), before)

    def test_empty_papers_writes_when_site_already_empty(self):
        """线上本来就是空（首启）：0 篇照写，不卡死首注入。
        断言只可能由注入产生的键（fixture 里没有 briefing_date）——
        钉「会不会只会拒绝」型缺陷，防拒绝型检查假绿（2026-11-07 复核席 M1）。"""
        self.path.write_text(_html_with("[]"), encoding="utf-8")
        eng.inject_index_html([], {}, "2026-11-08")
        self.assertIn('"briefing_date":"2026-11-08"', self._read())
        self.assertIn('"papers":[]', self._read())

    def test_nonempty_papers_still_writes(self):
        """正常产出：守卫不拦，数据照常刷新。"""
        self.path.write_text(_html_with('[{"pmid":"1"}]'), encoding="utf-8")
        eng.inject_index_html([{"pmid": "2"}], {"fetched": 10, "journal_matched": 1}, "2026-11-08")
        self.assertIn('"pmid":"2"', self._read())

    def test_missing_markers_still_raises(self):
        """标记缺失（被手改坏）：守卫之外的原防线不松动。"""
        self.path.write_text("<html>no markers</html>", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            eng.inject_index_html([{"pmid": "1"}], {}, "2026-11-07")


if __name__ == "__main__":
    unittest.main()
