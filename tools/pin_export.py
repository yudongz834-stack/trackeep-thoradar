# -*- coding: utf-8 -*-
"""pin_export.py — 门禁件③ 钉表导出器（意志书 v1.1 批件）。

从现行册导出钉表快照＋SHA256（机读哈希件＝衍生，修订单「弃用记录」明载；书是人志）。
快照含：config 字节级 SHA256＋版本＋附录 A 各钉组在活册/封存档的逐刊落位。供
pin_reconcile.py 做「上次导出 ↔ 现行」增量漂移对账，也让每次动钉 commit 自带对价实物。

用法：
  E:/Python/python.exe -X utf8 -I tools/pin_export.py [--config ...] [--out data/pin_snapshot.json]
⚠ 动钉表前必读意志书并对拍附录 A（意志书 v1.1 地形表「消费方接线」）；改钉＝意志变更（六.2）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

sys.stdout.reconfigure(encoding="utf-8")

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import thoradar_pins as pins  # noqa: E402

ROOT = TOOLS_DIR.parent
CONFIG_PATH = ROOT / "config" / "journals_taxonomy.json"
SEAL_PATH = ROOT / "design" / "名册封存-20261101.json"
DEFAULT_OUT = ROOT / "data" / "pin_snapshot.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pin_row(nlm: str, where: str, j: Dict[str, Any] = None) -> Dict[str, Any]:
    row: Dict[str, Any] = {"nlm_id": nlm, "where": where}
    if j is not None:
        row.update({
            "name": j.get("name"),
            "name_norm": pins.norm(j.get("name")),
            "tier_new": j.get("tier_new"),
            "category": str(j.get("category", "")),
            "tier_rule": j.get("tier_rule"),
            "src": j.get("src"),
        })
    return row


def export_snapshot(config_doc: Dict[str, Any], seal_doc: Dict[str, Any],
                    config_sha256: str) -> Dict[str, Any]:
    live = pins.index_by_nlm(config_doc.get("journals") or [])
    sealed = pins.index_by_nlm(seal_doc.get("journals") or [])
    live_forms = pins.name_form_set(config_doc.get("journals") or [])

    groups: Dict[str, List[Dict[str, Any]]] = {}

    def fill(group: str, table: Dict[str, str], expect: str) -> None:
        rows = []
        for nlm, name in table.items():
            src_doc = live if expect == "live" else sealed
            rows.append(_pin_row(nlm, expect, src_doc.get(nlm)))
        groups[group] = rows

    fill("S七刊", {k: v for k, v in pins.S_PINS.items()}, "live")
    fill("冠冕三刊", dict(pins.CROWN_PINS), "live")
    fill("量控六刊(留册)", dict(pins.Q_CTRL_LIVE), "live")
    fill("量控六刊(封存)", dict(pins.Q_CTRL_SEALED), "sealed")
    fill("平台16(封存)", dict(pins.PLATFORM_16_SEALED), "sealed")
    fill("判例九(留册)", {k: v[0] for k, v in pins.PRECEDENT_LIVE.items()}, "live")
    fill("判例九(封存)", {k: v[0] for k, v in pins.PRECEDENT_SEALED.items()}, "sealed")
    fill("裁定五(留册)", {k: v[0] for k, v in pins.ADJUDICATED_LIVE.items()}, "live")
    fill("裁定五(封存)", {k: v[0] for k, v in pins.ADJUDICATED_SEALED.items()}, "sealed")
    # 不收十：记缺席证词（快照时点两册均无此名形）
    groups["不收十(缺席)"] = [
        {"name": n, "name_norm": pins.norm(n),
         "absent_live": pins.norm(n) not in live_forms,
         "absent_sealed": pins.norm(n) not in pins.name_form_set(seal_doc.get("journals") or [])}
        for n in pins.NOT_ACCEPTED_10
    ]

    return {
        "schema": "thoradar-pin-snapshot/1",
        "exported_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "config_version": config_doc.get("version"),
        "config_sha256": config_sha256,
        "seal_count": seal_doc.get("count"),
        "basis": "意志书 v1.1 附录 A＋AMENDMENT_LEDGER（单源 tools/thoradar_pins.py）；衍生机读件",
        "amendment_ledger": pins.AMENDMENT_LEDGER,
        "groups": groups,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="门禁件③ 钉表导出器：导出钉表快照＋SHA256")
    ap.add_argument("--config", default=str(CONFIG_PATH))
    ap.add_argument("--seal", default=str(SEAL_PATH))
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="快照落盘路径（默认 data/pin_snapshot.json）")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    seal_path = Path(args.seal)
    config_doc = json.loads(cfg_path.read_text(encoding="utf-8"))
    seal_doc = json.loads(seal_path.read_text(encoding="utf-8"))
    sha = sha256_file(cfg_path)
    snap = export_snapshot(config_doc, seal_doc, sha)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(out_path) + ".tmp")
    tmp.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(out_path)

    total = sum(len(v) for v in snap["groups"].values())
    print(f"[OK] 钉表快照已导出：{out_path}")
    print(f"     config={cfg_path.name} version={snap['config_version']} sha256={sha[:16]}…")
    print(f"     钉组 {len(snap['groups'])} 组共 {total} 行（附录 A＋台账口径，不收十记缺席证词）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
