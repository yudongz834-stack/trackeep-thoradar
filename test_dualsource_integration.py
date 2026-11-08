# -*- coding: utf-8 -*-
"""双源装配集成测试：真断路器＋真路由判定＋mock EPMC HTTP——打真实接缝。
覆盖：patch 补取／stripped 救回＋保全／full_epmc 窗口＋账本去重／双源齐断→None。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dualsource as dsrc          # noqa: E402
import epmc_adapter as epmc        # noqa: E402
import thoradar_dualsource as ds   # noqa: E402


def make_record(pmid, abstract="Background. Real abstract text.", **kw):
    base = {
        "pmid": pmid, "title": f"Title {pmid}", "abstract": abstract,
        "journal_title": "Chest", "nlmid": "780208", "issn": "0012-3692", "essn": "",
        "pub_types": ["Journal Article"], "first_publication_date": "2026-11-07",
        "first_index_date": "2026-11-07", "retraction_events": [],
        "doi": f"10.1/test{pmid}", "pmcid": "", "author_string": "A B",
        "affiliation": "Hosp", "source": "epmc",
    }
    base.update(kw)
    return base


class FallbackTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_path = str(Path(self.tmp.name) / "circuit_state.json")
        self.breaker = dsrc.CircuitBreaker(self.state_path)
        self.cfg = {"journals": [{"p_issn": "0012-3692", "e_issn": "1556-0864"}]}
        self.seen = {"999": "2026-11-01"}
        self.funnel: dict = {}

    def tearDown(self):
        self.tmp.cleanup()


class TestPatchMode(FallbackTestBase):
    """CLOSED＋有单＋efetch 零解析 → patch：EPMC 按 PMID 补取，无 NCBI 可保全。"""

    def test_patch_fetches_by_pmids_and_maps(self):
        recs = [make_record("1"), make_record("2")]
        with mock.patch.object(epmc, "epmc_fetch_pmids", return_value=recs) as mfetch, \
             mock.patch.object(epmc, "epmc_search_day", side_effect=AssertionError("patch 模式不许走窗口检索")):
            out = ds.run_dualsource_fallback(
                None, ["1", "2"], [], self.cfg, self.funnel, 3, self.seen, self.breaker, reason="empty")
        self.assertEqual(len(out), 2)
        self.assertEqual({a["pmid"] for a in out}, {"1", "2"})
        self.assertTrue(all(a["abstract_en"] for a in out))
        self.assertTrue(all(a["source"] == "epmc" for a in out))
        mfetch.assert_called_once_with(["1", "2"])
        self.assertEqual(self.funnel["dualsource_mode"], "patch")
        self.assertEqual(self.funnel["source"], "epmc")

    def test_stripped_rescue_and_ncbi_keep(self):
        ncbi_articles = [
            {"pmid": "1", "title_en": "T1", "abstract_en": "", "authors": "N1",
             "status": {"kind": "ok"}, "source": "ncbi"},
            {"pmid": "2", "title_en": "T2", "abstract_en": "Good NCBI abstract.",
             "authors": "N2", "status": {"kind": "ok"}, "source": "ncbi"},
        ]
        recs = [make_record("1", abstract="Rescued abstract."), make_record("2", abstract="EPMC abs 2.")]
        with mock.patch.object(epmc, "epmc_fetch_pmids", return_value=recs):
            out = ds.run_dualsource_fallback(
                None, ["1", "2"], ncbi_articles, self.cfg, self.funnel, 3, self.seen,
                self.breaker, reason="stripped")
        by_pmid = {a["pmid"]: a for a in out}
        # 🔴 红钉：剥离记录被 EPMC 救回；健康 NCBI 记录保全不被覆盖
        self.assertEqual(by_pmid["1"]["abstract_en"], "Rescued abstract.")
        self.assertEqual(by_pmid["1"]["source"], "epmc")
        self.assertEqual(by_pmid["2"]["abstract_en"], "Good NCBI abstract.")
        self.assertEqual(by_pmid["2"]["authors"], "N2")
        self.assertEqual(self.funnel["dualsource_rescued"], 1)
        self.assertEqual(self.funnel["dualsource_kept_ncbi"], 1)
        self.assertEqual(self.funnel["source"], "mixed")


class TestFullEpmcMode(FallbackTestBase):
    """esearch 败（无单）→ full_epmc：分片窗口检索＋见过账本去重。"""

    def test_full_epmc_searches_window_and_filters_seen(self):
        recs = [make_record("1"), make_record("2"), make_record("999")]  # 999 在 seen 账本
        with mock.patch.object(epmc, "epmc_search_day", return_value=recs) as msearch, \
             mock.patch.object(epmc, "epmc_fetch_pmids", side_effect=AssertionError("full_epmc 不许按 PMID 补")):
            out = ds.run_dualsource_fallback(
                None, [], [], self.cfg, self.funnel, 3, self.seen, self.breaker, reason="empty")
        self.assertEqual({a["pmid"] for a in out}, {"1", "2"})
        msearch.assert_called_once()
        args = msearch.call_args[0]
        self.assertEqual(args[0], ["0012-3692", "1556-0864"])  # ISSN 分片传入
        # 🔴 复核 B2 钉（2026-11-08）：日期窗实参必须真传递且方向正确——窗死＝full_epmc 全库翻底
        from datetime import date as _date
        d_from, d_to = args[1], args[2]
        self.assertEqual((_date.fromisoformat(d_to) - _date.fromisoformat(d_from)).days, 3 + 1)

    def test_open_breaker_routes_full_epmc_even_with_pmids(self):
        # 断路器已 OPEN（前日掐锁遗留）→ 即便清单在手也整条切 EPMC（契约钉：不信任 NCBI 清单）
        self.breaker.state = "OPEN"
        self.breaker.tripped_at = "2026-11-08T10:00:00"
        recs = [make_record("1")]
        with mock.patch.object(epmc, "epmc_search_day", return_value=recs):
            out = ds.run_dualsource_fallback(
                None, ["1"], [], self.cfg, self.funnel, 3, self.seen, self.breaker, reason="probe_fail")
        self.assertEqual(len(out), 1)
        self.assertEqual(self.funnel["dualsource_mode"], "full_epmc")


class TestBothDown(FallbackTestBase):
    def test_epmc_error_returns_none(self):
        with mock.patch.object(epmc, "epmc_fetch_pmids",
                               side_effect=epmc.EpmcError("EPMC 429 beyond retries")):
            out = ds.run_dualsource_fallback(
                None, ["1"], [], self.cfg, self.funnel, 3, self.seen, self.breaker, reason="empty")
        self.assertIsNone(out)

    def test_zero_records_returns_none(self):
        with mock.patch.object(epmc, "epmc_fetch_pmids", return_value=[]):
            out = ds.run_dualsource_fallback(
                None, ["1"], [], self.cfg, self.funnel, 3, self.seen, self.breaker, reason="empty")
        self.assertIsNone(out)

    def test_zero_abstract_after_merge_returns_none(self):
        recs = [make_record("1", abstract="")]  # 只有无摘要记录＝假救回
        with mock.patch.object(epmc, "epmc_fetch_pmids", return_value=recs):
            out = ds.run_dualsource_fallback(
                None, ["1"], [], self.cfg, self.funnel, 3, self.seen, self.breaker, reason="empty")
        self.assertIsNone(out)


class TestBreakerTripAcrossRuns(unittest.TestCase):
    """跨运行状态机全链：连 2 败 OPEN → 冷却满 HALF_OPEN → 连 3 成 CLOSED。"""

    def test_full_cycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "st.json")
            b1 = dsrc.CircuitBreaker(path)
            self.assertEqual(b1.route(), "ncbi")
            b1.record_probe(False)
            b1.record_probe(False)
            self.assertEqual(b1.route(), "epmc")            # 连 2 败 → OPEN
            b2 = dsrc.CircuitBreaker(path)                  # 新实例（模拟次日新运行）
            self.assertEqual(b2.route(), "epmc")            # 跨运行记忆
            b2.record_probe(True)                           # 冷却未满 → 仍 OPEN
            self.assertEqual(b2.route(), "epmc")
            # 手动把 tripped_at 拨回 13h 前＝冷却已满
            st = json.loads(Path(path).read_text(encoding="utf-8"))
            import datetime
            st["tripped_at"] = (datetime.datetime.now(datetime.timezone.utc)
                                - datetime.timedelta(hours=13)).isoformat()
            Path(path).write_text(json.dumps(st), encoding="utf-8")
            b3 = dsrc.CircuitBreaker(path)
            b3.record_probe(True)                           # 冷却满 → HALF_OPEN
            self.assertEqual(b3.route(), "ncbi")            # 半开探针模式回 NCBI
            b3.record_probe(True)
            b3.record_probe(True)                           # 连 3 成 → CLOSED
            self.assertEqual(b3.route(), "ncbi")
            self.assertEqual(json.loads(Path(path).read_text(encoding="utf-8"))["state"], "CLOSED")


if __name__ == "__main__":
    unittest.main()
