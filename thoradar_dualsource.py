# -*- coding: utf-8 -*-
"""双源桥：Europe PMC 回退集成层（2026-11-08 双源改造·Astra/Argon 会诊方案落地）。

职责：
1. EPMC Record → engine 文章字典映射（含撤稿三态合成，对齐 Collector.parse_status 语义）
2. 断路器探针（回归集地标文献＝已知有摘要探针）
3. 三级降级装配：patch（NCBI 清单＋EPMC 补详情）→ full_epmc（EPMC 独立检索）

不动管线既有函数；main() 在 efetch 硬校验闸处调用本层。
双源模块（dualsource.py／epmc_adapter.py）缺失＝回退关闭，引擎照旧跑 NCBI 单源。
"""
from __future__ import annotations

import json
import re
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CIRCUIT_STATE_PATH = DATA_DIR / "circuit_state.json"
PROBE_COUNT = 3                       # 断路器探针数（回归集地标文献，天然带摘要）
FALLBACK_ISSN_CHUNK = 50              # full_epmc 检索式按 50 刊/查分片（p+e ISSN ≈100 词元/查）
PROBE_FALLBACK_PMIDS = ["35403841", "33184242", "29899785"]  # 回归集缺失时的硬兜底（地标试验）


def log(msg: str) -> None:
    print(f"[dualsource] {msg}", flush=True)


# ============================================================================
# 1. 断路器探针
# ============================================================================

def load_probe_pmids(n: int = PROBE_COUNT) -> List[str]:
    try:
        cases = json.loads((DATA_DIR / "regression" / "cases.json").read_text(encoding="utf-8"))["cases"]
        pmids = [str(c["pmid"]) for c in cases if c.get("pmid")][:n]
        if pmids:
            return pmids
    except Exception as e:  # noqa: BLE001 回归集缺失不拖垮探针
        log(f"回归集探针加载失败，用硬兜底: {e}")
    return PROBE_FALLBACK_PMIDS[:n]


def efetch_probe_ok(collector: Any) -> bool:
    """探针＝已知有摘要的地标文献走一遍 efetch；任一缺摘要/解析失败＝NCBI 输出不健康。"""
    probes = load_probe_pmids()
    try:
        arts = collector.efetch_articles(probes)
    except Exception as e:  # noqa: BLE001
        log(f"探针 efetch 异常: {e}")
        return False
    got = {a.get("pmid", ""): a for a in arts}
    ok = all(p in got and (got[p].get("abstract_en") or "").strip() for p in probes)
    log(f"NCBI 探针 {'健康' if ok else '不健康（缺摘要/缺解析）'}: {probes}")
    return ok


# ============================================================================
# 2. Record → engine 文章字典映射
# ============================================================================

# EPMC commentCorrection type（去空格小写）→ (kind, impact_known, note)，对齐 parse_status 五态
_EVENT_KIND = {
    "retractionin": ("retracted", True, "原文已被撤稿（EPMC: Retraction in）"),
    "retractionof": ("notice", True, "本文为撤稿通知，不作为研究文献收录"),
    "erratumin": ("corrected", False, "原文存在更正启事；更正对结论的影响未明，解读暂停"),
    "erratumfor": ("notice", True, "本文为更正启事，不作为研究文献收录"),
    "expressionofconcernin": ("concern", False, "原文被发布关注声明（Expression of Concern），解读暂停"),
    "expressionofconcernfor": ("notice", True, "本文为关注声明通知，不作为研究文献收录"),
}
_PT_NOTICE = {"retraction of publication", "published erratum",
              "corrected and republished article"}
_PT_RETRACTED = {"retracted publication"}
# kind 优先级与 parse_status 判序一致：notice > retracted > corrected > concern > ok
_KIND_PRIORITY = {"ok": 0, "concern": 1, "corrected": 2, "retracted": 3, "notice": 4}


