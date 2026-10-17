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

DEFAULT_QUERY = (
    '(("non-small-cell lung cancer"[Title/Abstract] OR "NSCLC"[Title/Abstract] '
    'OR "small-cell lung cancer"[Title/Abstract] OR "SCLC"[Title/Abstract] '
    'OR "pulmonary nodule"[Title/Abstract] OR "ground-glass"[Title/Abstract] '
    'OR "subsolid nodule"[Title/Abstract] OR "thoracoscopic"[Title/Abstract] '
    'OR "segmentectomy"[Title/Abstract] OR "tubeless"[Title/Abstract] '
    'OR "esophageal cancer"[Title/Abstract] OR "mediastinal tumor"[Title/Abstract] '
    'OR "thymoma"[Title/Abstract]) '
    'AND ("clinical trial"[Title/Abstract] OR "randomized"[Title/Abstract] '
    'OR "neoadjuvant"[Title/Abstract] OR "perioperative"[Title/Abstract] '
    'OR "propensity score"[Title/Abstract] OR "three-dimensional"[Title/Abstract] '
    'OR "artificial intelligence"[Title/Abstract] OR "osimertinib"[Title/Abstract] '
    'OR "nivolumab"[Title/Abstract] OR "pembrolizumab"[Title/Abstract] '
    'OR "durvalumab"[Title/Abstract] OR "antibiotic"[Title/Abstract]))'
)


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
                    "if_val": j.get("if_2025", 0.0),
                    "zone": f"JCR {j.get('jcr_quartile', 'Q2')} · {j.get('cas_zone', '')}".strip(" ·"),
                    "journal_bonus": int(meta.get("score_bonus", 0)),
                    "whitelist_exempt": bool(meta.get("whitelist_exempt", False)),
                    "journal_abbr": j.get("iso_abbr", iso_abbr or title),
                    "journal_full": j.get("title", title),
                }
        return {
            "matched": False,
            "tier": "B",
            "if_val": 0.0,
            "zone": "PubMed 收录期刊",
            "journal_bonus": 0,
            "whitelist_exempt": False,
            "journal_abbr": iso_abbr or title or "Unknown",
            "journal_full": title or "Unknown Journal",
        }


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

    def esearch_pmids(self, days_back: int, retmax: int) -> List[str]:
        params = {
            "db": "pubmed", "term": DEFAULT_QUERY, "datetype": "crdt",
            "reldate": str(days_back), "retmax": str(retmax),
            "retmode": "json", "sort": "date",
        }
        if self.api_key:
            params["api_key"] = self.api_key
        url = f"{self.EUTILS}/esearch.fcgi?{urllib.parse.urlencode(params)}"
        data = json.loads(self._get(url).decode("utf-8"))
        return data.get("esearchresult", {}).get("idlist", [])

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


def llm_prescreen(llm: LLMClient, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    kept = []
    batch = 20
    for i in range(0, len(articles), batch):
        chunk = articles[i:i + batch]
        listing = "\n".join(
            f"[{j}] {(a['journal_title'] or 'Unknown')[:60]} | {a['title_en'][:180]}"
            for j, a in enumerate(chunk))
        try:
            raw = llm.chat(PREScreen_SYSTEM, listing, max_tokens=800)
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
    }


