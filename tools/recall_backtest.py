# -*- coding: utf-8 -*-
"""历史回测：以「340 本字典刊全集 × 近 N 天」为参考全集，实测各检索式召回/盲区/垃圾率。
用法: python recall_backtest.py [天数]  （默认 30；先跑 2 天冒烟）
"""
import json, os, sys, time
sys.path.insert(0, r"D:\trackeep-thoradar")

os.environ.setdefault("LLM_API_KEY", os.environ.get("DEEPSEEK_TOKEN", ""))
os.environ.setdefault("LLM_BASE_URL", "https://api.deepseek.com/v1")
os.environ.setdefault("LLM_MODEL", "deepseek-chat")
os.environ.setdefault("MAX_DAILY_COST_USD", "8")

import thoradar_engine as te

DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 30
OUT = r"D:\tmp\recall_backtest_out"
os.makedirs(OUT, exist_ok=True)
LOG = lambda m: print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

cfg = json.load(open(r"D:\trackeep-thoradar\config\journals_taxonomy.json", encoding="utf-8"))
jm = te.JournalMatcher(cfg)
c = te.Collector()

# ---------- 1) 参考全集：逐刊拉近 N 天全部 PMID ----------
LOG(f"参考全集构建开始（字典 {len(cfg['journals'])} 刊 × 近 {DAYS} 天）")
uni, empty_ta, zero_hit = {}, 0, []
t0 = time.time()
for i, j in enumerate(cfg["journals"]):
    ta = (j.get("iso_abbr") or j.get("title") or "").strip()
    if not ta:
        empty_ta += 1
        continue
    try:
        ids = c.esearch_pmids(DAYS, 1000, query=f'"{ta}"[ta]')
    except Exception as e:  # noqa: BLE001 单刊失败不断全卷
        LOG(f"  ⚠ 刊查询失败 {ta}: {e}")
        zero_hit.append(ta)
        continue
    if not ids:
        zero_hit.append(ta)
    if ids:
        uni[ta] = ids
    if i % 40 == 0:
        LOG(f"  进度 {i}/{len(cfg['journals'])}｜已收 {sum(len(v) for v in uni.values())} 篇｜{time.time()-t0:.0f}s")
pmids = sorted({p for v in uni.values() for p in v}, key=int)
LOG(f"参考全集 = {len(pmids)} 篇唯一 PMID（零命中刊 {len(zero_hit)}、无名刊 {empty_ta}）")
json.dump({"days": DAYS, "universe": uni, "zero_hit": zero_hit},
          open(f"{OUT}/universe_{DAYS}d.json", "w", encoding="utf-8"), ensure_ascii=False)

# ---------- 2) 全量取回（标题+摘要+期刊身份） ----------
LOG("EFetch 全量取回…")
arts = []
for k in range(0, len(pmids), 400):
    arts.extend(c.efetch_articles(pmids[k:k+400]))
    if k % 2000 == 0:
        LOG(f"  efetch {k}/{len(pmids)}")
stage = []
ta_false = 0
for a in arts:
    if not (a["pmid"] and a["title_en"] and a["abstract_en"]):
        continue
    m = jm.match(a["p_issn"], a["e_issn"], a["issn_linking"], a["nlm_id"],
                 a["iso_abbr"], a["journal_title"])
    if m["matched"]:
        stage.append(a)
    else:
        ta_false += 1
LOG(f"解析+字典复验 {len(stage)} 篇（[ta] 误命中 {ta_false} 篇剔除）")

# ---------- 3) 「全要」口径标注（LLM；失败回退关键词） ----------
llm = te.LLMClient()
LOG(f"标注器：{'LLM(deepseek-chat)' if llm.available else '关键词回退'}")
try:
    kept = te.llm_prescreen(llm, stage, system=te.SHADOW_PRESCREEN_SYSTEM)
except te.BudgetExceeded:
    LOG("⚠ 标注预算熔断，按已标注部分收卷")
    kept = stage  # 不可靠，标记
    kept = []
R = {a["pmid"] for a in kept}
LOG(f"胸科相关参考集 R = {len(R)} / {len(stage)}")

# ---------- 4) 各检索式本地对卷 ----------
V2_A = te._SHADOW_TERMS                                    # 与主式病种组同源(26)
V2_B = ("clinical trial", "randomized", "neoadjuvant", "adjuvant", "perioperative",
        "propensity score", "three-dimensional", "artificial intelligence", "deep learning",
        "machine learning", "radiomics", "neural network", "immunotherapy", "chemotherapy",
        "radiotherapy", "screening", "survival", "resection", "stereotactic", "lymph node",
        "EGFR", "ALK", "PD-L1", "PD-1", "ctDNA", "MRD", "osimertinib", "nivolumab",
        "pembrolizumab", "durvalumab", "antibiotic")
AMBIG, ANAT = te._SHADOW_AMBIG, te._SHADOW_ANATOMY

def matched(text, terms):
    return any(t in text for t in terms)

results = {}
for name, fn in {
    "v2(A×B)":      lambda t: matched(t, V2_A) and matched(t, V2_B),
    "乙(并集)":      lambda t: matched(t, V2_A) or (matched(t, AMBIG) and matched(t, ANAT)) or (matched(t, V2_A) and matched(t, V2_B)),
    "仅高特异A":     lambda t: matched(t, V2_A),
    "语境通道":      lambda t: matched(t, AMBIG) and matched(t, ANAT),
}.items():
    hit = [a for a in stage if fn(a["title_en"] + " " + a["abstract_en"].lower())]
    hit_in_R = [a for a in hit if a["pmid"] in R]
    results[name] = {
        "hit": len(hit), "hit_relevant": len(hit_in_R),
        "recall": round(len(hit_in_R) / len(R), 4) if R else None,
        "precision_in_universe": round(len(hit_in_R) / len(hit), 4) if hit else None,
    }

blind = [a for a in stage if a["pmid"] in R and not (matched(a["title_en"] + " " + a["abstract_en"].lower(), V2_A) and matched(a["title_en"] + " " + a["abstract_en"].lower(), V2_B))]
report = {
    "days": DAYS, "universe": len(stage), "R": len(R),
    "labeler": "llm" if llm.available else "keyword-fallback",
    "llm_cost_usd": round(getattr(llm, "cost_usd", 0), 4),
    "queries": results,
    "blind_v2": [{"pmid": a["pmid"], "title": a["title_en"][:140]} for a in blind[:80]],
    "n_blind_v2": len(blind),
}
json.dump(report, open(f"{OUT}/report_{DAYS}d.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

LOG("========== 回测结果 ==========")
LOG(f"参考全集 {len(stage)}｜胸科相关 R={len(R)}（{len(R)/max(1,len(stage)):.0%}）｜标注成本 ${getattr(llm,'cost_usd',0):.3f}")
for name, r in results.items():
    LOG(f"{name:12s} 命中 {r['hit']:>5}｜命中相关 {r['hit_relevant']:>5}｜召回 {r['recall']:.1%}｜全集中精确率 {r['precision_in_universe']:.1%}")
LOG(f"v2 盲区（相关但 v2 漏）= {len(blind)} 篇；样例：")
for b in blind[:12]:
    LOG(f"  - {b['pmid']} {b['title_en'][:100]}")
