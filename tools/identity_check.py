#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""identity_check.py — ThorRadar 期刊身份查新（NCBI NLM Catalog，eutils）

身份与分区分治（P6）：本脚本只核对刊名 / ISSN / NlmUniqueID 身份信息，
不读不写 tiering 分区；重跑本脚本不清零分区年龄。
分区年龄（tiering.generated_at 与 data_year 距今天数）在报告中独立成节，仅作事实陈述。

用法：
    python tools/identity_check.py                    # 全量查新，写 data/identity_report.json
    python tools/identity_check.py --self-test        # 离线自测三分支退出码（不打网络，不留数据）
    python tools/identity_check.py --api-key XXX      # 或用环境变量 NCBI_API_KEY（不会打印）

退出码：0 = 全部 match；1 = 有 diff；2 = 服务不可达（含连续 3 轮请求全败熔断后的未完成查询）。

NCBI 检索式坑位（实测 2026-10-17）：
  * ISSN 检索须用 '"<issn>"[ISSN]' 带引号加字段标签；
  * 一个 ISSN 可命中多条记录（如 NEJM 主刊 + Overseas Ed 版），须按 NlmUniqueID 挑目标记录；
  * esearch 的 idlist 会丢前导零（0255562 -> "255562"），核对一律用 efetch 正文里的 NlmUniqueID。
