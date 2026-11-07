# -*- coding: utf-8 -*-
"""roster_intake_check.py — 门禁件① 进门验收器（意志书 v1.1 批件）。

新表进门时校验四关（任一硬伤即 fail-closed 退回，退出码 1）：
  1. 行数守恒：对基准册总数带宽 ±5%（意志书四.3）；基准行若被删，必须在封存档有账
     （删减走退役冻结正门，意志书四.1）；新进行必须带 src 溯源（写盘留名）。
  2. 五键齐全：ISSN-L／P-ISSN／E-ISSN／NLM ID／ISO 缩写五重身份键（引擎 JournalMatcher
     五重索引同源）字段齐全；NLM ID 逐行必填（意志书「全以 NLM ID 硬锚」＋C2 宁缺勿假）；
     五键任一维度重复＝查重红线（年检法§七.1）。缺 ISO/ISSN 只告警（现册有 6/5 行先例）。
  3. 档位合法值：tier_new ∈ {S,A,B,C,D}；category ∈ 1-10＋11(2026-11-07 拆分)＋待定；
     bonus_map＝15/12/8/0/0（三.1）；待定上限 30（一.8）。
  4. 钉表刊全在：附录 A 钉表＋漂移台账 ↔ 新册零漂移（单源＝tools/thoradar_pins.py）。

用法：
  E:/Python/python.exe -X utf8 -I tools/roster_intake_check.py --table <新表.json> \
      [--baseline config/journals_taxonomy.json] [--json-out <验.json>]
退出码：0 全过；1 有硬伤（fail-closed 保旧册）。
⚠ 动表前必读意志书并对拍附录 A（意志书 v1.1 地形表「消费方接线」）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.stdout.reconfigure(encoding="utf-8")

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import thoradar_pins as pins  # noqa: E402

ROOT = TOOLS_DIR.parent
CONFIG_PATH = ROOT / "config" / "journals_taxonomy.json"
SEAL_PATH = ROOT / "design" / "名册封存-20261101.json"
FIVE_KEYS = ("issn_l", "p_issn", "e_issn", "nlm_id", "iso_abbr")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_row_count(new_rows: List[Dict], base_rows: List[Dict],
                    sealed_rows: List[Dict]) -> Tuple[List[str], List[str]]:
    hard, warn = [], []
    base_by_key = pins.index_by_nlm(base_rows)
    base_names = pins.name_form_set(base_rows)
    new_keys = set(pins.index_by_nlm(new_rows))
    new_names = set(pins.name_form_set(new_rows))
    sealed_keys = set(pins.index_by_nlm(sealed_rows))
    sealed_names = set(pins.name_form_set(sealed_rows))

    def accounted(j: Dict) -> bool:
        nlm = str(j.get("nlm_id") or "").strip()
        if nlm and nlm in sealed_keys:
            return True
        forms = {pins.norm(x) for x in [j.get("name")] + list(j.get("name_aliases") or [])}
        return bool(forms & sealed_names)

    # 总数带宽 ±5%（意志书四.3）
    if base_rows:
        delta = (len(new_rows) - len(base_rows)) / len(base_rows)
        if abs(delta) > pins.TOTAL_BAND_PCT:
            hard.append(f"行数守恒: 新册 {len(new_rows)} 行对基准 {len(base_rows)} 行偏差 "
                        f"{delta:+.1%}，超出 ±5% 带宽（四.3）")
    # 删除须有封存账（退役冻结正门，四.1）
    unaccounted = []
    for nlm, j in base_by_key.items():
        if nlm in new_keys:
            continue
        forms = {pins.norm(x) for x in [j.get("name")] + list(j.get("name_aliases") or [])}
        if not (forms & new_names):
            if not accounted(j):
                unaccounted.append(f"{j.get('name')}(NLM {nlm})")
    if unaccounted:
        hard.append(f"行数守恒: {len(unaccounted)} 行基准刊被删且封存档无账（退役须走冻结正门）："
                    f"{unaccounted[:5]}")
    # 新进必带 src 溯源
    no_src = [j.get("id") or j.get("name") for j in new_rows
              if str(j.get("nlm_id") or "").strip() not in base_by_key
              and pins.norm(j.get("name")) not in base_names
              and not str(j.get("src") or "").strip()]
    if no_src:
        hard.append(f"行数守恒: {len(no_src)} 行新增刊缺 src 溯源（写盘留名）：{no_src[:5]}")
    return hard, warn


def check_five_keys(rows: List[Dict]) -> Tuple[List[str], List[str]]:
    hard, warn = [], []
    for i, j in enumerate(rows):
        rid = j.get("id") or f"#{i}"
        for k in FIVE_KEYS:
            if k not in j:
                hard.append(f"五键齐全: 行 {rid} 缺字段 {k}")
        if not str(j.get("nlm_id") or "").strip():
            hard.append(f"五键齐全: 行 {rid}（{j.get('name')}）NLM ID 空——意志书硬锚＋C2 宁缺勿假")
        if not (str(j.get("iso_abbr") or "").strip()
                or str(j.get("issn_l") or "").strip()
                or str(j.get("p_issn") or "").strip()
                or str(j.get("e_issn") or "").strip()):
            warn.append(f"五键齐全: 行 {rid}（{j.get('name')}）ISO 缩写与三 ISSN 全空，仅剩 NLM 弱身份")
    # 五键任一维度跨行重复＝查重红线（年检法§七.1）
    for k in FIVE_KEYS:
        cnt = Counter(str(j.get(k, "")).strip().upper() for j in rows
                      if str(j.get(k, "")).strip())
        for val, n in cnt.items():
            if n > 1:
                hard.append(f"五键齐全: {k}={val} 重复 {n} 行（查重红线）")
    return hard, warn


def check_legal_values(doc: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    hard, warn = [], []
    rows = doc.get("journals") or []
    for j in rows:
        rid = j.get("id") or j.get("name")
        tn = j.get("tier_new")
        if tn not in pins.TIERS_LEGAL:
            hard.append(f"档位合法值: 行 {rid} tier_new={tn!r} ∉ {pins.TIERS_LEGAL}")
        t = j.get("tier")
        if t is not None and t not in pins.TIERS_LEGAL:
            hard.append(f"档位合法值: 行 {rid} tier={t!r} ∉ {pins.TIERS_LEGAL}")
        cat = str(j.get("category", ""))
        if cat not in pins.CATEGORIES_LEGAL:
            hard.append(f"档位合法值: 行 {rid} category={cat!r} ∉ 1-10＋11(拆分)＋待定")
    tiers = doc.get("tiers") or {}
    got_bonus = {k: v.get("score_bonus") for k, v in tiers.items() if isinstance(v, dict)}
    if got_bonus != pins.BONUS_MAP_WILL:
        hard.append(f"档位合法值: bonus_map={got_bonus}≠意志书 {pins.BONUS_MAP_WILL}（三.1）")
    axis = doc.get("category_axis") or {}
    if axis.get("pending_cap") != pins.PENDING_CAP_WILL:
        hard.append(f"档位合法值: 待定上限 {axis.get('pending_cap')}≠{pins.PENDING_CAP_WILL}（一.8）")
    return hard, warn


def main() -> int:
    ap = argparse.ArgumentParser(
        description="门禁件① 进门验收器：新表进门四关（行数守恒/五键齐全/档位合法值/钉表刊全在）")
    ap.add_argument("--table", required=True, help="待验收的新表 config JSON 路径")
    ap.add_argument("--baseline", default=str(CONFIG_PATH), help="基准册（默认现行 config）")
    ap.add_argument("--seal", default=str(SEAL_PATH), help="封存档（默认 design/名册封存-20261101.json）")
    ap.add_argument("--json-out", default=None, help="验收结论 JSON 落盘路径（可选）")
    args = ap.parse_args()

    hard: List[str] = []
    warn: List[str] = []
    try:
        new_doc = json.loads(Path(args.table).read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] 新表不可读：{type(e).__name__}: {e}")
        return 1
    base_doc = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    seal_doc = json.loads(Path(args.seal).read_text(encoding="utf-8"))
    new_rows = new_doc.get("journals") or []
    base_rows = base_doc.get("journals") or []
    sealed_rows = seal_doc.get("journals") or []

    h, w = check_row_count(new_rows, base_rows, sealed_rows)
    hard += h
    warn += w
    h, w = check_five_keys(new_rows)
    hard += h
    warn += w
    h, w = check_legal_values(new_doc)
    hard += h
    warn += w

    findings = pins.audit_pins(new_rows, sealed_rows)
    hard += findings
    hard += pins.audit_seal_integrity(seal_doc)

    verdict = {
        "table": str(args.table),
        "table_sha256": sha256_file(Path(args.table)),
        "table_version": new_doc.get("version"),
        "rows": len(new_rows),
        "baseline_rows": len(base_rows),
        "pass": not hard,
        "hard_findings": hard,
        "warnings": warn,
        "amendment_ledger": pins.AMENDMENT_LEDGER,
        "basis": "意志书 v1.1 附录 A＋四.1/四.3/一.8/三.1；单源 tools/thoradar_pins.py",
    }
    out = json.dumps(verdict, ensure_ascii=False, indent=1)
    if args.json_out:
        Path(args.json_out).write_text(out, encoding="utf-8")
    if hard:
        print(f"[FAIL] 进门验收不过（{len(hard)} 硬伤，fail-closed 保旧册）：")
        for f in hard[:20]:
            print(f"  ✗ {f}")
        if len(hard) > 20:
            print(f"  …共 {len(hard)} 条（详见 --json-out）")
        for w in warn[:5]:
            print(f"  ⚠ {w}")
        return 1
    print(f"[PASS] 进门验收四关全过：{len(new_rows)} 行（基准 {len(base_rows)}），"
          f"版本 {new_doc.get('version')}，告警 {len(warn)} 条")
    for w in warn:
        print(f"  ⚠ {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
