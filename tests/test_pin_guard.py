#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
门禁件② 钉守护断言（意志书 v1.1 附录 A 钉表写死成测试；2026-11-08 批件）。

把附录 A 钉表逐刊写死：S 七刊（9 名形）／冠冕三刊／量控六刊／不收十刊／平台 16 刊／
判例九／裁定五，任一钉刊被动静默漂移即红。意志书明载 42＝席定钉 JUDGMENT_PINS 计数
（正本 classify.py），由 test_judgment_pins_42 以 AST 复算断言（二.4，四.7 书码对拍）。
册面与意志书的已批差异（量控 6→3 封存、平台 16 封存等）走 tools/thoradar_pins.py
AMENDMENT_LEDGER（PI 口令＋仓内证据锚）；台账外漂移＝红。

运行：E:/Python/python.exe -X utf8 -I -m unittest discover -s tests -v
（或单文件直跑：E:/Python/python.exe -X utf8 -I tests/test_pin_guard.py）
"""
import ast
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

import thoradar_pins as pins  # noqa: E402

CONFIG = json.loads((REPO / "config" / "journals_taxonomy.json").read_text(encoding="utf-8"))
SEAL = json.loads((REPO / "design" / "名册封存-20261101.json").read_text(encoding="utf-8"))
LIVE = CONFIG["journals"]
SEALED = SEAL["journals"]
LIVE_BY_NLM = pins.index_by_nlm(LIVE)
SEALED_BY_NLM = pins.index_by_nlm(SEALED)
LIVE_FORMS = pins.name_form_set(LIVE)
SEALED_FORMS = pins.name_form_set(SEALED)

# 席定钉正本（意志书地形表：D:\workbench\thoradar-journal-class\classify.py）
CLASSIFY_PY = Path(r"D:\workbench\thoradar-journal-class\classify.py")


def count_dict_assign(path: Path, var: str) -> int:
    """AST 复算模块级 dict 赋值的键数（不 import、不执行目标文件）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == var:
                    return len(ast.literal_eval(node.value))
    raise AssertionError(f"{path} 里找不到模块级赋值 {var}")


