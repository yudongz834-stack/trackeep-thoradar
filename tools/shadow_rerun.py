# -*- coding: utf-8 -*-
"""shadow_rerun.py — 门禁件④ 影子重跑对账器（意志书四.3 断言制换册的先导件）。

新旧两册对同一数据源跑分类，产出三件（只写 --out 目录，账外一字不落、永不写册）：
  shadow_conservation.json   守恒表：每篇恰分类一次×两册；匹配/兜底/册差（增删行＋封存账）
  shadow_migration_matrix.json 迁移矩阵：旧档位×新档位（含类目迁移计数）
  shadow_discrepancies.json  差额单：两册判定不同的逐篇明细＋逐条解释

确定性口径：文章→期刊＝引擎 JournalMatcher 生产匹配器（五重索引＋名形弱键，单源不另写）；
期刊判定＝册面行（tier_new 优先、旧册回落 tier）。LLM 预筛判分类不在本件射程——
classifier 钩子（run_shadow(..., classifier=...)）留给未来 LLM 判官接入；默认确定性对账，
LLM 依赖处 mock 化（遗留风险见交付回报）。

用法：
  E:/Python/python.exe -X utf8 -I tools/shadow_rerun.py --old <旧册.json> --new <新册.json> \
      [--articles <文章.jsonl>] [--seal design/名册封存-20261101.json] [--out <目录>]
articles 缺省用内置最小样例（只验框架通；真实影子重跑须喂全量源数据）。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import thoradar_engine as eng  # noqa: E402  生产匹配器单源（引擎模块纯 stdlib）

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import thoradar_pins as pins  # noqa: E402

SEAL_PATH = ROOT / "design" / "名册封存-20261101.json"

# 内置最小样例：三篇分别落「两册同判／册面钉档／两册未收」三种路径（框架自证用）
SAMPLE_ARTICLES = [
    {"pmid": "demo-nejm", "title": "Randomized trial in pulmonary embolism",
     "e_issn": "1533-4406"},                                   # NEJM：两册在册（旧册 v3 tier S）
    {"pmid": "demo-ejcts", "title": "Outcomes after esophagectomy",
     "p_issn": "1873-734X"},                                   # EJCTS 冠冕钉：新册钉 B
    {"pmid": "demo-unknown", "title_journal": "Journal of Nowhere",
     "title": "A study with no ledger match anywhere"},        # 两册未收：兜底 D
]

Classifier = Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]


def default_classifier(matcher: eng.JournalMatcher, article: Dict[str, Any]) -> Dict[str, Any]:
    """确定性判官：生产匹配器五重索引＋名形；未命中＝兜底 D（引擎 P2 口径）。"""
    m = matcher.match(
        p_issn=article.get("p_issn", ""), e_issn=article.get("e_issn", ""),
        issn_linking=article.get("issn_l", ""), nlm_id=article.get("nlm_id", ""),
        iso_abbr=article.get("iso_abbr", ""), title=article.get("title", ""))
    return {"matched": bool(m.get("matched")), "tier": m.get("tier", "D"),
            "category": str(m.get("journal_category", "")),
            "journal": m.get("journal_full", "")}


def classify_all(doc: Dict[str, Any], articles: List[Dict[str, Any]],
                 classifier: Optional[Classifier] = None) -> List[Dict[str, Any]]:
    matcher = eng.JournalMatcher(doc)
    fn = classifier or (lambda art, m=matcher: default_classifier(m, art))
    out = []
    for art in articles:
        r = fn(art)
        out.append({**r, "pmid": art.get("pmid", ""), "title": art.get("title", "")})
    return out


def roster_delta(old_rows: List[Dict], new_rows: List[Dict],
                 sealed_rows: List[Dict]) -> Dict[str, Any]:
    old_nlm, new_nlm = set(pins.index_by_nlm(old_rows)), set(pins.index_by_nlm(new_rows))
    sealed_nlm = set(pins.index_by_nlm(sealed_rows))
    added = sorted(new_nlm - old_nlm)
    removed = sorted(old_nlm - new_nlm)
    return {
        "old_rows": len(old_rows), "new_rows": len(new_rows),
        "added": [{"nlm_id": n, "in_seal": n in sealed_nlm} for n in added],
        "removed": [{"nlm_id": n, "in_seal": n in sealed_nlm} for n in removed],
        "removed_without_seal_account": [n for n in removed if n not in sealed_nlm],
    }


def run_shadow(old_doc: Dict[str, Any], new_doc: Dict[str, Any],
               articles: List[Dict[str, Any]], sealed_rows: Optional[List[Dict]] = None,
               classifier: Optional[Classifier] = None) -> Dict[str, Any]:
    """框架主入口（classifier 钩子＝LLM 判官 mock/接入点）。返回三件套 dict。"""
    old_res = classify_all(old_doc, articles, classifier)
    new_res = classify_all(new_doc, articles, classifier)

    # —— 守恒表：每篇在两册各恰分类一次 ——
    tier_dist = lambda rs: dict(Counter(r["tier"] for r in rs))  # noqa: E731
    conservation = {
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "articles_total": len(articles),
        "old": {"version": old_doc.get("version"), "classified": len(old_res),
                "matched": sum(1 for r in old_res if r["matched"]),
                "fallback_d": sum(1 for r in old_res if not r["matched"]),
                "tier_dist": tier_dist(old_res)},
        "new": {"version": new_doc.get("version"), "classified": len(new_res),
                "matched": sum(1 for r in new_res if r["matched"]),
                "fallback_d": sum(1 for r in new_res if not r["matched"]),
                "tier_dist": tier_dist(new_res)},
        "conservation_ok": len(old_res) == len(new_res) == len(articles),
        "roster_delta": roster_delta(old_doc.get("journals") or [],
                                     new_doc.get("journals") or [],
                                     sealed_rows or []),
    }

    # —— 迁移矩阵：旧档×新档；类目迁移只对两册皆命中者计 ——
    matrix = Counter((o["tier"], n["tier"]) for o, n in zip(old_res, new_res))
    cat_moves = Counter((o["category"], n["category"]) for o, n in zip(old_res, new_res)
                        if o["matched"] and n["matched"] and o["category"] != n["category"])
    migration = {
        "generated_at": conservation["generated_at"],
        "tier_matrix_cells": [{"old": k[0], "new": k[1], "count": v}
                              for k, v in sorted(matrix.items())],
        "category_moves": [{"old": k[0] or "(未收)", "new": k[1] or "(未收)", "count": v}
                           for k, v in sorted(cat_moves.items())],
    }

    # —— 差额单：判定不同者逐条解释（差额必须能解释，账外不写产线） ——
    discrepancies: List[Dict[str, Any]] = []
    for art, o, n in zip(articles, old_res, new_res):
        if o["tier"] == n["tier"] and o["category"] == n["category"]:
            continue
        if o["matched"] and n["matched"]:
            why = (f"同刊两册行不同：{o.get('journal')}——册面 tier/category 改动"
                   f"（旧 {o['tier']}/{o['category'] or '∅'} → 新 {n['tier']}/{n['category'] or '∅'}）")
        elif n["matched"] and not o["matched"]:
            why = f"旧册未收此刊（{n.get('journal')}），旧判兜底 D；新册收录后按册面定档"
        elif o["matched"] and not n["matched"]:
            why = f"新册未收此刊（旧册 {o.get('journal')}）——若属删减须有封存账（四.1），否则即误删"
        else:
            why = "两册均未收，双边兜底 D（等类，判定相同档位不同来源，仍入单供人览)"
        discrepancies.append({
            "pmid": art.get("pmid", ""), "title": art.get("title", ""),
            "old": {"tier": o["tier"], "category": o["category"], "matched": o["matched"]},
            "new": {"tier": n["tier"], "category": n["category"], "matched": n["matched"]},
            "explain": why,
        })
    return {"conservation": conservation, "migration": migration, "discrepancies": discrepancies}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="门禁件④ 影子重跑对账器：新旧两册对同一数据源跑分类，出守恒表/迁移矩阵/差额单")
    ap.add_argument("--old", required=True, help="旧册 config JSON")
    ap.add_argument("--new", required=True, help="新册 config JSON")
    ap.add_argument("--articles", default=None, help="文章 JSONL（缺省内置最小样例，只验框架）")
    ap.add_argument("--seal", default=str(SEAL_PATH), help="封存档（册差封存账核对）")
    ap.add_argument("--out", default=None,
                    help="三件套落盘目录；不给则只打摘要。拒绝指向 config/（账外不写产线）")
    args = ap.parse_args()

    articles: List[Dict[str, Any]]
    if args.articles:
        articles = [json.loads(line) for line in
                    Path(args.articles).read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        articles = SAMPLE_ARTICLES
        print("[i] 未给 --articles，用内置最小样例（只验框架通，非真实影子重跑）")

    old_doc = json.loads(Path(args.old).read_text(encoding="utf-8"))
    new_doc = json.loads(Path(args.new).read_text(encoding="utf-8"))
    sealed_rows = []
    seal_p = Path(args.seal)
    if seal_p.exists():
        sealed_rows = json.loads(seal_p.read_text(encoding="utf-8")).get("journals") or []

    if args.out:
        out_dir = Path(args.out).resolve()
        cfg_real = (ROOT / "config").resolve()
        if cfg_real in out_dir.parents or out_dir == cfg_real:
            print("[FAIL] --out 指向 config/——账外不写产线，拒绝执行")
            return 2
        out_dir.mkdir(parents=True, exist_ok=True)

    result = run_shadow(old_doc, new_doc, articles, sealed_rows)
    cons, mig, dis = result["conservation"], result["migration"], result["discrepancies"]

    if args.out:
        for name, payload in (("shadow_conservation.json", cons),
                              ("shadow_migration_matrix.json", mig),
                              ("shadow_discrepancies.json", dis)):
            (out_dir / name).write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
        print(f"[OK] 三件套已落 {out_dir}")

    c = cons
    print(f"[守恒] 文章 {c['articles_total']}：旧册判定 {c['old']['classified']}（命中 {c['old']['matched']}"
          f"／兜底 {c['old']['fallback_d']}），新册判定 {c['new']['classified']}（命中 {c['new']['matched']}"
          f"／兜底 {c['new']['fallback_d']}）；conservation_ok={c['conservation_ok']}")
    rd = c["roster_delta"]
    print(f"[册差] 旧 {rd['old_rows']} 行 → 新 {rd['new_rows']} 行：增 {len(rd['added'])}／删 {len(rd['removed'])}"
          f"（删行无封存账 {len(rd['removed_without_seal_account'])}）")
    print(f"[迁移] 档位格 {len(mig['tier_matrix_cells'])} 个："
          + "，".join(f"{c_['old']}→{c_['new']}×{c_['count']}" for c_ in mig["tier_matrix_cells"]))
    print(f"[差额] {len(dis)} 篇判定不同（逐条带解释；账外不写产线，人览后定夺）：")
    for d in dis[:10]:
        print(f"  · {d['pmid']}: {d['old']['tier']}/{d['old']['category'] or '∅'} → "
              f"{d['new']['tier']}/{d['new']['category'] or '∅'}｜{d['explain']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