"""

import argparse
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DELAY_NO_KEY = 0.4   # 秒/请求，NCBI 无 api_key 礼貌限速
DELAY_WITH_KEY = 0.12  # 有 key 官方上限 10 req/s
RETRIES_PER_REQUEST = 3
BREAKER_ROUNDS = 3   # 连续 3 轮（每轮=单请求重试 3 次全败）不可达即熔断，剩余刊不再硬打
REQUEST_TIMEOUT = 30


class NcbiUnavailable(Exception):
    """NCBI 请求在重试后仍失败。"""


class BreakerOpen(NcbiUnavailable):
    """连续多轮不可达，熔断：不再继续打接口。"""


class NcbiClient:
    """eutils 客户端：限速、重试、熔断。api_key 只用于拼参数，永不打印。"""

    def __init__(self, api_key=None):
        self.api_key = api_key or None
        self.delay = DELAY_WITH_KEY if self.api_key else DELAY_NO_KEY
        self._last_ts = 0.0
        self.fail_rounds = 0

    def _throttle(self):
        wait = self.delay - (time.monotonic() - self._last_ts)
        if wait > 0:
            time.sleep(wait)
        self._last_ts = time.monotonic()

    def _get(self, url):
        for attempt in range(1, RETRIES_PER_REQUEST + 1):
            self._throttle()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "ThorRadar-identity-check/1.0"})
                with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                    body = resp.read()
                self.fail_rounds = 0
                return body
            except (urllib.error.URLError, OSError, TimeoutError) as exc:
                if attempt < RETRIES_PER_REQUEST:
                    time.sleep(0.5 * (2 ** (attempt - 1)))  # 0.5s / 1s 退避
                else:
                    self.fail_rounds += 1
                    if self.fail_rounds >= BREAKER_ROUNDS:
                        raise BreakerOpen(f"连续 {self.fail_rounds} 轮请求失败，熔断: {exc}") from exc
                    raise NcbiUnavailable(f"重试 {RETRIES_PER_REQUEST} 次后仍失败: {exc}") from exc

    def search_by_issn(self, issn):
        """esearch：返回 (uid 列表, 实际检索式)。uid 可能丢前导零，仅用于 efetch 取回正文。"""
        term = f'"{issn}"[ISSN]'
        params = {"db": "nlmcatalog", "term": term, "retmode": "json"}
        if self.api_key:
            params["api_key"] = self.api_key
        url = f"{EUTILS_BASE}/esearch.fcgi?{urllib.parse.urlencode(params)}"
        data = json.loads(self._get(url).decode("utf-8"))
        ids = data.get("esearchresult", {}).get("idlist", [])
        return ids, term

    def fetch_records(self, uids):
        """efetch：批量取记录正文，解析为 dict 列表（NlmUniqueID 保留前导零）。"""
        params = {"db": "nlmcatalog", "id": ",".join(uids), "rettype": "full", "retmode": "xml"}
        if self.api_key:
            params["api_key"] = self.api_key
        url = f"{EUTILS_BASE}/efetch.fcgi?{urllib.parse.urlencode(params)}"
        root = ET.fromstring(self._get(url))
        return [parse_record(rec) for rec in root.findall("NLMCatalogRecord")]


def parse_record(rec):
    """从 NLMCatalogRecord XML 提取身份字段。"""
    def texts(path):
        return [(el.text or "").strip() for el in rec.findall(path) if (el.text or "").strip()]

    nlm_id = (rec.findtext("NlmUniqueID") or "").strip()
    titles_main = texts("TitleMain/Title")
    titles_alt = texts("TitleAlternate/Title")
    medline_ta = (rec.findtext("MedlineTA") or "").strip()
    issns = {"print": [], "electronic": [], "other": []}
    for el in rec.iter("ISSN"):
        val = (el.text or "").strip()
        if not val:
            continue
        kind = (el.get("IssnType") or "other").lower()
        bucket = issns.get(kind)
        if bucket is None:
            bucket = issns["other"]
        bucket.append(val)
    return {
        "nlm_id": nlm_id,
        "titles_main": titles_main,
        "titles_alt": titles_alt,
        "medline_ta": medline_ta,
        "issn_print": issns["print"],
        "issn_electronic": issns["electronic"],
        "issn_other": issns["other"],
    }


def normalize_title(t):
    """刊名归一化：小写、去尾句点、去冠词 the、压空白。"""
    t = " ".join((t or "").split()).lower().rstrip(".")
    if t.startswith("the "):
        t = t[4:]
    return t


def check_journal(j, client, now_iso):
    """核对单刊身份，返回报告条目。只报事实差异，不做猜测性推断。"""
    entry = {
        "id": j.get("id"),
        "local_title": j.get("title"),
        "status": "diff",
        "diffs": [],
        "checked_at": now_iso,
    }
    uids, query = client.search_by_issn(j["p_issn"])
    entry["query"] = query
    if not uids and j.get("e_issn") and j["e_issn"] != j["p_issn"]:
        uids, query2 = client.search_by_issn(j["e_issn"])
        entry["query"] = f"{query} | {query2}"
    if not uids:
        entry["diffs"].append({
            "field": "record",
            "local": j["p_issn"],
            "remote": "not found",
            "note": "NLM Catalog 检索不到该 ISSN 对应记录",
        })
        entry["status"] = "diff"
        return entry

    records = client.fetch_records(uids)
    target = None
    for r in records:
        if r["nlm_id"].lower() == (j.get("nlm_id") or "").lower():
            target = r
            break

    if target is None:
        entry["diffs"].append({
            "field": "nlm_id",
            "local": j.get("nlm_id"),
            "remote": sorted({r["nlm_id"] for r in records}),
            "note": "ISSN 命中记录中无 NlmUniqueID 匹配",
        })
        target = records[0]  # 差异已记；ISSN/刊名继续对第一条命中记录核对，报告注明基准
        entry["checked_against"] = f"nlm_id 不匹配，以下核对基准=记录 {target['nlm_id']}"

    remote_all = set(target["issn_print"]) | set(target["issn_electronic"]) | set(target["issn_other"])
    for field in ("p_issn", "e_issn"):
        local_val = j.get(field)
        if not local_val:
            continue
        bucket = "issn_electronic" if field == "e_issn" else "issn_print"
        matched_kind = target[bucket] if local_val in target[bucket] else (
            remote_all if local_val in remote_all else None)
        if matched_kind is None:
            entry["diffs"].append({
                "field": field,
                "local": local_val,
                "remote": {
                    "print": target["issn_print"],
                    "electronic": target["issn_electronic"],
                    "other(undetermined)": target["issn_other"],
                },
                "note": "NLM 记录 ISSN 集合中未找到该值",
            })
        elif matched_kind is remote_all and local_val not in target[bucket]:
            entry.setdefault("issn_notes", []).append(
                f"{field}={local_val} 仅在记录的非常规 IssnType 中出现（Undetermined/历史值）")

    norm_local = normalize_title(j.get("title"))
    norm_mains = [normalize_title(t) for t in target["titles_main"]]
    norm_alts = [normalize_title(t) for t in target["titles_alt"]]
    if norm_local not in norm_mains:
        diff_item = {
            "field": "title",
            "local": j.get("title"),
            "remote_main": target["titles_main"],
            "note": "归一化后与 TitleMain 不一致",
        }
        if norm_local in norm_alts:
            diff_item["note"] += "；与某 TitleAlternate 一致（低严重度，刊名变更史）"
        entry["diffs"].append(diff_item)

    entry["remote"] = {
        "nlm_id": target["nlm_id"],
        "title_main": target["titles_main"][0] if target["titles_main"] else None,
        "medline_ta": target["medline_ta"],
        "issn_print": target["issn_print"],
        "issn_electronic": target["issn_electronic"],
    }
    entry["status"] = "match" if not entry["diffs"] else "diff"
    return entry


def decide_exit_code(summary):
    """有 diff -> 1；无 diff 有 unreachable -> 2；全 match -> 0。"""
    if summary["diff"] > 0:
        return 1
    if summary["unreachable"] > 0:
        return 2
    return 0


def build_report(journals_cfg, client, config_path, out_path):
    now_iso = datetime.now().astimezone().isoformat(timespec="seconds")
    entries = []
    breaker_note = None
    for j in journals_cfg["journals"]:
        try:
            entries.append(check_journal(j, client, now_iso))
        except NcbiUnavailable as exc:
            entries.append({
                "id": j.get("id"),
                "local_title": j.get("title"),
                "status": "unreachable",
                "diffs": [],
                "error": str(exc),
                "checked_at": now_iso,
            })
            if isinstance(exc, BreakerOpen):
                breaker_note = str(exc)
                break
    if breaker_note:  # 熔断后剩余未查的刊如实标注，不算 diff 也不算查过
        done_ids = {e["id"] for e in entries}
        for j in journals_cfg["journals"]:
            if j["id"] not in done_ids:
                entries.append({
                    "id": j["id"], "local_title": j.get("title"), "status": "unreachable",
                    "diffs": [], "error": "熔断跳过（前置连续不可达）", "checked_at": now_iso,
                })

    summary = {
        "total": len(entries),
        "match": sum(1 for e in entries if e["status"] == "match"),
        "diff": sum(1 for e in entries if e["status"] == "diff"),
        "unreachable": sum(1 for e in entries if e["status"] == "unreachable"),
    }
    summary["exit_code"] = decide_exit_code(summary)

    tiering = journals_cfg.get("tiering", {})
    today = date.today()
    generated_at = tiering.get("generated_at")
    data_year = tiering.get("data_year")
    tiering_age = {
        "note": "重跑本脚本不清零分区年龄：本工具不写 tiering 字段，以下仅为当前年龄的事实陈述",
        "generated_at": generated_at,
        "generated_age_days": (today - date.fromisoformat(generated_at)).days if generated_at else None,
        "data_year": data_year,
        "data_age_days": (today - date(data_year, 12, 31)).days if data_year else None,
        "data_age_anchor": f"{data_year}-12-31（自分区数据标称年份年末起算）" if data_year else None,
    }

    return {
        "tool": "tools/identity_check.py",
        "purpose": "期刊身份查新（刊名/ISSN/NlmUniqueID）；身份核对通过不等于分区已更新",
        "generated_at": now_iso,
        "source": "NCBI NLM Catalog (eutils db=nlmcatalog: esearch '\"<issn>\"[ISSN]' + efetch)",
        "config": str(config_path),
        "output": str(out_path),
        "rate_limit": f"{client.delay}s/请求" + ("（有 api_key）" if client.api_key else "（无 api_key）"),
        "breaker": breaker_note,
        "summary": summary,
        "tiering_age": tiering_age,
        "journals": entries,
    }


# ---------- 离线自测：注入假数据验证三分支退出码，不打网络、不留脏数据 ----------

class FakeClient:
    def __init__(self, records_by_issn, fail=False):
        self.records = records_by_issn
        self.fail = fail
        self.delay = 0
        self.api_key = None

    def search_by_issn(self, issn):
        if self.fail:
            raise NcbiUnavailable("fake: unreachable")
        return list(self.records.get(issn, [])), f'"issn={issn}"[FAKE]'

    def fetch_records(self, uids):
        out = []
        for rec in self._all_records():
            if rec["nlm_id"] in uids:
                out.append(rec)
        return out

    def _all_records(self):
        return [r for recs in self.records.values() for r in recs]


def _fake_record(nlm_id, title, p_issn=None, e_issn=None):
    return {
        "nlm_id": nlm_id, "titles_main": [title], "titles_alt": [],
        "medline_ta": title, "issn_print": [p_issn] if p_issn else [],
        "issn_electronic": [e_issn] if e_issn else [], "issn_other": [],
    }


def self_test():
    """验证 decide_exit_code 三分支＋check_journal 对假数据的判定，输出走临时文件用毕即删。"""
    ok = [0]

    def expect(label, actual, want):
        if actual == want:
            print(f"  PASS {label}: {actual}")
        else:
            print(f"  FAIL {label}: got {actual}, want {want}")
            ok[0] = 1

    # 分支 0：全 match
    good = {"id": "fake_ok", "title": "Journal of Fake Research", "p_issn": "0000-0001",
            "e_issn": "0000-0002", "nlm_id": "0000001"}

    # 直接构造：search 返回固定 uid，fetch 返回预置记录
    class DirectClient(FakeClient):
        def __init__(self, rec, fail=False):
            super().__init__({})
            self.rec = rec
            self.fail = fail
        def search_by_issn(self, issn):
            if self.fail:
                raise NcbiUnavailable("fake: unreachable")
            return ["1000001"], f'"issn={issn}"[FAKE]'
        def fetch_records(self, uids):
            return [self.rec] if uids else []

    rec_match = _fake_record("0000001", "Journal of fake research.", p_issn="0000-0001", e_issn="0000-0002")
    cfg = {"journals": [good], "tiering": {"generated_at": "2026-10-15", "data_year": 2025}}
    report = build_report(cfg, DirectClient(rec_match), Path("fake_cfg"), Path("fake_out"))
    expect("全 match 场景退出码", report["summary"]["exit_code"], 0)
    expect("全 match 场景状态", report["journals"][0]["status"], "match")

    # 分支 1：假 diff（nlm_id 对但 e_issn 缺失＋刊名不同）
    bad = {"id": "fake_bad", "title": "Journal of Wrong Name", "p_issn": "0000-0003",
           "e_issn": "0000-0004", "nlm_id": "0000002"}
    rec_diff = _fake_record("0000002", "Journal of something else.", p_issn="0000-0003")
    cfg2 = {"journals": [bad], "tiering": cfg["tiering"]}
    report2 = build_report(cfg2, DirectClient(rec_diff), Path("fake_cfg"), Path("fake_out"))
    expect("假 diff 场景退出码", report2["summary"]["exit_code"], 1)
    expect("假 diff 场景状态", report2["journals"][0]["status"], "diff")
    diff_fields = sorted(d["field"] for d in report2["journals"][0]["diffs"])
    expect("假 diff 捕获字段", diff_fields, ["e_issn", "title"])

    # 分支 2：服务不可达
    cfg3 = {"journals": [good], "tiering": cfg["tiering"]}
    report3 = build_report(cfg3, DirectClient(rec_match, fail=True), Path("fake_cfg"), Path("fake_out"))
    expect("全不可达场景退出码", report3["summary"]["exit_code"], 2)
    expect("全不可达场景状态", report3["journals"][0]["status"], "unreachable")

    # 报告落盘结构可读（临时文件，用毕即删，不在 git 库内）
    tmp = Path(tempfile.gettempdir()) / f"identity_check_selftest_{os.getpid()}.json"
    try:
        tmp.write_text(json.dumps(report2, ensure_ascii=False, indent=2), encoding="utf-8")
        roundtrip = json.loads(tmp.read_text(encoding="utf-8"))
        expect("临时报告读写往返", roundtrip["summary"]["exit_code"], 1)
    finally:
        if tmp.exists():
            tmp.unlink()

    print(f"self-test {'PASS' if ok[0] == 0 else 'FAIL'}（退出码 {ok[0]}）")
    return ok[0]


def main():
    ap = argparse.ArgumentParser(description="ThorRadar 期刊身份查新（NCBI NLM Catalog）")
    ap.add_argument("--config", default=None, help="期刊字典路径（默认 <仓根>/config/journals_taxonomy.json）")
    ap.add_argument("--output", default=None, help="报告输出路径（默认 <仓根>/data/identity_report.json）")
    ap.add_argument("--api-key", default=None, help="NCBI api_key（默认读环境变量 NCBI_API_KEY；不打印）")
    ap.add_argument("--self-test", action="store_true", help="离线自测三分支退出码，不打网络不留数据")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())

    repo_root = Path(__file__).resolve().parent.parent
    config_path = Path(args.config) if args.config else repo_root / "config" / "journals_taxonomy.json"
    out_path = Path(args.output) if args.output else repo_root / "data" / "identity_report.json"

    api_key = args.api_key or os.environ.get("NCBI_API_KEY") or None
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    client = NcbiClient(api_key=api_key)
    report = build_report(cfg, client, config_path, out_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    s = report["summary"]
    print(f"身份查新完成：{s['match']} match / {s['diff']} diff / {s['unreachable']} unreachable（共 {s['total']} 刊）")
    print(f"报告：{out_path}")
    for e in report["journals"]:
        mark = {"match": "OK ", "diff": "DIFF", "unreachable": "UNRC"}[e["status"]]
        line = f"  [{mark}] {e['id']}"
        if e["status"] == "diff":
            line += " — " + "; ".join(d["field"] for d in e["diffs"])
        if e["status"] == "unreachable":
            line += " — " + e.get("error", "")
        print(line)
    sys.exit(s["exit_code"])


if __name__ == "__main__":
    main()
