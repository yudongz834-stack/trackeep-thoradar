# -*- coding: utf-8 -*-
"""weekly_gate_columns.py — 门禁件⑤ 周检扩展列（意志书 v1.1 批件）。

在周六周检（tools/journal_qc.py）之外增算四列，落 data/journal_gate_columns.json 供
workflow 提交与首页一行通报（意志书四.7 通报必达）：
  新刊计数     进册新行（不在封存档且 src 非历史源集＝自动进册管道产物，四.2）
  红灯立案数   健康红灯（≥100 天静默，引擎 HEALTH_RED_DAYS 同口径；先读周检报告，缺则自算）
  预警名单交集 预警源（config warned 位＋停挂台账＋红灯名单）∩ 活册（四.4 只挂徽不改档）
  量控建议列   高量线 B/C 档年发文≥3,000 → 量控候选；低量线年发文<10 → 降 D 建议列
              （四.5：改量控名单＝意志变更唯 PI；只列不改，永不自动动档）

用法：E:/Python/python.exe -X utf8 -I tools/weekly_gate_columns.py [--out data/journal_gate_columns.json]
只读 config/design/data，唯一写点＝--out 一个 JSON（账外不写产线）。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List

sys.stdout.reconfigure(encoding="utf-8")

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import thoradar_pins as pins  # noqa: E402

ROOT = TOOLS_DIR.parent
CONFIG_PATH = ROOT / "config" / "journals_taxonomy.json"
SEAL_PATH = ROOT / "design" / "名册封存-20261101.json"
QC_REPORT = ROOT / "design" / "journal-qc-report.json"
HEALTH_JSON = ROOT / "data" / "journal_health.json"
SUSPENDED_JSON = ROOT / "data" / "journal_suspended.json"
DEFAULT_OUT = ROOT / "data" / "journal_gate_columns.json"

HEALTH_RED_DAYS = 100   # 与引擎 HEALTH_RED_DAYS 同口径（年检法§六）
KNOWN_HISTORICAL_SRC = {  # 2026-11-08 盘面实测历史源集；此集之外的 src＝新进册管道产物
    "walk", "carry", "walk+crown-pin-20261101", "zotero-pin-20261102", "review-pin-20261102",
}


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 缺件降级：列记缺失，不拦周检
        return default


def new_journal_column(live_rows: List[Dict], sealed_rows: List[Dict]) -> Dict[str, Any]:
    sealed_nlm = set(pins.index_by_nlm(sealed_rows))
    rows = [j for j in live_rows
            if str(j.get("nlm_id") or "").strip() not in sealed_nlm
            and str(j.get("src") or "").strip() not in KNOWN_HISTORICAL_SRC]
    return {"count": len(rows),
            "rows": [{"id": j.get("id"), "name": j.get("name"), "src": j.get("src")} for j in rows],
            "口径": "活册 ∖ 封存档，且 src ∉ 历史源集（四.2 自动进册产物）"}


def red_light_column(qc_doc: Dict[str, Any], health: Dict[str, str],
                     today: date) -> Dict[str, Any]:
    qc_health = qc_doc.get("journal_health") or {}
    red_names = list(qc_health.get("red") or [])
    source = "design/journal-qc-report.json（周六周检口径）"
    if not red_names and health:
        def age(iso: str) -> int:
            try:
                return (today - date.fromisoformat(str(iso))).days
            except ValueError:
                return 10 ** 6
        red_names = sorted(n for n, d in health.items() if age(d) >= HEALTH_RED_DAYS)
        source = f"data/journal_health.json（自算 ≥{HEALTH_RED_DAYS} 天）"
    return {"count": len(red_names), "red": red_names[:50], "source": source}


def warning_intersection_column(live_rows: List[Dict], health: Dict[str, str],
                                qc_doc: Dict[str, Any],
                                suspended: Dict[str, Any]) -> Dict[str, Any]:
    warned: Dict[str, str] = {}
    for j in live_rows:  # 源1：config warned 位（引擎打标）
        if j.get("warned"):
            warned[str(j.get("nlm_id") or pins.norm(j.get("name")))] = f"config warned 位（{j.get('name')}）"
    for k in (suspended or {}):  # 源2：停挂台账（引擎 load_suspended）
        warned[pins.norm(k)] = f"停挂台账（{k}）"
    for n in (qc_doc.get("journal_health") or {}).get("red") or []:  # 源3：红灯＝预警候选（四.4）
        warned[pins.norm(n)] = f"健康红灯（{n}）"
    live_by_nlm = pins.index_by_nlm(live_rows)
    live_forms = pins.name_form_set(live_rows)
    hits = []
    for key, why in sorted(warned.items()):
        j = live_by_nlm.get(key) or live_forms.get(pins.norm(key))
        if j is not None:
            hits.append({"name": j.get("name"), "source": why})
    return {"count": len(hits), "rows": hits,
            "口径": "预警源（warned 位∪停挂台账∪红灯）∩ 活册；只挂徽不改档（四.4）"}


def volume_control_column(live_rows: List[Dict], qc_doc: Dict[str, Any]) -> Dict[str, Any]:
    vol_by_nlm = {str(r.get("nlm_id") or ""): r.get("vol_365")
                  for r in qc_doc.get("results") or []}
    live_by_nlm = pins.index_by_nlm(live_rows)
    high, low = [], []
    for nlm, vol in vol_by_nlm.items():
        j = live_by_nlm.get(nlm)
        if j is None or not isinstance(vol, (int, float)):
            continue
        tier = j.get("tier_new")
        suspect = vol > 100000  # 超常见年发文上界（顶刊年量数千、最大水刊约数万）＝疑检索键漂移
        if tier in ("B", "C") and vol >= pins.VOL_HIGH_LINE:
            high.append({"name": j.get("name"), "tier_new": tier, "vol_365": vol,
                         "suspect": suspect})
        if vol < pins.VOL_LOW_LINE:
            low.append({"name": j.get("name"), "tier_new": tier, "vol_365": vol})
    if any(r.get("suspect") for r in high):
        high.append({"suspect_note": "带 suspect=true 行年发文超常见上界，疑周检检索键漂移，先人工核再谈量控"})
    return {
        "高量线_量控候选": high,
        "低量线_降D建议列": low,
        "口径": (f"B/C 档年发文≥{pins.VOL_HIGH_LINE} → 量控候选（改量控名单＝意志变更，唯 PI）；"
                 f"年发文<{pins.VOL_LOW_LINE} → 只出降 D 建议列；永不自动动档（四.5）"),
        "未实现": "同比涨≥50% 线：缺两年 vol 数据源，暂只跑绝对线 3,000（遗留，见交付回报）",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="门禁件⑤ 周检扩展列：新刊计数/红灯立案数/预警交集/量控建议列")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="落盘路径（默认 data/journal_gate_columns.json）")
    args = ap.parse_args()

    config_doc = load_json(CONFIG_PATH, None)
    if config_doc is None:
        print(f"[FAIL] config 不可读：{CONFIG_PATH}")
        return 1
    live_rows = config_doc.get("journals") or []
    seal_doc = load_json(SEAL_PATH, {})
    qc_doc = load_json(QC_REPORT, {})
    health = load_json(HEALTH_JSON, {})
    suspended = load_json(SUSPENDED_JSON, {})

    columns = {
        "schema": "thoradar-gate-columns/1",
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "config_version": config_doc.get("version"),
        "新刊计数": new_journal_column(live_rows, seal_doc.get("journals") or []),
        "红灯立案数": red_light_column(qc_doc, health, datetime.now().date()),
        "预警名单交集": warning_intersection_column(live_rows, health, qc_doc, suspended),
        "量控建议列": volume_control_column(live_rows, qc_doc),
        "依据": "意志书 v1.1 四.2/四.4/四.5/四.7；阈值单源 tools/thoradar_pins.py",
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(out_path) + ".tmp")
    tmp.write_text(json.dumps(columns, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(out_path)

    # 首页一行通报（四.7 必达）
    high_rows = columns["量控建议列"]["高量线_量控候选"]
    high_n = sum(1 for r in high_rows if r.get("name"))
    print(f"[周检门禁列] 新刊 {columns['新刊计数']['count']}｜红灯立案 {columns['红灯立案数']['count']}"
          f"｜预警交集 {columns['预警名单交集']['count']}｜量控候选 {high_n}"
          f"／降D建议 {len(columns['量控建议列']['低量线_降D建议列'])} → {out_path}")
    if columns["新刊计数"]["count"]:
        for r in columns["新刊计数"]["rows"][:5]:
            print(f"  · 新刊：{r['name']}（src={r['src']}）")
    if columns["红灯立案数"]["count"]:
        for n in columns["红灯立案数"]["red"][:5]:
            print(f"  · 红灯：{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
