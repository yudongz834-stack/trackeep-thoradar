#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
胸科雷达 ThorRadar — 胸部肿瘤文献每日雷达流水线引擎 v3.0

真实流水线（区别于早期空壳原型）：
  1. 采集   PubMed ESearch（datetype=crdt 按入库日 + [Title/Abstract] 自由词）→ EFetch 取全文元数据
  2. 定级   五重主键期刊索引（ISSN-L / P-ISSN / E-ISSN / NlmUniqueID / ISO 缩写），S/A 级白名单豁免
  3. 预筛   LLM 批量轻量预筛（无 LLM key 时退化为启发式，诚实标注 score_source）
  4. 精评   LLM 结构化 PICO 精评 + 反阳性偏倚条款（保护高质量阴性研究）
  5. 核验   四元组核验器（数值存在性 + 语境锚定；未通过 fail-closed 标注，不静默放行）
  6. 产出   data/curated_literature.json + data/daily_briefing_<date>.md + 注入 index.html（标记区间替换）

用法：
  python thoradar_engine.py --self-test        # 离线单元自测
  python thoradar_engine.py                    # 正式跑（无 LLM_API_KEY 自动走启发式模式）
  python thoradar_engine.py --days-back 7      # 拉近 7 天（默认 2；结果过少会自动放宽到 7）

环境变量：
  LLM_API_KEY / LLM_BASE_URL / LLM_MODEL   OpenAI 兼容接口（缺省则启发式模式）
  NCBI_API_KEY                             选填，3 req/s -> 10 req/s
  MAX_DAILY_COST_USD                       LLM 成本熔断（默认 0.10 美元）
  LLM_PRICE_IN / LLM_PRICE_OUT             每百万 token 单价（美元，默认 0.27 / 1.10）

红线：.env 与任何密钥永不入库；本引擎不输出任何个人身份或课题信息。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
INDEX_HTML = ROOT / "index.html"
JOURNALS_FILE = ROOT / "config" / "journals_taxonomy.json"

DATA_START = "/*__THORADAR_DATA_START__*/"
DATA_END = "/*__THORADAR_DATA_END__*/"

CATEGORIES: Dict[str, str] = {
    "perioperative": "围术期与新辅助治疗",
    "nodule": "肺结节与早筛管理",
    "surgery": "微创与无管化胸外科",
    "ai_digital": "胸外科 AI 与三维重建",
    "advanced": "局晚期与晚期靶向/免疫",
    "esophageal": "食管与纵隔肿瘤",
}

# 检索式路：纯病种词 26 词直通（2026-10-18 回测裁决：双门召回 62.5% → 直通 76.7%）。
# 只负责字典外世界的胸科文章；字典刊全覆盖由目录路（fetch_journal_toc）天然完成。
# 检索式路 v3（PI 2026-10-18 第一性裁决）：只病种名，术式/治疗词全删，只搜摘要域。
# 只负责字典外世界；字典刊全覆盖由目录路天然完成。实测（30 天回放）：
# 仅摘要域丢标题独占 46/1974≈2.3%（真货多在字典刊内被 TOC 接住）；
# 病名变体 +266 / 纯术式词命中 −292（术式文多发字典刊内，实际影响窄）。
A_TERMS = (
    # 肺恶性肿瘤（含亚型与缩写）
    "lung cancer", "lung tumor", "lung tumour", "lung neoplasm",
    "non-small cell lung cancer", "NSCLC", "small cell lung cancer", "SCLC",
    "lung adenocarcinoma", "LUAD", "lung squamous cell carcinoma", "LUSC",
    "pulmonary carcinoid",
    # 肺结节
    "pulmonary nodule", "lung nodule", "ground-glass nodule", "ground glass nodule",
    "subsolid nodule", "solitary pulmonary nodule",
    # 胸膜
    "mesothelioma", "malignant pleural effusion",
    # 食管
    "esophageal cancer", "oesophageal cancer", "esophageal carcinoma", "oesophageal carcinoma",
    "esophageal squamous cell carcinoma", "oesophageal squamous cell carcinoma",
    "esophageal adenocarcinoma", "ESCC",
    # 纵隔/胸腺
    "thymoma", "thymic carcinoma", "thymic tumor", "thymic tumour",
    "mediastinal tumor", "mediastinal tumour", "mediastinal mass",
)
DEFAULT_QUERY = "(" + " OR ".join(f'"{t}"[Abstract]' for t in A_TERMS) + ")"

# MeSH 月度兜底层词表（2026-10-18 重测立项：双路视野之外独有 1,096 篇/90 天、
# 27% 普胸相关 → 每天约 3-4 篇独有真货，月扫成本几美分）。
# 「Esophageal Surgical Procedures」MeSH 无此主题词，不列。
MESH_BACKSTOP_TERMS = (
    "Lung Neoplasms", "Esophageal Neoplasms", "Mesothelioma",
    "Thymus Neoplasms", "Mediastinal Neoplasms", "Thoracic Surgical Procedures",
)

# 语境通道词汇（2026-10-18 回测否决入产线：单独精确率仅 52.4%；留作离线分析工具词汇）
_SHADOW_AMBIG = ("screening", "deep learning", "machine learning", "radiomics",
                 "neural network", "artificial intelligence", "three-dimensional")
_SHADOW_ANATOMY = ("lung", "pulmonary", "thoracic", "esophageal", "oesophageal",
                   "mediastinal", "thymic", "pleural", "mesothelioma", "chest")
_SHADOW_TERMS = A_TERMS           # 旧分析脚本别名

# 预筛正选口径（全量库）：普胸相关全收（基础/转化/临床/流病/筛查/AI），只扔非普胸器官。
LIBRARY_PRESCREEN_SYSTEM = """你是普胸文献全量库的收录审读员。输入若干篇 PubMed 文献的标题、摘要开头与期刊。
判断每篇是否属于「普胸」范围而应入库。收录（符合任一）：
1) 肺癌（NSCLC/SCLC/间皮瘤）、肺结节、食管癌、纵隔/胸腺肿瘤、恶性胸膜疾病的任何研究——基础机制、转化、临床、流行病学、筛查、卫生经济学均收；
2) 普胸外科（肺/食管/纵隔/胸壁手术，VATS/RATS/tubeless/肺段/食管切除）任何报道；
3) 胸外科 AI、三维重建、影像组学、数字医疗。
剔除：与普胸无关的器官/系统（含心脏外科）；与胸部无交集的泛癌或泛外科研究；**兽医研究与人类疾病无关的动物研究**（判例：猫的胸膜增厚病例报告不该收——只收人类疾病相关：人类患者/人类样本/人源细胞系）。
只输出 JSON：{"decisions": [{"i": <输入序号>, "keep": true/false}]}"""
SHADOW_PRESCREEN_SYSTEM = LIBRARY_PRESCREEN_SYSTEM   # 旧名别名（离线分析脚本在用）


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ============================================================================
# 1. 期刊五重索引
# ============================================================================

class JournalMatcher:
    """ISSN-L / P-ISSN / E-ISSN / NlmUniqueID / ISO 缩写 五重主键匹配期刊层级。"""

    def __init__(self, cfg: Dict[str, Any]) -> None:
        self.tiers = cfg.get("tiers", {})
        self.index: Dict[str, Dict[str, Any]] = {}
        for j in cfg.get("journals", []):
            for field in ("issn_l", "p_issn", "e_issn", "nlm_id", "iso_abbr", "title"):
                val = str(j.get(field, "")).strip().upper()
                if val:
                    self.index[val] = j

    def match(self, p_issn: str = "", e_issn: str = "", issn_linking: str = "",
              nlm_id: str = "", iso_abbr: str = "", title: str = "") -> Dict[str, Any]:
        for cand in (issn_linking, p_issn, e_issn, nlm_id, iso_abbr, title):
            key = str(cand or "").strip().upper()
            if key and key in self.index:
                j = self.index[key]
                tier = j.get("tier", "B")
                meta = self.tiers.get(tier, {})
                return {
                    "matched": True,
                    "tier": tier,
                    "if_val": j.get("if_2025") or None,
                    "zone": " · ".join(([f"JCR {j['jcr_quartile']}"] if j.get("jcr_quartile") else [])
                                       + ([j["cas_zone"]] if j.get("cas_zone") else [])) or "已收录期刊",
                    "journal_bonus": int(meta.get("score_bonus", 0)),
                    "whitelist_exempt": bool(meta.get("whitelist_exempt", False)),
                    "warned": bool(j.get("warned", False)),
                    "journal_abbr": j.get("iso_abbr", iso_abbr or title),
                    "journal_full": j.get("title", title),
                }
        return {
            "matched": False,
            "tier": "B",
            "if_val": None,
            "zone": "PubMed 收录期刊",
            "journal_bonus": 0,
            "whitelist_exempt": False,
            "warned": False,
            "journal_abbr": iso_abbr or title or "Unknown",
            "journal_full": title or "Unknown Journal",
        }


# ============================================================================
# 1b. 逐刊目录健康台账 + 全量见过账本（目录路护栏：钥匙静默失灵必须响）
# ============================================================================

# 目录健康阈值（唯一真相源；tools/journal_qc.py 从这里引用，改阈值只改此处）
HEALTH_YELLOW_DAYS = 45          # 静默 ≥45 天：提示（低频刊/季刊可能正常）
HEALTH_RED_DAYS = 100            # 静默 ≥100 天：报警（疑改名/停刊/检索键失效，人工核）

SEEN_LEDGER_DAYS = 90            # 见过账本滚动窗（与站上滚动档案同宽）


def load_seen(path: Optional[Path] = None) -> Dict[str, str]:
    """见过账本：{pmid: 最后见到日期}，滚动 90 天。凡检查过（examined）的文章不再重看——
    这是双路架构的防重复税闸：目录路 3 天窗每日重拉，不去重预筛量会逐日滚雪球。"""
    path = path or (DATA_DIR / "seen_pmids.json")
    cutoff = (date.today() - timedelta(days=SEEN_LEDGER_DAYS)).isoformat()
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 账本损坏从零重建（宁重看，勿漏看）
        state = {}
    if not isinstance(state, dict):
        state = {}
    clean: Dict[str, str] = {}
    for p, d in state.items():
        if not isinstance(d, str):
            continue
        try:
            if date.fromisoformat(d) >= date.fromisoformat(cutoff):
                clean[p] = d
        except ValueError:        # 坏日期串＝剪（与账本「宁重看，勿漏看」方向一致）
            continue
    return clean


def save_seen(state: Dict[str, str], path: Optional[Path] = None) -> None:
    path = path or (DATA_DIR / "seen_pmids.json")
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def update_journal_health(counts: Dict[str, int], path: Optional[Path] = None) -> Dict[str, Any]:
    """逐刊目录健康台账：命中>0 即刷新最后命中日；45–99 天静默提示、≥100 天报警。
    （覆盖月刊/季刊的正常出刊间隔；≥100 天仍静默＝疑改名/停刊/检索键失效，人工核。）"""
    path = path or (DATA_DIR / "journal_health.json")
    today = date.today()
    state: Dict[str, str] = {}
    if path.exists():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 台账损坏从零重建
            state = {}
    for ta in counts:
        state.setdefault(ta, today.isoformat())       # 首见即登记（假设部署时健康）
        if counts[ta] > 0:
            state[ta] = today.isoformat()
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    def _age(d: str) -> int:
        try:
            return (today - date.fromisoformat(d)).days
        except (ValueError, TypeError):
            return 0
    stale = sorted(ta for ta, d in state.items() if _age(d) >= HEALTH_RED_DAYS)
    quiet = sorted(ta for ta, d in state.items()
                   if HEALTH_YELLOW_DAYS <= _age(d) < HEALTH_RED_DAYS)
    if quiet:
        log(f"目录静默 45–99 天 {len(quiet)} 刊（季刊可能正常）: {', '.join(quiet[:8])}"
            + ("…" if len(quiet) > 8 else ""))
    if stale:
        log(f"⚠ 目录零命中 ≥100 天 {len(stale)} 刊——疑改名/停刊/键失效，人工核: "
            f"{', '.join(stale[:10])}" + ("…" if len(stale) > 10 else ""))
    return {"red": stale, "yellow": quiet, "green": len(state) - len(stale) - len(quiet),
            "total": len(state)}


# ============================================================================
# 2. 四元组核验器（数值存在性 + 语境锚定，fail-closed）
# ============================================================================

METRIC_ANCHORS: Dict[str, List[str]] = {
    "os": ["overall survival", "os rate", "survival"],
    "pfs": ["progression-free", "progression free", "pfs"],
    "efs": ["event-free", "event free", "efs"],
    "hr": ["hazard ratio", "hr"],
    "ci": ["confidence interval", "ci"],
    "pcr": ["pathological complete response", "pcr", "complete response"],
    "p CR": ["pathological complete response", "pcr"],
    "orr": ["objective response", "response rate", "orr"],
    "ae": ["adverse event", "ae", "toxicity"],
    "trae": ["treatment-related adverse", "trae"],
    "mpfs": ["progression-free", "pfs"],
    "mos": ["overall survival", "os"],
    "vas": ["visual analogue", "visual analog", "vas"],
    "p": ["p ==", "p<", "p <", "p=", "p ="],
}


