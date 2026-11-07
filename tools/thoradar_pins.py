# -*- coding: utf-8 -*-
"""thoradar_pins.py — 意志书附录 A 钉表机读正本（门禁件①②③共用单源）。

⚠ 动钉表前必读意志书并对拍附录 A（意志书 v1.1 地形表「消费方接线」＋修订单 B4）。
意志书正本：E:\\trackeep-backup\\thoradar-will\\意志书-期刊体系-20261031.md（v1.1，2026-10-31 立，
同日「照准」升 v1.1）。本模块＝意志名单的机读转录（衍生件，修订单「弃用记录」明载机读件为衍生），
真相源＝意志书原文。改钉＝意志变更（意志书六.2），唯 PI 口令＋单独 commit＋过书码对拍；
PI 口令后的册面变动一律先记 AMENDMENT_LEDGER（附口令与仓内证据锚）再动码。

意志书口径（附录 A）：S 七刊（9 名形，JAMA/BMJ 双写）／冠冕钉三刊／量控六刊／不收十刊／
平台 16 刊／PI 判例九条／主控裁定五条；全部以 NLM ID 硬锚。席定裁量钉 42 条正本在
classify.py JUDGMENT_PINS（D:\\workbench\\thoradar-journal-class\\classify.py），
其计数由书码对拍断言（门禁件③ pin_reconcile）。
"""
from __future__ import annotations

import unicodedata
from typing import Any, Dict, List

# ---------- 名形归一（与 classify.py norm 同构：NFKC＋大写＋非字母数字归空格＋压空白） ----------
def norm(s: Any) -> str:
    s = unicodedata.normalize("NFKC", str(s or "")).upper()
    s = "".join(ch if ch.isalnum() else " " for ch in s)
    return " ".join(s.split())


# ---------- 附录 A 钉表（NLM ID 硬锚；cats＝意志钉的类目轴期望） ----------
# A-1 S 七刊（9 名形：JAMA/BMJ 名形双行并册，别名 JAMA、BMJ 须在 name_aliases）
S_PINS = {
    "0255562": "New England Journal of Medicine",
    "2985213R": "Lancet",
    "7501160": "JAMA",
    "8900488": "BMJ",
    "0410462": "Nature",
    "0404511": "Science",
    "0413066": "Cell",
}
S_ALIAS_FORMS = ("JAMA", "BMJ")  # 双写名形（S_LIST 9 名形 = 7 本 + 此 2 别名）

# A-2 冠冕钉三刊（钉 B；EJCTS 意志书原记「空缺·待验」，2026-11-01 config 以 NLM 8804069
#     efetch 实证回填——见该行 note「冠冕钉悬项补齐」与 src walk+crown-pin-20261101）
CROWN_PINS = {
    "0376343": "Journal of Thoracic and Cardiovascular Surgery",
    "15030100R": "Annals of Thoracic Surgery",
    "8804069": "European Journal of Cardio-Thoracic Surgery",  # 意志书待验项，config 实证回填
}

# A-3 量控六刊（收录但强制 D；2026-11-01 PI 令精准优先后 3 本留册、3 本封存）
Q_CTRL_LIVE = {
    "101769674": "Esophagus",
    "8606160": "Journal of Thoracic Imaging",
    "101731833": "Mediastinum",
}
Q_CTRL_SEALED = {
    "101526829": "Cancers",
    "101568867": "Frontiers in Oncology",
    "101563288": "Scientific Reports",
}

# A-4 不收十刊（终审表 2026-10-26 原录缩写形；意志书明载不在册无 NLM 号——按名形断缺席）
NOT_ACCEPTED_10 = [
    "JACC CardioOncol", "Cardiooncology", "J Bone Oncol", "Endocr Pathol",
    "Endocr Relat Cancer", "Hematol Oncol Clin", "J Vasc Surg Venous Lymphat Disord",
    "Psychooncology", "Transl Behav Med", "J Reconstr Microsurg",
]

