#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
门禁件①③④⑤ 工具面回归（意志书 v1.1 五门禁件施工 2026-11-08）。

① roster_intake_check：现册自检 PASS；拔钉/改档/空 NLM/重键/超带宽/换 bonus 各 tamper 全红。
③ pin_export＋pin_reconcile：快照 SHA256 可复算、组计数与附录 A 对齐；对拍现册零漂移；
   tamper 册面与快照后必红；席定钉正本失联＝红（fail-closed）。
④ shadow_rerun：守恒闭合、矩阵非空、差额单逐条带解释；classifier 钩子 mock 可插；
   --out 指向 config/ 拒绝（账外不写产线）。
⑤ weekly_gate_columns：四列齐、现盘真值（新刊 0）、新进行与量控两线单测直证。

运行：E:/Python/python.exe -X utf8 -I tests/test_gate_files.py
"""
import json
import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

import thoradar_pins as pins  # noqa: E402
import weekly_gate_columns as wgc  # noqa: E402

CONFIG_PATH = REPO / "config" / "journals_taxonomy.json"
SEAL_PATH = REPO / "design" / "名册封存-20261101.json"
V3_PATH = REPO / "config" / "journals_taxonomy_v3.1.0.json.bak"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
SEAL = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
PYEXE = [sys.executable, "-X", "utf8", "-I"]
TOOLS = REPO / "tools"


def run_cli(script: Path, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(PYEXE + [str(script)] + list(argv), capture_output=True,
                          text=True, encoding="utf-8", timeout=120)


def write_tmp(tmp: Path, name: str, doc: dict) -> Path:
    p = tmp / name
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return p


class IntakeCheckTests(unittest.TestCase):
    """① 进门验收器：好表放行，六种 tamper 全红。"""

    def test_current_config_passes_self_check(self):
        r = run_cli(TOOLS / "roster_intake_check.py", "--table", str(CONFIG_PATH),
                    "--baseline", str(CONFIG_PATH))
        self.assertEqual(r.returncode, 0, f"现册自检应 PASS：{r.stdout[-600:]}{r.stderr[-300:]}")
        self.assertIn("[PASS]", r.stdout)

    def test_removed_pin_row_fails(self):
        doc = copy.deepcopy(CONFIG)
        doc["journals"] = [j for j in doc["journals"] if j.get("nlm_id") != "101769674"]  # 拔 Esophagus
        with tempfile.TemporaryDirectory() as td:
            p = write_tmp(Path(td), "tampered.json", doc)
            r = run_cli(TOOLS / "roster_intake_check.py", "--table", str(p),
                        "--baseline", str(CONFIG_PATH))
        self.assertEqual(r.returncode, 1, "拔量控钉刊必须红")
        self.assertIn("量控六刊", r.stdout)

    def test_illegal_tier_fails(self):
        doc = copy.deepcopy(CONFIG)
        doc["journals"][0]["tier_new"] = "X"
        with tempfile.TemporaryDirectory() as td:
            p = write_tmp(Path(td), "tampered.json", doc)
            r = run_cli(TOOLS / "roster_intake_check.py", "--table", str(p),
                        "--baseline", str(CONFIG_PATH))
        self.assertEqual(r.returncode, 1)
        self.assertIn("档位合法值", r.stdout)

    def test_empty_nlm_id_fails(self):
        doc = copy.deepcopy(CONFIG)
        doc["journals"][0]["nlm_id"] = ""
        with tempfile.TemporaryDirectory() as td:
            p = write_tmp(Path(td), "tampered.json", doc)
            r = run_cli(TOOLS / "roster_intake_check.py", "--table", str(p),
                        "--baseline", str(CONFIG_PATH))
        self.assertEqual(r.returncode, 1)
        self.assertIn("五键齐全", r.stdout)

    def test_duplicate_nlm_id_fails(self):
        doc = copy.deepcopy(CONFIG)
        doc["journals"][1]["nlm_id"] = doc["journals"][0]["nlm_id"]
        with tempfile.TemporaryDirectory() as td:
            p = write_tmp(Path(td), "tampered.json", doc)
            r = run_cli(TOOLS / "roster_intake_check.py", "--table", str(p),
                        "--baseline", str(CONFIG_PATH))
        self.assertEqual(r.returncode, 1)
        self.assertIn("重复", r.stdout)

    def test_over_band_shrink_fails(self):
        doc = copy.deepcopy(CONFIG)
        doc["journals"] = doc["journals"][:150]  # 197→150 ≈ -23.9%，超 ±5%
        with tempfile.TemporaryDirectory() as td:
            p = write_tmp(Path(td), "tampered.json", doc)
            r = run_cli(TOOLS / "roster_intake_check.py", "--table", str(p),
                        "--baseline", str(CONFIG_PATH))
        self.assertEqual(r.returncode, 1)
        self.assertIn("±5% 带宽", r.stdout)

    def test_bonus_map_change_fails(self):
        doc = copy.deepcopy(CONFIG)
        doc["tiers"]["S"]["score_bonus"] = 20  # 意志书三.1 钉 15
        with tempfile.TemporaryDirectory() as td:
            p = write_tmp(Path(td), "tampered.json", doc)
            r = run_cli(TOOLS / "roster_intake_check.py", "--table", str(p),
                        "--baseline", str(CONFIG_PATH))
        self.assertEqual(r.returncode, 1)
        self.assertIn("bonus_map", r.stdout)


class ExportReconcileTests(unittest.TestCase):
    """③ 导出器＋对账器。"""

    def test_export_snapshot_structure_and_sha(self):
        import hashlib
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "snap.json"
            r = run_cli(TOOLS / "pin_export.py", "--out", str(out))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            snap = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(snap["config_sha256"],
                             hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest())
            g = snap["groups"]
            self.assertEqual(len(g["S七刊"]), 7)
            self.assertEqual(len(g["冠冕三刊"]), 3)
            self.assertEqual(len(g["量控六刊(留册)"]), 3)
            self.assertEqual(len(g["量控六刊(封存)"]), 3)
            self.assertEqual(len(g["平台16(封存)"]), 16)
            self.assertEqual(len(g["判例九(留册)"]), 7)
            self.assertEqual(len(g["判例九(封存)"]), 2)
            self.assertEqual(len(g["裁定五(留册)"]), 2)
            self.assertEqual(len(g["裁定五(封存)"]), 3)
            self.assertEqual(len(g["不收十(缺席)"]), 10)
            self.assertTrue(all(row["absent_live"] and row["absent_sealed"]
                                for row in g["不收十(缺席)"]), "不收十须两册双缺席")

    def test_reconcile_current_zero_drift(self):
        r = run_cli(TOOLS / "pin_reconcile.py", "--no-snapshot")
        self.assertEqual(r.returncode, 0, f"现册对拍应零漂移：{r.stdout[-600:]}")
        self.assertIn("[PASS]", r.stdout)

    def test_reconcile_detects_tampered_tier(self):
        doc = copy.deepcopy(CONFIG)
        for j in doc["journals"]:
            if j.get("nlm_id") == "0376343":  # JTCVS 冠冕钉 B→C
                j["tier_new"] = "C"
        with tempfile.TemporaryDirectory() as td:
            p = write_tmp(Path(td), "tampered.json", doc)
            r = run_cli(TOOLS / "pin_reconcile.py", "--config", str(p), "--no-snapshot")
        self.assertEqual(r.returncode, 1, "冠冕钉改档必须红")
        self.assertIn("冠冕三刊", r.stdout)

    def test_reconcile_detects_snapshot_drift(self):
        doc = copy.deepcopy(CONFIG)
        for j in doc["journals"]:
            if j.get("nlm_id") == "0376343":
                j["tier_new"] = "C"
        with tempfile.TemporaryDirectory() as td:
            snap = Path(td) / "snap.json"
            self.assertEqual(run_cli(TOOLS / "pin_export.py", "--out", str(snap)).returncode, 0)
            p = write_tmp(Path(td), "tampered.json", doc)
            r = run_cli(TOOLS / "pin_reconcile.py", "--config", str(p), "--snapshot", str(snap))
        self.assertEqual(r.returncode, 1)
        self.assertIn("快照后漂移", r.stdout)

    def test_reconcile_fails_closed_when_classify_py_missing(self):
        r = run_cli(TOOLS / "pin_reconcile.py", "--no-snapshot",
                    "--classify-py", "Z:/definitely/not/here/classify.py")
        self.assertEqual(r.returncode, 1, "席定钉正本失联＝对拍失眼，fail-closed 即红")
        self.assertIn("席定钉正本不可达", r.stdout)


class ShadowRerunTests(unittest.TestCase):
    """④ 影子重跑：守恒闭合＋差额带解释＋mock 钩子＋账外不写产线。"""

    def test_framework_end_to_end_v3_vs_current(self):
        from shadow_rerun import run_shadow
        articles = [
            {"pmid": "t1", "title": "x", "e_issn": "1533-4406"},       # NEJM 两册在册
            {"pmid": "t2", "title": "y", "p_issn": "1873-734X"},       # EJCTS 新册钉 B
            {"pmid": "t3", "title": "A STUDY WITH NO LEDGER MATCH"},   # 兜底 D
        ]
        res = run_shadow(json.loads(V3_PATH.read_text(encoding="utf-8")), CONFIG,
                         articles, sealed_rows=SEAL["journals"])
        cons = res["conservation"]
        self.assertTrue(cons["conservation_ok"], "三篇在两册各恰分类一次")
        self.assertEqual(cons["articles_total"], 3)
        self.assertGreater(len(res["migration"]["tier_matrix_cells"]), 0)
        rd = cons["roster_delta"]
        self.assertGreater(rd["old_rows"], rd["new_rows"], "v3 340 行 > 现册 197 行")
        for d in res["discrepancies"]:
            self.assertTrue(d["explain"].strip(), f"差额单必带解释：{d['pmid']}")

    def test_classifier_hook_mock(self):
        from shadow_rerun import run_shadow
        def mock_classifier(article):
            return {"matched": True, "tier": "B", "category": "1", "journal": "MOCK"}
        res = run_shadow(CONFIG, CONFIG, [{"pmid": "m1", "title": "whatever"}],
                         classifier=mock_classifier)
        self.assertEqual(res["conservation"]["old"]["tier_dist"], {"B": 1},
                         "classifier 钩子应可整体替换判定（LLM mock 接入点）")

    def test_out_inside_config_dir_rejected(self):
        r = run_cli(TOOLS / "shadow_rerun.py", "--old", str(CONFIG_PATH), "--new",
                    str(CONFIG_PATH), "--out", str(REPO / "config" / "shadow_tmp"))
        self.assertEqual(r.returncode, 2, "--out 指向 config/ 必须拒绝（账外不写产线）")

    def test_cli_writes_three_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            r = run_cli(TOOLS / "shadow_rerun.py", "--old", str(V3_PATH), "--new",
                        str(CONFIG_PATH), "--out", str(td))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for name in ("shadow_conservation.json", "shadow_migration_matrix.json",
                         "shadow_discrepancies.json"):
                self.assertTrue((Path(td) / name).exists(), f"缺产出 {name}")


class WeeklyGateColumnsTests(unittest.TestCase):
    """⑤ 周检扩展列。"""

    def test_cli_on_current_repo_state(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "cols.json"
            r = run_cli(TOOLS / "weekly_gate_columns.py", "--out", str(out))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            doc = json.loads(out.read_text(encoding="utf-8"))
            for key in ("新刊计数", "红灯立案数", "预警名单交集", "量控建议列"):
                self.assertIn(key, doc, f"缺门禁列 {key}")
            self.assertEqual(doc["新刊计数"]["count"], 0, "现盘无自动进册产物，新刊计数真值 0")
            self.assertIn("高量线_量控候选", doc["量控建议列"])
            self.assertIn("低量线_降D建议列", doc["量控建议列"])

    def test_new_intake_row_counted(self):
        rows = [{"nlm_id": "999", "name": "Brand New Journal", "src": "auto-intake-20261108"}]
        col = wgc.new_journal_column(rows, SEAL["journals"])
        self.assertEqual(col["count"], 1)
        self.assertEqual(col["rows"][0]["name"], "Brand New Journal")
        col2 = wgc.new_journal_column([{"nlm_id": "101769674", "name": "Esophagus",
                                        "src": "walk"}], SEAL["journals"])
        self.assertEqual(col2["count"], 0, "历史源集行不算新刊")

    def test_volume_control_two_lines(self):
        qc = {"results": [
            {"nlm_id": "1", "vol_365": 3001}, {"nlm_id": "2", "vol_365": 9},
            {"nlm_id": "3", "vol_365": 2999}, {"nlm_id": "nope", "vol_365": 99999},
        ]}
        rows = [{"nlm_id": "1", "name": "BigB", "tier_new": "B"},
                {"nlm_id": "2", "name": "Tiny", "tier_new": "A"},
                {"nlm_id": "3", "name": "JustUnder", "tier_new": "C"}]
        col = wgc.volume_control_column(rows, qc)
        self.assertEqual([r["name"] for r in col["高量线_量控候选"]], ["BigB"])
        self.assertEqual([r["name"] for r in col["低量线_降D建议列"]], ["Tiny"])
        self.assertNotIn("nope", str(col), "不在活册的 vol 行不入列")


if __name__ == "__main__":
    unittest.main(verbosity=2)
