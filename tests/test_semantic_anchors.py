#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SemanticChecker 锚定词扩充·合成摘要验收（不联网）。

覆盖：
  ① 新增锚命中 → 通过；
  ② 人群偷换仍拦截（换人群后锚不命中）；
  ③ 空锚词表行为不变（未收录词 / 未收录指标仍 fail-closed）；
  ④ 明确不加锚的词仍误杀。

运行：
  E:/Python/python.exe -X utf8 -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import thoradar_engine as eng  # noqa: E402

# 合成摘要：同时含本批新增锚，不含鳞癌/脑转移，也不含 video-assisted。
ABS_HIT = (
    "All patients in the entire cohort were followed for 36 months. "
    "Primary cells were maintained in vitro, and sequencing samples were profiled. "
    "All videos included in the study were reviewed by two readers. "
    "The primary endpoint was overall survival."
)
ABS_OS_ONLY = "The 5-year overall survival was 65.4% in the predefined subgroup."


def audit(abstract: str, group: str, metric: str = "总生存") -> dict:
    return eng.SemanticChecker.check(
        abstract, [{"group": group, "metric": metric, "val": "10%", "stat": ""}]
    )


def reasons(result: dict) -> list:
    return result["tuple_audit"][0]["mismatch_reasons"]


class SemanticAnchorExpansion(unittest.TestCase):
    """新增人群锚：命中放行；偷换与空锚仍拦截。"""

    def test_zongti_phrase_passes(self):
        result = audit(ABS_HIT, "总体")
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["n_mismatch"], 0)

    def test_suifang_passes(self):
        result = audit(ABS_HIT, "随访")
        self.assertTrue(result["passed"], result)

    def test_xibao_passes(self):
        result = audit(ABS_HIT, "细胞")
        self.assertTrue(result["passed"], result)

    def test_cexuyangben_passes(self):
        result = audit(ABS_HIT, "测序样本")
        self.assertTrue(result["passed"], result)

    def test_tiwai_yuandai_passes_only_when_both_hit(self):
        both = audit(ABS_HIT, "体外原代")
        self.assertTrue(both["passed"], both)
        invitro_only = audit(
            "Cells were treated in vitro. The primary endpoint was overall survival.",
            "体外原代",
        )
        self.assertFalse(invitro_only["passed"], invitro_only)
        self.assertTrue(any("原代" in r for r in reasons(invitro_only)), invitro_only)

    def test_quanbu_naru_shipin_passes(self):
        result = audit(ABS_HIT, "全部纳入视频")
        self.assertTrue(result["passed"], result)

    def test_population_swap_still_blocked(self):
        """同一摘要、同一终点：总体放行；换成摘要里没有的鳞癌/脑转移必须拦截。"""
        kept = audit(ABS_HIT, "总体")
        self.assertTrue(kept["passed"], kept)
        for swapped in ("鳞癌", "脑转移"):
            blocked = audit(ABS_HIT, swapped)
            self.assertFalse(blocked["passed"], blocked)
            self.assertTrue(
                any(swapped in r and "未在原摘要出现" in r for r in reasons(blocked)),
                blocked,
            )

    def test_empty_anchor_list_unchanged(self):
        """词典未收录 → 锚表为空 → 仍写「宁误杀」，不改判通过。"""
        quals = eng.SemanticChecker._qualifiers_of("主导条件", eng.SEMANTIC_QUALIFIER_ANCHORS)
        self.assertTrue(any(q["label"] == "主导条件" and q["anchors"] == [] for q in quals), quals)
        blocked = audit(ABS_HIT, "主导条件")
        self.assertFalse(blocked["passed"], blocked)
        self.assertTrue(any("无英文锚" in r and "主导条件" in r for r in reasons(blocked)), blocked)

        self.assertEqual(eng.SemanticChecker.metric_anchors("招牌终点"), [])
        metric_blocked = audit(ABS_HIT, "总体", metric="招牌终点")
        self.assertFalse(metric_blocked["passed"], metric_blocked)
        self.assertTrue(any("无可用锚" in r for r in reasons(metric_blocked)), metric_blocked)

    def test_bing_still_fail_closed(self):
        abstract = "The disease burden remained high. Overall survival was 40%."
        result = audit(abstract, "病")
        self.assertFalse(result["passed"], result)
        self.assertTrue(any("无英文锚" in r and "病" in r for r in reasons(result)), result)

    def test_single_char_generics_still_fail_closed(self):
        """全/单/后/对 不加锚：摘要里即使有 all/single/after/versus 也仍误杀。"""
        cases = {
            "全": "All patients were analyzed. Overall survival was 50%.",
            "单": "A single arm was enrolled. Overall survival was 50%.",
            "后": "After treatment, overall survival was 50%.",
            "对": "Arm A versus arm B was compared. Overall survival was 50%.",
        }
        for group, abstract in cases.items():
            result = audit(abstract, group)
            self.assertFalse(result["passed"], result)
            self.assertTrue(
                any("无英文锚" in r and f"「{group}」" in r for r in reasons(result)),
                result,
            )

    def test_year_1957_not_exempted(self):
        """1957 已是数字自锚，不另造英文锚；摘要没有这四个数字就仍拦截。"""
        missing = audit("The historical cohort was reassembled. Overall survival was 40%.", "1957")
        self.assertFalse(missing["passed"], missing)
        self.assertTrue(any("1957" in r and "未在原摘要出现" in r for r in reasons(missing)), missing)
        present = audit("The cohort was assembled in 1957. Overall survival was 40%.", "1957")
        self.assertTrue(present["passed"], present)

    def test_zongti_not_satisfied_by_overall_survival_alone(self):
        result = audit(ABS_OS_ONLY, "总体")
        self.assertFalse(result["passed"], result)
        self.assertTrue(any("总体" in r for r in reasons(result)), result)

    def test_xibao_not_satisfied_by_in_vitro_or_in_vivo(self):
        abstract = "Assays were performed in vitro and in vivo. Overall survival was 40%."
        result = audit(abstract, "细胞")
        self.assertFalse(result["passed"], result)
        self.assertTrue(any("细胞" in r and "未在原摘要出现" in r for r in reasons(result)), result)

    def test_videos_anchor_does_not_match_video_assisted(self):
        abstract = (
            "Video-assisted thoracoscopic surgery was performed. "
            "Overall survival was 70%."
        )
        result = audit(abstract, "全部纳入视频")
        self.assertFalse(result["passed"], result)


if __name__ == "__main__":
    unittest.main()