class PinGuardTests(unittest.TestCase):
    """附录 A 钉表逐刊写死。任何断言红＝钉表被动＝意志变更未走正门。"""

    def test_s_seven_pins_live_tier_s_and_nine_name_forms(self):
        for nlm, name in pins.S_PINS.items():
            j = LIVE_BY_NLM.get(nlm)
            self.assertIsNotNone(j, f"S 钉刊 {name}（NLM {nlm}）不在活册")
            self.assertEqual(j.get("tier_new"), "S", f"S 钉刊 {name} 档位被动")
        for alias in pins.S_ALIAS_FORMS:
            j = LIVE_FORMS.get(pins.norm(alias))
            self.assertIsNotNone(j, f"S 名形 {alias} 未在册（9 名形破缺）")
            self.assertEqual(j.get("tier_new"), "S", f"S 名形 {alias} 档位被动")
        s_rows = [j for j in LIVE if j.get("tier_new") == "S"]
        self.assertEqual(len(s_rows), 7, f"S 档行数应 7，实 {len(s_rows)}")

    def test_crown_three_pins_live_tier_b(self):
        for nlm, name in pins.CROWN_PINS.items():
            j = LIVE_BY_NLM.get(nlm)
            self.assertIsNotNone(j, f"冠冕钉 {name}（NLM {nlm}）不在活册")
            self.assertEqual(j.get("tier_new"), "B", f"冠冕钉 {name} 钉 B 被动")
            self.assertEqual(str(j.get("category")), "1", f"冠冕钉 {name} 阵地被动")

    def test_qty_ctrl_six_three_live_three_sealed(self):
        for nlm, name in pins.Q_CTRL_LIVE.items():
            j = LIVE_BY_NLM.get(nlm)
            self.assertIsNotNone(j, f"量控钉 {name}（NLM {nlm}）失联")
            self.assertEqual(j.get("tier_new"), "D", f"量控钉 {name} 强制 D 被动")
            self.assertEqual(j.get("tier_rule"), 1, f"量控钉 {name} tier_rule≠1")
        for nlm, name in pins.Q_CTRL_SEALED.items():
            self.assertNotIn(nlm, LIVE_BY_NLM, f"量控钉 {name} 台账记封存却回活册")
            self.assertIn(nlm, SEALED_BY_NLM, f"量控钉 {name}（NLM {nlm}）失联")

    def test_platform_sixteen_all_sealed_none_live(self):
        for nlm, name in pins.PLATFORM_16_SEALED.items():
            self.assertNotIn(nlm, LIVE_BY_NLM, f"平台钉 {name} 台账记封存却回活册")
            self.assertIn(nlm, SEALED_BY_NLM, f"平台钉 {name}（NLM {nlm}）失联")

    def test_precedent_nine_categories_per_will(self):
        for nlm, (name, cat) in pins.PRECEDENT_LIVE.items():
            j = LIVE_BY_NLM.get(nlm)
            self.assertIsNotNone(j, f"判例钉 {name}（NLM {nlm}）失联")
            legal = pins.CAT1_SPLIT_LEGAL if cat == "1" else (cat,)
            self.assertIn(str(j.get("category")), legal,
                          f"判例钉 {name} 类目被动：{j.get('category')} ∉ {legal}")
        for nlm, (name, _cat) in pins.PRECEDENT_SEALED.items():
            self.assertNotIn(nlm, LIVE_BY_NLM, f"判例钉 {name} 台账记封存却回活册")
            self.assertIn(nlm, SEALED_BY_NLM, f"判例钉 {name}（NLM {nlm}）失联")

    def test_adjudicated_five_categories_per_will(self):
        for nlm, (name, cat) in pins.ADJUDICATED_LIVE.items():
            j = LIVE_BY_NLM.get(nlm)
            self.assertIsNotNone(j, f"裁定钉 {name}（NLM {nlm}）失联")
            self.assertEqual(str(j.get("category")), cat, f"裁定钉 {name} 类目被动")
        for nlm, (name, _cat) in pins.ADJUDICATED_SEALED.items():
            self.assertNotIn(nlm, LIVE_BY_NLM, f"裁定钉 {name} 台账记封存却回活册")
            self.assertIn(nlm, SEALED_BY_NLM, f"裁定钉 {name}（NLM {nlm}）失联")

    def test_not_accepted_ten_absent_everywhere(self):
        for name in pins.NOT_ACCEPTED_10:
            k = pins.norm(name)
            self.assertNotIn(k, LIVE_FORMS, f"不收刊 {name} 回流活册")
            self.assertNotIn(k, SEALED_FORMS, f"不收刊 {name} 出现在封存档")

    def test_jti_dual_axis_qty_d_and_category_4(self):
        """JTI 两轴各管各（意志书 A-7 注）：量控钉 D ＋ 裁定钉 cat 4 同行并存。"""
        j = LIVE_BY_NLM["8606160"]
        self.assertEqual(j.get("tier_new"), "D")
        self.assertEqual(str(j.get("category")), "4")

    def test_judgment_pins_42_in_classify_py(self):
        """席定钉 42 条（意志书二.4）：AST 复算 classify.py JUDGMENT_PINS，fail-closed。"""
        if not CLASSIFY_PY.exists():
            self.fail(f"席定钉正本不可达：{CLASSIFY_PY} 不存在——书码对拍失眼即停（四.6 fail-closed）")
        n = count_dict_assign(CLASSIFY_PY, "JUDGMENT_PINS")
        self.assertEqual(n, pins.JUDGMENT_PIN_COUNT_WILL,
                         f"席定钉计数 {n}≠意志书 42——动钉未走正门或正本漂移")

    def test_amendment_ledger_sealed_claims_match_seal(self):
        """漂移台账自证：台账每条「记封存」的 NLM ID 必须真在封存档。"""
        for group, table in (("量控", pins.Q_CTRL_SEALED), ("平台16", pins.PLATFORM_16_SEALED),
                             ("判例", pins.PRECEDENT_SEALED), ("裁定", pins.ADJUDICATED_SEALED)):
            for nlm in table:
                self.assertIn(nlm, SEALED_BY_NLM, f"台账 {group} 封存声明与封存档不符：{nlm}")

    def test_will_constants_frozen(self):
        """意志书硬数字写死（三.1/一.8/二.4）：bonus 15/12/8/0/0、待定上限 30。"""
        got = {k: v.get("score_bonus") for k, v in CONFIG["tiers"].items()}
        self.assertEqual(got, pins.BONUS_MAP_WILL)
        self.assertEqual(CONFIG["category_axis"].get("pending_cap"), pins.PENDING_CAP_WILL)

    def test_full_audit_zero_drift(self):
        """总闸：附录 A＋台账 ↔ 活册/封存档零漂移（①③共用判据的单源审计）。"""
        findings = pins.audit_pins(LIVE, SEALED)
        self.assertEqual(findings, [], f"钉表漂移 {len(findings)} 条：{findings[:5]}")
        seal_findings = pins.audit_seal_integrity(SEAL)
        self.assertEqual(seal_findings, [], f"封存档完整性：{seal_findings}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
