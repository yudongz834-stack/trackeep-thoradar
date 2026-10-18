# -*- coding: utf-8 -*-
"""journal_qc.py — ThorRadar 期刊库一次性质检（OpenAlex 对拍 + PubMed 年发文量）
运行：E:/Python/python.exe -X utf8 -I D:/tmp/journal_qc.py
写域：design/journal-qc-report.json + design/journal-qc-报告.md（断点续跑：已成功的条目自动跳过）
"""
import json, re, sys, time, urllib.request, urllib.parse, os
from pathlib import Path
from datetime import date, datetime, timedelta

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY = ROOT / "config" / "journals_taxonomy.json"
OUT_JSON = ROOT / "design" / "journal-qc-report.json"
OUT_MD   = ROOT / "design" / "journal-qc-报告.md"
HEALTH_JSON = ROOT / "data" / "journal_health.json"   # 引擎每日写：{"期刊ta": "最后命中日期ISO", ...}

OA_URL = ("https://api.openalex.org/sources?filter=issn:{issn}"
          "&select=id,display_name,issn,issn_l,works_count,cited_by_count,summary_stats")
ES_URL = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
          "?db=pubmed&term={term}&retmax=0&retmode=json")
_today = datetime.now().date(); _start = _today - timedelta(days=365)
DP_WINDOW = f'("{_start.isoformat()}"[DP] : "{_today.isoformat()}"[DP])'

OA_SLEEP, PM_SLEEP = 0.15, 0.35
HDRS = {"User-Agent": "thoradar-journal-qc/1.0 (one-shot QC batch)"}


def fetch_json(url, tries=3, timeout=25):
    """GET→json；网络类失败重试（初试+2），全败返回 (None, err)。"""
    err = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HDRS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace")), None
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            if i < tries - 1:
                time.sleep(1.5 * (i + 1))
    return None, err


def norm_name(s):
    s = s.casefold().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def name_match(a, b):
    """宽松比对：归一后相等，或一方包含另一方（双方≥8字符，防短串误含）。"""
    na, nb = norm_name(a or ""), norm_name(b or "")
    if not na or not nb:
        return False
    if na == nb:
        return True
    return len(na) >= 8 and len(nb) >= 8 and (na in nb or nb in na)


def load_progress():
    if os.path.exists(OUT_JSON):
        try:
            with open(OUT_JSON, encoding="utf-8") as f:
                done = json.load(f)
            if isinstance(done, dict):   # 新版带 journal_health 小节；旧版为裸 list，续跑兼容
                done = done.get("results") or []
            return {e["nlm_id"]: e for e in done if e.get("error") is None}, len(done)
        except Exception:
            pass
    return {}, 0


def save_progress(results, journal_health=None):
    """json 报告＝{"results": [...], "journal_health": {...}|null}（终跑写入健康小节）。"""
    tmp = Path(str(OUT_JSON) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"results": results, "journal_health": journal_health},
                  f, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT_JSON)


# ---------- 期刊目录健康（周检接 data/journal_health.json；纯函数可单测） ----------
# 阈值唯一真相源＝thoradar_engine.HEALTH_*_DAYS（改阈值只改引擎一处）
sys.path.insert(0, str(ROOT))
from thoradar_engine import HEALTH_RED_DAYS, HEALTH_YELLOW_DAYS  # noqa: E402


def classify_journal_health(state: dict, today: date) -> dict:
    """逐刊目录健康分类：距最后命中 ≥HEALTH_RED_DAYS→red（疑改名/停刊/检索键失效，人工核）；
    HEALTH_YELLOW_DAYS–RED-1 天→yellow（低频刊/季刊可能正常）；其余→green。
    state＝{"期刊ta": "最后命中日期ISO", ...}（data/journal_health.json 原样）；
    None/空 → 空档标记（total=0，报告显示「台账尚未生成」）。
    坏日期串不崩：计入 total 并归 red（无法确认新鲜度＝需人工核）。
    """
    out = {"red": [], "yellow": [], "green": 0, "total": 0}
    if not state:
        return out
    for ta, iso in state.items():
        out["total"] += 1
        try:
            days = (today - date.fromisoformat(str(iso).strip())).days
        except (ValueError, TypeError):
            out["red"].append(str(ta))
            continue
        if days >= HEALTH_RED_DAYS:
            out["red"].append(ta)
        elif days >= HEALTH_YELLOW_DAYS:
            out["yellow"].append(ta)
        else:
            out["green"] += 1
    return out


