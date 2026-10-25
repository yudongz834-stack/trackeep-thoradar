#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-10-26 锚词典扩容（T-THR-ANCHOR）验收测试。

数据源：data/radar_latest.json + data/archive/ 近 7 天日档 semantic_audit.mismatch_reasons
（1720 条误拦 → 974 唯一案例 → 端到端重放救活 36/494 唯一 tuple）。
本文件锚表与 thoradar_engine.py 新增键一一对应：正例回环（锚在摘要 → 放行）＋
逐键反例自检（错误人群/指标的变造 tuple 在无锚摘要上必须拦截）。

来源 PMID（中文短语→英文锚的收割出处；PROSPECTIVE＝当期无案例、按标准表述收的前瞻锚）：
  Q 男性 42829651/42842856 · 女性 42842856/42900167 · 女童 42913690 · 女孩 42897101 ·
  儿童 42903281 · 糖尿病 42921584 · 恶病质 42910566 · 疑似 42813481 · 单发 42900398 ·
  结节型 42908532 · 腹膜后 42926214 · 原发灶/转移灶 42924072 · 肺部病变 42813481 ·
  健康对照 42910566/42914826 · 健康个体 42921584 · 正常对照 42897609 · 对照组/观察组 42908730 ·
  对照 42897609 等 · 安慰剂 42907709 · 一线奥希替尼 42926199 · 激素组（复核判越界，10-26 整键弃收）42899166 ·
  世贸中心/粉尘暴露 42906939 · 倾向匹配 42804884 · 单例 42831722/42862852 · 单病例 42829651 ·
  病例 42827939（42833719 系 cases 旧锚来源，复核判越界删锚后失效，弃）· 未校正 42823163 · 校正后 42899166 · 完全调整 42908676 ·
  安全性/按实际治疗 42909113/42914998 · 验证集 42902382/42907266/42918128 · 训练 42837362 等 ·
  建模 42857233/42901404/42907266/42919290 · 独立测试 42918128 · 外部/内部测试集 42907266 ·
  整体测试集 42907991 · 内部验证集 42918128 · 内部验证/外部验证 42837362 ·
  独立时间验证 42919290 · 数据集 42832530/42897609 等 · 列线图模型/临床模型 42871060 ·
  无监督 42837362 · 影像组学(表) 42837362/42920785 · 单细胞/图谱 42811976 ·
  人原发/长读长/测序 42912151 · 医疗提供者 42911076 · 全部提供者 42901462 ·
  全体受访者 42911076 · 受访者 42898221/42911076 · 医生 42901462/42926850 · 护士/执业护士 42901462 ·
  肺切除 42901404 · 叶切除/左上/单病例 42829651 · 食管切除 42901404 · 拒绝手术 42908532 ·
  接受手术 42900289/42908532 · 生存分析 42823758 · 跨试验间接比较 42896976 ·
  实施(前后/叙事/结构化) 42893559/42901462/42906638 · 全部纳入新生儿 42900289 ·
  Q PROSPECTIVE：健康对照组、正常对照组（标准对照臂表述的变体）
  M 样本量 PROSPECTIVE（短语出处 42823161 等，词面 0 命中）· 敏感度/特异度 42907266 · 敏感性/特异性 42813481/42918128 ·
  死亡率 42900289/42905367/42922218 · 全因死亡 42907709 · 院内死亡 42900289 ·
  准确率 42915230 等 · 准确性 42926850 · 脑转移 42902382 · 再手术 42829651/42899166 ·
  再入院 42920008 · 切缘阳性 42897335 · 多因素 42919290 ·
  M PROSPECTIVE：住院时间（length of stay，当期无直接案例）· 样本量 · 随访时间（短语出处 42904154/42923912，词面 0 命中）
  A（METRIC_ANCHORS/别名）：auc 42902382 等 · ic50 42903066 等 · ki-67 42909554 等 ·
  ppv/npv 42813481 · idi/nri 42857233/42871060 · dsc 42826729 · hba1c 42908608 · mvi 42919290 ·
  vs 42857233 等真实词面佐证（42804884/42813853 为救不活例，不作来源）· vats 42922218

运行：E:/Python/python.exe -m pytest tests/ -q
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import thoradar_engine as eng  # noqa: E402