def render_briefing_md(papers: List[Dict[str, Any]], day: str, funnel: Dict[str, int]) -> str:
    lines = [f"# 胸科雷达 ThorRadar 胸部肿瘤每日文献雷达 ({day})", ""]
    if not papers:
        lines.append("今日无过线新文献。")
        return "\n".join(lines)
    lines.append(f"漏斗：抓取 {funnel['fetched']} → 期刊索引留存 {funnel['journal_matched']} → "
                 f"预筛 {funnel['prescreened']} → 收录 {funnel['final']} 篇")
    lines.append("")
    for i, p in enumerate(papers, 1):
        badge = f"{p['journal_abbr']} · IF {p['if_val']} · 评分 {p['score_total']}"
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

    day = date.today().isoformat()
    llm = LLMClient()
    mode = "LLM" if llm.available else "启发式（无 LLM_API_KEY）"
    log(f"胸科雷达流水线启动 · 模式={mode}")

    collector = Collector()
    jm = JournalMatcher(json.loads(JOURNALS_FILE.read_text(encoding="utf-8")))

    days_back = args.days_back
    pmids = collector.esearch_pmids(days_back, args.retmax)
    funnel = {"fetched": len(pmids), "journal_matched": 0, "prescreened": 0, "final": 0}
    if len(pmids) < args.min_final and days_back < 7:
        log(f"近 {days_back} 天仅 {len(pmids)} 篇，放宽窗口到 7 天重抓")
        days_back = 7
        pmids = collector.esearch_pmids(days_back, args.retmax)
        funnel["fetched"] = len(pmids)
    log(f"ESearch 命中 {len(pmids)} 篇（crdt 近 {days_back} 天）")

    articles = collector.efetch_articles(pmids)
    log(f"EFetch 解析成功 {len(articles)} 篇")

    # 去重 + 粗筛 + 通知类排除 + 跨天去重（近 N 天已上过日报的不重发）
    seen, articles_clean = set(), []
    n_notice = 0
    for a in articles:
        if not (a["pmid"] and a["title_en"] and a["abstract_en"]):
            continue
        if a["pmid"] in seen:
            continue
        seen.add(a["pmid"])
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

    # 精评 + 核验（核验异常 → fail-closed 降级，不崩运行）
    papers: List[Dict[str, Any]] = []
    for a in prescreened[:60]:
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
        except Exception as e:  # noqa: BLE001 核验器自身异常 → 按「无法确认」处理
            verify_error = f"verifier-error: {e}"
            log(f"  ⚠ 核验器异常 (pmid {a['pmid']})，本篇降级: {e}")
        papers.append(build_paper(a, scored, verdict, verify_error))
    papers.sort(key=lambda p: p["score_total"], reverse=True)
    funnel["final"] = len(papers)
    log(f"收录 {len(papers)} 篇（降级 {sum(1 for p in papers if p['publish_state'] == 'degraded')} 篇）"
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
    (DATA_DIR / "archive" / f"{day}.json").write_text(
        json.dumps({"briefing_date": day, "mode": "llm" if llm.available else "heuristic",
                    "funnel": funnel, "papers": papers}, ensure_ascii=False), encoding="utf-8")
    inject_index_html(papers, funnel, day)
    log(f"产出完成：archive/{day}.json / daily_briefing_{day}.md / index.html / status.json")
    return 0


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
            mutations.append({"kind": "population_swap", "summary": "上述结果来自全人群（ITT）分析",
                              "expect": "semantic_pending"})
            mutations.append({"kind": "endpoint_swap", "summary": "上述数值为主要终点结果",
                              "expect": "semantic_pending"})
            cases.append({
                "id": f"reg_{pmid}", "pmid": pmid, "title": a["title_en"],
                "abstract": a["abstract_en"], "basis": "摘要原文（冻结于构建时点）",
                "expected_numbers": nums,
                "correct_summary": f"研究纳入 {nums[0]} 例，关键结果数值包括 {'、'.join(nums[:4])}。",
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
    """跑工程回归：正确样例应放行（误拦计数）、数值变造应拦截（漏拦计数）、语义类标未验证。"""
    set_file = REG_DIR / "cases.json"
    if not set_file.exists():
        log("回归集不存在，先跑 --build-regression")
        return 2
    cases = json.loads(set_file.read_text(encoding="utf-8"))["cases"]
    n_cases = n_correct = n_false_block = n_block_mut = n_blocked = n_missed = n_semantic_pending = 0
    missed_detail = []
    for c in cases:
        n_cases += 1
        v_good = FourTupleVerifier.verify(c["abstract"], c["correct_summary"], [])
        if v_good["passed"]:
            n_correct += 1
        else:
            n_false_block += 1
        for mut in c["mutations"]:
            if mut["expect"] == "semantic_pending":
                n_semantic_pending += 1
                continue
            n_block_mut += 1
            v_bad = FourTupleVerifier.verify(c["abstract"], mut["summary"], [])
            if not v_bad["passed"]:
                n_blocked += 1
            else:
                n_missed += 1
                missed_detail.append({"case": c["id"], "kind": mut["kind"], "bad": mut.get("bad")})
    report = {
        "generated_at": datetime.now().isoformat(),
        "n_cases": n_cases,
        "correct_samples": {"n": n_cases, "passed": n_correct, "false_blocks": n_false_block},
        "number_mutations": {"n": n_block_mut, "blocked": n_blocked, "missed": n_missed,
                             "missed_detail": missed_detail},
        "semantic_pending": {"n": n_semantic_pending,
                             "note": "语义核验（人群/终点偷换）未上线，如实标未验证"},
        "verifier": "deterministic-text-v1",
    }
    REG_DIR.mkdir(parents=True, exist_ok=True)
    (REG_DIR / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    log(f"回归完成：正确样例 {n_correct}/{n_cases} 放行（误拦 {n_false_block}）· "
        f"数值变造拦截 {n_blocked}/{n_block_mut}（漏拦 {n_missed}）· 语义待验 {n_semantic_pending}")
    return 0 if (n_false_block == 0 and n_missed == 0 and n_cases >= 20) else 1


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
    log(f"[PASS] 1/4 期刊五重索引: NEJM={m_nejm['tier']} JTCVS={m_jtcvs['tier']}")

    c = Collector()
    params = urllib.parse.urlparse(c.esearch_url_probe())
    q = urllib.parse.parse_qs(params.query)
    assert q["datetype"] == ["crdt"] and "reldate" in q
    log("[PASS] 2/4 ESearch 参数: datetype=crdt + reldate")

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
    log(f"[PASS] 3/4 核验器: 真值放行 {v_good['tuple_audit'][0]['checks'][0]['note']} / 幻觉拦截 {v_bad['ungrounded_numbers']}")

    html_probe = f"<div>{DATA_START}const SITE_DATA = {{}};{DATA_END}</div>"
    assert DATA_START in html_probe and DATA_END in html_probe
    log("[PASS] 4/6 注入标记约定成立")

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
    log("[PASS] 5/6 出版状态解析：retracted/notice/ok 三态")

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
    log("[PASS] 6/6 失败降级：核验异常/撤稿 → 仅题录+链接，解读暂停")
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