def status_from_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    pts = {(pt or "").strip().lower() for pt in rec.get("pub_types", [])}
    kinds: List[Tuple[str, bool, str, str]] = []
    for ev in rec.get("retraction_events", []):
        t = (ev.get("type") or "").strip().lower().replace(" ", "")
        if t in _EVENT_KIND:
            k, imp, note = _EVENT_KIND[t]
            kinds.append((k, imp, note, ev.get("ref_pmid", "")))
    if (pts & _PT_NOTICE) or any(k[0] == "notice" for k in kinds):
        return {"kind": "notice", "notice_pmid": "", "notice_ref": "", "impact_known": True,
                "note": "本文为撤稿/更正/关注声明类通知，不作为研究文献收录"}
    if (pts & _PT_RETRACTED) or any(k[0] == "retracted" for k in kinds):
        r = next((k for k in kinds if k[0] == "retracted"), None)
        return {"kind": "retracted", "notice_pmid": r[3] if r else "", "notice_ref": "",
                "impact_known": True, "note": "原文已被撤稿（Retracted Publication）"}
    if any(k[0] == "corrected" for k in kinds):
        r = next(k for k in kinds if k[0] == "corrected")
        return {"kind": "corrected", "notice_pmid": r[3], "notice_ref": "",
                "impact_known": False, "note": "原文存在更正启事；更正对结论的影响未明，解读暂停"}
    if any(k[0] == "concern" for k in kinds):
        r = next(k for k in kinds if k[0] == "concern")
        return {"kind": "concern", "notice_pmid": r[3], "notice_ref": "",
                "impact_known": False, "note": "原文被发布关注声明（Expression of Concern），解读暂停"}
    return {"kind": "ok", "notice_pmid": "", "notice_ref": "", "impact_known": True, "note": ""}


def record_to_article(rec: Dict[str, Any]) -> Dict[str, Any]:
    """契约 Record → engine 文章字典（build_paper 全键覆盖，键形状对齐 _parse_article）。"""
    abstract = rec.get("abstract", "") or ""
    m = re.search(r"NCT\d{8}", abstract)
    return {
        "pmid": rec.get("pmid", ""),
        "title_en": rec.get("title", ""),
        "p_issn": rec.get("issn", ""),
        "e_issn": rec.get("essn", ""),
        "issn_linking": rec.get("issn", ""),   # EPMC issn 即 journal-info 主 ISSN，linking 等价可配
        "nlm_id": rec.get("nlmid", ""),
        "iso_abbr": "",                         # EPMC 无 ISO 缩写字段；展示用 journal_title 顶
        "journal_title": rec.get("journal_title", ""),
        "abstract_en": abstract,
        "authors": rec.get("author_string", "") or "（作者信息缺失）",
        "affiliations": (rec.get("affiliation", "") or "")[:300],
        "pub_date": rec.get("first_publication_date", "") or "",
        "doi": rec.get("doi", ""),
        "pmcid": rec.get("pmcid", ""),
        "nct_id": m.group(0) if m else "",
        "status": status_from_record(rec),
        "source": "epmc",
    }


# ============================================================================
# 3. 三级降级装配
# ============================================================================

def load_breaker() -> Optional[Any]:
    try:
        from dualsource import CircuitBreaker  # type: ignore
    except ImportError as e:
        log(f"双源模块缺失，回退关闭: {e}")
        return None
    try:
        return CircuitBreaker(str(CIRCUIT_STATE_PATH))
    except Exception as e:
        # 2026-11-08 复核 B2 修：状态文件坏/半写时集成层收养——隔离坏件、fresh CLOSED。
        # （模块层拒绝静默复位＝有意设计，收养决策在集成层做。CI 次日 git 自愈可 limited 一日一红，
        #  但断路器记忆恰在「最需要记忆的日子」失效，故就地收养。）
        log(f"断路器状态文件损坏，隔离坏件后全新启动: {e}")
        try:
            p = Path(str(CIRCUIT_STATE_PATH))
            p.replace(p.with_name(p.name + ".corrupt"))
        except Exception:
            pass
        try:
            return CircuitBreaker(str(CIRCUIT_STATE_PATH))
        except Exception as e2:
            log(f"断路器仍无法初始化，回退关闭: {e2}")
            return None


def _issn_chunks(cfg: Dict[str, Any]) -> List[List[str]]:
    terms: List[str] = []
    for j in cfg.get("journals", []):
        for key in ("p_issn", "e_issn"):
            v = (j.get(key) or "").strip()
            if v:
                terms.append(v)
    return [terms[i:i + FALLBACK_ISSN_CHUNK * 2]
            for i in range(0, len(terms), FALLBACK_ISSN_CHUNK * 2)]


