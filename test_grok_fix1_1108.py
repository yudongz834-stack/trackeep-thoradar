# -*- coding: utf-8 -*-
"""GROK-FIX1-1108 先红后绿：覆盖层热出口、空元组数值降级、断路器同轮禁双计。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dualsource as dsrc  # noqa: E402
import epmc_adapter as epmc  # noqa: E402
import thoradar_dualsource as ds  # noqa: E402
import thoradar_engine as eng  # noqa: E402

DATA_START = "/*__THORADAR_DATA_START__*/"
DATA_END = "/*__THORADAR_DATA_END__*/"


def _article(pmid: str) -> dict:
    return {
        "pmid": pmid, "pmcid": "", "doi": "", "nct_id": "",
        "pub_date": "2026-11-04", "title_en": "t", "authors": "A",
        "affiliations": "", "abstract_en": "abs",
        "status": {"kind": "ok", "notice_pmid": "", "notice_ref": "",
                   "impact_known": True, "note": ""},
    }


def _scored(source: str, results: str, tuples: list, conclusion: str = "") -> dict:
    return {
        "llm": {
            "title_zh": "题", "study_type": "RCT", "category": "surgery",
            "score_clinical": 20, "score_methodology": 10, "score_specialty": 10,
            "pico_p": "", "pico_ic": "",
            "results": results, "authors_conclusion": conclusion,
            "ai_note": "", "reason": "r", "is_negative_highlight": False,
            "tuples": tuples, "tags": [],
        },
        "match": {
            "journal_abbr": "J", "journal_full": "Journal", "tier": "B",
            "if_val": 5.0, "zone": "Q1", "journal_bonus": 8,
        },
        "score_total": 48,
        "score_source": source,
    }


def _epmc_record(pmid: str) -> dict:
    return {
        "pmid": pmid, "title": f"Title {pmid}",
        "abstract": "Background. Real abstract text.",
        "journal_title": "Chest", "nlmid": "780208", "issn": "0012-3692", "essn": "",
        "pub_types": ["Journal Article"], "first_publication_date": "2026-11-07",
        "first_index_date": "2026-11-07", "retraction_events": [],
        "doi": "", "pmcid": "", "author_string": "A B", "affiliation": "Hosp",
        "source": "epmc",
    }


class TestStatusOverlayHotExits(unittest.TestCase):
    """内嵌 ok + 覆盖层 corrected → 两条热出口都输出 corrected。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.status_path = root / "status.json"
        self.archive = root / "archive"
        self.archive.mkdir()
        self.out = root / "radar_latest.json"
        self.index = root / "index.html"
        self.index.write_text(
            f"<html><script>\n{DATA_START}\n    const SITE_DATA = {{\"papers\":[]}};\n"
            f"{DATA_END}\n</script></html>",
            encoding="utf-8")
        self._orig_status = eng.STATUS_FILE
        self._orig_index = eng.INDEX_HTML
        eng.STATUS_FILE = self.status_path
        eng.INDEX_HTML = self.index
        self.embedded = {
            "pmid": "42857111", "briefing_date": "2026-11-04", "title_en": "embedded-ok",
            "status": {"kind": "ok", "note": "", "notice_pmid": "", "notice_ref": "",
                       "impact_known": True},
        }
        self.untouched = {
            "pmid": "111", "briefing_date": "2026-11-04", "title_en": "no-overlay",
            "status": {"kind": "ok", "note": "keep", "notice_pmid": "", "notice_ref": "",
                       "impact_known": True},
        }
        (self.archive / "2026-11-04.json").write_text(
            json.dumps({"papers": [self.embedded, self.untouched]}, ensure_ascii=False),
            encoding="utf-8")
        self.status_path.write_text(json.dumps({
            "updated_at": "2026-11-08 09:00",
            "papers": {
                "42857111": {
                    "kind": "corrected",
                    "notice_pmid": "999000",
                    "notice_ref": "Erratum in PMID 999000",
                    "impact_known": False,
                    "note": "原文存在更正启事；更正对结论的影响未明，解读暂停",
                }
            },
        }, ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        eng.STATUS_FILE = self._orig_status
        eng.INDEX_HTML = self._orig_index
        self.tmp.cleanup()

    def test_archive_overlay_ok_to_corrected(self):
        payload = eng.build_radar_archive(days=90, archive_dir=self.archive, out_path=self.out)
        by = {p["pmid"]: p for p in payload["papers"]}
        st = by["42857111"]["status"]
        self.assertEqual(st["kind"], "corrected")
        self.assertEqual(st["notice_pmid"], "999000")
        self.assertEqual(st["notice_ref"], "Erratum in PMID 999000")
        self.assertIs(st["impact_known"], False)
        self.assertIn("更正", st["note"])
        self.assertEqual(by["111"]["status"]["kind"], "ok")
        self.assertEqual(by["111"]["status"]["note"], "keep")

    def test_inject_overlay_ok_to_corrected(self):
        papers = [json.loads(json.dumps(self.embedded)), json.loads(json.dumps(self.untouched))]
        eng.inject_index_html(papers, {"fetched": 1, "journal_matched": 1}, "2026-11-04")
        html = self.index.read_text(encoding="utf-8")
        self.assertIn('"pmid":"42857111"', html)
        self.assertIn('"kind":"corrected"', html)
        self.assertIn('"notice_pmid":"999000"', html)
        self.assertIn('"impact_known":false', html)
        self.assertEqual(papers[0]["status"]["kind"], "ok")
        self.assertIn('"pmid":"111"', html)
        # 无覆盖层的 pmid 仍是内嵌 ok，note 不被洗掉
        self.assertIn('"note":"keep"', html)


class TestUnverifiedNumericClaim(unittest.TestCase):
    """llm + 数字结论 + tuples 空 → publish_state 非 full；启发式不误伤。"""

    def test_llm_numeric_claim_empty_tuples_not_full(self):
        cases = (
            ("results", "5年OS率为88.9%。", ""),
            ("conclusion", "", "作者称缓解率达到88.9%。"),
        )
        for label, results, conclusion in cases:
            with self.subTest(label=label):
                paper = eng.build_paper(
                    _article("42970796"),
                    _scored("llm", results, [], conclusion),
                    None, "")
                self.assertNotEqual(paper["publish_state"], "full")
                self.assertIn("数值未经四元组核验", paper.get("ai_note", ""))

    def test_heuristic_numeric_empty_tuples_stays_full(self):
        paper = eng.build_paper(
            _article("2"),
            _scored("heuristic", "5年OS率为88.9%。", []),
            None, "")
        self.assertEqual(paper["publish_state"], "full")
        self.assertNotIn("数值未经四元组核验", paper.get("ai_note") or "")

    def test_llm_without_numeric_claim_stays_full(self):
        paper = eng.build_paper(
            _article("3"),
            _scored("llm", "主要终点未报告可抽取数值", []),
            None, "")
        self.assertEqual(paper["publish_state"], "full")


class TestBreakerNoSameRoundDoubleCount(unittest.TestCase):
    """探针已在 main 记过：同轮批败不再记；跨两轮各败一次才 OPEN。"""

    def _fallback(self, breaker):
        funnel: dict = {}
        with mock.patch.object(epmc, "epmc_fetch_pmids", return_value=[_epmc_record("1")]):
            out = ds.run_dualsource_fallback(
                None, ["1"], [], {"journals": []}, funnel, 3, {}, breaker, reason="empty")
        return out, funnel

    def test_same_round_stays_closed_two_rounds_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "circuit_state.json")
            b1 = dsrc.CircuitBreaker(path)
            b1.record_probe(False)
            _out, funnel = self._fallback(b1)
            self.assertEqual(funnel.get("dualsource_mode"), "patch")
            self.assertEqual(b1.state, "CLOSED")
            self.assertEqual(b1.consecutive_failures, 1)

            b2 = dsrc.CircuitBreaker(path)
            b2.record_probe(False)
            self._fallback(b2)
            self.assertEqual(b2.state, "OPEN")
            self.assertEqual(b2.consecutive_failures, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