# A-5 平台 16 刊（口令 2026-10-30 追认收；2026-11-02 精准封存批全数入封存档）。
#     意志书只给名形未给 NLM ID；NLM ID 取自封存档行（衍生锚，PI 封存令的实物对价）。
PLATFORM_16_SEALED = {
    "9518021": "Genome Research",
    "9809459": "Journal of Immunology",
    "101758887": "Human Molecular Genetics",
    "1273201": "European Journal of Immunology",
    "9918715277706676": "Clinical Immunology",
    "100953417": "Genes and Immunity",
    "101235427": "Immunity & Ageing",
    "101304616": "Journal of Genetics and Genomics",
    "101775540": "Frontiers in Genome Editing",
    "9302235": "European Journal of Human Genetics",
    "101092707": "Proteomics",
    "101721411": "ACS Pharmacology & Translational Science",
    "100965258": "BMC Genomics",
    "8800135": "Genomics",
    "101627166": "Journal of Immunology Research",
    "101083949": "Pharmacogenomics Journal",
}

# A-6 PI 判例九条（类目钉；2026-11-07 阵地1拆分后意志钉「→1」合法落位 = {1, 11}）
CAT1_SPLIT_LEGAL = ("1", "11")  # 11＝呼吸与睡眠（PI 2026-11-07 阵地1拆分，tests/test_taxonomy_v4.py L27 注）
PRECEDENT_LIVE = {
    "101274235": ("Journal of Thoracic Oncology", "1"),
    "0330057": ("Heart & Lung", "7"),
    "100963739": ("Heart Lung and Circulation", "1"),
    "9918752186406676": ("NEJM AI", "10"),
    "101751302": ("Lancet Digital Health", "10"),
    "101731738": ("npj Digital Medicine", "10"),
    "8310780": ("IEEE Trans Medical Imaging", "10"),
}
PRECEDENT_SEALED = {
    "101767765": ("Patterns", "10"),
    "9918589989006676": ("Smart Medicine", "10"),
}

# A-7 主控裁定五条（JTI 档位另受量控钉 D，两轴各管各）
ADJUDICATED_LIVE = {
    "8606160": ("Journal of Thoracic Imaging", "4"),
    "101748663": ("Radiology: Cardiothoracic Imaging", "4"),
}
ADJUDICATED_SEALED = {
    "101658402": ("Diagnostics", "4"),
    "101718985": ("Diagnostic and Prognostic Research", "4"),
    "101519118": ("Journal of Transplantation", "6"),
}

# ---------- 意志书节三/四的硬数字 ----------
BONUS_MAP_WILL = {"S": 15, "A": 12, "B": 8, "C": 0, "D": 0}   # 三.1 口令 2026-10-26
PENDING_CAP_WILL = 30                                          # 一.8／category_axis
TIERS_LEGAL = ("S", "A", "B", "C", "D")
CATEGORIES_LEGAL = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "待定"}
                                                               # 11＝2026-11-07 拆分新增（见上）
JUDGMENT_PIN_COUNT_WILL = 42                                   # 二.4：席定钉 42，正本 classify.py
IF_LINE_A = 15.0                                               # 三.2 A 档线 IF≥15
INTAKE_90D_MIN = 3                                             # 四.2 90 天≥3 篇
VOL_HIGH_LINE = 3000                                           # 四.5 高量线（B/C 档年发文）
VOL_LOW_LINE = 10                                              # 四.5 低量线（年发文<10 只出降 D 建议）
TOTAL_BAND_PCT = 0.05                                          # 四.3 换表总数带宽 ±5%
TIER_BAND_PCT = 0.03                                           # 四.3 各档分布带宽 ±3%