class FourTupleVerifier:
    """
    每个数值要求两关：
      a) 存在性：数字（去千分位/百分号归一后）出现在英文原摘要中；
      b) 语境锚定：数字所在句（或相邻句）含有该终点指标的关键词锚。
    两关全过才算 grounded；任何失败都在数据里如实标注，绝不静默放行。
    局限（诚实声明）：这是确定性文本比对，不是语义理解；语境锚定按关键词锚实现，
    无法识别「同数值不同人群」的高级张冠李戴，此类风险由 LLM 精评提示词约束 + 人工抽查兜底。
    """

    NUMBER_RE = re.compile(r"(?<![a-zA-Z0-9])(\d+(?:\.\d+)?%?)(?![a-zA-Z0-9])")
    ALLOWLIST = {"1", "2", "3", "4", "5", "95", "95%", "100%", "100", "0.05"}

    @classmethod
    def _norm_numbers(cls, text: str) -> List[str]:
        return [r for r in cls.NUMBER_RE.findall(text.replace(",", "").replace("·", "."))
                if r not in cls.ALLOWLIST]

    @staticmethod
    def _sentences(text: str) -> List[str]:
        parts = re.split(r"(?<=[.;])\s+", text.replace(",", ""))
        return [p.strip() for p in parts if p.strip()]

    @classmethod
    def _anchors_for_metric(cls, metric: str) -> List[str]:
        m = metric.lower()
        anchors: List[str] = []
        for token in re.split(r"[\s/&+、（）()·]+", m):
            anchors.extend(METRIC_ANCHORS.get(token, []))
        # 兜底：指标里的英文原词本身就是锚
        anchors.extend(re.findall(r"[a-z][a-z\-]{3,}", m))
        return [a.lower() for a in anchors if len(a) >= 2]

    @classmethod
    def _num_bound_regex(cls, bare: str) -> "re.Pattern":
        """词边界数值匹配：'35' 不得命中 '135'/'35.4'；'0.72' 不得命中 '10.72'。"""
        return re.compile(rf"(?<![a-zA-Z0-9.]){re.escape(bare)}(?![a-zA-Z0-9])")

    @classmethod
    def _number_grounded_in_context(cls, num: str, abstract: str, anchors: List[str]) -> tuple:
        """返回 (grounded, note)。bare 数字按词边界在摘要里；若能定位句则要求句内有锚。"""
        bare = num.rstrip("%")
        rx = cls._num_bound_regex(bare)
        sents = cls._sentences(abstract)
        hits = [s for s in sents if rx.search(s)]
        if not hits:
            # 整文边界兜底（如数值写在结构化标签旁、分句失败时）
            if rx.search(abstract.replace(",", "")):
                return True, "整串边界命中（未定位到句）"
            return False, "数值未在原摘要出现"
        if not anchors:
            return True, "数值命中（指标无可用锚词，仅存在性比对）"
        for s in hits:
            s_low = s.lower()
            if any(a in s_low for a in anchors):
                return True, "数值+语境锚命中"
        # 相邻句放宽一档（摘要里数值常与指标分句书写）
        for i, s in enumerate(hits):
            idx = sents.index(s)
            neigh = " ".join(sents[max(0, idx - 1): idx + 2]).lower()
            if any(a in neigh for a in anchors):
                return True, "数值命中+邻句锚命中"
        return False, "数值在摘要中，但所在句无该指标语境（疑似张冠李戴）"

    @classmethod
    def verify(cls, abstract_en: str, summary_zh: str,
               tuples: List[Dict[str, Any]]) -> Dict[str, Any]:
        # 与抽取同口径归一：欧式中点小数 '·' → '.'，千分位逗号剔除
        abstract_en = abstract_en.replace("·", ".")
        abstract_norm = abstract_en.replace(",", "")

        def _grounded(n: str) -> bool:
            return bool(cls._num_bound_regex(n.rstrip("%")).search(abstract_norm))

        summary_nums = [n for n in cls._norm_numbers(summary_zh) if _grounded(n)]
        ungrounded_summary = [n for n in cls._norm_numbers(summary_zh) if not _grounded(n)]

        tuple_audit = []
        for t in tuples or []:
            anchors = cls._anchors_for_metric(str(t.get("metric", "")))
            nums = cls._norm_numbers(str(t.get("val", "")) + " " + str(t.get("stat", "")))
            checks = []
            for n in nums:
                ok, note = cls._number_grounded_in_context(n, abstract_en, anchors)
                checks.append({"num": n, "grounded": ok, "note": note})
            bad = [c["num"] for c in checks if not c["grounded"]]
            tuple_audit.append({
                "group": t.get("group", ""),
                "metric": t.get("metric", ""),
                "val": t.get("val", ""),
                "stat": t.get("stat", ""),
                "grounded": len(bad) == 0,
                "checks": checks,
                "missing_tokens": bad,
            })

        passed = len(ungrounded_summary) == 0 and all(a["grounded"] for a in tuple_audit)
        return {
            "passed": passed,
            "ungrounded_numbers": ungrounded_summary,
            "tuple_audit": tuple_audit,
        }


# ============================================================================
# 2b. 语义核验器（规则版，纯文本不调模型；fail-closed：宁误杀勿放过）
# ============================================================================

# CJK 限定词 → 英文锚（任一命中即算该限定词已核）。词典未收录的残余词 → 无法核验 → 按不匹配处理。
SEMANTIC_QUALIFIER_ANCHORS: Dict[str, List[str]] = {
    "意向治疗": ["intent-to-treat", "intention-to-treat"],
    "全人群": ["all patients", "entire cohort", "all randomized", "overall population",
               "total population", "all enrolled"],
    "鳞癌": ["squamous"],
    "腺癌": ["adenocarcinoma"],
    "脑转移": ["brain metast", "cns metast"],
    "老年": ["elderly", "older"],
    "吸烟": ["smok"],
    "突变": ["mutat"],
    "阳性": ["positive"],
    "阴性": ["negative"],
    "可切除": ["resectable", "resection"],
    "局部晚期": ["locally advanced"],
    "转移性": ["metastatic"],
    "复发": ["recurrence", "recurrent", "relapse"],
    "术后": ["postoperative", "resected"],
    "新辅助": ["neoadjuvant"],
    "辅助": ["adjuvant"],
    "高危": ["high risk", "high-risk"],
    "风险": ["risk"],
    "病理完全缓解": ["pathological complete response", "pcr"],
    "完全缓解": ["complete response"],
    "日本": ["japan"],
    "中国": ["china", "chinese"],
    # 2026-10-18 误杀补锚：只收与中文限定词 1:1 的英文。裸 overall/total/whole、
    # 裸 video（会命中 video-assisted）、细胞名下的 in vitro/in vivo 不收。
    "总体": [
        "overall population", "overall cohort", "entire cohort", "entire population",
        "all patients", "all comers", "all-comers", "all-comer",
        "total population", "whole population", "whole cohort",
    ],
    "随访": ["follow-up", "follow up", "followup", "followed up", "followed"],
    "细胞": ["cell", "cells", "cellular"],
    "测序样本": [
        "sequencing sample", "sequencing samples", "sequenced sample", "sequenced samples",
        "samples were sequenced", "sample was sequenced",
        "sequenced specimens", "sequencing specimens",
    ],
    # 「体外原代」拆成两条：任一命中才算该条已核，两条都要中，避免只出现 in vitro 就放行。
    "体外": ["in vitro"],
    "原代": [
        "primary culture", "primary cultures", "primary cells",
        "primary cell culture", "primary cell line", "primary cell lines",
        "primary in vitro",
    ],
    "全部纳入视频": [
        "videos", "all videos", "included videos", "enrolled videos", "video recordings",
    ],
}

# CJK 终点/指标词 → 英文锚（与上面同规则；用于 tuple.metric）
SEMANTIC_METRIC_ANCHORS: Dict[str, List[str]] = {
    "总生存": ["overall survival"],
    "无进展生存": ["progression-free", "progression free"],
    "无病生存": ["disease-free", "disease free"],
    "无事件生存": ["event-free", "event free"],
    "病理完全缓解": ["pathological complete response", "pcr"],
    "客观缓解": ["objective response", "response rate"],
    "缓解持续时间": ["duration of response"],
    "疾病控制": ["disease control"],
    "不良事件": ["adverse event"],
    "主要终点": ["primary endpoint", "primary outcome", "primary end point"],
    "次要终点": ["secondary endpoint", "secondary outcome"],
    "中位": ["median"],
    "安全性": ["safety", "tolerab"],
    "生存": ["survival"],
    "复发": ["recurrence", "relapse"],
    "并发症": ["complication"],
    "漏气": ["air leak"],
}

# ASCII 缩写 → 别名锚（缩写本身也是锚，别名单防摘要只写全称的漏杀）
SEMANTIC_ASCII_ALIASES: Dict[str, List[str]] = {
    "pcr": ["pathological complete response"],
    "itt": ["intent-to-treat", "intention-to-treat", "all patients"],
    "ctdna": ["circulating tumor dna", "circulating tumour dna"],
    "mrd": ["molecular residual disease", "measurable residual disease"],
    "os": ["overall survival"],
    "pfs": ["progression-free", "progression free"],
    "efs": ["event-free", "event free"],
    "orr": ["objective response", "response rate"],
    "pd-l1": ["pd-l1", "pd l1"],
    "nsclc": ["non-small-cell", "non-small cell"],
    "tki": ["tyrosine kinase"],
    "ici": ["immune checkpoint"],
    "ae": ["adverse event"],
    "hr": ["hazard ratio"],
    "ci": ["confidence interval"],
}

# 限定词串里的通用衬底词：不携带人群信息，不产生核验要求
SEMANTIC_STOPWORDS = ("人群", "患者", "亚组", "分析", "研究", "队列", "治疗组", "的", "率",
                      "期", "年", "月", "例", "岁", "与", "及", "和", "在", "为", "中",
                      "肺", "非", "型")

CJK_RUN_RE = re.compile(r"[一-鿿]+")
ASCII_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-/]{1,}")


