# -*- coding: utf-8 -*-
"""pin_reconcile.py — 门禁件③ 书码对拍（意志书四.6「本件的眼睛」）。

对拍三路，失配即 fail-closed（退出码 1，保旧册停更报警）：
  A. 意志书附录 A 钉表 ↔ config 现行（零漂移判据；单源 tools/thoradar_pins.py，
     含 AMENDMENT_LEDGER 已批漂移台账——台账外漂移＝红）；
  B. 意志书硬数字 ↔ config：bonus 15/12/8/0/0（三.1）、待定上限 30（一.8）、
     席定钉计数 42（二.4，AST 复算 classify.py JUDGMENT_PINS，正本不可达即红）；
  C. 上次导出快照 ↔ config 现行（--snapshot；字节级 SHA256 不同则逐刊定位漂移）。

⚠ 动钉表前必读意志书并对拍附录 A（意志书 v1.1 地形表「消费方接线」＋修订单 B4；
   意志书正本：E:\\trackeep-backup\\thoradar-will\\意志书-期刊体系-20261031.md）。
用法：
  E:/Python/python.exe -X utf8 -I tools/pin_reconcile.py [--snapshot data/pin_snapshot.json]
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.stdout.reconfigure(encoding="utf-8")

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import thoradar_pins as pins  # noqa: E402
from pin_export import DEFAULT_OUT, sha256_file  # noqa: E402

ROOT = TOOLS_DIR.parent
CONFIG_PATH = ROOT / "config" / "journals_taxonomy.json"
SEAL_PATH = ROOT / "design" / "名册封存-20261101.json"
CLASSIFY_PY = Path(r"D:\workbench\thoradar-journal-class\classify.py")  # 意志书地形表正本位


def count_dict_assign(path: Path, var: str) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == var:
                    return len(ast.literal_eval(node.value))
    raise AssertionError(f"{path} 里找不到模块级赋值 {var}")


def snapshot_diff(snapshot: Dict[str, Any], live_by_nlm: Dict[str, Dict[str, Any]],
                  sealed_by_nlm: Dict[str, Dict[str, Any]]) -> List[str]:
    """快照 ↔ 现行逐刊落位比对：where/tier/category 变了就报。"""
    diffs: List[str] = []
    for group, rows in (snapshot.get("groups") or {}).items():
        for row in rows:
            nlm = str(row.get("nlm_id") or "")
            if not nlm:
                continue  # 不收十缺席证词行无 nlm
            exp_where = row.get("where")
            j = live_by_nlm.get(nlm) if exp_where == "live" else sealed_by_nlm.get(nlm)
            if j is None:
                diffs.append(f"{group}: 钉刊 {row.get('name')}（NLM {nlm}）不在快照记录的落位 {exp_where}")
                continue
            for field in ("tier_new", "category", "tier_rule"):
                old_v, new_v = row.get(field), j.get(field)
                if field == "category":
                    old_v, new_v = str(old_v), str(new_v)
                if old_v != new_v:
                    diffs.append(f"{group}: {row.get('name')} {field} {old_v!r}→{new_v!r}（快照后漂移）")
    return diffs


def main() -> int:
    ap = argparse.ArgumentParser(
        description="门禁件③ 书码对拍：意志书附录 A ↔ config 现行 ↔ 导出快照（零漂移判据）")
    ap.add_argument("--config", default=str(CONFIG_PATH))
    ap.add_argument("--seal", default=str(SEAL_PATH))
    ap.add_argument("--snapshot", default=None,
                    help=f"上次导出快照（默认 {DEFAULT_OUT.name}，存在才比对；--no-snapshot 跳过）")
    ap.add_argument("--no-snapshot", action="store_true", help="跳过 C 路快照比对")
    ap.add_argument("--classify-py", default=str(CLASSIFY_PY),
                    help="席定钉正本 classify.py 路径（AST 复算 42，不可达即红）")
    args = ap.parse_args()

    findings: List[str] = []
    config_doc = json.loads(Path(args.config).read_text(encoding="utf-8"))
    seal_doc = json.loads(Path(args.seal).read_text(encoding="utf-8"))
    live_rows = config_doc.get("journals") or []
    sealed_rows = seal_doc.get("journals") or []
    live_by_nlm = pins.index_by_nlm(live_rows)
    sealed_by_nlm = pins.index_by_nlm(sealed_rows)

    # A 路：附录 A＋台账 ↔ 册面
    findings += pins.audit_pins(live_rows, sealed_rows)
    findings += pins.audit_seal_integrity(seal_doc)

    # B 路：意志书硬数字
    got_bonus = {k: v.get("score_bonus") for k, v in (config_doc.get("tiers") or {}).items()
                 if isinstance(v, dict)}
    if got_bonus != pins.BONUS_MAP_WILL:
        findings.append(f"硬数字: bonus_map={got_bonus}≠意志书 {pins.BONUS_MAP_WILL}（三.1）")
    cap = (config_doc.get("category_axis") or {}).get("pending_cap")
    if cap != pins.PENDING_CAP_WILL:
        findings.append(f"硬数字: 待定上限 {cap}≠{pins.PENDING_CAP_WILL}（一.8）")
    classify_py = Path(args.classify_py)
    if not classify_py.exists():
        findings.append(f"硬数字: 席定钉正本不可达 {classify_py}——书码对拍失眼即停（四.6）")
    else:
        try:
            n = count_dict_assign(classify_py, "JUDGMENT_PINS")
            if n != pins.JUDGMENT_PIN_COUNT_WILL:
                findings.append(f"硬数字: classify.py JUDGMENT_PINS={n}≠意志书 42（二.4）")
        except Exception as e:  # noqa: BLE001
            findings.append(f"硬数字: 席定钉计数复算失败 {type(e).__name__}: {e}")

    # C 路：快照 ↔ 现行
    snap_path: Optional[Path] = None
    if not args.no_snapshot:
        snap_path = Path(args.snapshot) if args.snapshot else DEFAULT_OUT
        if snap_path.exists():
            snap = json.loads(snap_path.read_text(encoding="utf-8"))
            sha_now = sha256_file(Path(args.config))
            if snap.get("config_sha256") != sha_now:
                print(f"[i] config SHA256 较快照已变（{str(snap.get('config_sha256'))[:12]}… → {sha_now[:12]}…），逐刊定位：")
            findings += snapshot_diff(snap, live_by_nlm, sealed_by_nlm)
        else:
            print(f"[i] 未找到快照 {snap_path}（先跑 pin_export.py），C 路跳过")

    if findings:
        print(f"[FAIL] 书码对拍失配 {len(findings)} 条——fail-closed 保旧册停更（意志书四.6）：")
        for f in findings[:20]:
            print(f"  ✗ {f}")
        if len(findings) > 20:
            print(f"  …共 {len(findings)} 条")
        return 1
    print(f"[PASS] 书码对拍零漂移：附录 A 钉表＋硬数字（bonus/待定上限/席定钉 42）＋"
          f"{'快照' if snap_path and snap_path.exists() else '无快照(跳过)'} 全对齐；"
          f"活册 {len(live_rows)} 行 config={Path(args.config).name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
