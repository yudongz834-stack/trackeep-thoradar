# -*- coding: utf-8 -*-
"""期刊产出率周表（方案 v2 排期①·产出数据即刻起跑）：
从日档收录 + 拒件日志复算每刊「送审/收录/产出率」，落 data/journal_yield.json。
周六周检随跑；裁刊评审（2027-02-01）吃 90 天累计——篇数是唯一样本口径（codex 三先决之一）。
用法：python tools/journal_yield.py [窗口天数，默认 90]
"""
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WINDOW = int(sys.argv[1]) if len(sys.argv) > 1 else 90
cutoff = (date.today() - timedelta(days=WINDOW)).isoformat()

kept = defaultdict(int)
for f in sorted((ROOT / "data" / "archive").glob("*.json")):
    if f.stem < cutoff or "-mesh" in f.stem:      # 只算窗口内（弃旧）
        continue
    for p in json.loads(f.read_text(encoding="utf-8")).get("papers", []):
        kept[(p.get("journal_abbr") or p.get("journal_title") or "?").strip()] += 1

rej = defaultdict(int)
for f in sorted((ROOT / "data" / "prescreen_rejected").glob("*.json")):
    if f.stem < cutoff:
        continue
    for r in json.loads(f.read_text(encoding="utf-8")).get("rejected", []):
        rej[(r.get("ta") or "?").strip()] += 1

rows = []
for ta in set(kept) | set(rej):
    k, r = kept.get(ta, 0), rej.get(ta, 0)
    rows.append({"ta": ta, "kept": k, "sent": k + r,
                 "yield": round(k / (k + r), 3) if k + r else 0.0})
rows.sort(key=lambda x: (-x["kept"], -x["sent"]))
out = {"window_days": WINDOW, "cutoff": cutoff, "computed_at": date.today().isoformat(),
       "journals": rows}
(ROOT / "data" / "journal_yield.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

zero = [r for r in rows if r["kept"] == 0 and r["sent"] >= 10]
invest = [r for r in rows if r["kept"] == 0 and 100 <= r["sent"] < 300]
print(f"窗口 {WINDOW} 天｜有记录刊 {len(rows)}｜零产出(送审≥10) {len(zero)}｜"
      f"够调查线(≥100 篇) {len(invest)}｜够裁线(≥300 篇) {len([r for r in rows if r['kept'] == 0 and r['sent'] >= 300])}")
print("产出前 5：", [(r['ta'], r['kept']) for r in rows[:5]])