# ---------- 漂移台账（PI 口令后的册面变动先记此处；每条附仓内证据锚） ----------
AMENDMENT_LEDGER = [
    {
        "date": "2026-11-01",
        "order": "PI 令「精准优先」（v4.2-precision）",
        "change": "量控六刊中非胸科专科名三本封存：Cancers／Frontiers in Oncology／Scientific Reports",
        "evidence": "config description「2026-11-01 PI 令精准优先」；tests/test_taxonomy_v4.py R2 注；design/名册封存-20261101.json",
    },
    {
        "date": "2026-11-01",
        "order": "PI 批冠冕钉悬项补齐",
        "change": "EJCTS（意志书 A-2「空缺·待验」）以 NLM 8804069 efetch 实证回填",
        "evidence": "config 行 european-journal-of-cardio-thoracic-surgery note 与 src=walk+crown-pin-20261101",
    },
    {
        "date": "2026-11-02",
        "order": "PI 批双席终审（v4.3→v4.4-precision）",
        "change": "平台 16 刊、判例钉 Patterns／Smart Medicine、裁定钉 Diagnostics／Diagnostic and Prognostic "
                  "Research／Journal of Transplantation 等封存（封存档三批）",
        "evidence": "design/名册封存-20261101.json sealed_at/amended；config version=v4.4-precision",
    },
    {
        "date": "2026-11-07",
        "order": "PI 令阵地1拆分",
        "change": "新阵地 11＝呼吸与睡眠；意志钉「→1」类目合法落位扩为 {1, 11}（判例 HLC 实落 11）",
        "evidence": "tests/test_taxonomy_v4.py JCAT_LEGAL 注「11=呼吸与睡眠（2026-11-07 阵地1拆分）」",
    },
]


