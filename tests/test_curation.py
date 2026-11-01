#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T1017-THOR-B2A 规则式精选·固定场景验收套件

四场景＋解绑断言：
  S1 零候选：空输入 → 精选为空，不崩；
  S2 全部合格：全部过线 → 全部入选（无上限、不硬删）；
  S3 全部不合格：个案/回顾性 B 级 → 精选为零（不凑数）；
  S4 混合：只有过线者入选；非精选照常发布；curated ⊆ published；解读暂停不入精选；
  S5 解绑：启发式模式强信号照常入选（不因无 LLM 而残废）；
          LLM 模式弱信号不自动入选（LLM 不自动等于精选）。

测试输入全部为结构真实的合成文献（不联网）。运行：
  E:/Python/python.exe -X utf8 -I -m unittest discover -s tests -v
（或直接 python tests/test_curation.py）
"""
import json
import sys
import unittest
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import thoradar_engine as eng  # noqa: E402

JM = eng.JournalMatcher(json.loads(eng.JOURNALS_FILE.read_text(encoding="utf-8")))


def make_article(pmid: str, title: str, abstract: str, e_issn: str = "") -> dict:
    return {
        "pmid": pmid, "title_en": title, "abstract_en": abstract,
        "p_issn": "", "e_issn": e_issn, "issn_linking": "", "nlm_id": "",
        "iso_abbr": "", "journal_title": "", "authors": "Synthetic A, Synthetic B",
        "affiliations": "Department of Thoracic Surgery, Synthetic University",
        "pub_date": "2026-Oct-17", "doi": "", "pmcid": "", "nct_id": "",
        "status": {"kind": "ok", "notice_pmid": "", "notice_ref": "",
                   "impact_known": True, "note": ""},
    }


def make_paper(pmid, title, abstract, e_issn="", verify_error=""):
    """走真实 build_paper 路径（启发式评分），保证测试对象与生产同构。"""
    a = make_article(pmid, title, abstract, e_issn)
    scored = eng.heuristic_score(a, JM)
    return eng.build_paper(a, scored, None, verify_error)


# 结构真实的合成文献（研究类型/主要终点/期刊层级信号显式）
ABS_RCT_PERIOP = (
    "Background: Perioperative chemotherapy improves outcomes in resectable non-small-cell lung "
    "cancer, but the optimal perioperative systemic therapy remains debated. Methods: In this "
    "randomized phase 3 trial, 415 patients with resectable non-small-cell lung cancer were "
    "assigned to perioperative immunotherapy plus chemotherapy or chemotherapy alone. The primary "
    "endpoint was event-free survival. Results: Event-free survival was significantly longer with "
    "perioperative immunotherapy; pathological complete response was 25.4% versus 5.1%."
)
ABS_RCT_ADVANCED = (
    "Background: First-line treatment of advanced EGFR-mutated non-small-cell lung cancer. "
    "Methods: Patients with EGFR-mutated advanced non-small-cell lung cancer were randomized to "
    "osimertinib plus chemotherapy or osimertinib monotherapy. The primary endpoint was "
    "investigator-assessed progression-free survival. Results: Median progression-free survival "
    "was 25.5 months versus 16.7 months."
)
ABS_PROSP_MATCH_SURGERY = (
    "Background: Segmentectomy versus lobectomy for small-sized pulmonary nodules. Methods: We "
    "conducted a prospective propensity score-matched cohort study of patients undergoing "
    "thoracoscopic segmentectomy or lobectomy. The primary endpoint was overall survival. "
    "Results: Overall survival did not differ significantly between matched groups."
)
ABS_CASE_REPORT = (
    "Case report: A 54-year-old patient presented with an unusual mediastinal tumor compressing "
    "the superior vena cava. The patient underwent resection and adjuvant therapy with an "
    "uneventful postoperative course."
)
ABS_RETRO_B = (
    "Background: Prognostic value of ground-glass opacity components. Methods: This retrospective "
    "review included 212 patients who underwent pulmonary nodule resection at a single center. "
    "Results: The ground-glass component was associated with slower growth."
)
ABS_RCT_S_DEGRADED = (
    "Background: Neoadjuvant therapy for esophageal cancer. Methods: In this randomized trial of "
    "320 patients with esophageal cancer, the primary endpoint was overall survival. Results: "
    "Overall survival was 60.2% versus 49.5%."
)


class CurationFixedScenarios(unittest.TestCase):

    # ---- S1 零候选：允许精选为空 ----
    def test_s1_zero_candidates(self):
        n = eng.apply_curation([])
        self.assertEqual(n, 0)
        # 单篇但毫无信号也可为空：unknown 设计 + B 级
        p = make_paper("9001", "A brief survey of thoracic oncology practice patterns",
                       "A questionnaire-based survey among thoracic surgeons.")
        n = eng.apply_curation([p])
        self.assertEqual(n, 0)
        self.assertFalse(p["curated"])
        self.assertEqual(p["curation_reason"], "")

    # ---- S2 全部合格：全部入选（无上限、不硬删、理由具体） ----
    def test_s2_all_qualified_all_curated(self):
        papers = [
            make_paper("9002", "Perioperative immunotherapy in resectable NSCLC",
                       ABS_RCT_PERIOP, e_issn="1533-4406"),            # NEJM S
            make_paper("9003", "Osimertinib combinations in advanced NSCLC",
                       ABS_RCT_ADVANCED, e_issn="1527-7755"),          # JCO S
            make_paper("9004", "Segmentectomy versus lobectomy: matched cohort",
                       ABS_PROSP_MATCH_SURGERY, e_issn="1569-8041"),   # Ann Oncol A（换册 v4 实测重锚：旧锚 Ann Thorac Surg 新制降 C，不再满足 S/A 夹具前提；断言未动）
        ]
        n = eng.apply_curation(papers)
        self.assertEqual(n, 3)                      # 全合格 → 全入选，不设配额
        self.assertTrue(all(p["curated"] for p in papers))
        for p in papers:
            r = p["curation_reason"]
            self.assertIn("，直接影响", r)           # 理由落到具体问题
            # 理由必须包含该栏目映射的问题类别串（禁空话的机判形式）
            self.assertIn(eng.CURATION_PROBLEM_BY_CATEGORY[p["category"]], r,
                          f"理由未落到具体问题: {r}")
            self.assertTrue(p["curation_clinical_value"] and p["curation_research_value"])
            self.assertIn("tier", p["curation_signals"])
        self.assertIn("RCT/III 期", papers[0]["curation_reason"])
        self.assertIn("前瞻匹配队列", papers[2]["curation_reason"])

    # ---- S3 全部不合格：精选为零（不凑数） ----
    def test_s3_all_unqualified_zero_curated(self):
        papers = [
            make_paper("9005", "Unusual mediastinal tumor presentation",
                       ABS_CASE_REPORT),                               # 个案
            make_paper("9006", "Ground-glass components prognosis",
                       ABS_RETRO_B, e_issn="2045-2322"),               # 回顾性 B 级
            make_paper("9007", "A survey of practice patterns",
                       "A survey-based study without clinical outcome data."),
        ]
        n = eng.apply_curation(papers)
        self.assertEqual(n, 0)                      # 不为凑数收录
        self.assertFalse(any(p["curated"] for p in papers))
        for p in papers:
            self.assertEqual(p["curation_reason"], "")

    # ---- S4 混合：只选过线者；非精选照常发布；curated ⊆ published；降级不入精选 ----
    def test_s4_mixed_selection_and_no_hard_delete(self):
        papers = [
            make_paper("9008", "Perioperative immunotherapy in resectable NSCLC",
                       ABS_RCT_PERIOP, e_issn="1533-4406"),            # 过线（S 级 RCT）
            make_paper("9009", "Unusual mediastinal tumor presentation",
                       ABS_CASE_REPORT),                               # 个案：不过线
            make_paper("9010", "Ground-glass components prognosis",
                       ABS_RETRO_B, e_issn="2045-2322"),               # 回顾 B：不过线
            make_paper("9011", "Neoadjuvant therapy for esophageal cancer",
                       ABS_RCT_S_DEGRADED, e_issn="1533-4406",
                       verify_error="verifier-error: chaos"),          # 过线设计但解读暂停
        ]
        published_before = [p["id"] for p in papers]
        n = eng.apply_curation(papers)
        self.assertEqual(n, 1)
        curated_ids = [p["id"] for p in papers if p["curated"]]
        self.assertEqual(curated_ids, ["pmid_9008"])
        # 不硬删：发布集合不变，curated ⊆ published
        self.assertEqual([p["id"] for p in papers], published_before)
        self.assertTrue(set(curated_ids) <= set(published_before))
        # 解读暂停者即使 S 级 RCT 也不入精选
        self.assertFalse(papers[3]["curated"])
        self.assertEqual(papers[3]["publish_state"], "degraded")
        # 个案被规则排除
        self.assertEqual(papers[1]["curation_signals"]["design"], "case_report")

    # ---- S5 与 LLM 开关解绑 ----
    def test_s5_decoupled_from_llm_switch(self):
        # 启发式模式（score_source=heuristic）＋强信号 → 照常精选（启发式也可以真精选）
        p_heu = make_paper("9012", "Perioperative immunotherapy in resectable NSCLC",
                           ABS_RCT_PERIOP, e_issn="1533-4406")
        # LLM 模式（score_source=llm、高分）＋弱信号 → 不自动精选（LLM 不自动等于精选）
        a_llm = make_article("9013", "A survey of thoracic practice patterns",
                             "A questionnaire-based survey among thoracic surgeons.")
        scored = eng.heuristic_score(a_llm, JM)
        scored["score_source"] = "llm"
        scored["score_total"] = 34
        p_llm = eng.build_paper(a_llm, scored, None, "")
        n = eng.apply_curation([p_heu, p_llm])
        self.assertTrue(p_heu["curated"])
        self.assertFalse(p_llm["curated"])
        self.assertEqual(n, 1)
        # LLM 模式的精选理由带「模型补充」段（规则骨架＋模型理由综合）
        p_llm_rct = make_paper("9014", "Perioperative immunotherapy in resectable NSCLC",
                               ABS_RCT_PERIOP, e_issn="1533-4406")
        p_llm_rct["score_source"] = "llm"
        p_llm_rct["reason"] = " III 期围术期免疫联合方案的主要终点阳性结果。"
        eng.apply_curation([p_llm_rct])
        self.assertTrue(p_llm_rct["curated"])
        self.assertIn("模型补充", p_llm_rct["curation_reason"])
        # 规则骨架仍在（不是只剩模型话）
        self.assertIn("直接影响", p_llm_rct["curation_reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestRadarArchive(unittest.TestCase):
    """滚动窗档案（Batch3）：按 pmid 去重、新 briefing 覆盖旧、锚定最新日期取 N 天窗。"""

    def test_dedupe_anchor_window(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as td:
            adir = Path(td) / "archive"; adir.mkdir()
            out = Path(td) / "radar_latest.json"
            mk = lambda pmid, bd, tag: {"pmid": pmid, "briefing_date": bd, "title_en": tag}
            (adir / "2026-08-01.json").write_text(json.dumps({"papers": [mk("1", "2026-06-01", "old"), mk("2", "2026-06-01", "keep-old")]}, ensure_ascii=False), encoding="utf-8")
            (adir / "2026-10-17.json").write_text(json.dumps({"papers": [mk("2", "2026-10-17", "newer-wins"), mk("3", "2026-10-17", "fresh")]}, ensure_ascii=False), encoding="utf-8")
            (adir / "broken.json").write_text("{oops", encoding="utf-8")
            payload = eng.build_radar_archive(days=90, archive_dir=adir, out_path=out)
            self.assertEqual(payload["anchor_date"], "2026-10-17")
            by = {p["pmid"]: p for p in payload["papers"]}
            self.assertEqual(by["2"]["title_en"], "newer-wins")   # 新覆盖旧
            self.assertNotIn("1", by)                              # 90 天窗外的丢弃
            self.assertIn("3", by)
            self.assertIsNone(payload["papers"][0].get("_missing"))  # 无脏字段
            reloaded = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(reloaded["count"], len(reloaded["papers"]))

    def test_empty_archive(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            payload = eng.build_radar_archive(archive_dir=Path(td), out_path=Path(td) / "x.json")
            self.assertEqual(payload, {})



class TestCuratedWarnAndCap(unittest.TestCase):
    """Batch3 收尾：预警刊不入精选 + 同刊每日限量（挪威式稀释）。"""

    @staticmethod
    def mk_paper(pmid, abbr, score=80, warned=False):
        return {"pmid": pmid,
                "title_en": "Randomized trial of segmentectomy versus lobectomy",
                "abstract_en": "Patients were randomized to segmentectomy or lobectomy; "
                               "the primary endpoint was overall survival.",
                "tier": "S", "publish_state": "full", "journal_abbr": abbr,
                "score_total": score, "score_source": "heuristic", "category": "surgery",
                "warned": warned}

    def test_warned_excluded_from_curated(self):
        papers = [self.mk_paper("1", "WarnedJ", warned=True)]
        n = eng.apply_curation(papers)
        self.assertEqual(n, 0)
        self.assertFalse(papers[0]["curated"])

    def test_cap_two_per_journal(self):
        papers = [self.mk_paper(str(i), "MegaJ", score=90 - i) for i in range(3)]
        papers.append(self.mk_paper("9", "OtherJ", score=50))
        n = eng.apply_curation(papers)
        mega = [p for p in papers if p["journal_abbr"] == "MegaJ" and p.get("curated")]
        self.assertEqual(len(mega), 2)
        self.assertEqual(mega[0]["score_total"], 90)
        self.assertEqual(n, 3)
        self.assertIn("限量", [p for p in papers if p["journal_abbr"] == "MegaJ" and not p.get("curated")][0]["curation_reason"])

    def test_matcher_warned_default_false(self):
        r = JM.match(iso_abbr="N Engl J Med")
        self.assertTrue(r["matched"])
        self.assertFalse(r.get("warned", True))


class TestEsearchPagination(unittest.TestCase):
    """retmax 只是页大小：命中总量以 Count 为准，分页取全防静默截断。"""

    class _FakeCollector(eng.Collector):
        def __init__(self, total, page_size_seen):
            super().__init__()
            self.total = total
            self.calls = []
            self.page_size_seen = page_size_seen

        def _get(self, url):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            start, size = int(q["retstart"][0]), int(q["retmax"][0])
            self.calls.append((start, size))
            ids = [str(start + i + 1) for i in range(size) if start + i < self.total]
            return json.dumps({"esearchresult": {"count": str(self.total), "idlist": ids}}).encode()

    def test_pages_through_full_count(self):
        fc = self._FakeCollector(total=35, page_size_seen=None)
        pmids = fc.esearch_pmids(3, retmax=10, query="test")
        self.assertEqual(len(pmids), 35)
        self.assertEqual(pmids, [str(i) for i in range(1, 36)])
        starts = [c[0] for c in fc.calls]
        self.assertEqual(starts, [0, 0, 10, 20, 30])   # 首调 Count + 四页

    def test_single_page_small_count(self):
        fc = self._FakeCollector(total=8, page_size_seen=None)
        pmids = fc.esearch_pmids(3, retmax=200, query="test")
        self.assertEqual(len(pmids), 8)

    def test_hard_cap_truncates_loudly(self):
        fc = self._FakeCollector(total=3000, page_size_seen=None)
        pmids = fc.esearch_pmids(3, retmax=200, query="test", hard_cap=500)
        self.assertEqual(len(pmids), 500)

    def test_zero_count_returns_empty(self):
        fc = self._FakeCollector(total=0, page_size_seen=None)
        self.assertEqual(fc.esearch_pmids(3, retmax=200, query="test"), [])


class TestJournalHealth(unittest.TestCase):
    """目录健康台账：45–99 天静默提示、≥100 天报警、首见登记、命中即刷新。"""

    def _state_path(self):
        import shutil, tempfile
        from pathlib import Path
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        return Path(d) / "journal_health.json"

    def test_thresholds(self):
        from datetime import date, timedelta
        today = eng.bj_today()
        p = self._state_path()
        p.write_text(json.dumps({
            "OldJ": (today - timedelta(days=139)).isoformat(),
            "QuietJ": (today - timedelta(days=60)).isoformat(),
            "FreshJ": today.isoformat()}), encoding="utf-8")
        r = eng.update_journal_health({}, path=p)
        self.assertEqual(r["red"], ["OldJ"])
        self.assertEqual(r["yellow"], ["QuietJ"])
        self.assertEqual(r["total"], 3)
        self.assertEqual(r["green"], 1)

    def test_first_seen_registered_and_hit_refreshes(self):
        from datetime import date
        p = self._state_path()
        eng.update_journal_health({"NewJ": 5, "QuietJ": 0}, path=p)
        state = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(state["NewJ"], eng.bj_today().isoformat())
        self.assertIn("QuietJ", state)               # 零命中也首见入册

    def test_merge_dedup_preserves_order(self):
        merged = list(dict.fromkeys(["2", "1", "3", "1"]))
        self.assertEqual(merged, ["2", "1", "3"])


class TestSeenLedger(unittest.TestCase):
    """见过账本：滚动 90 天剪枝；防重复税。"""

    def test_prune_old_and_keep_recent(self):
        import shutil, tempfile
        from datetime import date, timedelta
        from pathlib import Path
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        p = Path(d) / "seen_pmids.json"
        today = eng.bj_today()
        p.write_text(json.dumps({
            "111": (today - timedelta(days=89)).isoformat(),   # 留
            "222": (today - timedelta(days=90)).isoformat(),   # 留（边界含）
            "333": (today - timedelta(days=91)).isoformat(),   # 剪
            "444": "garbage",                                  # 坏值剪
        }), encoding="utf-8")
        seen = eng.load_seen(path=p)
        self.assertEqual(sorted(seen), ["111", "222"])

    def test_corrupt_ledger_rebuilds_empty(self):
        import shutil, tempfile
        from pathlib import Path
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        p = Path(d) / "seen_pmids.json"
        p.write_text("not-json{", encoding="utf-8")
        self.assertEqual(eng.load_seen(path=p), {})


class TestSeenDoiLedger(unittest.TestCase):
    """DOI 二级账本：同论文双 PMID（ahead-of-print 双录）收一弃一。"""

    def test_norm_doi_strips_prefix_and_lowercases(self):
        cases = {
            "10.1016/j.jtho.2026.10.001": "10.1016/j.jtho.2026.10.001",
            "https://doi.org/10.1056/NEJMoA2032125": "10.1056/nejmoa2032125",
            "doi:10.1093/nar/gkz430": "10.1093/nar/gkz430",
            "https://dx.doi.org/10.1038/S41592-019-0686-2": "10.1038/s41592-019-0686-2",
            "": "",
            None: "",
        }
        for raw, want in cases.items():
            self.assertEqual(eng.norm_doi(raw), want, raw)

    def test_prune_and_roundtrip(self):
        import shutil, tempfile
        from datetime import date, timedelta
        from pathlib import Path
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        p = Path(d) / "seen_dois.json"
        today = eng.bj_today()
        W = eng.DOI_LEDGER_DAYS  # 账本窗与常量同源，窗宽再调不破测试
        state = {
            "10.1/keep": {"pmid": "111", "date": (today - timedelta(days=W - 1)).isoformat()},
            "10.1/edge": {"pmid": "222", "date": (today - timedelta(days=W)).isoformat()},
            "10.1/old": {"pmid": "333", "date": (today - timedelta(days=W + 1)).isoformat()},
            "10.1/bad-date": {"pmid": "444", "date": "garbage"},
            "10.1/bad-shape": "flat-string",
        }
        eng.save_seen_dois(state, path=p)
        loaded = eng.load_seen_dois(path=p)
        self.assertEqual(sorted(loaded), ["10.1/edge", "10.1/keep"])
        self.assertEqual(loaded["10.1/keep"]["pmid"], "111")

    def test_corrupt_doi_ledger_rebuilds_empty(self):
        import shutil, tempfile
        from pathlib import Path
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        p = Path(d) / "seen_dois.json"
        p.write_text("not-json{", encoding="utf-8")
        self.assertEqual(eng.load_seen_dois(path=p), {})


class TestScopeGate(unittest.TestCase):
    """胸科范围机械闸（2026-10-31 PHERGain 判例）：负词命中且无正锚＝拦；负正互搏＝放行。"""

    @staticmethod
    def _a(title, abstract=""):
        return {"title_en": title, "abstract_en": abstract}

    def test_phergain_breast_rejected(self):
        a = self._a("5-year outcomes of chemotherapy de-escalation in HER2-positive early "
                    "breast cancer and exploratory circulating tumor DNA analyses from the "
                    "randomized phase 2 PHERGain trial.",
                    "PHERGain was a randomized phase 2 trial in HER2-positive early breast cancer.")
        self.assertFalse(eng.thoracic_scope_gate(a))

    def test_kras_pancreatic_and_mi_rejected(self):
        self.assertFalse(eng.thoracic_scope_gate(self._a(
            "KRASG12D-targeted therapy sensitivity depends on interferon signaling "
            "activation in pancreatic cancer")))
        self.assertFalse(eng.thoracic_scope_gate(self._a(
            "Performance of 0/1 h versus 0/3 h pathways in patients with suspected "
            "myocardial infarction")))

    def test_thoracic_aortic_is_cardiac_not_thoracic(self):
        self.assertFalse(eng.thoracic_scope_gate(self._a(
            "Endovascular repair of descending thoracic aortic aneurysm")))

    def test_neg_pos_collision_passes_to_judge(self):
        self.assertTrue(eng.thoracic_scope_gate(self._a(
            "Surgical resection of pulmonary metastases from breast cancer")))
        self.assertTrue(eng.thoracic_scope_gate(self._a(
            "Primary mediastinal B-cell lymphoma: long-term outcomes")))

    def test_true_thoracic_passes(self):
        for t in ("VATS anatomic segmentectomy for clinical T1N0 lung cancer",
                  "Pragmatic trial of weight loss intervention in obstructive sleep apnea",
                  "Perioperative immunotherapy in resectable esophageal squamous cell carcinoma"):
            self.assertTrue(eng.thoracic_scope_gate(self._a(t)), t)

    def test_word_boundary_colony_not_colon(self):
        # 「granulocyte colony-stimulating factor」不得被 \bcolon\b 误中
        self.assertTrue(eng.thoracic_scope_gate(self._a(
            "Granulocyte colony-stimulating factor prophylaxis in patients receiving "
            "chemotherapy for solid tumors")))

    def test_prescreen_prompt_requires_anchor(self):
        self.assertIn("anchor", eng.LIBRARY_PRESCREEN_SYSTEM)
        self.assertIn("PHERGain", eng.LIBRARY_PRESCREEN_SYSTEM)

    def test_llm_outage_falls_open_not_closed(self):
        """判官失联日＝fail-open：整批放行交精评，不得被锚点校验误杀成全天归零。"""
        class DeadLLM:
            available, cost_usd, calls = True, 0.0, 0
            def chat(self, *a, **k):
                raise RuntimeError("connection refused")
        arts = [{"pmid": str(i), "journal_title": "J Thorac Dis", "title_en": f"lung cancer study {i}",
                 "abstract_en": "lung cancer"} for i in range(3)]
        kept = eng.llm_prescreen(DeadLLM(), arts)
        self.assertEqual(len(kept), 3)          # 全放行；锚为哨兵串非空


class TestRefit20261101(unittest.TestCase):
    """换装三件套（PI 2026-11-01）：检索式路关停／范围闸影子模式／Anthropic 协议支。"""

    def test_query_path_disabled_by_ruling(self):
        self.assertFalse(eng.QUERY_PATH_ENABLED)      # PI 裁定关停；翻 True 复活

    def test_scope_gate_mode_shadow(self):
        self.assertEqual(eng.SCOPE_GATE_MODE, "shadow")
        # 影子模式不改判据：PHERGain 仍判 False（一致性由每日影子账对账）
        self.assertFalse(eng.thoracic_scope_gate(
            {"title_en": "chemotherapy de-escalation in HER2-positive early breast cancer",
             "abstract_en": ""}))

    def test_scope_shadow_ledger_writes(self):
        import shutil, tempfile
        from pathlib import Path
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        p = Path(d) / "scope_gate_shadow.json"
        eng.log_scope_shadow("2026-11-01", [
            {"pmid": "1", "title_en": "breast cancer trial"},
            {"pmid": "2", "title_en": "glioblastoma immunity"},
        ], path=p)
        state = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(state["2026-11-01"][0]["pmid"], "1")
        self.assertIn("breast", state["2026-11-01"][0]["title"])

    def test_llm_protocol_autodetect_and_pricing(self):
        import os
        saved = {k: os.environ.pop(k, None) for k in
                 ("LLM_BASE_URL", "LLM_PROTOCOL", "LLM_PRICE_IN", "LLM_PRICE_OUT")}
        self.addCleanup(lambda: [os.environ.__setitem__(k, v) for k, v in saved.items() if v is not None])
        llm = eng.LLMClient()
        self.assertEqual(llm.protocol, "openai")
        self.assertGreater(llm.price_in, 0)
        os.environ["LLM_BASE_URL"] = "https://token-plan-sgp.xiaomimimo.com/anthropic"
        llm2 = eng.LLMClient()
        self.assertEqual(llm2.protocol, "anthropic")
        self.assertEqual(llm2.price_in, 0.0)          # 订阅包月＝边际 0
        self.assertEqual(llm2.price_out, 0.0)


class TestLifecycleV2(unittest.TestCase):
    """名册生命周期 v2 排期①：检查点回补＋降档止血＋产出表。"""

    def test_toc_window_backfill_and_overlap(self):
        self.assertEqual(eng.toc_window("2026-10-29", "2026-11-01", 3), 5)     # 缺口+2 重叠
        self.assertEqual(eng.toc_window("2026-09-01", "2026-11-01", 3), 63)    # 长停机全补
        self.assertEqual(eng.toc_window("2026-11-01", "2026-11-01", 3), 3)     # 当日＝基础窗
        self.assertEqual(eng.toc_window("bad", "2026-11-01", 3), 10)           # 坏日期保守放大

    def test_toc_checkpoint_roundtrip(self):
        import shutil, tempfile
        from pathlib import Path
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        p = Path(d) / "toc_checkpoint.json"
        eng.save_toc_checkpoint({"Lung Cancer": "2026-11-01"}, path=p)
        self.assertEqual(eng.load_toc_checkpoint(path=p), {"Lung Cancer": "2026-11-01"})
        p.write_text("not-json{", encoding="utf-8")
        self.assertEqual(eng.load_toc_checkpoint(path=p), {})                  # 坏档从零起

    def test_suspended_loader_and_bootstrap(self):
        import shutil, tempfile
        from pathlib import Path
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        p = Path(d) / "journal_suspended.json"
        p.write_text(json.dumps({"Biomedicines": {"since": "2026-11-01", "reason": "yield=0"}}),
                     encoding="utf-8")
        self.assertIn("Biomedicines", eng.load_suspended(path=p))
        p.write_text("not-json{", encoding="utf-8")
        self.assertEqual(eng.load_suspended(path=p), {})                       # 坏档＝无降档
        # 生产降档册已入库：85 刊、全部带 since 与 v2 评审期限说明
        prod = eng.load_suspended()
        self.assertGreaterEqual(len(prod), 80)
        self.assertTrue(all("2027-02-01" in v.get("reason", "") for v in prod.values()))


class TestPrescreenRejectedLog(unittest.TestCase):
    """拒件落盘（T-THR-REJLOG）：进了预筛但不在幸存列表者记 {pmid, ta} 日档；
    同日多批并集不丢；滚动 90 天清档（边界含）；fail-open 坏目录/烂旧档不打断主管线。"""

    @staticmethod
    def _art(pmid, iso_abbr="", journal_title=""):
        return {"pmid": pmid, "iso_abbr": iso_abbr, "journal_title": journal_title}

    def _tmp(self):
        import shutil, tempfile
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        return Path(d)

    def test_write_content_and_same_day_merge(self):
        d = self._tmp()
        day = "2026-10-26"
        stage = [self._art("1", "J Thorac Dis", "Journal of Thoracic Disease"),
                 self._art("2", "", "Chest"),
                 self._art("3", "Lancet", "The Lancet")]
        survivors = [self._art("3", "Lancet", "The Lancet")]       # 3 幸存 → 1/2 落拒件档
        eng.log_prescreen_rejected(day, stage, survivors, dir_path=d)
        f = d / f"{day}.json"
        payload = json.loads(f.read_text(encoding="utf-8"))
        self.assertEqual(payload["rejected"],
                         [{"pmid": "1", "ta": "J Thorac Dis"},
                          {"pmid": "2", "ta": "Chest"}])           # ta=iso_abbr，缺则 journal_title
        self.assertTrue(payload["generated_at"])                  # 落盘时刻在档
        # 同日第二批（mesh 兜底路同天）：按 pmid 并集累积——每批不丢、不重条
        eng.log_prescreen_rejected(day, [self._art("4", "Ann Thorac Surg", "")], [], dir_path=d)
        payload2 = json.loads(f.read_text(encoding="utf-8"))
        self.assertEqual([r["pmid"] for r in payload2["rejected"]], ["1", "2", "4"])

    def test_rolling_window_cleanup(self):
        from datetime import timedelta
        d = self._tmp()
        W = eng.SEEN_LEDGER_DAYS        # 窗宽与常量同源，窗宽再调不破测试
        today = eng.bj_today()
        beyond = (today - timedelta(days=W + 1)).isoformat()   # 超窗 → 剪
        edge = (today - timedelta(days=W)).isoformat()         # 边界含（与账本同语义）→ 留
        inside = (today - timedelta(days=1)).isoformat()
        for name in (beyond, edge, inside):
            (d / f"{name}.json").write_text('{"rejected": []}', encoding="utf-8")
        (d / "not-a-date.json").write_text("{}", encoding="utf-8")      # 他名不动
        (d / "2026-13-99.json").write_text("{}", encoding="utf-8")      # 伪日期不动
        eng.log_prescreen_rejected(today.isoformat(), [self._art("9", "Lancet")],
                                   [], dir_path=d)
        self.assertFalse((d / f"{beyond}.json").exists())
        for name in (edge, inside, "not-a-date", "2026-13-99"):
            self.assertTrue((d / f"{name}.json").exists(), name)
        self.assertTrue((d / f"{today.isoformat()}.json").exists())     # 当日档已写

    def test_fail_open_bad_dir_and_corrupt_prev(self):
        d = self._tmp()
        # 坏目录：目标路径被普通文件占住 → mkdir 必炸 → 调用不得抛（fail-open）
        blocker = d / "prescreen_rejected"
        blocker.write_text("i am a file", encoding="utf-8")
        eng.log_prescreen_rejected("2026-10-26", [self._art("1", "J")], [], dir_path=blocker)
        # 烂旧档：当日档是坏 JSON → 从本批重建不崩，内容＝本次批
        d2 = self._tmp()
        (d2 / "2026-10-26.json").write_text("{oops", encoding="utf-8")
        eng.log_prescreen_rejected("2026-10-26", [self._art("7", "Lancet")], [], dir_path=d2)
        payload = json.loads((d2 / "2026-10-26.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["rejected"], [{"pmid": "7", "ta": "Lancet"}])


class TestMeshBackstop(unittest.TestCase):
    """MeSH 兜底层：词表非空、无已废弃主题词、检索式可拼装。"""

    def test_terms_present_and_esophageal_surgery_absent(self):
        self.assertGreaterEqual(len(eng.MESH_BACKSTOP_TERMS), 5)
        self.assertNotIn("Esophageal Surgical Procedures", eng.MESH_BACKSTOP_TERMS)

    def test_query_builds_with_mesh_tag(self):
        t = eng.MESH_BACKSTOP_TERMS[0]
        q = f'"{t}"[Mesh]'
        self.assertIn("[Mesh]", q)
        self.assertIn(t, q)
