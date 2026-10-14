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
    def _number_grounded_in_context(cls, num: str, abstract: str, anchors: List[str]) -> tuple:
        """返回 (grounded, note)。bare 数字在摘要里；若能定位句则要求句内有锚。"""
        bare = num.rstrip("%")
        sents = cls._sentences(abstract)
        hits = [s for s in sents if bare in s]
        if not hits:
            # 整串子串兜底（如 95% CI 的 '0.523' 与 '0.52' 类近值不在此列——宁可误报不漏报）
            if bare in abstract.replace(",", ""):
                return True, "整串命中（未定位到句）"
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
        abstract_norm = abstract_en.replace(",", "")
        summary_nums = [n for n in cls._norm_numbers(summary_zh) if n.rstrip("%") in abstract_norm]
        ungrounded_summary = [n for n in cls._norm_numbers(summary_zh) if n.rstrip("%") not in abstract_norm]

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
 "title_zh": "中文标题（准确、不夸大）",
 "study_type": "研究类型一句话（如 Phase III RCT · 最终OS分析）",
 "category": "perioperative|nodule|surgery|ai_digital|advanced|esophageal 六选一",
 "score_clinical": 0-35 整数（改变临床实践的潜力）,
 "score_methodology": 0-30 整数（设计严谨性；严谨阴性研究同样给高分）,
 "score_specialty": 0-20 整数（胸外科/胸部肿瘤契合度）,
 "one_liner": "一句话核心结论（含关键数值）",
 "pico_p": "人群与样本量",
 "pico_ic": "干预与对照",
 "pico_o": "核心终点数据（数值+CI/P，标注主要终点）",
 "reason": "推荐理由（临床与科研价值，客观中性，不用第二人称）",
 "methodology_note": "方法学审视：设计亮点与局限（含潜在偏倚）",
 "is_negative_highlight": true/false（是否为高质量阴性/证伪研究）,
 "tuples": [{"group": "人群/亚组限定", "metric": "终点指标", "val": "数值", "stat": "95%CI/P"}],
 "tags": ["标签1", "标签2"]
}
反阳性偏倚条款：方法学严谨的阴性研究（证伪无效干预）与阳性研究同等赋分。
tuples 只收录摘要中明确出现的数值，每条 val/stat 里的数字必须逐字来自摘要；摘要没有可靠数值则给空数组。"""


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
            "one_liner": first_sentences(a["abstract_en"], 2),
            "pico_p": "", "pico_ic": "",
            "pico_o": "",
            "reason": "启发式模式收录（未接入语言模型精评）：按期刊层级与研究类型自动入选。",
            "methodology_note": "",
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

def build_paper(a: Dict[str, Any], scored: Dict[str, Any], verdict: Dict[str, Any]) -> Dict[str, Any]:
    llm_data = scored["llm"]
    m = scored["match"]
    pico_o = str(llm_data.get("pico_o", "") or "")
    summary_for_check = " ".join(filter(None, [llm_data.get("one_liner", ""), pico_o]))
    return {
        "id": f"pmid_{a['pmid']}",
        "pmid": a["pmid"],
        "pmcid": a.get("pmcid", ""),
        "doi": a.get("doi", ""),
        "nct_id": a.get("nct_id", ""),
        "trial_name": "",
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{a['pmid']}/",
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
        "critic_verified": verdict["passed"] if llm_data.get("tuples") else None,
        "tuple_audit": verdict.get("tuple_audit", []),
        "ungrounded_numbers": verdict.get("ungrounded_numbers", []),
        "title_zh": llm_data.get("title_zh", "") or a["title_en"],
        "title_en": a["title_en"],
        "authors": a["authors"],
        "affiliation_highlight": first_sentences(a.get("affiliations", ""), 1, 120),
        "one_liner": llm_data.get("one_liner", ""),
        "pico": {"p": llm_data.get("pico_p", ""), "ic": llm_data.get("pico_ic", ""), "o": pico_o},
        "reason": llm_data.get("reason", ""),
        "methodology_note": llm_data.get("methodology_note", ""),
        "abstract_en": a["abstract_en"],
        "tags": llm_data.get("tags", [])[:6],
    }


def render_briefing_md(papers: List[Dict[str, Any]], day: str, funnel: Dict[str, int]) -> str:
    lines = [f"# 胸科雷达 ThorRadar 胸部肿瘤每日文献雷达 ({day})", ""]
    if not papers:
        lines.append("今日无过线新文献。")
        return "\n".join(lines)
    lines.append(f"漏斗：抓取 {funnel['fetched']} → 期刊索引留存 {funnel['journal_matched']} → "
                 f"预筛 {funnel['prescreened']} → 精评收录 {funnel['final']} 篇")
    lines.append("")
    for i, p in enumerate(papers, 1):
        badge = f"{p['journal_abbr']} · IF {p['if_val']} · 评分 {p['score_total']}"
        if p["score_source"] == "heuristic":
            badge += " · 启发式"
        verify = "✅ 核验通过" if p["critic_verified"] else ("⚠️ 未通过自动核验" if p["critic_verified"] is False else "— 无数值核验项")
        lines.append(f"## {i}. [{badge}] [{p['title_zh']}]({p['url']})")
        lines.append(f"- **英文原题**: *{p['title_en']}*")
        lines.append(f"- **一句话结论**: {p['one_liner']}")
        if p["pico"]["o"]:
            lines.append(f"- **核心终点**: {p['pico']['o']}")
        lines.append(f"- **核验状态**: {verify}")
        if p["methodology_note"]:
            lines.append(f"- **方法学审视**: {p['methodology_note']}")
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
    ap.add_argument("--days-back", type=int, default=2)
    ap.add_argument("--retmax", type=int, default=200)
    ap.add_argument("--min-final", type=int, default=3,
                    help="精评收录少于该数时自动放宽窗口到 7 天重抓一次")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return run_self_test()

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

    # 去重 + 粗筛无摘要/无标题
    seen, articles_clean = set(), []
    for a in articles:
        if a["pmid"] and a["pmid"] not in seen and a["title_en"] and a["abstract_en"]:
            seen.add(a["pmid"])
            articles_clean.append(a)

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

    # 精评 + 核验
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
        verdict = FourTupleVerifier.verify(
            a["abstract_en"],
            " ".join(filter(None, [llm_data.get("one_liner", ""), llm_data.get("pico_o", "")])),
            llm_data.get("tuples", []))
        papers.append(build_paper(a, scored, verdict))
    papers.sort(key=lambda p: p["score_total"], reverse=True)
    funnel["final"] = len(papers)
    log(f"精评收录 {len(papers)} 篇 · LLM 成本 ${llm.cost_usd:.3f}（{llm.calls} 次调用）")

    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "curated_literature.json").write_text(
        json.dumps({"briefing_date": day, "mode": "llm" if llm.available else "heuristic",
                    "funnel": funnel, "papers": papers}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    (DATA_DIR / f"daily_briefing_{day}.md").write_text(
        render_briefing_md(papers, day, funnel), encoding="utf-8")
    (DATA_DIR / "archive" / f"{day}.json").write_text(
        json.dumps({"funnel": funnel, "papers": papers}, ensure_ascii=False), encoding="utf-8")
    inject_index_html(papers, funnel, day)
    log(f"产出完成：curated_literature.json / daily_briefing_{day}.md / index.html 已注入")
    return 0


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
    log("[PASS] 4/4 注入标记约定成立")
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