# 2026-10-18 R 席原批键（引擎既有，勿动）——本批新键须全部不在其中
R_SEAT_Q = {
    "意向治疗", "全人群", "鳞癌", "腺癌", "脑转移", "老年", "吸烟", "突变", "阳性", "阴性",
    "可切除", "局部晚期", "转移性", "复发", "术后", "新辅助", "辅助", "高危", "风险",
    "病理完全缓解", "完全缓解", "日本", "中国", "总体", "随访", "细胞", "测序样本", "体外",
    "原代", "全部纳入视频",
}

NEW_Q = [
    "男性", "女性", "女童", "女孩", "儿童", "糖尿病", "恶病质", "疑似", "单发", "结节型",
    "腹膜后", "原发灶", "转移灶", "肺部病变", "健康对照", "健康对照组", "健康个体", "正常对照",
    "正常对照组", "对照组", "观察组", "对照", "安慰剂", "一线奥希替尼", "世贸中心",
    "粉尘暴露", "倾向匹配", "单例", "单病例", "病例", "未校正", "校正后", "完全调整", "安全性",
    "按实际治疗", "验证集", "训练集", "训练", "建模", "独立测试", "外部测试集", "内部测试集",
    "整体测试集", "内部验证集", "内部验证", "外部验证", "独立时间验证", "数据集", "列线图模型",
    "临床模型", "无监督", "影像组学", "影像组学表", "单细胞", "图谱", "人原发", "长读长", "测序",
    "医疗提供者", "全部提供者", "全体受访者", "受访者", "医生", "护士", "执业护士", "肺切除",
    "叶切除", "食管切除", "左上", "拒绝手术", "接受手术", "生存分析", "跨试验间接比较", "实施",
    "实施前叙事报告", "实施后结构化报告", "实施前后比较", "全部纳入新生儿",
]
NEW_M = [
    "样本量", "敏感度", "敏感性", "特异度", "特异性", "死亡率", "全因死亡", "院内死亡",
    "准确率", "准确性", "脑转移", "再手术", "再入院", "住院时间", "随访时间", "切缘阳性",
    "多因素",
]
NEW_ASCII_METRIC = ["auc", "ic50", "ki-67", "ppv", "npv", "idi", "nri", "dsc", "hba1c", "mvi"]
NEW_ALIAS = ["vs", "vats"]

# 负例摘要：刻意不含任何本批新锚（自检断言兜底——谁加锚撞上它谁修）
NEG_QUAL = ("Patients with stage III non-small-cell lung cancer were randomly assigned "
            "to two groups. The primary endpoint was overall survival. "
            "The hazard ratio for death was 0.72.")
NEG_METRIC = ("Patients were randomly assigned to two groups. "
              "The primary endpoint was overall survival.")


def hit(abstract_low: str, anchor: str) -> bool:
    return eng.SemanticChecker._hit(abstract_low, anchor)


class AnchorExpansionIntegrity(unittest.TestCase):
    """新键全部落在引擎词典中、全部为增（R 席原批一字未动）。"""

    def test_new_qualifier_keys_in_engine(self):
        for k in NEW_Q:
            self.assertIn(k, eng.SEMANTIC_QUALIFIER_ANCHORS, k)
            anchors = eng.SEMANTIC_QUALIFIER_ANCHORS[k]
            self.assertTrue(anchors, k)
            for a in anchors:
                self.assertEqual(a, a.lower(), f"{k}->{a} 应小写")
                self.assertGreaterEqual(len(a), 3, f"{k}->{a} 禁单字/双字符泛词")

    def test_r_seat_keys_untouched(self):
        # 只增不删不并：R 席原批键仍在且锚表长度不减（抽查代表键）
        self.assertGreaterEqual(len(eng.SEMANTIC_QUALIFIER_ANCHORS["总体"]), 11)
        self.assertEqual(eng.SEMANTIC_QUALIFIER_ANCHORS["随访"],
                         ["follow-up", "follow up", "followup", "followed up", "followed"])
        self.assertEqual(eng.SEMANTIC_QUALIFIER_ANCHORS["体外"], ["in vitro"])
        self.assertIn("意向治疗", eng.SEMANTIC_QUALIFIER_ANCHORS)
        self.assertIn("总体", R_SEAT_Q)

    def test_new_metric_and_ascii_keys_in_engine(self):
        for k in NEW_M:
            self.assertIn(k, eng.SEMANTIC_METRIC_ANCHORS, k)
            self.assertTrue(eng.SEMANTIC_METRIC_ANCHORS[k], k)
        for k in NEW_ASCII_METRIC:
            self.assertIn(k, eng.METRIC_ANCHORS, k)
            self.assertTrue(eng.METRIC_ANCHORS[k], k)
        for k in NEW_ALIAS:
            self.assertIn(k, eng.SEMANTIC_ASCII_ALIASES, k)