class SemanticChecker:
    """
    规则版语义核验：核对 LLM 四元组的【人群限定词】与【终点指标词】是否在英文原摘要出现。
      - tuple.group 的每个限定词（ASCII 缩写/CN 词/数字）须在摘要命中其锚词，任一限定词落空 → 该 tuple
        semantic_mismatch；
      - tuple.metric 须在摘要命中至少一个指标锚（全词或锚词表），否则 semantic_mismatch；
      - 摘要中不存在、词典也未收录的限定词按不匹配处理（fail-closed，宁误杀勿放过；误杀率由回归集量出）。
    诚实边界：这是词面级比对，不是语义理解；「同义改写」可能误杀，「隐蔽的人群偷换」若限定词碰巧都
    在摘要出现则拦不住。词典覆盖率决定误杀率，随回归集持续校准。
    """

    @staticmethod
    def _hit(abstract_low: str, anchor: str) -> bool:
        """ASCII/数字锚按词边界匹配；含空格短语按子串匹配。"""
        a = anchor.strip().lower()
        if not a:
            return False
        if " " in a:
            return a in abstract_low
        return re.search(rf"(?<![a-z0-9]){re.escape(a)}(?![a-z0-9])", abstract_low) is not None

    @classmethod
    def _qualifiers_of(cls, text: str, cn_dict: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """从 group/metric 串抽出待核限定词：ASCII token（带别名）、两位以上数字、CN 词典词。"""
        quals: List[Dict[str, Any]] = []
        for tok in ASCII_TOKEN_RE.findall(text):
            t = tok.lower().strip("-/")
            if len(t) < 2:
                continue
            anchors = [t] + [a.lower() for a in SEMANTIC_ASCII_ALIASES.get(t, [])]
            quals.append({"label": tok, "anchors": anchors})
        for num in re.findall(r"\d{2,}", text):
            quals.append({"label": num, "anchors": [num]})
        rest = text
        for key in sorted(cn_dict, key=len, reverse=True):
            if key in rest:
                rest = rest.replace(key, "◇")     # 已识别占位，防止「完全缓解」截胡「病理完全缓解」
                quals.append({"label": key,
                              "anchors": [a.lower() for a in cn_dict[key]]})
        for sw in SEMANTIC_STOPWORDS:
            rest = rest.replace(sw, "◇")
        for run in CJK_RUN_RE.findall(rest):
            if run.strip():
                quals.append({"label": run, "anchors": []})   # 词典未收录 → 无法核验 → fail-closed
        return quals

    @classmethod
    def metric_anchors(cls, metric: str) -> List[str]:
        """指标串 → 判定用锚全集（METRIC_ANCHORS + CJK 词典 + 别名）。生成器与判定共用此推导，防两端锚集漂移。"""
        anchors: List[str] = []
        for tok in ASCII_TOKEN_RE.findall(str(metric)):
            tl = tok.lower().strip("-/")
            if len(tl) >= 2:
                anchors.extend(FourTupleVerifier._anchors_for_metric(tl))
        for key in sorted(SEMANTIC_METRIC_ANCHORS, key=len, reverse=True):
            if key in str(metric):
                anchors.extend(a.lower() for a in SEMANTIC_METRIC_ANCHORS[key])
        return list(dict.fromkeys(anchors))

    @classmethod
    def check(cls, abstract_en: str, tuples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """逐 tuple 核人群限定 + 终点指标；返回 {passed, n_mismatch, tuple_audit}。"""
        abs_low = (abstract_en or "").lower()
        audit = []
        for t in tuples or []:
            reasons: List[str] = []
            # 1) 人群限定：每个限定词的锚都必须有命中（any-of-anchors per qualifier）
            for q in cls._qualifiers_of(str(t.get("group", "")), SEMANTIC_QUALIFIER_ANCHORS):
                if q["anchors"]:
                    if not any(cls._hit(abs_low, a) for a in q["anchors"]):
                        reasons.append(f"人群限定「{q['label']}」未在原摘要出现")
                else:
                    reasons.append(f"人群限定「{q['label']}」无英文锚（词典未收录，宁误杀）")
            # 2) 终点指标：任一指标锚命中即过
            m_anchors = cls.metric_anchors(str(t.get("metric", "")))
            if not m_anchors:
                reasons.append("终点指标词无可用锚（词典未收录，宁误杀）")
            elif not any(cls._hit(abs_low, a) for a in m_anchors):
                reasons.append("终点指标词未在原摘要出现")
            audit.append({
                "group": t.get("group", ""), "metric": t.get("metric", ""),
                "population_ok": all("人群限定" not in r for r in reasons),
                "metric_ok": all("指标" not in r for r in reasons),
                "mismatch_reasons": reasons,
            })
        n_bad = sum(1 for a in audit if a["mismatch_reasons"])
        return {"passed": n_bad == 0, "n_mismatch": n_bad, "tuple_audit": audit}


# ============================================================================
# 3. LLM 客户端（OpenAI 兼容 + 成本熔断）
# ============================================================================

class LLMClient:
    def __init__(self) -> None:
        self.key = os.environ.get("LLM_API_KEY", "").strip()
        self.base = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1").strip().rstrip("/")
        self.model = os.environ.get("LLM_MODEL", "deepseek-chat").strip()
        self.price_in = float(os.environ.get("LLM_PRICE_IN", "0.27"))
        self.price_out = float(os.environ.get("LLM_PRICE_OUT", "1.10"))
        self.cap_usd = float(os.environ.get("MAX_DAILY_COST_USD", "0.10"))
        self.cost_usd = 0.0
        self.calls = 0
        self._lock = threading.Lock()   # 并行精评时的成本计数保护

    @property
    def available(self) -> bool:
        return bool(self.key)

    def chat(self, system: str, user: str, max_tokens: int = 2000) -> str:
        if not self.available:
            raise RuntimeError("LLM_API_KEY 未配置")
        if self.cost_usd > self.cap_usd:
            raise BudgetExceeded(f"LLM 成本 ${self.cost_usd:.3f} 超熔断上限 ${self.cap_usd:.2f}")
        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base}/chat/completions", data=payload,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.key}"})
        last_err: Optional[Exception] = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                usage = data.get("usage", {})
                with self._lock:
                    self.cost_usd += (usage.get("prompt_tokens", 0) * self.price_in
                                      + usage.get("completion_tokens", 0) * self.price_out) / 1e6
                    self.calls += 1
                return data["choices"][0]["message"]["content"]
            except BudgetExceeded:
                raise
            except Exception as e:  # noqa: BLE001 网络抖动重试
                last_err = e
                time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"LLM 调用三连失败: {last_err}")


class BudgetExceeded(RuntimeError):
    pass