def _full_epmc_records(epmc_search_day, cfg: Dict[str, Any], days_back: int) -> List[Dict[str, Any]]:
    """EPMC 独立检索：分片查询＋PMID 去重（窗尾外推 1 天覆盖镜像延迟与 UTC/Tokyo 偏差）。"""
    date_to = date.today()
    date_from = date_to - timedelta(days=days_back + 1)
    merged: Dict[str, Dict[str, Any]] = {}
    for chunk in _issn_chunks(cfg):
        for rec in epmc_search_day(chunk, date_from.isoformat(), date_to.isoformat()):
            merged.setdefault(rec["pmid"], rec)
        time.sleep(0.3)
    return list(merged.values())


def run_dualsource_fallback(collector: Any, pmids: List[str], ncbi_articles: List[Dict[str, Any]],
                            cfg: Dict[str, Any], funnel: Dict[str, int], days_back: int,
                            seen: Dict[str, str], breaker: Any, reason: str,
                            ) -> Optional[List[Dict[str, Any]]]:
    """三级降级主入口。返回 engine 文章字典列表（可能混合 NCBI 保全＋EPMC 补取）；
    双源齐断／模块缺失返回 None（调用方维持 exit 2＝CI 重试语义）。"""
    try:
        from dualsource import decide_route  # type: ignore
        from epmc_adapter import EpmcError, epmc_fetch_pmids, epmc_search_day  # type: ignore
    except ImportError as e:
        log(f"双源模块缺失，回退关闭: {e}")
        return None

    esearch_ok = bool(pmids)
    route, mode = decide_route(esearch_ok, False, breaker)
    funnel["dualsource_reason"] = reason
    if mode == "normal":  # 防御：降级入口不该拿到 normal
        return ncbi_articles or None

    t0 = time.time()
    try:
        if mode == "patch":
            records = epmc_fetch_pmids(pmids)
            log(f"【双源】patch：NCBI 清单 {len(pmids)} 篇 → EPMC 补取 {len(records)} 篇")
        else:  # full_epmc
            records = _full_epmc_records(epmc_search_day, cfg, days_back)
            before = len(records)
            records = [r for r in records if r["pmid"] not in seen]
            log(f"【双源】full_epmc：窗口检索 {before} 篇 → 见过账本去重后 {len(records)} 篇")
    except EpmcError as e:
        log(f"【双源】EPMC 也失败（双源齐断）: {e}")
        return None
    if not records:
        log("【双源】EPMC 零产出——判双源齐断，维持 CI 重试")
        return None

    epmc_by_pmid = {r["pmid"]: r for r in records}
    out: List[Dict[str, Any]] = []
    rescued = kept = 0
    for a in ncbi_articles:  # patch/stripped：NCBI 保全在先
        r = epmc_by_pmid.pop(a.get("pmid", ""), None)
        if r and not (a.get("abstract_en") or "").strip() and (r.get("abstract") or "").strip():
            out.append(record_to_article(r))   # EPMC 摘要救回被剥离记录
            rescued += 1
        else:
            out.append(a)                       # NCBI 健康记录保全
            kept += 1
    for pmid, r in epmc_by_pmid.items():        # NCBI 全漏（空信封形）
        if (r.get("abstract") or "").strip():
            out.append(record_to_article(r))
    filled = sum(1 for a in out if (a.get("abstract_en") or "").strip())
    if not filled:
        log("【双源】合并后零带摘要记录——判双源齐断，维持 CI 重试")
        return None
    funnel["dualsource_mode"] = mode
    funnel["dualsource_records"] = len(records)
    funnel["dualsource_rescued"] = rescued
    funnel["dualsource_kept_ncbi"] = kept
    funnel["source"] = "epmc" if not kept else "mixed"
    log(f"【双源】回退完成 {len(out)} 篇（救回 {rescued}｜NCBI 保全 {kept}｜带摘要 {filled}）"
        f" 用时 {time.time() - t0:.1f}s")
    return out
