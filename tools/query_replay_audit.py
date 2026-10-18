# -*- coding: utf-8 -*-
"""检索式 v0 vs v2 召回回放审计（只读 PubMed，不改引擎）。"""
import json, os, re, sys, time
import urllib.parse, urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, r"D:\trackeep-thoradar")

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
API_KEY = os.environ.get("NCBI_API_KEY", "").strip()
GAP = 0.15 if API_KEY else 0.45

A0 = ["non-small-cell lung cancer", "NSCLC", "small-cell lung cancer", "SCLC",
      "pulmonary nodule", "ground-glass", "subsolid nodule", "thoracoscopic",
      "segmentectomy", "tubeless", "esophageal cancer", "mediastinal tumor", "thymoma"]
A_NEW = ["mesothelioma", "lung cancer", "lung tumor", "lobectomy", "pneumonectomy",
         "sublobar", "thymic", "esophagectomy", "robotic"]
B0 = ["clinical trial", "randomized", "neoadjuvant", "perioperative", "propensity score",
      "three-dimensional", "artificial intelligence", "osimertinib", "nivolumab",
      "pembrolizumab", "durvalumab", "antibiotic"]
B_NEW = ["immunotherapy", "chemotherapy", "radiotherapy", "adjuvant", "screening",
         "EGFR", "ALK", "PD-L1", "PD-1", "ctDNA", "MRD", "stereotactic",
         "lymph node", "survival", "resection"]

def q(a_terms, b_terms):
    a = "(" + " OR ".join(f'"{t}"[Title/Abstract]' for t in a_terms) + ")"
    b = "(" + " OR ".join(f'"{t}"[Title/Abstract]' for t in b_terms) + ")"
    return a + " AND " + b

Q0 = q(A0, B0)
Q1 = q(A0 + A_NEW, B0 + B_NEW)

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "thoradar-query-audit/1.0"})
    time.sleep(GAP)
    for attempt in (1, 2, 3):
        try:
            return urllib.request.urlopen(req, timeout=60).read()
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(2 * attempt)

def esearch_ids(term, days, use_key=True):
    p = {"db": "pubmed", "term": term, "datetype": "crdt", "reldate": str(days),
         "retmax": "100000", "retmode": "json"}
    if API_KEY and use_key:
        p["api_key"] = API_KEY
    data = json.loads(get(f"{EUTILS}/esearch.fcgi?{urllib.parse.urlencode(p)}"))
    er = data["esearchresult"]
    return int(er["count"]), er.get("idlist", [])

def efetch(pmids):
    out = []
    for i in range(0, len(pmids), 180):
        chunk = pmids[i:i + 180]
        p = {"db": "pubmed", "id": ",".join(chunk), "retmode": "xml"}
        if API_KEY:
            p["api_key"] = API_KEY
        root = ET.fromstring(get(f"{EUTILS}/efetch.fcgi?{urllib.parse.urlencode(p)}"))
        for art in root.iter("PubmedArticle"):
            try:
                pmid = art.findtext(".//PMID")
                jr = art.find(".//Journal")
                rec = {
                    "pmid": pmid,
                    "p_issn": (jr.findtext("ISSN[@IssnType='Print']") or "") if jr is not None else "",
                    "e_issn": (jr.findtext("ISSN[@IssnType='Electronic']") or "") if jr is not None else "",
                    "issn_linking": art.findtext(".//ISSNLinking") or "",
                    "nlm_id": art.findtext(".//MedlineJournalInfo/NlmUniqueID") or "",
                    "iso_abbr": (jr.findtext("ISOAbbreviation") or "") if jr is not None else "",
                    "journal_title": (jr.findtext("Title") or "") if jr is not None else "",
                    "title": (art.findtext(".//ArticleTitle") or ""),
                }
                abst = " ".join(t.text or "" for t in art.iter("AbstractText"))
                rec["text"] = (rec["title"] + " " + abst).lower()
                out.append(rec)
            except Exception:
                continue
    return out

def main():
    days = 30
    c0, ids0 = esearch_ids(Q0, days)
    c1, ids1 = esearch_ids(Q1, days)
    s0, s1 = set(ids0), set(ids1)
    print(f"[窗口 crdt 近 {days} 天] Q0(现版)={c0}  Q1(候选v2)={c1}  新增={len(s1 - s0)}  丢失(Q0-Q1)={len(s0 - s1)}")
    assert not (s0 - s1), "结构保证破坏：v2 竟漏掉 v0 的命中！"

    added = sorted(s1 - s0, key=lambda x: -int(x))
    arts = efetch(added) if added else []
    print(f"[efetch 取回新增记录] {len(arts)}")

    cfg = json.load(open(r"D:\trackeep-thoradar\config\journals_taxonomy.json", encoding="utf-8"))
    import thoradar_engine as te
    jm = te.JournalMatcher(cfg)

    gained, outside = [], []
    for a in arts:
        m = jm.match(a["p_issn"], a["e_issn"], a["issn_linking"], a["nlm_id"],
                     a["iso_abbr"], a["journal_title"])
        (gained if m.get("matched") else outside).append((a, m))

    tier_n = {}
    for a, m in gained:
        t = m.get("tier", "?")
        tier_n[t] = tier_n.get(t, 0) + 1
    print(f"[新增且命中 340 本字典] {len(gained)} 篇  分档分布={tier_n}  字典外(照旧被闸掉)={len(outside)}")

    new_terms = [(t, "A") for t in A_NEW] + [(t, "B") for t in B_NEW]
    tally = {t: 0 for t, _ in new_terms}
    for a, _ in gained:
        for t, _g in new_terms:
            if t.lower() in a["text"]:
                tally[t] += 1
    print("\n[新词贡献 · 命中字典的新增文章中含该词的篇数]")
    for t, g in sorted(new_terms, key=lambda x: -tally[x[0]]):
        print(f"  {tally[t]:>4}  {g}组  {t}")

    print("\n[抽样 · 新增字典内文章 40 条（pmid|档|缩写|标题）]")
    for a, m in gained[:40]:
        tier = m.get("tier", "?")
        print(f"  {a['pmid']}|{tier}|{m.get('iso_abbr') or m.get('title','')[:24]}|{a['title'][:110]}")

if __name__ == "__main__":
    main()