def parse_json_loose(text: str) -> Any:
    """剥掉 ```json 围栏后解析；失败抛 ValueError。"""
    t = text.strip()
    m = re.search(r"```(?:json)?\s*(.+?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    return json.loads(t)


# ============================================================================
# 4. 采集：ESearch(crdt) + EFetch
# ============================================================================

class Collector:
    EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self) -> None:
        self.api_key = os.environ.get("NCBI_API_KEY", "").strip()
        self._last_count = 0

    def _get(self, url: str) -> bytes:
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "ThorRadar/3.0"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    return resp.read()
            except Exception as e:  # noqa: BLE001
                if attempt == 2:
                    raise
                log(f"  网络重试 {attempt + 1}/3: {e}")
                time.sleep(2 * (attempt + 1))
        raise RuntimeError("unreachable")

    def esearch_pmids(self, days_back: int, retmax: int = 200,
                      query: Optional[str] = None, hard_cap: int = 2000) -> List[str]:
        """分页抓全：retmax 只是页大小，命中总量以 Count 为准，防单页截断静默丢文献。"""
        base = {
            "db": "pubmed", "term": query or DEFAULT_QUERY, "datetype": "crdt",
            "reldate": str(days_back), "retmode": "json", "sort": "date",
        }
        if self.api_key:
            base["api_key"] = self.api_key

        def _page(start: int, size: int) -> "tuple[List[str], int]":
            params = dict(base)
            params["retmax"] = str(size)
            params["retstart"] = str(start)
            url = f"{self.EUTILS}/esearch.fcgi?{urllib.parse.urlencode(params)}"
            er = json.loads(self._get(url).decode("utf-8")).get("esearchresult", {})
            return er.get("idlist", []), int(er.get("count", "0"))

        ids0, total = _page(0, 0)         # 首调只取 Count（retmax=0 不回 idlist）
        self._last_count = total          # 兼容探针读取（线程内局部使用，无竞态）
        if total <= 0:
            return []
        if total > hard_cap:
            log(f"⚠ ESearch 命中 {total} 超过硬顶 {hard_cap}，只取最新 {hard_cap} 篇"
                f"（疑似检索式过宽或窗口异常，人工看板跟进）")
            total = hard_cap
        page = max(1, retmax)
        pmids: List[str] = []
        start = 0
        while start < total:
            batch, _ = _page(start, min(page, total - start))
            if not batch:
                log(f"⚠ 分页在第 {start} 条处提前断流（已取 {len(pmids)}/{total}）")
                break
            pmids.extend(batch)
            start += len(batch)
        return pmids[:total]

    def fetch_journal_toc(self, journals: List[Dict[str, Any]],
                          days_back: int, workers: int = 6) -> "tuple[List[str], Dict[str, int]]":
        """目录路（并行）：逐刊拉近 N 天全部 PMID（340 刊全收，无词表漏法）。
        返回 (去重前 pmid 列表, {刊ta: 命中数|−1=失败})；单刊失败计 -1，不断全卷。"""
        def _one(j: Dict[str, Any]):
            ta = (j.get("iso_abbr") or j.get("title") or "").strip()
            if not ta:
                return None, 0
            try:
                return ta, self.esearch_pmids(days_back, 500, query=f'"{ta}"[ta]')
            except Exception as e:  # noqa: BLE001 单刊失败不断全卷
                log(f"⚠ 目录扫描失败 {ta}: {e}")
                return ta, None

        toc: List[str] = []
        counts: Dict[str, int] = {}
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for ta, ids in ex.map(_one, journals):
                if ta is None:
                    continue
                if ids is None:
                    counts[ta] = -1
                else:
                    counts[ta] = len(ids)
                    toc.extend(ids)
        return toc, counts

    def efetch_articles(self, pmids: List[str]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for i in range(0, len(pmids), 80):
            batch = pmids[i:i + 80]
            params = {"db": "pubmed", "id": ",".join(batch), "retmode": "xml"}
            if self.api_key:
                params["api_key"] = self.api_key
            url = f"{self.EUTILS}/efetch.fcgi?{urllib.parse.urlencode(params)}"
            xml_body = self._get(url)
            root = ET.fromstring(xml_body)
            for art in root.findall(".//PubmedArticle"):
                try:
                    out.append(self._parse_article(art))
                except Exception as e:  # noqa: BLE001 单篇脏数据不拖垮整批
                    log(f"  单篇解析失败跳过: {e}")
            time.sleep(0.4 if not self.api_key else 0.12)
        return out

    @staticmethod
    def _parse_article(article_elem: ET.Element) -> Dict[str, Any]:
        pmid = article_elem.findtext(".//MedlineCitation/PMID", default="")
        title_el = article_elem.find(".//Article/ArticleTitle")
        title = "".join(title_el.itertext()).strip() if title_el is not None else ""

        p_issn = e_issn = ""
        for issn_el in article_elem.findall(".//Article/Journal/ISSN"):
            if issn_el.attrib.get("IssnType") == "Electronic":
                e_issn = (issn_el.text or "").strip()
            else:
                p_issn = (issn_el.text or "").strip()
        issn_linking = article_elem.findtext(".//MedlineCitation/MedlineJournalInfo/ISSNLinking", default="")
        nlm_id = article_elem.findtext(".//MedlineCitation/MedlineJournalInfo/NlmUniqueID", default="")
        iso_abbr = article_elem.findtext(".//Article/Journal/ISOAbbreviation", default="")
        journal_title = article_elem.findtext(".//Article/Journal/Title", default="")

        abstract_parts = []
        for ab in article_elem.findall(".//Article/Abstract/AbstractText"):
            label = ab.attrib.get("Label", "")
            txt = "".join(ab.itertext()).strip()
            if txt:
                abstract_parts.append(f"{label}: {txt}" if label else txt)
        abstract = " ".join(abstract_parts)

        affs = ["".join(a.itertext()).strip()
                for a in article_elem.findall(".//AffiliationInfo/Affiliation")]
        authors = []
        for au in article_elem.findall(".//AuthorList/Author")[:8]:
            last = au.findtext("LastName", "")
            init = au.findtext("Initials", "")
            if last:
                authors.append(f"{last} {init}".strip())
        author_str = ", ".join(authors) + (" et al." if len(authors) >= 8 else "")

        year = article_elem.findtext(".//Article/Journal/JournalIssue/PubDate/Year", default="")
        month = article_elem.findtext(".//Article/Journal/JournalIssue/PubDate/Month", default="")
        day = article_elem.findtext(".//Article/Journal/JournalIssue/PubDate/Day", default="")
        pub_date = "-".join(x for x in (year, month, day) if x) or year
        doi = ""
        for aid in article_elem.findall(".//ArticleIdList/ArticleId"):
            if aid.attrib.get("IdType") == "doi":
                doi = (aid.text or "").strip()
        pmcid = ""
        for aid in article_elem.findall(".//ArticleIdList/ArticleId"):
            if aid.attrib.get("IdType") == "pmc":
                pmcid = (aid.text or "").strip()
        nct = ""
        for acc in article_elem.findall(".//DataBankList/DataBank/AccessionNumberList/AccessionNumber"):
            m = re.match(r"NCT\d{8}$", (acc.text or "").strip())
            if m:
                nct = m.group(0)
                break
        if not nct:
            m = re.search(r"NCT\d{8}", abstract)
            nct = m.group(0) if m else ""

        return {
            "pmid": pmid, "title_en": title, "p_issn": p_issn, "e_issn": e_issn,
            "issn_linking": issn_linking, "nlm_id": nlm_id, "iso_abbr": iso_abbr,
            "journal_title": journal_title, "abstract_en": abstract,
            "authors": author_str or "（作者信息缺失）",
            "affiliations": " ; ".join(affs)[:300],
            "pub_date": pub_date, "doi": doi, "pmcid": pmcid, "nct_id": nct,
            "status": Collector.parse_status(article_elem),
        }

    # ---- 出版状态识别（撤稿/更正/关注声明；依据真实 NLM 结构，不假定 withdrawn 字段）----

    # PublicationType 标记本文自身身份
    PT_RETRACTED = "retracted publication"       # 本文已被撤稿
    PT_RETRACTION_NOTICE = "retraction of publication"  # 本文是撤稿通知
    PT_ERRATUM_NOTICE = "published erratum"      # 本文是更正启事
    PT_CORRECTED_REPUB = "corrected and republished article"
    # CommentsCorrections RefType 标记本文与通知的关联（本文为原始文章时）
    REF_RETRACTED_IN = "retractedin"             # 本文被某撤稿通知撤稿
    REF_ERRATUM_IN = "erratumin"                 # 本文有更正启事
    REF_EOC_IN = "expressionofconcernin"         # 本文被发关注声明

    @classmethod
    def parse_status(cls, article_elem: ET.Element) -> Dict[str, Any]:
        """
        返回 {kind, notice_pmid, notice_ref, impact_known, note}。
        kind ∈ ok / retracted / corrected / concern / notice（本文自身是通知类，不进精选流）。
        更正的影响是否可知：我们只有通知关联而读不到更正内容时，impact_known=False → 暂停解读。
        """
        pts = {(pt.text or "").strip().lower()
               for pt in article_elem.findall(".//MedlineCitation/Article/PublicationTypeList/PublicationType")}
        refs = []
        for cc in article_elem.findall(".//MedlineCitation/CommentsCorrectionsList/CommentsCorrections"):
            refs.append(((cc.attrib.get("RefType") or "").strip().lower(),
                         (cc.findtext("PMID") or "").strip(),
                         (cc.findtext("RefSource") or "").strip()[:160]))
        is_notice = (cls.PT_RETRACTION_NOTICE in pts or cls.PT_ERRATUM_NOTICE in pts
                     or any(r[0] in ("retractionof", "erratumfor", "expressionofconcernfor") for r in refs))
        if is_notice:
            return {"kind": "notice", "notice_pmid": "", "notice_ref": "", "impact_known": True,
                    "note": "本文为撤稿/更正/关注声明类通知，不作为研究文献收录"}
        if cls.PT_RETRACTED in pts or any(r[0] == cls.REF_RETRACTED_IN for r in refs):
            r = next((x for x in refs if x[0] == cls.REF_RETRACTED_IN), ("", "", ""))
            return {"kind": "retracted", "notice_pmid": r[1], "notice_ref": r[2],
                    "impact_known": True, "note": "原文已被撤稿（Retracted Publication）"}
        if cls.PT_CORRECTED_REPUB in pts or any(r[0] == cls.REF_ERRATUM_IN for r in refs):
            r = next((x for x in refs if x[0] == cls.REF_ERRATUM_IN), ("", "", ""))
            return {"kind": "corrected", "notice_pmid": r[1], "notice_ref": r[2],
                    "impact_known": False, "note": "原文存在更正启事；更正对结论的影响未明，解读暂停"}
        if any(r[0] == cls.REF_EOC_IN for r in refs):
            r = next((x for x in refs if x[0] == cls.REF_EOC_IN), ("", "", ""))
            return {"kind": "concern", "notice_pmid": r[1], "notice_ref": r[2],
                    "impact_known": False, "note": "原文被发布关注声明（Expression of Concern），解读暂停"}
        return {"kind": "ok", "notice_pmid": "", "notice_ref": "", "impact_known": True, "note": ""}


# ============================================================================
# 4b. 出版状态覆盖层（日档永不回改；最新状态独立记录，展示/导出统一应用）
# ============================================================================

STATUS_FILE = DATA_DIR / "status.json"
RECHECK_INTERVAL_DAYS = 7      # 每篇已跟踪文献的最小回查间隔
RECHECK_MAX_BATCH = 300        # 单次回查上限（控运行时长）


def load_status_db() -> Dict[str, Any]:
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001 损坏即重建，不拖垮主流程
            log(f"⚠ status.json 损坏，重建: {e}")
    return {"updated_at": "", "papers": {}}


def save_status_db(db: Dict[str, Any]) -> None:
    db["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    DATA_DIR.mkdir(exist_ok=True)
    STATUS_FILE.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")


def recheck_stale_statuses(collector: "Collector", db: Dict[str, Any],
                           recheck_days: int = RECHECK_INTERVAL_DAYS,
                           max_batch: int = RECHECK_MAX_BATCH) -> int:
    """对已跟踪且临近过期的 PMID 批量回查状态；接口失败→保留旧状态并标 stale，不崩运行。"""
    now = datetime.now()
    due = []
    for pmid, rec in db["papers"].items():
        last = rec.get("last_checked", "")
        try:
            age = (now - datetime.strptime(last, "%Y-%m-%d %H:%M")).days if last else 999
        except ValueError:
            age = 999
        if age >= recheck_days:
            due.append(pmid)
    due = due[:max_batch]
    if not due:
        return 0
    log(f"状态回查：{len(due)} 篇到期")
    try:
        arts = collector.efetch_articles(due)
    except Exception as e:  # noqa: BLE001 接口失败
        log(f"⚠ 状态回查接口失败（保留旧状态，标 stale）: {e}")
        for pmid in due:
            db["papers"][pmid]["stale"] = True
        return 0
    got = {a["pmid"]: a for a in arts}
    for pmid in due:
        rec = db["papers"].get(pmid, {})
        if pmid in got:
            st = got[pmid]["status"]
            rec.update({
                "kind": st["kind"], "notice_pmid": st["notice_pmid"],
                "notice_ref": st["notice_ref"], "impact_known": st["impact_known"],
                "note": st["note"], "last_checked": now.strftime("%Y-%m-%d %H:%M"),
                "stale": False,
            })
        else:
            rec["stale"] = True   # 单篇取不到：保旧标陈
        db["papers"][pmid] = rec
    changed = sum(1 for pmid in due
                  if pmid in got and got[pmid]["status"]["kind"] != "ok"
                  and db["papers"][pmid].get("kind", "ok") != "ok")
    return changed


def upsert_today_status(db: Dict[str, Any], papers: List[Dict[str, Any]]) -> None:
    """当日文献首次入库即登记状态（含 ok）。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    for p in papers:
        st = p["status"]
        db["papers"][p["pmid"]] = {
            "kind": st["kind"], "notice_pmid": st["notice_pmid"],
            "notice_ref": st["notice_ref"], "impact_known": st["impact_known"],
            "note": st["note"], "first_seen": now, "last_checked": now, "stale": False,
        }


# ============================================================================
# 5. 预筛 + 精评（LLM，启发式兜底）
# ============================================================================

PREScreen_SYSTEM = """你是胸部肿瘤文献初审员。输入若干篇新入库 PubMed 文献的标题与期刊。
判断每篇是否值得进入精选流。保留标准（符合任一）：
1) 围术期/新辅助/辅助治疗临床研究（NSCLC、食管癌；含 pCR、ctDNA/MRD 等终点）；
2) 肺结节随访、筛查与干预管理；
3) 微创胸外科（VATS/RATS/Tubeless/肺段切除/引流疼痛管理）；
4) 胸外科 AI、三维重建、影像组学、数字医疗；
5) 晚期胸部肿瘤靶向/免疫关键临床研究（NSCLC/SCLC/间皮瘤/胸腺肿瘤）。
剔除：纯细胞/动物实验、无关器官、单例个案报告（S 级顶刊重大信号除外）。
只输出 JSON：{"decisions": [{"i": <输入序号>, "keep": true/false}]}"""

SCORE_SYSTEM = """你是胸部肿瘤临床科研资深评审。对给定文献输出严格 JSON（不要任何额外文字）：
{
 "title_zh": "中文标题（描述研究问题与结果，不照搬作者最乐观的表述）",
 "study_type": "研究设计与类型一句话（如 Phase III RCT · 最终OS分析）",
 "category": "perioperative|nodule|surgery|ai_digital|advanced|esophageal 六选一",
 "score_clinical": 0-35 整数（影响临床判断的潜力，如手术患者选择/随访决策/结节风险判断）,
 "score_methodology": 0-30 整数（设计严谨性；严谨阴性研究同样给高分）,
 "score_specialty": 0-20 整数（胸外科/胸部肿瘤契合度）,
 "pico_p": "人群与样本量（摘要为准；信息不足给空串）",
 "pico_ic": "干预与对照（摘要为准；信息不足给空串）",
 "results": "实际报告的结果：只陈述摘要中明确出现的主要结果数值（含CI/P与主要/次要终点标注），逐字取数，不加解读；摘要无可靠数值给空串",
 "authors_conclusion": "作者自己的结论表述（照录其口径，可含乐观倾向，不加修饰；无明确结论给空串）",
 "ai_note": "AI 疑点与提示：选择性强调/次要终点替代主要终点/人群限定松动/方法学局限等；发现矛盾或信息不足时如实写'信息不足'；无发现给空串",
 "reason": "入选理由：具体到这篇影响什么判断（临床或科研，如'影响可切除NSCLC新辅助方案选择'或'为队列设计提供对照基线'），不用第二人称",
 "is_negative_highlight": true/false（是否为高质量阴性/证伪研究）,
 "tuples": [{"group": "人群/亚组限定", "metric": "终点指标", "val": "数值", "stat": "95%CI/P"}],
 "tags": ["标签1", "标签2"]
}
规则：
- 四栏分离是硬要求：results 只报事实数值，authors_conclusion 只照录作者口径，ai_note 只放你的独立疑点——三栏不得互相越界混写。
- 摘要存在选择性强调（如主要终点阴性却突出次要终点）时，results 如实报主要终点，ai_note 点明。
- 反阳性偏倚条款：方法学严谨的阴性研究与阳性研究同等赋分。
- 信息不足时宁可留空串，禁止编造或外推；少说不是失败。
- tuples 只收录摘要明确出现的数值，数字必须逐字来自摘要；无可靠数值给空数组。"""


def heuristic_prescreen(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """无 LLM 时的兜底：标题关键词粗筛。诚实标注。"""
    keep_kw = ("trial", "randomized", "neoadjuvant", "adjuvant", "perioperative", "resection",
               "segmentectomy", "lobectomy", "tubeless", "thoracoscopic", "nodule", "screening",
               "immunotherapy", "chemoradiotherapy", "targeted", "osimertinib", "durvalumab",
               "artificial intelligence", "three-dimensional", "radiomics", "esophageal", "thymoma",
               "mesothelioma", "small-cell", "nsclc", "survival")
    kept = []
    for a in articles:
        blob = (a["title_en"] + " " + a["abstract_en"][:600]).lower()
        if any(k in blob for k in keep_kw):
            a["_prescreen"] = "keyword"
            kept.append(a)
    return kept


def heuristic_score(a: Dict[str, Any], jm: JournalMatcher) -> Dict[str, Any]:
    """无 LLM 时的兜底打分：期刊层级 + 研究类型关键词。"""
    m = jm.match(a["p_issn"], a["e_issn"], a["issn_linking"], a["nlm_id"],
                 a["iso_abbr"], a["journal_title"])
    blob = (a["title_en"] + " " + a["abstract_en"][:800]).lower()
    clinical = 15
    if any(k in blob for k in ("randomized", "phase 3", "phase iii", "pivotal")):
        clinical = 28
    elif any(k in blob for k in ("prospective", "cohort", "registry")):
        clinical = 20
    methodology = 15 if "randomized" in blob or "propensity" in blob or "matched" in blob else 10
    study_type = "研究类型待评定（启发式模式）"
    if "randomized" in blob:
        study_type = "RCT（启发式判定）"
    elif "cohort" in blob or "propensity" in blob:
        study_type = "队列研究（启发式判定）"
    score = clinical + methodology + 10 + m["journal_bonus"]
    return {
        "llm": {
            "title_zh": "", "study_type": study_type,
            "category": guess_category(blob),
            "score_clinical": clinical, "score_methodology": methodology,
            "score_specialty": 10,
            "pico_p": "", "pico_ic": "",
            "results": first_sentences(a["abstract_en"], 2),
            "authors_conclusion": "",
            "ai_note": "",
            "reason": "启发式模式收录（未接入语言模型精评）：按期刊层级与研究类型自动入选。",
            "is_negative_highlight": False,
            "tuples": [],
            "tags": [],
        },
        "match": m,
        "score_total": score,
        "score_source": "heuristic",
    }


def guess_category(blob_low: str) -> str:
    if any(k in blob_low for k in ("nodule", "ground-glass", "subsolid", "screening", "lung-rads")):
        return "nodule"
    if any(k in blob_low for k in ("tubeless", "thoracoscopic", "vats", "rats", "segmentectomy",
                                   "lobectomy", "air leak", "chest tube", "esophagectomy")):
        return "surgery"
    if any(k in blob_low for k in ("three-dimensional", "3d reconstruction", "radiomics",
                                   "artificial intelligence", "deep learning", "navigation")):
        return "ai_digital"
    if any(k in blob_low for k in ("esophageal", "thymoma", "mediastinal", "mesothelioma")):
        return "esophageal"
    if any(k in blob_low for k in ("osimertinib", "durvalumab", "stage iii", "advanced", "metastatic",
                                   "small-cell", "chemoradiotherapy", "consolidation")):
        return "advanced"
    return "perioperative"


def first_sentences(text: str, n: int, limit: int = 220) -> str:
    sents = re.split(r"(?<=\.)\s+", text)
    out = " ".join(sents[:n]).strip()
    return out[:limit] + ("…" if len(out) > limit else "")


def llm_prescreen(llm: LLMClient, articles: List[Dict[str, Any]],
                  system: str = "") -> List[Dict[str, Any]]:
    """预筛（全量库口径）：标题＋摘要头 300 字一起给 LLM 判。LLM 挂→批内全保留（诚实降级）。"""
    system = system or LIBRARY_PRESCREEN_SYSTEM
    kept = []
    batch = 20
    for i in range(0, len(articles), batch):
        chunk = articles[i:i + batch]
        listing = "\n".join(
            f"[{j}] {(a['journal_title'] or 'Unknown')[:60]} | {a['title_en'][:180]}"
            f" || {a['abstract_en'][:300]}"
            for j, a in enumerate(chunk))
        try:
            raw = llm.chat(system, listing, max_tokens=800)
            decisions = {d.get("i"): bool(d.get("keep")) for d in parse_json_loose(raw).get("decisions", [])}
        except BudgetExceeded:
            raise
        except Exception as e:  # noqa: BLE001 预筛失败→本批全保留，交给精评关
            log(f"  预筛批失败（本批全保留）: {e}")
            decisions = {j: True for j in range(len(chunk))}
        for j, a in enumerate(chunk):
            if decisions.get(j, True):
                a["_prescreen"] = "llm"
                kept.append(a)
    return kept


def llm_score_one(llm: LLMClient, a: Dict[str, Any], m: Dict[str, Any]) -> Dict[str, Any]:
    user = (f"标题: {a['title_en']}\n期刊: {a['journal_title']}（{m['journal_abbr']}）\n"
            f"摘要:\n{a['abstract_en'][:6000]}")
    raw = llm.chat(SCORE_SYSTEM, user, max_tokens=1800)
    return parse_json_loose(raw)


# ============================================================================
# 6. 组装 + 产出（JSON / 早报 / 注入 index.html）
# ============================================================================

def build_paper(a: Dict[str, Any], scored: Dict[str, Any], verdict: Optional[Dict[str, Any]],
                verify_error: Optional[str] = "") -> Dict[str, Any]:
    llm_data = scored["llm"]
    m = scored["match"]
    st = a["status"]
    has_tuples = bool(llm_data.get("tuples"))
    critic_verified = None
    if verify_error:
        critic_verified = False          # 核验异常 → 按未通过处理（fail-closed）
    elif has_tuples:
        critic_verified = bool(verdict and verdict.get("passed"))
    # 降级判定：核验未通过/异常，或出版状态要求暂停解读（撤稿/影响不明的更正/关注声明）
    status_degrades = st["kind"] in ("retracted", "concern") or (st["kind"] == "corrected" and not st["impact_known"])
    publish_state = "degraded" if ((critic_verified is False) or status_degrades) else "full"
    return {
        "id": f"pmid_{a['pmid']}",
        "pmid": a["pmid"],
        "pmcid": a.get("pmcid", ""),
        "doi": a.get("doi", ""),
        "nct_id": a.get("nct_id", ""),
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{a['pmid']}/",
        "notice_url": f"https://pubmed.ncbi.nlm.nih.gov/{st['notice_pmid']}/" if st.get("notice_pmid") else "",
        "trial_url": f"https://clinicaltrials.gov/study/{a['nct_id']}" if a.get("nct_id") else "",
        "pub_date": a.get("pub_date", ""),
        "briefing_date": date.today().isoformat(),
        "journal_abbr": m["journal_abbr"],
        "journal_full": m["journal_full"],
        "tier": m["tier"],
        "if_val": m["if_val"],
        "zone": m["zone"],
        "warned": bool(m.get("warned", False)),
        "study_type": llm_data.get("study_type", ""),
        "category": llm_data.get("category") if llm_data.get("category") in CATEGORIES else "advanced",
        "category_label": CATEGORIES.get(
            llm_data.get("category") if llm_data.get("category") in CATEGORIES else "advanced", ""),
        "score_total": scored["score_total"],
        "score_breakdown": {
            "clinical": int(llm_data.get("score_clinical", 0)),
            "methodology": int(llm_data.get("score_methodology", 0)),
            "specialty": int(llm_data.get("score_specialty", 0)),
            "journal": m["journal_bonus"],
        },
        "score_source": scored["score_source"],
        "prescreen": a.get("_prescreen", ""),
        "is_negative_highlight": bool(llm_data.get("is_negative_highlight")),
        "critic_verified": critic_verified,
        "verify_error": verify_error or "",
        "tuple_audit": (verdict or {}).get("tuple_audit", []),
        "ungrounded_numbers": (verdict or {}).get("ungrounded_numbers", []),
        "semantic_passed": ((verdict or {}).get("semantic") or {}).get("passed")
                           if verdict is not None else None,
        "semantic_audit": (verdict or {}).get("semantic", {}).get("tuple_audit", []),
        "publish_state": publish_state,
        "status": {"kind": st["kind"], "note": st["note"], "notice_pmid": st["notice_pmid"],
                   "notice_ref": st["notice_ref"], "impact_known": st["impact_known"]},
        "title_zh": llm_data.get("title_zh", "") or a["title_en"],
        "title_en": a["title_en"],
        "authors": a["authors"],
        "affiliation_highlight": first_sentences(a.get("affiliations", ""), 1, 120),
        "results": llm_data.get("results", ""),
        "authors_conclusion": llm_data.get("authors_conclusion", ""),
        "ai_note": llm_data.get("ai_note", ""),
        "pico": {"p": llm_data.get("pico_p", ""), "ic": llm_data.get("pico_ic", "")},
        "reason": llm_data.get("reason", ""),
        "abstract_en": a["abstract_en"],
        "tags": llm_data.get("tags", [])[:6],
        # 规则式精选（apply_curation 落值；此处默认值保证旧路径 schema 完整）
        "curated": False,
        "curation_reason": "",
        "curation_clinical_value": "",
        "curation_research_value": "",
        "curation_signals": {},
    }


# ============================================================================
# 6a. 规则式精选（阅读优先级）——与 LLM 开关解绑
# ============================================================================

# 精选理由必须落到具体问题类别（禁空话）：按栏目映射到「影响什么判断」
CURATION_PROBLEM_BY_CATEGORY: Dict[str, str] = {
    "perioperative": "可切除胸部肿瘤围术期/新辅助方案选择",
    "nodule": "肺结节随访间隔与恶性风险判断",
    "surgery": "手术方式选择与患者围术期管理",
    "ai_digital": "影像判读/术前规划工具的临床落地",
    "advanced": "局晚/晚期治疗线序与方案选择",
    "esophageal": "食管/纵隔肿瘤治疗决策",
}

# 阴性/证伪表述短语（配严谨设计信号使用，单独出现不足以触发）
NEGATIVE_RESULT_PHRASES = (
    "no significant difference", "did not significantly", "not significantly different",
    "failed to meet", "no statistically significant", "did not improve",
    "no improvement in", "did not reach", "no significant reduction",
    "no significant increase", "did not translate",
)


def detect_curation_signals(title_en: str, abstract_en: str) -> Dict[str, Any]:
    """从标题+摘要抽四个文本信号：研究设计 / 主要终点陈述 / 严谨阴性 / III 期标记。"""
    blob = (title_en + " " + abstract_en).lower()
    if "case report" in blob:
        design = "case_report"
    elif "randomized" in blob or "randomised" in blob or re.search(r"phase\s*(?:3|iii)\b", blob):
        design = "rct"                      # RCT 与 III 期同档（III 期未写 randomized 的少见，保守同判）
    elif (("prospective" in blob or "registry" in blob)
          and ("propensity" in blob or "match" in blob)):
        design = "prospective_matched"
    elif "prospective" in blob:
        design = "prospective"
    elif "retrospective" in blob:
        design = "retrospective"
    else:
        design = "unknown"
    return {
        "design": design,
        "phase3": bool(re.search(r"phase\s*(?:3|iii)\b", blob)),
        "primary_endpoint": ("primary endpoint" in blob or "primary outcome" in blob
                             or "primary end point" in blob),
        "negative_rigorous": bool(design in ("rct", "prospective_matched")
                                  and any(p in blob for p in NEGATIVE_RESULT_PHRASES)),
    }


def apply_curation(papers: List[Dict[str, Any]]) -> int:
    """
    规则式精选（阅读优先级），两模式同规则：
      【规则部分】四信号（design/primary_endpoint/tier/negative_rigorous，均出自文本与期刊字典）决定
        curated 布尔与理由骨架——三条入选线（全部要求 S/A 级期刊、排除个案、解读暂停不入选、预警刊不入选）：
          A. RCT/III 期于 S/A 级期刊；
          B. 前瞻匹配队列于 S/A 级期刊且明确陈述主要终点；
          C. 严谨阴性/证伪结果于 S/A 级期刊（保护阴性研究）。
      【模型部分·仅 LLM 模式】不改入选布尔（模型不能把稿抬进精选、也不能挤掉）——只在理由尾部追加
        模型 reason（标注「模型补充」）；排序仍按 score_total（LLM 模式下即模型分数）。
    精选不删稿：非精选照常发布；精选可为空（不凑数），也可全选（不设上限、不硬删）。
    返回：curated 计数（写进 funnel）。
    """
    n = 0
    for p in papers:
        sig = detect_curation_signals(p.get("title_en", ""), p.get("abstract_en", ""))
        tier = p.get("tier", "B")
        tier_ok = tier in ("S", "A")
        gate_open = p.get("publish_state") == "full" and sig["design"] != "case_report" and not p.get("warned", False)
        path_trial = sig["design"] == "rct" and tier_ok
        path_cohort = sig["design"] == "prospective_matched" and tier_ok and sig["primary_endpoint"]
        path_negative = sig["negative_rigorous"] and tier_ok
        curated = bool(gate_open and (path_trial or path_cohort or path_negative))

        problem = CURATION_PROBLEM_BY_CATEGORY.get(p.get("category", ""), "胸部肿瘤临床与科研判断")
        design_desc = {"rct": "RCT/III 期", "prospective_matched": "前瞻匹配队列"}.get(sig["design"], "")
        if curated:
            detail = f"{design_desc}证据发表于 {tier} 级期刊"
            if sig["primary_endpoint"]:
                detail += "且明确陈述主要终点"
            if sig["negative_rigorous"]:
                detail = f"严谨阴性/证伪结果（{detail}）"
            reason = f"{detail}，直接影响{problem}"
            clinical = f"阅读后可直接核对{problem}的现有依据是否需要更新"
            research = ("阴性结果可限定现有证据边界，其设计与分析可借鉴" if sig["negative_rigorous"]
                        else f"{design_desc}设计可作为同类研究的对照与方法学参照")
            if p.get("score_source") == "llm" and p.get("reason"):
                reason += f"（模型补充：{str(p['reason'])[:80]}）"
        else:
            reason = clinical = research = ""
        p["curation_signals"] = {**sig, "tier": tier}
        p["curated"] = curated
        p["curation_reason"] = reason
        p["curation_clinical_value"] = clinical
        p["curation_research_value"] = research
        n += int(curated)
    # 同刊每日限量（挪威式稀释）：量大刊不降档，但同刊一天最多 N 篇进精选，其余让位（全量库照常可查）
    cap = int(os.environ.get("CURATED_PER_JOURNAL_CAP", "2"))
    if cap > 0:
        counts: Dict[str, int] = {}
        for p in sorted((x for x in papers if x.get("curated")),
                        key=lambda x: -int(x.get("score_total", 0) or 0)):
            j = str(p.get("journal_abbr", "")) or "?"
            counts[j] = counts.get(j, 0) + 1
            if counts[j] > cap:
                p["curated"] = False
                p["curation_reason"] = (p.get("curation_reason") or "入选") + f"；同刊每日限量 {cap} 篇，本轮让位"
        n = sum(1 for x in papers if x.get("curated"))
    return n


def render_briefing_md(papers: List[Dict[str, Any]], day: str, funnel: Dict[str, int]) -> str:
    lines = [f"# 胸科雷达 ThorRadar 胸部肿瘤每日文献雷达 ({day})", ""]
    if not papers:
        lines.append("今日无过线新文献。")
        return "\n".join(lines)
    lines.append(f"漏斗：抓取 {funnel['fetched']} → 期刊索引留存 {funnel['journal_matched']} → "
                 f"预筛 {funnel['prescreened']} → 收录 {funnel['final']} 篇 → 规则精选 {funnel.get('curated', 0)} 篇")
    lines.append("")
    for i, p in enumerate(papers, 1):
        star = "⭐" if p.get("curated") else ""
        badge = f"{star}{p['journal_abbr']} · IF {p['if_val'] if p['if_val'] is not None else '—'} · 评分 {p['score_total']}"
        if p["score_source"] == "heuristic":
            badge += " · 启发式"
        verify = "✅ 核验通过" if p["critic_verified"] else ("⚠️ 未通过自动核验，解读暂停" if p["critic_verified"] is False else "— 无数值核验项")
        st = p["status"]["kind"]
        st_mark = {"retracted": "🚫 **已撤稿**", "corrected": "📄 **有更正**（影响未明）",
                   "concern": "⚠ **关注声明**"}.get(st, "")
        lines.append(f"## {i}. [{badge}] [{p['title_zh']}]({p['url']})")
        lines.append(f"- **英文原题**: *{p['title_en']}*")
        if st_mark:
            lines.append(f"- {st_mark} {p['status']['note']}{'（通知：' + p['notice_url'] + '）' if p.get('notice_url') else ''}")
        if p["publish_state"] == "full":
            if p["results"]:
                lines.append(f"- **实际结果**: {p['results']}")
            if p["authors_conclusion"]:
                lines.append(f"- **作者结论**: {p['authors_conclusion']}")
            if p["ai_note"]:
                lines.append(f"- **AI 疑点**: {p['ai_note']}")
        else:
            lines.append("- **解读暂停**（核验未通过或出版状态存疑）：仅呈现题录与链接，请以原文为准。")
        lines.append(f"- **核验状态**: {verify}")
        if p.get("curated"):
            lines.append(f"- ⭐ **规则精选**: {p['curation_reason']}")
        lines.append("")
    return "\n".join(lines)


def inject_index_html(papers: List[Dict[str, Any]], funnel: Dict[str, int], day: str) -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    if DATA_START not in html or DATA_END not in html:
        raise RuntimeError("index.html 缺少数据注入标记（DATA_START/DATA_END），拒绝盲写")
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "briefing_date": day,
        "funnel": funnel,
        "papers": papers,
    }
    block = f"{DATA_START}\n    const SITE_DATA = {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))};\n    {DATA_END}"
    new_html = re.sub(
        re.escape(DATA_START) + r".*?" + re.escape(DATA_END),
        lambda _: block, html, flags=re.S)
    if new_html == html and SITE_DATA_MARKER_STALE.search(html):
        raise RuntimeError("index.html 注入未生效，拒绝假绿")
    INDEX_HTML.write_text(new_html, encoding="utf-8")


SITE_DATA_MARKER_STALE = re.compile(r"const\s+SITE_DATA\s*=")


def build_radar_archive(days: int = 90, archive_dir: Optional[Path] = None,
                        out_path: Optional[Path] = None) -> Dict[str, Any]:
    """滚动窗档案：合并 data/archive/*.json，按 pmid 去重（新 briefing 覆盖旧），
    锚定最新 briefing_date 取近 N 天，写 data/radar_latest.json 供前端滑杆使用。"""
    adir = archive_dir or (DATA_DIR / "archive")
    by_pmid: Dict[str, Dict[str, Any]] = {}
    for f in sorted(Path(adir).glob("*.json")):
        try:
            rec = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001 旧档损坏不拖垮重建
            log(f"⚠ 日档 {Path(f).name} 损坏跳过: {e}")
            continue
        for p in rec.get("papers", []):
            pmid = str(p.get("pmid", "")).strip()
            if not pmid:
                continue
            if p.get("if_val") == 0.0:  # 旧引擎假 0 洗涤：0 不是任何真实 IF
                p["if_val"] = None
            prev = by_pmid.get(pmid)
            if prev is None or str(p.get("briefing_date", "")) >= str(prev.get("briefing_date", "")):
                by_pmid[pmid] = p
    papers = list(by_pmid.values())
    if not papers:
        log("滚动窗：无任何日档，跳过生成")
        return {}
    anchor = max(str(p.get("briefing_date", "")) for p in papers)
    cutoff = (date.fromisoformat(anchor) - timedelta(days=days - 1)).isoformat()
    window = [p for p in papers if str(p.get("briefing_date", "")) >= cutoff]
    payload = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "anchor_date": anchor,
               "window_days": days, "count": len(window), "papers": window}
    out = out_path or (DATA_DIR / "radar_latest.json")
    out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    log(f"滚动窗档案：{len(papers)} 篇去重 → 近 {days} 天 {len(window)} 篇 → {Path(out).name}")
    return payload


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="胸科雷达 ThorRadar 每日流水线")
    ap.add_argument("--days-back", type=int, default=3)
    ap.add_argument("--retmax", type=int, default=200)
    ap.add_argument("--min-final", type=int, default=3,
                    help="精评收录少于该数时自动放宽窗口到 7 天重抓一次")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--build-regression", action="store_true",
                    help="抓取地标试验真实摘要，构建/刷新工程回归集")
    ap.add_argument("--regression", action="store_true", help="跑工程回归并出报告（exit 1=有漏拦/误拦）")
    ap.add_argument("--probe-status", metavar="PMID",
                    help="对单篇真实文献做状态解析探针（验收用：喂真实撤稿/更正例）")
    ap.add_argument("--build-archive", action="store_true",
                    help="仅从 data/archive/*.json 重建 data/radar_latest.json（不打网络）")
    ap.add_argument("--mesh-backstop", type=int, metavar="DAYS", default=0,
                    help="MeSH 月度兜底模式：用 MeSH 词回扫近 N 天，减去见过账本后走全下游；日档写 {日}-mesh.json")
    args = ap.parse_args(argv)

    if args.self_test:
        return run_self_test()
    if args.build_regression:
        return build_regression_set(Collector()) or 0
    if args.regression:
        return run_regression()
    if args.probe_status:
        arts = Collector().efetch_articles([args.probe_status])
        if not arts:
            log("未取到该 PMID")
            return 1
        st = arts[0]["status"]
        log(f"PMID {args.probe_status} 状态解析: {json.dumps(st, ensure_ascii=False)}")
        log(f"标题: {arts[0]['title_en'][:100]}")
        return 0
    if args.build_archive:
        build_radar_archive(90)
        return 0

    day = date.today().isoformat()
    llm = LLMClient()
    mode = "LLM" if llm.available else "启发式（无 LLM_API_KEY）"
    log(f"胸科雷达流水线启动 · 模式={mode}")

    collector = Collector()
    cfg = json.loads(JOURNALS_FILE.read_text(encoding="utf-8"))
    jm = JournalMatcher(cfg)

    days_back = args.days_back
    mesh_mode = bool(args.mesh_backstop)

    def _collect_mesh(dback: int):
        """MeSH 兜底采集：六主题词并集（分页抓全）。去重交给下游见过账本/跨天去重。"""
        merged: List[str] = []
        for term in MESH_BACKSTOP_TERMS:
            ids = collector.esearch_pmids(dback, 500, query=f'"{term}"[Mesh]', hard_cap=10000)
            log(f"MeSH {term}: {len(ids)}")
            merged.extend(ids)
        return list(dict.fromkeys(merged))

    def _collect(dback: int):
        """双路采集：目录路（340 刊全收）＋ 检索式路（字典外世界）→ 合并去重。"""
        toc_pmids, toc_counts = collector.fetch_journal_toc(cfg.get("journals", []), dback)
        health = update_journal_health(toc_counts)
        q_pmids = collector.esearch_pmids(dback, args.retmax)
        merged = list(dict.fromkeys(toc_pmids + q_pmids))   # TOC 保序在前，PMID 去重
        return toc_pmids, q_pmids, merged, health

    if mesh_mode:
        days_back = args.mesh_backstop
        log(f"MeSH 兜底模式：六主题词回扫近 {days_back} 天…")
        mesh_pmids = _collect_mesh(days_back)
        toc_pmids: List[str] = []
        q_pmids = mesh_pmids
        pmids = mesh_pmids
        health = {"red": [], "yellow": [], "green": 0, "total": 0}
        seen = load_seen()
        pmids = [p for p in pmids if p not in seen]
        log(f"见过账本去重后待处理 {len(pmids)} 篇")
        funnel = {"toc_fetched": 0, "query_fetched": len(mesh_pmids), "mesh_mode": True,
                  "fetched": len(pmids), "journal_matched": 0, "prescreened": 0,
                  "final": 0, "curated": 0}
    else:
        log("目录路：逐刊扫描中…")
        toc_pmids, q_pmids, pmids, health = _collect(days_back)
        seen = load_seen()
        pmids = [p for p in pmids if p not in seen]
        if len(pmids) < len(toc_pmids) + len(q_pmids):
            log(f"见过账本：去掉近 {SEEN_LEDGER_DAYS} 天已检查 "
                f"{len(toc_pmids) + len(q_pmids) - len(pmids)} 篇（不重看，防重复税）")
        if len(pmids) < args.min_final and days_back < 7:
            log(f"近 {days_back} 天仅 {len(pmids)} 篇，放宽窗口到 7 天重抓")
            days_back = 7
            toc_pmids, q_pmids, merged, health = _collect(days_back)
            pmids = [p for p in merged if p not in seen]
        funnel = {"toc_fetched": len(toc_pmids), "query_fetched": len(q_pmids),
                  "fetched": len(pmids), "journal_matched": 0, "prescreened": 0,
                  "final": 0, "curated": 0}
        log(f"采集：目录路 {len(toc_pmids)} ＋ 检索式路 {len(q_pmids)} → 合并 {len(pmids)} 篇"
            f"（crdt 近 {days_back} 天｜目录健康 红{len(health['red'])}/黄{len(health['yellow'])}）")

    articles = collector.efetch_articles(pmids)
    log(f"EFetch 解析成功 {len(articles)} 篇")

    # 去重 + 粗筛 + 通知类排除 + 跨天去重（近 N 天已上过日报的不重发）
    first_seen, articles_clean = set(), []
    n_notice = 0
    for a in articles:
        if not (a["pmid"] and a["title_en"] and a["abstract_en"]):
            continue
        if a["pmid"] in first_seen:
            continue
        first_seen.add(a["pmid"])
        if a["status"]["kind"] == "notice":
            n_notice += 1          # 撤稿/更正/关注声明通知本身不作为研究文献收录
            continue
        articles_clean.append(a)
    if n_notice:
        log(f"排除通知类文献（撤稿/更正/关注声明通知本身）{n_notice} 篇")

    recent_seen = set()
    for back in range(1, days_back):
        prev = (date.today() - timedelta(days=back)).isoformat()
        prev_file = DATA_DIR / "archive" / f"{prev}.json"
        if prev_file.exists():
            try:
                for p in json.loads(prev_file.read_text(encoding="utf-8")).get("papers", []):
                    recent_seen.add(p.get("pmid", ""))
            except Exception as e:  # noqa: BLE001 旧档损坏不拖垮今日运行
                log(f"⚠ 旧日档 {prev} 读取失败（跳过去重）: {e}")
    before_dedup = len(articles_clean)
    articles_clean = [a for a in articles_clean if a["pmid"] not in recent_seen]
    log(f"跨天去重：排除近 {days_back - 1} 天已收录 {before_dedup - len(articles_clean)} 篇")

    # 期刊五重索引：S/A 白名单豁免直接保留；未命中且无摘要不收录
    stage_journal = []
    for a in articles_clean:
        m = jm.match(a["p_issn"], a["e_issn"], a["issn_linking"], a["nlm_id"],
                     a["iso_abbr"], a["journal_title"])
        if m["whitelist_exempt"] or a["abstract_en"]:
            a["_match"] = m
            stage_journal.append(a)
    funnel["journal_matched"] = len(stage_journal)
    log(f"期刊索引阶段留存 {len(stage_journal)} 篇")

    # 预筛
    if llm.available:
        prescreened = llm_prescreen(llm, stage_journal)
    else:
        prescreened = heuristic_prescreen(stage_journal)
    funnel["prescreened"] = len(prescreened)
    log(f"预筛通过 {len(prescreened)} 篇")

    # 精评 + 核验（核验异常 → fail-closed 降级，不崩运行）；并行 4 线程
    # 名额按档位排序分配（S>A>B>C，同档按新到旧）：MeSH 月扫实测预筛留存远超硬顶时，
    # 让最重要的文章优先被 AI 读懂；超顶者启发式兜底（分数照有、来源诚实标注）。
    _TIER_RANK = {"S": 0, "A": 1, "B": 2, "C": 3}
    prescreened = sorted(prescreened,
                         key=lambda a: _TIER_RANK.get(a["_match"].get("tier", "B"), 2))
    # 硬顶 200：双路架构下每日新见约 140 篇；顶住只防失控，靠预算熔断守成本。
    SCORE_HARD_CAP = 200
    if len(prescreened) > SCORE_HARD_CAP:
        log(f"⚠ 预筛留存 {len(prescreened)} 超精评硬顶 {SCORE_HARD_CAP}，只精评前 "
            f"{SCORE_HARD_CAP} 篇（疑似检索式过宽，人工看板跟进）")

    def _score_one(a: Dict[str, Any]) -> Dict[str, Any]:
        m = a["_match"]
        try:
            if llm.available:
                llm_data = llm_score_one(llm, a, m)
                total = (int(llm_data.get("score_clinical", 0)) + int(llm_data.get("score_methodology", 0))
                         + int(llm_data.get("score_specialty", 0)) + m["journal_bonus"])
                scored = {"llm": llm_data, "match": m, "score_total": total, "score_source": "llm"}
            else:
                scored = heuristic_score(a, jm)
                scored["match"] = m  # 统一用主流程已算的匹配
        except BudgetExceeded as e:
            log(f"⚠ 成本熔断触发，剩余文献按启发式补齐: {e}")
            llm.key = ""
            scored = heuristic_score(a, jm)
            scored["match"] = m
        except Exception as e:  # noqa: BLE001 单篇精评失败→启发式兜底，不弃文献
            log(f"  精评失败转启发式 (pmid {a['pmid']}): {e}")
            scored = heuristic_score(a, jm)
            scored["match"] = m

        llm_data = scored["llm"]
        verify_error = ""
        verdict: Optional[Dict[str, Any]] = None
        try:
            verdict = FourTupleVerifier.verify(
                a["abstract_en"],
                " ".join(filter(None, [llm_data.get("results", ""), llm_data.get("authors_conclusion", "")])),
                llm_data.get("tuples", []))
            # 语义核验（规则版）：任一 tuple 人群限定/终点指标对不上 → fail-closed 并入 passed
            sem = SemanticChecker.check(a["abstract_en"], llm_data.get("tuples", []))
            verdict["semantic"] = sem
            if llm_data.get("tuples") and not sem["passed"]:
                verdict["passed"] = False
                log(f"  ⚠ 语义核验未通过 (pmid {a['pmid']}): {sem['tuple_audit'][0]['mismatch_reasons']}")
        except Exception as e:  # noqa: BLE001 核验器自身异常 → 按「无法确认」处理
            verify_error = f"verifier-error: {e}"
            log(f"  ⚠ 核验器异常 (pmid {a['pmid']})，本篇降级: {e}")
        return build_paper(a, scored, verdict, verify_error)

    with ThreadPoolExecutor(max_workers=4) as ex:
        papers = list(ex.map(_score_one, prescreened[:SCORE_HARD_CAP]))
    papers.sort(key=lambda p: p["score_total"], reverse=True)
    funnel["final"] = len(papers)
    funnel["curated"] = apply_curation(papers)
    log(f"收录 {len(papers)} 篇（降级 {sum(1 for p in papers if p['publish_state'] == 'degraded')} 篇 · "
        f"规则精选 {funnel['curated']} 篇）"
        f" · LLM 成本 ${llm.cost_usd:.3f}（{llm.calls} 次调用）")

    # 出版状态覆盖层：回查到期文献 → 登记今日文献 → 落盘（日档不动）
    status_db = load_status_db()
    try:
        recheck_stale_statuses(collector, status_db)
    except Exception as e:  # noqa: BLE001 回查整体失败不阻断主流程
        log(f"⚠ 状态回查异常（跳过）: {e}")
    upsert_today_status(status_db, papers)
    save_status_db(status_db)

    # 产出三件：日档（当日冷存，当日重跑可覆写，隔日不回改）／早报 md／index 注入
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "archive").mkdir(exist_ok=True)
    (DATA_DIR / f"daily_briefing_{day}.md").write_text(
        render_briefing_md(papers, day, funnel), encoding="utf-8")
    arch_name = f"{day}-mesh.json" if mesh_mode else f"{day}.json"
    (DATA_DIR / "archive" / arch_name).write_text(
        json.dumps({"briefing_date": day, "mode": ("mesh-" if mesh_mode else "")
                    + ("llm" if llm.available else "heuristic"),
                    "funnel": funnel, "papers": papers}, ensure_ascii=False), encoding="utf-8")
    if mesh_mode:
        (DATA_DIR / "mesh_backstop_report.json").write_text(
            json.dumps({"briefing_date": day, "window_days": days_back,
                        "mesh_hits": funnel["query_fetched"], "after_seen": funnel["fetched"],
                        "journal_matched": funnel["journal_matched"],
                        "prescreened": funnel["prescreened"], "final": funnel["final"],
                        "curated": funnel["curated"],
                        "llm_cost_usd": round(llm.cost_usd, 4)}, ensure_ascii=False),
            encoding="utf-8")
        log(f"MeSH 兜底报告：data/mesh_backstop_report.json")
    inject_index_html(papers, funnel, day)
    build_radar_archive(90)

    # 见过账本落盘：凡「有效检查过」的都记账；无摘要且非豁免的明天再查（摘要可能后补）
    seen_set = {a["pmid"] for a in articles if a["abstract_en"]}
    seen_set |= {a["pmid"] for a in stage_journal if not a.get("abstract_en")}
    today_iso = date.today().isoformat()
    for p in seen_set:
        seen[p] = today_iso
    save_seen(seen)
    log(f"见过账本：累计 {len(seen)} 条（滚动 {SEEN_LEDGER_DAYS} 天）")
    log(f"产出完成：archive/{day}.json / daily_briefing_{day}.md / index.html / radar_latest.json / status.json")
    return 0


# ============================================================================
# 6a'. 影子通道（乙案）已于 2026-10-18 退役——被目录路取代，测量使命完成。
#      data/shadow/*.json 留档备查；复算脚本与回测工具在 D:\tmp（离线）。
# ============================================================================


# ============================================================================
# 6b. 工程回归集（测管线漂移；非医学准确率金标准——预期依据＝摘要原文本身）
# ============================================================================

REG_DIR = DATA_DIR / "regression"
# 地标试验名单（构建时按名抓取真实摘要并冻结；名单可增删）
LANDMARK_QUERIES = [
    "CheckMate-816 nivolumab", "KEYNOTE-671 pembrolizumab", "LAURA osimertinib stage III",
    "ADRIATIC durvalumab small-cell", "ESOPEC FLOT CROSS", "NADIM neoadjuvant",
    "PACIFIC durvalumab", "CheckMate-77T", "RATIONALE-315", "ADJUVANT/BR31 adjuvant",
    "CCTG BR.19 adjuvant", "ANVIL nivolumab resectable", "SAPT thoracic",
    "JCOG0802 segmentectomy", "CALGB 140503 sublobar", "AMOLET wedge",
    "NELSON lung cancer screening", "PLCO screening", "MILD trial screening",
    "Chinese GGN antibiotic", "Fleischner nodule", "Lung-RADS",
    "TAERforce tubeless", "tubeless VATS randomized", "non-intubated thoracic",
    "RATS lobectomy randomized", "robotic versus thoracoscopic",
    "ADURA osimertinib", "ALCHEMIST adjuvant", "IMpower010 adjuvant",
]


# 语义变造素材：候选限定词/指标（命名与 SemanticChecker 词典兼容，保证可被核验器解析）。
# correct 样例取「第一个在摘要出现的」；变造样例取「第一个在摘要缺席的」——生成用独立字符串扫描，
# 不经过 SemanticChecker（防循环论证：生成与判定解耦，判定的误拦/漏拦才是真数字）。
SEMANTIC_MUTATION_QUALIFIERS = [
    ("PD-L1 阳性人群", ["pd-l1", "pd l1"]),
    ("ctDNA 阳性人群", ["ctdna", "circulating tumor dna", "circulating tumour dna"]),
    ("脑转移人群", ["brain metast", "cns metast"]),
    ("鳞癌人群", ["squamous"]),
    ("老年人群", ["elderly", "older"]),
    ("EGFR 突变人群", ["egfr"]),
    ("全人群", ["all patients", "entire cohort", "all randomized", "overall population"]),
    # 保底档（外科/筛查类摘要常有具体限定词全缺席）：无锚通用人群，仅撑起指标断言
    ("患者人群", []),
]
SEMANTIC_MUTATION_METRICS = [
    ("主要终点 ORR", ["objective response", "response rate", "orr"]),
    ("无进展生存 PFS", ["progression-free", "progression free", "pfs"]),
    ("病理完全缓解率 pCR", ["pathological complete response", "pcr"]),
    ("总生存", ["overall survival", "survival"]),
    ("严重不良事件", ["adverse event", "toxicity"]),
    ("缓解持续时间 DOR", ["duration of response"]),
]


def _group_verifiable(abstract_low: str, group: str) -> bool:
    """生成端存在性扫描：group 的每个可核限定词（按判定端同源词典展开）都有锚命中。空锚限定词视作通过。"""
    for q in SemanticChecker._qualifiers_of(group, SEMANTIC_QUALIFIER_ANCHORS):
        if q["anchors"] and not any(SemanticChecker._hit(abstract_low, a) for a in q["anchors"]):
            return False
    return True


def _group_unverifiable(abstract_low: str, group: str) -> bool:
    """生成端缺席扫描：存在至少一个可核限定词完全落空（判定端必拦）。"""
    for q in SemanticChecker._qualifiers_of(group, SEMANTIC_QUALIFIER_ANCHORS):
        if q["anchors"] and not any(SemanticChecker._hit(abstract_low, a) for a in q["anchors"]):
            return True
    return False


def generate_semantic_case_parts(abstract_en: str, numbers: List[str]) -> Dict[str, Any]:
    """为一个冻结摘要生成：正确语义 tuple（应放行）＋人群偷换/终点偷换变造（应拦截）。可能部分缺省。
    存在性扫描用与判定端同源的锚词推导（_qualifiers_of/metric_anchors），但不调用判卷本身——
    判定的误拦/漏拦仍是独立数字。"""
    low = abstract_en.lower()
    num = numbers[0] if numbers else ""
    pres_q = next((q for q in SEMANTIC_MUTATION_QUALIFIERS if _group_verifiable(low, q[0])), None)
    abs_q = next((q for q in SEMANTIC_MUTATION_QUALIFIERS if _group_unverifiable(low, q[0])), None)
    pres_m = next((m for m in SEMANTIC_MUTATION_METRICS
                   if SemanticChecker.metric_anchors(m[0])
                   and any(SemanticChecker._hit(low, a) for a in SemanticChecker.metric_anchors(m[0]))), None)
    abs_m = next((m for m in SEMANTIC_MUTATION_METRICS
                  if SemanticChecker.metric_anchors(m[0])
                  and not any(SemanticChecker._hit(low, a) for a in SemanticChecker.metric_anchors(m[0]))), None)

    correct = None
    if pres_q and pres_m and num:
        correct = {"group": pres_q[0], "metric": pres_m[0], "val": num, "stat": "",
                   "note": f"限定词「{pres_q[0]}」与指标「{pres_m[0]}」均在原摘要出现（独立扫描确认）"}
    mutations = []
    if abs_q and pres_m and num:
        mutations.append({"kind": "population_swap", "layer": "semantic",
                          "group": abs_q[0], "metric": pres_m[0], "val": num, "stat": "",
                          "expect": "block",
                          "note": f"把全人群结果安到摘要未出现的限定人群「{abs_q[0]}」（数值真实存在，数值层对此失明）"})
    if abs_m and num:
        mutations.append({"kind": "endpoint_swap", "layer": "semantic",
                          "group": pres_q[0] if pres_q else "", "metric": abs_m[0], "val": num,
                          "stat": "", "expect": "block",
                          "note": f"把该数值标为摘要中不存在的终点「{abs_m[0]}」（数值真实存在，数值层对此失明）"})
    return {"correct_tuple": correct, "semantic_mutations": mutations}


def build_regression_set(collector: "Collector", n_target: int = 30) -> None:
    """抓真实地标试验摘要并冻结；预期数值与变造样例均机械生成（依据=摘要原文）。"""
    import random
    rng = random.Random(20261017)
    cases = []
    for q in LANDMARK_QUERIES:
        if len(cases) >= n_target:
            break
        params = {"db": "pubmed", "term": f"{q}[Title/Abstract]", "retmax": "3",
                  "retmode": "json", "sort": "relevance"}
        if collector.api_key:
            params["api_key"] = collector.api_key
        url = f"{collector.EUTILS}/esearch.fcgi?{urllib.parse.urlencode(params)}"
        try:
            ids = json.loads(collector._get(url).decode("utf-8")).get("esearchresult", {}).get("idlist", [])
        except Exception:  # noqa: BLE001 单条查询失败跳过
            continue
        for pmid in ids:
            arts = collector.efetch_articles([pmid])
            if not arts or not arts[0]["abstract_en"] or len(arts[0]["abstract_en"]) < 400:
                continue
            a = arts[0]
            if a["status"]["kind"] != "ok":
                continue  # 状态异常的不进回归集
            nums = FourTupleVerifier._norm_numbers(a["abstract_en"])[:6]
            if len(nums) < 3:
                continue
            mutations = []
            for n in nums[:2]:
                bad = _mutate_number(n, rng, a["abstract_en"])
                if bad:
                    mutations.append({"kind": "number_fabricated", "orig": n, "bad": bad,
                                      "summary": f"结果为 {bad}（{a['title_en'][:40]}…）",
                                      "expect": "block"})
            sem_parts = generate_semantic_case_parts(a["abstract_en"], nums)
            mutations.extend(sem_parts["semantic_mutations"])
            cases.append({
                "id": f"reg_{pmid}", "pmid": pmid, "title": a["title_en"],
                "abstract": a["abstract_en"], "basis": "摘要原文（冻结于构建时点）",
                "expected_numbers": nums,
                "correct_summary": f"研究纳入 {nums[0]} 例，关键结果数值包括 {'、'.join(nums[:4])}。",
                "correct_tuples": [sem_parts["correct_tuple"]] if sem_parts["correct_tuple"] else [],
                "mutations": mutations,
                "frozen_at": date.today().isoformat(),
            })
            break
    REG_DIR.mkdir(parents=True, exist_ok=True)
    (REG_DIR / "cases.json").write_text(
        json.dumps({"generated_at": datetime.now().isoformat(), "cases": cases},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"回归集构建完成：{len(cases)} 例（含数值变造 {sum(len(c['mutations']) for c in cases)} 条）")


def _mutate_number(n: str, rng: "random.Random", abstract: str = "") -> str:
    """机械变造一个数值；若变造值仍按词边界出现在原文（撞车）则重试，仍撞则放弃该条。"""
    core = n.rstrip("%")
    pct = n.endswith("%")
    for _ in range(8):
        try:
            if "." in core:
                head, tail = core.split(".")
                bad_core = head + "." + str((int(tail[0]) + rng.randint(1, 9)) % 10) + tail[1:]
            else:
                bad_core = str(int(core) + rng.randint(3, 19))
        except ValueError:
            return ""
        bad = bad_core + ("%" if pct else "")
        if bad in FourTupleVerifier.ALLOWLIST:
            continue  # 撞结构白名单（如 95% CI）的变造值无测试意义
        if not abstract or not FourTupleVerifier._num_bound_regex(bad_core).search(abstract.replace(",", "")):
            return bad
    return ""


def run_regression() -> int:
    """跑工程回归：数值层（正确放行/变造拦截）＋语义层（正确 tuple 放行、人群/终点偷换拦截）。"""
    set_file = REG_DIR / "cases.json"
    if not set_file.exists():
        log("回归集不存在，先跑 --build-regression")
        return 2
    cases = json.loads(set_file.read_text(encoding="utf-8"))["cases"]
    n_cases = n_correct = n_false_block = n_block_mut = n_blocked = n_missed = 0
    missed_detail = []
    n_sem_tuples = n_sem_false_block = n_sem_mut = n_sem_blocked = n_sem_missed = n_numeric_blind = 0
    sem_missed_detail = []
    for c in cases:
        n_cases += 1
        v_good = FourTupleVerifier.verify(c["abstract"], c["correct_summary"], [])
        if v_good["passed"]:
            n_correct += 1
        else:
            n_false_block += 1
        for mut in c["mutations"]:
            if mut.get("layer") == "semantic":
                # 语义层：先证数值层对该变造失明（真数值+假限定），再验语义层拦截
                n_sem_mut += 1
                tup = {"group": mut["group"], "metric": mut["metric"],
                       "val": mut["val"], "stat": mut.get("stat", "")}
                v_num = FourTupleVerifier.verify(c["abstract"], "", [tup])
                if v_num["passed"]:
                    n_numeric_blind += 1
                sem = SemanticChecker.check(c["abstract"], [tup])
                if sem["passed"]:
                    n_sem_missed += 1
                    sem_missed_detail.append({"case": c["id"], "kind": mut["kind"],
                                              "group": mut["group"], "metric": mut["metric"]})
                else:
                    n_sem_blocked += 1
                continue
            if mut["expect"] == "semantic_pending":
                continue      # 兼容旧版占位条目（已迁移，理论上不再出现）
            n_block_mut += 1
            v_bad = FourTupleVerifier.verify(c["abstract"], mut["summary"], [])
            if not v_bad["passed"]:
                n_blocked += 1
            else:
                n_missed += 1
                missed_detail.append({"case": c["id"], "kind": mut["kind"], "bad": mut.get("bad")})
        for t in c.get("correct_tuples", []):
            # 语义层正确样例应放行（生成时经独立字符串扫描确认锚在摘要内；判定走核验器本身）
            n_sem_tuples += 1
            sem = SemanticChecker.check(c["abstract"], [t])
            if not sem["passed"]:
                n_sem_false_block += 1
    sem_false_rate = round(n_sem_false_block / n_sem_tuples, 4) if n_sem_tuples else None
    report = {
        "generated_at": datetime.now().isoformat(),
        "n_cases": n_cases,
        "correct_samples": {"n": n_cases, "passed": n_correct, "false_blocks": n_false_block},
        "number_mutations": {"n": n_block_mut, "blocked": n_blocked, "missed": n_missed,
                             "missed_detail": missed_detail},
        "semantic_layer": {
            "checker": "semantic-rules-v1（词面级：人群限定词/终点指标词须在原摘要命中；词典未收录词宁误杀）",
            "correct_tuples": {"n": n_sem_tuples, "false_blocks": n_sem_false_block,
                               "false_block_rate": sem_false_rate},
            "mutations": {"n": n_sem_mut, "blocked": n_sem_blocked, "missed": n_sem_missed,
                          "missed_detail": sem_missed_detail},
            "numeric_blind_confirmed": n_numeric_blind,
            "note": "numeric_blind_confirmed＝数值层放行而语义层拦截的变造数（语义层的增量价值）",
        },
        "verifier": "deterministic-text-v2 + semantic-rules-v1",
    }
    REG_DIR.mkdir(parents=True, exist_ok=True)
    (REG_DIR / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    log(f"回归完成：正确样例 {n_correct}/{n_cases} 放行（误拦 {n_false_block}）· "
        f"数值变造拦截 {n_blocked}/{n_block_mut}（漏拦 {n_missed}）· "
        f"语义变造拦截 {n_sem_blocked}/{n_sem_mut}（漏拦 {n_sem_missed} · 正确 tuple 误拦 {n_sem_false_block}/{n_sem_tuples}）· "
        f"数值层对语义变造失明 {n_numeric_blind}")
    return 0 if (n_false_block == 0 and n_missed == 0 and n_cases >= 20
                 and n_sem_missed == 0 and n_sem_false_block == 0) else 1


# ============================================================================
# 7. 自测
# ============================================================================

def run_self_test() -> int:
    log("=== 胸科雷达引擎自测 ===")
    jm = JournalMatcher(json.loads(JOURNALS_FILE.read_text(encoding="utf-8")))
    m_nejm = jm.match(e_issn="1533-4406")
    assert m_nejm["matched"] and m_nejm["tier"] == "S" and m_nejm["whitelist_exempt"]
    m_jtcvs = jm.match(nlm_id="0376343")
    assert m_jtcvs["matched"] and m_jtcvs["tier"] == "A"
    log(f"[PASS] 1/8 期刊五重索引: NEJM={m_nejm['tier']} JTCVS={m_jtcvs['tier']}")

    c = Collector()
    params = urllib.parse.urlparse(c.esearch_url_probe())
    q = urllib.parse.parse_qs(params.query)
    assert q["datetype"] == ["crdt"] and "reldate" in q
    log("[PASS] 2/8 ESearch 参数: datetype=crdt + reldate")

    abstract = ("A total of 358 patients were assigned to nivolumab plus chemotherapy (179 patients) "
                "or chemotherapy alone (179 patients). Hazard ratio for death, 0.72; 95% CI, 0.523 to 0.998; "
                "P = 0.048. At a median follow-up of 68.4 months, the 5-year overall survival was 65.4% "
                "with nivolumab plus chemotherapy and 55.0% with chemotherapy alone.")
    good_tuples = [{"group": "ITT (N=358)", "metric": "5年 OS & HR",
                    "val": "65.4% vs 55.0%; HR 0.72", "stat": "95% CI 0.523-0.998; P=0.048"}]
    v_good = FourTupleVerifier.verify(abstract, "5 年 OS 率为 65.4% vs 55.0%（HR 0.72）。", good_tuples)
    assert v_good["passed"], v_good
    bad_tuples = [{"group": "ITT (N=358)", "metric": "5年 OS", "val": "88.9%", "stat": ""}]
    v_bad = FourTupleVerifier.verify(abstract, "5 年 OS 率高达 88.9%。", bad_tuples)
    assert not v_bad["passed"] and "88.9" in "".join(v_bad["ungrounded_numbers"])
    log(f"[PASS] 3/8 数值核验器: 真值放行 {v_good['tuple_audit'][0]['checks'][0]['note']} / 幻觉拦截 {v_bad['ungrounded_numbers']}")

    html_probe = f"<div>{DATA_START}const SITE_DATA = {{}};{DATA_END}</div>"
    assert DATA_START in html_probe and DATA_END in html_probe
    log("[PASS] 4/8 注入标记约定成立")

    # 5. 出版状态解析（结构单元用例；真实端到端走 --probe-status）
    xml_retracted = (
        '<PubmedArticle><MedlineCitation><PMID>1</PMID><Article><ArticleTitle>t</ArticleTitle>'
        '<PublicationTypeList><PublicationType>Retracted Publication</PublicationType></PublicationTypeList>'
        '</Article><CommentsCorrectionsList><CommentsCorrections RefType="RetractedIn">'
        '<PMID>2</PMID><RefSource>Retraction notice</RefSource></CommentsCorrections>'
        '</CommentsCorrectionsList></MedlineCitation></PubmedArticle>')
    st = Collector.parse_status(ET.fromstring(xml_retracted))
    assert st["kind"] == "retracted" and st["notice_pmid"] == "2"
    xml_notice = xml_retracted.replace("Retracted Publication", "Retraction of Publication") \
        .replace('RefType="RetractedIn"', 'RefType="RetractionOf"')
    assert Collector.parse_status(ET.fromstring(xml_notice))["kind"] == "notice"
    xml_plain = '<PubmedArticle><MedlineCitation><PMID>1</PMID><Article><ArticleTitle>t</ArticleTitle></Article></MedlineCitation></PubmedArticle>'
    assert Collector.parse_status(ET.fromstring(xml_plain))["kind"] == "ok"
    log("[PASS] 5/8 出版状态解析：retracted/notice/ok 三态")

    # 6. 失败降级：核验异常 → publish_state=degraded（不崩、不发布解读）
    a_deg = {"pmid": "9", "title_en": "t", "abstract_en": "abs", "authors": "x",
             "p_issn": "", "e_issn": "", "issn_linking": "", "nlm_id": "",
             "iso_abbr": "", "journal_title": "",
             "affiliations": "", "pub_date": "", "doi": "", "pmcid": "", "nct_id": "",
             "status": {"kind": "ok", "notice_pmid": "", "notice_ref": "", "impact_known": True, "note": ""}}
    m_deg = jm.match()
    scored_deg = heuristic_score(a_deg, jm)
    p_deg = build_paper(a_deg, scored_deg, None, verify_error="verifier-error: chaos")
    assert p_deg["publish_state"] == "degraded" and p_deg["critic_verified"] is False
    a_ret = dict(a_deg, status={"kind": "retracted", "notice_pmid": "2", "notice_ref": "n",
                                "impact_known": True, "note": "x"})
    p_ret = build_paper(a_ret, scored_deg, None, "")
    assert p_ret["publish_state"] == "degraded"
    log("[PASS] 6/8 失败降级：核验异常/撤稿 → 仅题录+链接，解读暂停")

    # 7. 语义核验（规则版）：限定词/指标均在摘要 → 放行；人群偷换 → 拦截并 fail-closed 降级
    sem_abs = ("All patients were enrolled on an intent-to-treat basis. "
               "The primary endpoint was overall survival. Pathological complete response (pCR) "
               "was achieved in 30.4% of patients, and the 5-year overall survival was 65.4%. "
               "No patients had brain metastases at baseline.")
    v_sem_good = SemanticChecker.check(sem_abs, [
        {"group": "ITT 人群", "metric": "总生存", "val": "65.4%", "stat": ""}])
    assert v_sem_good["passed"], v_sem_good
    v_sem_pop = SemanticChecker.check(sem_abs, [
        {"group": "ctDNA 阳性人群", "metric": "总生存", "val": "65.4%", "stat": ""}])
    assert not v_sem_pop["passed"] and any("ctDNA" in r for r in v_sem_pop["tuple_audit"][0]["mismatch_reasons"]), v_sem_pop
    v_sem_metric = SemanticChecker.check(sem_abs, [
        {"group": "ITT 人群", "metric": "客观缓解率", "val": "65.4%", "stat": ""}])
    assert not v_sem_metric["passed"], v_sem_metric
    # fail-closed 贯通：数值层放行（数字真实）但语义层拦截 → publish_state=degraded
    a_sem = dict(a_deg, abstract_en=sem_abs,
                 title_en="Randomized trial of perioperative therapy")
    sd_sem = heuristic_score(a_sem, jm)
    sd_sem["llm"]["tuples"] = [{"group": "ctDNA 阳性人群", "metric": "总生存", "val": "65.4%", "stat": ""}]
    verdict_sem = FourTupleVerifier.verify(sem_abs, "", sd_sem["llm"]["tuples"])
    assert verdict_sem["passed"], verdict_sem        # 数值层确实放行（真数值）
    verdict_sem["semantic"] = SemanticChecker.check(sem_abs, sd_sem["llm"]["tuples"])
    verdict_sem["passed"] = verdict_sem["passed"] and verdict_sem["semantic"]["passed"]
    p_sem = build_paper(a_sem, sd_sem, verdict_sem, "")
    assert p_sem["publish_state"] == "degraded" and p_sem["semantic_passed"] is False
    log("[PASS] 7/8 语义核验（规则版）：真 tuple 放行 / 人群偷换·指标错配拦截 / fail-closed 降级")

    # 8. 规则精选：S 级 RCT 入选；个案+回顾性 B 级不入（不凑数）；固定场景套件＝tests/test_curation.py
    p_rct = build_paper(dict(a_sem, pmid="10", e_issn="1533-4406"), heuristic_score(a_sem, jm), None, "")
    p_rct["tier"] = "S"
    p_case = build_paper(dict(a_deg, pmid="11", title_en="Case report of an unusual thoracic tumor"),
                         heuristic_score(a_deg, jm), None, "")
    n_cur = apply_curation([p_rct, p_case])
    assert p_rct["curated"] and p_case["curated"] is False and n_cur == 1, (p_rct["curated"], n_cur)
    assert "直接影响" in p_rct["curation_reason"] and p_rct["curation_reason"]
    assert p_case["curation_reason"] == ""
    log("[PASS] 8/8 规则精选：S 级 RCT 入选·个案不凑数·理由落到具体问题")
    log("=== 自测全部通过 ===")
    return 0


def esearch_url_probe(self) -> str:  # type: ignore[misc]
    """供自测检查参数拼装（不发起网络请求）。"""
    params = {"db": "pubmed", "term": DEFAULT_QUERY, "datetype": "crdt",
              "reldate": "2", "retmode": "json"}
    if self.api_key:
        params["api_key"] = self.api_key
    return f"{self.EUTILS}/esearch.fcgi?{urllib.parse.urlencode(params)}"


Collector.esearch_url_probe = esearch_url_probe  # type: ignore[attr-defined]


if __name__ == "__main__":
    sys.exit(main())
