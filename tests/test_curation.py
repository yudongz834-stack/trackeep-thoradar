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
                       ABS_PROSP_MATCH_SURGERY, e_issn="1552-6259"),   # Ann Thorac Surg A
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
