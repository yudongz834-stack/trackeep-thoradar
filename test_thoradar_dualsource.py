# -*- coding: utf-8 -*-
"""双源桥测试：Record 映射、撤稿三态合成、探针加载、ISSN 分片。
（run_dualsource_fallback 的装配路径测试在 test_dualsource_integration.py，依赖模块二到位。）"""
import unittest

import thoradar_dualsource as ds


class TestStatusFromRecord(unittest.TestCase):
    """撤稿三态合成：对齐 Collector.parse_status 五态语义。"""

    def test_event_retraction_in_is_retracted_with_notice_pmid(self):
        rec = {"pub_types": [], "retraction_events": [{"type": "Retraction in", "ref_pmid": "15016483"}]}
        st = ds.status_from_record(rec)
        self.assertEqual(st["kind"], "retracted")
        self.assertEqual(st["notice_pmid"], "15016483")
        self.assertTrue(st["impact_known"])

    def test_event_retraction_of_is_notice(self):
        rec = {"pub_types": [], "retraction_events": [{"type": "Retraction of", "ref_pmid": "1"}]}
        st = ds.status_from_record(rec)
        self.assertEqual(st["kind"], "notice")

    def test_event_erratum_in_is_corrected_impact_unknown(self):
        rec = {"pub_types": [], "retraction_events": [{"type": "Erratum in", "ref_pmid": "2"}]}
        st = ds.status_from_record(rec)
        self.assertEqual(st["kind"], "corrected")
        self.assertFalse(st["impact_known"])

    def test_event_eoc_in_is_concern(self):
        rec = {"pub_types": [], "retraction_events": [{"type": "Expression of concern in", "ref_pmid": "3"}]}
        st = ds.status_from_record(rec)
        self.assertEqual(st["kind"], "concern")

    def test_pubtype_retracted_beats_concern(self):
        # 判序对齐 parse_status：retracted 优先于 concern
        rec = {"pub_types": ["Retracted Publication"],
               "retraction_events": [{"type": "Expression of concern in", "ref_pmid": "3"}]}
        self.assertEqual(ds.status_from_record(rec)["kind"], "retracted")

    def test_notice_pubtype_wins_over_retracted_event(self):
        # 本文是撤稿通知（notice）优先于一切
        rec = {"pub_types": ["Retraction of Publication"],
               "retraction_events": [{"type": "Retraction in", "ref_pmid": "9"}]}
        self.assertEqual(ds.status_from_record(rec)["kind"], "notice")

    def test_clean_record_is_ok(self):
        rec = {"pub_types": ["Journal Article"], "retraction_events": []}
        st = ds.status_from_record(rec)
        self.assertEqual(st["kind"], "ok")
        self.assertTrue(st["impact_known"])


class TestRecordToArticle(unittest.TestCase):
    """契约 Record → engine 文章字典：build_paper 全键覆盖。"""

    REC = {
        "pmid": "35403841", "title": "Nivolumab in Early-Stage NSCLC",
        "abstract": "Background Methods NCT01988996 results shown.",
        "journal_title": "New England Journal of Medicine",
        "nlmid": "101555957", "issn": "0028-4762", "essn": "1533-4406",
        "pub_types": ["Journal Article"],
        "first_publication_date": "2022-07-14", "first_index_date": "2022-07-14",
        "retraction_events": [],
        "doi": "10.1056/nejmoa2202170", "pmcid": "PMC9844511",
        "author_string": "Forde PM, Spicer J, Lu S",
        "affiliation": "Johns Hopkins School of Medicine",
        "source": "epmc",
    }

    def test_full_mapping_keys(self):
        a = ds.record_to_article(self.REC)
        for k in ("pmid", "title_en", "p_issn", "e_issn", "issn_linking", "nlm_id",
                  "iso_abbr", "journal_title", "abstract_en", "authors", "affiliations",
                  "pub_date", "doi", "pmcid", "nct_id", "status", "source"):
            self.assertIn(k, a, f"engine 键缺失: {k}")
        self.assertEqual(a["pmid"], "35403841")
        self.assertEqual(a["title_en"], self.REC["title"])
        self.assertEqual(a["p_issn"], "0028-4762")
        self.assertEqual(a["nlm_id"], "101555957")
        self.assertEqual(a["pub_date"], "2022-07-14")
        self.assertEqual(a["doi"], "10.1056/nejmoa2202170")
        self.assertEqual(a["pmcid"], "PMC9844511")
        self.assertEqual(a["source"], "epmc")

    def test_nct_extracted_from_abstract(self):
        a = ds.record_to_article(self.REC)
        self.assertEqual(a["nct_id"], "NCT01988996")

    def test_authors_fallback_when_missing(self):
        rec = dict(self.REC, author_string="")
        a = ds.record_to_article(rec)
        self.assertEqual(a["authors"], "（作者信息缺失）")

    def test_affiliation_truncated_300(self):
        rec = dict(self.REC, affiliation="x" * 500)
        a = ds.record_to_article(rec)
        self.assertEqual(len(a["affiliations"]), 300)


class TestProbeAndChunks(unittest.TestCase):
    def test_probe_pmids_loaded_from_regression_set(self):
        pmids = ds.load_probe_pmids()
        self.assertEqual(len(pmids), 3)
        for p in pmids:
            self.assertTrue(p.isdigit())

    def test_issn_chunks_cover_all_197_journals(self):
        import json
        cfg = json.loads((ds.ROOT / "config" / "journals_taxonomy.json").read_text(encoding="utf-8"))
        chunks = ds._issn_chunks(cfg)
        # 判据＝分片无损重组：切片拼接还原全部非空 ISSN 词元，无丢无重
        expect: list = []
        for j in cfg.get("journals", []):
            for key in ("p_issn", "e_issn"):
                v = (j.get(key) or "").strip()
                if v:
                    expect.append(v)
        got = [t for c in chunks for t in c]
        self.assertEqual(got, expect)
        self.assertGreater(len(expect), 300)   # 实测 197 刊约 328 词元，防配置整体退化
        for c in chunks:
            self.assertLessEqual(len(c), ds.FALLBACK_ISSN_CHUNK * 2)


if __name__ == "__main__":
    unittest.main()


class TestBreakerAdoption(unittest.TestCase):
    """复核 B2 钉：状态文件坏 JSON → 隔离 .corrupt＋fresh CLOSED 收养，不崩 main。"""

    def test_corrupt_state_adopted_fresh(self):
        import tempfile, os
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "circuit_state.json")
            with open(bad, "w", encoding="utf-8") as f:
                f.write('{"state": "OPEN", "tripped_at": SPLIT-BAD-JSON')
            with mock.patch.object(ds, "CIRCUIT_STATE_PATH", type(bad)(bad)):
                b = ds.load_breaker()
            self.assertIsNotNone(b)
            self.assertEqual(b.route(), "ncbi")   # 全新 CLOSED
            self.assertTrue(os.path.exists(bad + ".corrupt"))  # 坏件隔离留证