class PositiveRoundTrip(unittest.TestCase):
    """① 正例：锚真出现在摘要 → 该限定词/指标放行（每键用引擎锚表首锚合成摘要）。"""

    def test_qualifier_positive(self):
        for k in NEW_Q:
            a0 = eng.SEMANTIC_QUALIFIER_ANCHORS[k][0]
            ab = f"{a0[0].upper()}{a0[1:]} was recorded in this study. The primary endpoint was overall survival."
            r = eng.SemanticChecker.check(ab, [{"group": k, "metric": "总生存",
                                               "val": "1", "stat": ""}])
            self.assertTrue(r["passed"], (k, a0, r))

    def test_metric_positive(self):
        for k in NEW_M:
            a0 = eng.SEMANTIC_METRIC_ANCHORS[k][0]
            ab = f"The {a0} was reported. Overall survival was 40%."
            r = eng.SemanticChecker.check(ab, [{"group": "", "metric": k,
                                               "val": "1", "stat": ""}])
            self.assertTrue(r["passed"], (k, a0, r))


class CounterExampleSelfCheck(unittest.TestCase):
    """② 反例自检：错误人群/指标的变造 tuple 在无锚摘要上必须拦截。"""

    def test_negative_abstract_has_no_new_qualifier_anchor(self):
        low = NEG_QUAL.lower()
        for k in NEW_Q:
            for a in eng.SEMANTIC_QUALIFIER_ANCHORS[k]:
                self.assertFalse(hit(low, a), f"负例摘要被 {k}->{a} 撞上，换摘要")

    def test_qualifier_counterexample_blocked(self):
        for k in NEW_Q:
            r = eng.SemanticChecker.check(NEG_QUAL, [{"group": k, "metric": "总生存",
                                                     "val": "1", "stat": ""}])
            self.assertFalse(r["passed"], k)
            self.assertTrue(any(k in x and "未在原摘要出现" in x
                                for x in r["tuple_audit"][0]["mismatch_reasons"]), (k, r))

    def test_metric_counterexample_blocked(self):
        low = NEG_METRIC.lower()
        for k in NEW_M:
            for a in eng.SEMANTIC_METRIC_ANCHORS[k]:
                self.assertFalse(hit(low, a), f"负例摘要被 {k}->{a} 撞上")
            r = eng.SemanticChecker.check(NEG_METRIC, [{"group": "", "metric": k,
                                                       "val": "1", "stat": ""}])
            self.assertFalse(r["passed"], k)
            self.assertTrue(any("终点指标词" in x
                                for x in r["tuple_audit"][0]["mismatch_reasons"]), (k, r))

    def test_population_swap_on_real_style_abstracts(self):
        """同摘要偷换人群：锚在→放行；换人群→拦截。"""
        male_abs = ("A total of 120 male patients received therapy. "
                    "The primary endpoint was overall survival.")
        ok = eng.SemanticChecker.check(male_abs, [{"group": "男性", "metric": "总生存",
                                                  "val": "1", "stat": ""}])
        self.assertTrue(ok["passed"], ok)
        bad = eng.SemanticChecker.check(male_abs, [{"group": "女性", "metric": "总生存",
                                                   "val": "1", "stat": ""}])
        self.assertFalse(bad["passed"], bad)

        case_abs = ("CASE PRESENTATION: A 67-year-old woman presented with cough. "
                    "Overall survival data were not applicable.")
        self.assertTrue(eng.SemanticChecker.check(
            case_abs, [{"group": "病例", "metric": "总生存", "val": "1", "stat": ""}])["passed"])
        self.assertFalse(eng.SemanticChecker.check(
            case_abs, [{"group": "鳞癌", "metric": "总生存", "val": "1", "stat": ""}])["passed"])

        ml_abs = ("The dataset was split into a training set and a test set. "
                  "The machine learning model achieved an auc of 0.85.")
        self.assertTrue(eng.SemanticChecker.check(
            ml_abs, [{"group": "训练集", "metric": "AUC", "val": "1", "stat": ""}])["passed"])
        self.assertFalse(eng.SemanticChecker.check(
            ml_abs, [{"group": "验证集", "metric": "AUC", "val": "1", "stat": ""}])["passed"])

        neo_abs = ("Five studies reported neonates with perforation. "
                   "The primary endpoint was overall survival.")
        self.assertTrue(eng.SemanticChecker.check(
            neo_abs, [{"group": "全部纳入新生儿", "metric": "总生存", "val": "1", "stat": ""}])["passed"])
        self.assertFalse(eng.SemanticChecker.check(
            neo_abs, [{"group": "全部纳入儿童", "metric": "总生存", "val": "1", "stat": ""}])["passed"])