# ---------- 索引工具 ----------
def index_by_nlm(journals: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for j in journals or []:
        nlm = str(j.get("nlm_id") or "").strip()
        if nlm:
            out[nlm] = j
    return out


def name_form_set(journals: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """归一名形（name＋aliases）→ 行；用于无 NLM 号名单（不收十刊）的缺席断言。"""
    out: Dict[str, Dict[str, Any]] = {}
    for j in journals or []:
        for form in [j.get("name")] + list(j.get("name_aliases") or []):
            k = norm(form)
            if k:
                out.setdefault(k, j)
    return out


# ---------- 审计引擎（①进门验收/②守护断言/③书码对拍 共用的唯一判据） ----------
def audit_pins(live_journals: List[Dict[str, Any]],
               sealed_journals: List[Dict[str, Any]]) -> List[str]:
    """对拍「意志书附录 A＋漂移台账 ↔ 册面现实」，返回漂移发现清单（空＝零漂移）。

    fail-closed：任何发现都应拦下换表/动钉路径（意志书四.6／四.3）。
    """
    findings: List[str] = []
    live = index_by_nlm(live_journals)
    sealed = index_by_nlm(sealed_journals)
    live_forms = name_form_set(live_journals)
    sealed_forms = name_form_set(sealed_journals)

    def missing_nlm(group: str, nlm: str, name: str) -> None:
        findings.append(f"{group}: 钉刊 {name}（NLM {nlm}）既不在活册也不在封存档——钉表刊失联")

    # S 七刊：全在活册、tier_new=S、cat=9、9 名形（JAMA/BMJ 别名在册）
    for nlm, name in S_PINS.items():
        j = live.get(nlm)
        if j is None:
            missing_nlm("S七刊", nlm, name)
            continue
        if j.get("tier_new") != "S":
            findings.append(f"S七刊: {name} tier_new={j.get('tier_new')}≠S（钉档被动）")
        if str(j.get("category")) != "9":
            findings.append(f"S七刊: {name} category={j.get('category')}≠9")
    for alias in S_ALIAS_FORMS:
        j = live_forms.get(norm(alias))
        if j is None or j.get("tier_new") != "S":
            findings.append(f"S七刊: 名形 {alias} 未以 S 档别名在册（9 名形破缺）")

    # 冠冕三刊：活册、钉 B、cat=1
    for nlm, name in CROWN_PINS.items():
        j = live.get(nlm)
        if j is None:
            missing_nlm("冠冕三刊", nlm, name)
            continue
        if j.get("tier_new") != "B":
            findings.append(f"冠冕三刊: {name} tier_new={j.get('tier_new')}≠B（钉 B 被动）")
        if str(j.get("category")) != "1":
            findings.append(f"冠冕三刊: {name} category={j.get('category')}≠1")

    # 量控六刊：3 活（强制 D，tier_rule=1）＋3 封（台账）；任何一刊两头都不在＝失联
    for nlm, name in Q_CTRL_LIVE.items():
        j = live.get(nlm)
        if j is None:
            if nlm in sealed:
                findings.append(f"量控六刊: {name} 应留册（台账外）却现居封存档——封存越出台账")
            else:
                missing_nlm("量控六刊", nlm, name)
            continue
        if j.get("tier_new") != "D":
            findings.append(f"量控六刊: {name} tier_new={j.get('tier_new')}≠D（强制 D 被动）")
        if j.get("tier_rule") != 1:
            findings.append(f"量控六刊: {name} tier_rule={j.get('tier_rule')}≠1")
    for nlm, name in Q_CTRL_SEALED.items():
        if nlm in live:
            findings.append(f"量控六刊: {name} 台账记封存却回到活册——须走一键回滚正门并先记台账")
        elif nlm not in sealed:
            missing_nlm("量控六刊", nlm, name)

    # 平台 16：全封存、零活册
    for nlm, name in PLATFORM_16_SEALED.items():
        if nlm in live:
            findings.append(f"平台16: {name} 台账记封存却回到活册")
        elif nlm not in sealed:
            missing_nlm("平台16", nlm, name)

    # 判例九：7 活（类目按钉；→1 者合法落位 {1,11}）＋2 封
    for nlm, (name, cat) in PRECEDENT_LIVE.items():
        j = live.get(nlm)
        if j is None:
            missing_nlm("判例九", nlm, name)
            continue
        got = str(j.get("category"))
        legal = CAT1_SPLIT_LEGAL if cat == "1" else (cat,)
        if got not in legal:
            findings.append(f"判例九: {name} category={got}∉钉判 {legal}（类目钉被动）")
    for nlm, (name, _cat) in PRECEDENT_SEALED.items():
        if nlm in live:
            findings.append(f"判例九: {name} 台账记封存却回到活册")
        elif nlm not in sealed:
            missing_nlm("判例九", nlm, name)

    # 裁定五：2 活（类目按钉）＋3 封
    for nlm, (name, cat) in ADJUDICATED_LIVE.items():
        j = live.get(nlm)
        if j is None:
            missing_nlm("裁定五", nlm, name)
            continue
        got = str(j.get("category"))
        legal = CAT1_SPLIT_LEGAL if cat == "1" else (cat,)
        if got not in legal:
            findings.append(f"裁定五: {name} category={got}∉钉判 {legal}（类目钉被动）")
    for nlm, (name, _cat) in ADJUDICATED_SEALED.items():
        if nlm in live:
            findings.append(f"裁定五: {name} 台账记封存却回到活册")
        elif nlm not in sealed:
            missing_nlm("裁定五", nlm, name)

    # 不收十：活册与封存档双双缺席（按名形；它们从未入册，封存也不该收）
    for name in NOT_ACCEPTED_10:
        k = norm(name)
        if k in live_forms:
            findings.append(f"不收十: {name} 出现在活册（拒收族近亲回流）")
        if k in sealed_forms:
            findings.append(f"不收十: {name} 出现在封存档（不该曾入册）")

    # 封存档自身完整性：count 字段＝行数
    if sealed_journals and isinstance(sealed_journals, list):
        # count 在封存档顶层 dict；此处仅收 list，完整性由调用方（读档处）对 count 校验
        pass
    return findings


def audit_seal_integrity(seal_doc: Dict[str, Any]) -> List[str]:
    """封存档自检：count 字段＝实际行数；restore 指引在档（一键回滚正门）。"""
    findings: List[str] = []
    rows = seal_doc.get("journals") or []
    if seal_doc.get("count") != len(rows):
        findings.append(f"封存档: count={seal_doc.get('count')}≠实际行数 {len(rows)}")
    if not str(seal_doc.get("restore") or "").strip():
        findings.append("封存档: restore 回滚指引缺失")
    return findings
