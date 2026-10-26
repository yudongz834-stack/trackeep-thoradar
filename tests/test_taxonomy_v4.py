#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
换册 v4 最小回归（brief5 任务 4 · 2026-10-26）

四条新册回归＋两条引擎接线回归（离线，不联网）：
  R1 S=7 本在册（tier_new=='S' 条目数，JAMA/BMJ 名形双行并册后条目级）；
  R2 量控 6 本强制 D（tier_rule==1 的 6 本全 D）；
  R3 jcat 合法值：全条目 category ∈ {1..10, 待定}；
  R4 JAMA 别名在册（name_aliases 含 'JAMA'，S 档，9 综合类）；
  R5 引擎双读：match 读 tier_new（NEJM=S、JTCVS=C·bonus0），未命中兜底 D；
  R6 bonus 表＝S15/A12/B8/C0/D0 且 B 档 whitelist_exempt=true（主控已裁沿旧 A 政策）。

运行：E:/Python/python.exe -X utf8 -I -m unittest discover -s tests -v
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import thoradar_engine as eng  # noqa: E402

CFG = json.loads(eng.JOURNALS_FILE.read_text(encoding="utf-8"))
JOURNALS = CFG["journals"]
JCAT_LEGAL = {str(i) for i in range(1, 11)} | {"待定"}


class TaxonomyV4Tests(unittest.TestCase):
    def test_r1_s_tier_seven_entries(self):
        s = [j for j in JOURNALS if j.get("tier_new") == "S"]
        self.assertEqual(len(s), 7, f"S 档应 7 本，实得 {len(s)}：{[j['name'] for j in s]}")
        for j in s:
            self.assertEqual(str(j.get("category")), "9", f"S 档 {j['name']} 应在 9 综合类")

    def test_r2_volume_control_six_forced_d(self):
        vc = [j for j in JOURNALS if j.get("tier_rule") == 1]
        self.assertEqual(len(vc), 6, f"量控应 6 本，实得 {len(vc)}")
        for j in vc:
            self.assertEqual(j.get("tier_new"), "D", f"量控刊 {j['name']} 应强制 D")

    def test_r3_jcat_values_legal(self):
        bad = [(j["name"], j.get("category")) for j in JOURNALS
               if str(j.get("category", "")) not in JCAT_LEGAL]
        self.assertEqual(bad, [], f"jcat 非法值条目：{bad[:5]}")

    def test_r4_jama_alias_registered(self):
        hits = [j for j in JOURNALS if "JAMA" in (j.get("name_aliases") or [])]
        self.assertEqual(len(hits), 1, "应有且仅有 1 条 JAMA 别名条目")
        j = hits[0]
        self.assertEqual(j.get("tier_new"), "S", "JAMA 应为 S 档")
        self.assertEqual(str(j.get("category")), "9", "JAMA 应在 9 综合类")

    def test_r5_engine_reads_tier_new_and_falls_back_d(self):
        jm = eng.JournalMatcher(CFG)
        m_nejm = jm.match(e_issn="1533-4406")
        self.assertTrue(m_nejm["matched"])
        self.assertEqual(m_nejm["tier"], "S")
        self.assertTrue(m_nejm["whitelist_exempt"])
        m_jtcvs = jm.match(nlm_id="0376343")
        self.assertEqual(m_jtcvs["tier"], "C")            # 换册实跑反推：JTCVS=2区→C
        self.assertEqual(m_jtcvs["journal_bonus"], 0)
        self.assertEqual(m_jtcvs["journal_category"], "1")  # JTCVS 阵地＝1 胸部肿瘤与胸外科（胸科本家优先，实测）
        m_none = jm.match()
        self.assertFalse(m_none["matched"])
        self.assertEqual(m_none["tier"], "D")              # 未命中兜底 D（P2）
        self.assertEqual(m_none["journal_category"], "")

    def test_r7_empty_id_rows_reachable_by_name(self):
        """28 本空 NLM ID 刊五键全空、唯一身份＝walk 规范名：name 弱键须可命中且带阵地（红线 2 兜底准入）。"""
        noid = [j for j in JOURNALS if not j.get("nlm_id")]
        self.assertEqual(len(noid), 28, f"空 ID 刊应 28 本，实得 {len(noid)}")
        for j in noid:
            self.assertTrue(str(j.get("name", "")).strip(), f"空 ID 刊缺 name：{j.get('id')}")
        jm = eng.JournalMatcher(CFG)
        m = jm.match(title="EUROSURVEILLANCE")
        self.assertTrue(m["matched"], "name 弱键应命中 Eurosurveillance")
        self.assertEqual(m["tier"], "C")
        self.assertEqual(m["journal_category"], "5")  # Eurosurveillance＝感染监测刊，归 5 感染与免疫（实测）
        self.assertTrue(m["journal_full"], "journal_full 应回落 name 不落空")

    def test_r6_bonus_map_and_b_exempt(self):
        tiers = CFG["tiers"]
        self.assertEqual({k: v["score_bonus"] for k, v in tiers.items()},
                         {"S": 15, "A": 12, "B": 8, "C": 0, "D": 0})
        self.assertTrue(tiers["B"]["whitelist_exempt"], "新 B 档须沿用旧 A 豁免政策（主控已裁）")
        self.assertFalse(tiers["C"]["whitelist_exempt"])
        self.assertFalse(tiers["D"]["whitelist_exempt"])
        self.assertEqual(CFG.get("version"), "4.0.0")


if __name__ == "__main__":
    unittest.main()