class AsciiAliasAndMetricKeys(unittest.TestCase):
    """③ ASCII 指标缩写与 vs/VATS 别名：全称摘要可核，缺词仍拦。"""

    def test_ascii_metric_anchors_derived(self):
        for m in ["AUC", "auc", "诊断 AUC"]:
            self.assertTrue(eng.SemanticChecker.metric_anchors(m), m)
        self.assertIn("area under the curve", eng.FourTupleVerifier._anchors_for_metric("auc"))
        self.assertIn("half-maximal inhibitory concentration",
                      eng.FourTupleVerifier._anchors_for_metric("ic50"))
        ki = eng.SemanticChecker.metric_anchors("Ki-67标记指数")
        self.assertTrue(any("ki-67" == a or "proliferation index" == a for a in ki), ki)

    def test_vs_alias(self):
        ab = ("Video-assisted thoracoscopic surgery (VATS) versus robotic-assisted "
              "thoracoscopic surgery (RATS) was compared. Overall survival was 60%.")
        ok = eng.SemanticChecker.check(ab, [{"group": "VATS vs RATS", "metric": "总生存",
                                            "val": "1", "stat": ""}])
        self.assertTrue(ok["passed"], ok)
        miss = eng.SemanticChecker.check(NEG_QUAL, [{"group": "VATS vs RATS", "metric": "总生存",
                                                    "val": "1", "stat": ""}])
        self.assertFalse(miss["passed"], miss)

    def test_ki67_metric_passes_and_blocks(self):
        good = eng.SemanticChecker.check("The ki-67 proliferation index was 30%. Overall survival was 40%.",
                                         [{"group": "", "metric": "Ki-67标记指数", "val": "1", "stat": ""}])
        self.assertTrue(good["passed"], good)
        bad = eng.SemanticChecker.check(NEG_METRIC, [{"group": "", "metric": "Ki-67标记指数",
                                                     "val": "1", "stat": ""}])
        self.assertFalse(bad["passed"], bad)


class FailClosedPreserved(unittest.TestCase):
    """④ fail-closed 不弱化：单字残段（病/全/单/后/对）仍无锚；既有判例语义不变。"""

    def test_single_char_labels_still_unanchored(self):
        for ch in ["病", "全", "单", "后", "对", "项", "模"]:
            quals = eng.SemanticChecker._qualifiers_of(ch, eng.SEMANTIC_QUALIFIER_ANCHORS)
            self.assertTrue(any(q["label"] == ch and q["anchors"] == [] for q in quals), ch)

    def test_case_report_family_not_satisfied_by_generic_words(self):
        """cohort 式摘要（无任何案例报告措辞）上「病例」必须拦——案例锚不含 patients/study。"""
        r = eng.SemanticChecker.check(NEG_QUAL, [{"group": "病例", "metric": "总生存",
                                                 "val": "1", "stat": ""}])
        self.assertFalse(r["passed"], r)

    def test_training_not_satisfied_by_clinical_abstract(self):
        r = eng.SemanticChecker.check(NEG_QUAL, [{"group": "训练", "metric": "总生存",
                                                 "val": "1", "stat": ""}])
        self.assertFalse(r["passed"], r)


if __name__ == "__main__":
    unittest.main()