def main():
    with open(TAXONOMY, encoding="utf-8") as f:
        journals = json.load(f)["journals"]
    total = len(journals)
    done_map, prev = load_progress()
    print(f"total={total} resumed_done={prev}", flush=True)

    results = []
    n_hit = 0
    for idx, j in enumerate(journals, 1):
        nlm = j["nlm_id"]
        cached = done_map.get(nlm)
        if cached is not None:
            results.append(cached)
            n_hit += 1 if cached.get("openalex_hit") else 0
            continue

        rec = {
            "nlm_id": nlm,
            "title": j["title"],
            "openalex_hit": None,
            "openalex_name": None,
            "h_index": None,
            "cited_2yr": None,
            "works_count": None,
            "vol_365": None,
            "error": None,
            "query_issn": j.get("issn_l") or j.get("p_issn") or j.get("e_issn") or "",
        }
        errs = []

        # --- OpenAlex ---
        if rec["query_issn"]:
            data, err = fetch_json(OA_URL.format(issn=rec["query_issn"]))
            time.sleep(OA_SLEEP)
            if err:
                errs.append(f"openalex[{rec['query_issn']}]: {err}")
            else:
                res = data.get("results") or []
                pick = None
                for r in res:
                    if rec["query_issn"] in (r.get("issn") or []) or r.get("issn_l") == rec["query_issn"]:
                        pick = r
                        break
                if pick is None and res:
                    pick = res[0]
                if pick is None:
                    rec["openalex_hit"] = False
                else:
                    rec["openalex_hit"] = True
                    rec["openalex_name"] = pick.get("display_name")
                    ss = pick.get("summary_stats") or {}
                    rec["h_index"] = ss.get("h_index")
                    rec["cited_2yr"] = ss.get("2yr_mean_citedness")
                    rec["works_count"] = pick.get("works_count")
        else:
            errs.append("openalex: no issn available")

        # --- PubMed 年发文量 ---
        term = f'"{j["iso_abbr"]}"[ta] AND {DP_WINDOW}'
        data, err = fetch_json(ES_URL.format(term=urllib.parse.quote(term, safe="")))
        time.sleep(PM_SLEEP)
        if err:
            errs.append(f"pubmed: {err}")
        else:
            try:
                rec["vol_365"] = int(data["esearchresult"]["count"])
            except Exception:
                errs.append(f"pubmed: bad payload {str(data)[:120]}")

        if errs:
            rec["error"] = " | ".join(errs)
        results.append(rec)
        if rec["openalex_hit"]:
            n_hit += 1

        if idx % 20 == 0 or idx == total:
            save_progress(results)
            print(f"[{idx}/{total}] openalex_hit={n_hit} errors={sum(1 for r in results if r['error'])}",
                  flush=True)

    # ---- 期刊目录健康（读 data/journal_health.json，引擎每日写；缺失/空＝台账尚未生成） ----
    health_state = None
    health_note = ""
    if HEALTH_JSON.exists():
        try:
            with open(HEALTH_JSON, encoding="utf-8") as f:
                loaded = json.load(f)
            health_state = loaded if isinstance(loaded, dict) else None
        except Exception as e:  # noqa: BLE001 台账读不动→报告点名，不静默
            health_note = f"{type(e).__name__}: {e}"
    health = classify_journal_health(health_state, _today)
    save_progress(results, health)

    # ================= 报告 =================
    run_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    n = len(results)
    hits = [r for r in results if r["openalex_hit"]]
    miss = [r for r in results if r["openalex_hit"] is False]
    mismatch = [r for r in hits if not name_match(r["title"], r["openalex_name"])]
    errs = [r for r in results if r["error"]]
    vol_ok = [r for r in results if isinstance(r["vol_365"], int)]
    top15 = sorted(vol_ok, key=lambda r: -r["vol_365"])[:15]
    vol0 = [r for r in vol_ok if r["vol_365"] == 0]

    L = []
    L.append("# 期刊库质检报告（OpenAlex 对拍 + PubMed 年发文量）\n")
    L.append(f"- 跑批时间：{run_at}")
    L.append(f"- 总数：{n} 本（config/journals_taxonomy.json v3.1.0 全量）")
    L.append(f"- PubMed 窗口：2025/10/01 – 2026/10/17（约 365 天，[ta] 按缩写匹配）")
    L.append(f"- 脚本：D:\\tmp\\journal_qc.py（支持断点续跑，已成功条目跳过）\n")

    L.append("## 汇总\n")
    L.append(f"- OpenAlex 命中：{len(hits)}/{n}（{len(hits)*100//n}%）；未命中 {len(miss)} 本")
    L.append(f"- 名字宽松比对不一致：{len(mismatch)} 本（见下）")
    L.append(f"- PubMed vol_365 取到：{len(vol_ok)}/{n}；为 0 的 {len(vol0)} 本")
    L.append(f"- 异常条目（含 error）：{len(errs)} 本（见异常清单）\n")

    L.append("### 名字不一致清单\n")
    L.append("| 我们 title | OpenAlex display_name | nlm_id |")
    L.append("|---|---|---|")
    for r in mismatch:
        L.append(f"| {r['title']} | {r['openalex_name']} | {r['nlm_id']} |")
    L.append("")

    L.append("### vol_365 最高 15 本\n")
    L.append("| title | vol_365 | tier |")
    L.append("|---|---|---|")
    tier_by_nlm = {j["nlm_id"]: j["tier"] for j in journals}
    for r in top15:
        L.append(f"| {r['title']} | {r['vol_365']} | {tier_by_nlm.get(r['nlm_id'],'')} |")
    L.append("")

    L.append("### OpenAlex 未命中清单\n")
    if miss:
        for r in miss:
            L.append(f"- {r['title']}（query_issn={r.get('query_issn') or '无'}）")
    else:
        L.append("（无）")
    L.append("")

    L.append("### 异常清单（error 非空）\n")
    if errs:
        for r in errs:
            L.append(f"- {r['title']}（{r['nlm_id']}）：{r['error']}")
    else:
        L.append("（无）")
    L.append("")

    L.append("### 期刊目录健康（data/journal_health.json）\n")
    if health_note:
        L.append(f"- 台账读取失败（{health_note}）——本节按空档处理，请人工核查该文件")
    if health["total"] == 0:
        if not health_note:
            L.append("- 台账尚未生成（引擎首跑后出现）")
    else:
        L.append(f"- 红档（≥100 天未命中，疑改名/停刊/检索键失效，人工核）：{len(health['red'])} 本")
        for ta in sorted(health["red"])[:15]:
            L.append(f"  - {ta}")
        if len(health["red"]) > 15:
            L.append(f"  - …另 {len(health['red']) - 15} 本未列出")
        L.append(f"- 黄档（45–99 天，低频刊/季刊可能正常）：{len(health['yellow'])} 本")
        for ta in sorted(health["yellow"])[:15]:
            L.append(f"  - {ta}")
        if len(health["yellow"]) > 15:
            L.append(f"  - …另 {len(health['yellow']) - 15} 本未列出")
        L.append(f"- 绿档（<45 天）：{health['green']} 本")
        if health["red"]:
            verdict = f"红档 {len(health['red'])} 本需人工核"
            if health["yellow"]:
                verdict += f"，另关注黄档 {len(health['yellow'])} 本"
        elif health["yellow"]:
            verdict = f"无红档；黄档 {len(health['yellow'])} 本观察即可"
        else:
            verdict = "全部健康"
        L.append(f"- 结论：{verdict}。")
    L.append("")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(L))

    print(f"DONE n={n} hit={len(hits)} mismatch={len(mismatch)} errors={len(errs)} "
          f"health_red={len(health['red'])} health_yellow={len(health['yellow'])}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
