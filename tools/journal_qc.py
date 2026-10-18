# -*- coding: utf-8 -*-
"""journal_qc.py — ThorRadar 期刊库一次性质检（OpenAlex 对拍 + PubMed 年发文量）
运行：E:/Python/python.exe -X utf8 -I D:/tmp/journal_qc.py
写域：design/journal-qc-report.json + design/journal-qc-报告.md（断点续跑：已成功的条目自动跳过）
"""
import json, re, sys, time, urllib.request, urllib.parse, os
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY = ROOT / "config" / "journals_taxonomy.json"
OUT_JSON = ROOT / "design" / "journal-qc-report.json"
OUT_MD   = ROOT / "design" / "journal-qc-报告.md"

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
            return {e["nlm_id"]: e for e in done if e.get("error") is None}, len(done)
        except Exception:
            pass
    return {}, 0


def save_progress(results):
    tmp = OUT_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT_JSON)


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

    save_progress(results)

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

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(L))

    print(f"DONE n={n} hit={len(hits)} mismatch={len(mismatch)} errors={len(errs)}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
