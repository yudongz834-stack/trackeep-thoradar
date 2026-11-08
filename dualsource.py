"""ThorRadar 双源模块二：断路器、三级路由、幂等合并。

契约正本：contract.md「模块二 dualsource.py」。
本模块不 import thoradar_engine，也不依赖 epmc_adapter。Record 是普通 dict。

上游语义（只理解、不耦合）：thoradar_engine 在「有 PMID 但 efetch 解析为 0 篇」
时 return 2。那一次采集层故障对应一次 record_probe(False)。单篇缺摘要、当天零新增
不在本模块里解释，由调用方归并成 esearch_ok / efetch_ok 再进来。
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone

STATE_CLOSED = "CLOSED"
STATE_OPEN = "OPEN"
STATE_HALF_OPEN = "HALF_OPEN"
_STATES = frozenset({STATE_CLOSED, STATE_OPEN, STATE_HALF_OPEN})

# Record 契约里的字符串字段。空串保护对它们一视同仁（摘要是其中显式点名的一项）。
_STRING_FIELDS = (
    "pmid",
    "title",
    "abstract",
    "journal_title",
    "nlmid",
    "issn",
    "essn",
    "first_publication_date",
    "first_index_date",
    "source",
)

_STATE_KEYS = (
    "state",
    "consecutive_failures",
    "consecutive_successes",
    "tripped_at",
    "last_probe_at",
    "cooldown_hours",
)

DEFAULT_COOLDOWN_HOURS = 12
# CLOSED 下连续失败达到此数才跳闸。会诊与契约一致：不要一次失败就切源。
_TRIP_FAILURES = 2
# HALF_OPEN 下连续成功达到此数才回到 CLOSED。
_CLOSE_SUCCESSES = 3


class BreakerStateError(ValueError):
    """状态文件损坏或字段非法。

    不把坏文件重置成 CLOSED：那样会把「已经熔断、应走 EPMC」洗成「主源健康」。
    """


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _from_iso(text: str) -> datetime:
    raw = text.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _blank(value: object) -> bool:
    return value is None or value == ""


class CircuitBreaker:
    """跨运行记忆的三态断路器。状态只经临时文件 + os.replace 落盘。

    route() 只读当前状态，冷却届满也不会在 route() 里升到 HALF_OPEN。
    升态发生在 record_probe()：OPEN 且距 tripped_at ≥ cooldown 时，这次调用先进入
    HALF_OPEN，再把本次成败记在半开态上。decide_route() 在 esearch 成功且冷却届满时
    同样先升半开，否则 OPEN 分支会把探针永远挡在 full_epmc 外面。
    """

    def __init__(self, state_path: str):
        if not isinstance(state_path, str) or state_path == "":
            raise ValueError("state_path 必须是非空字符串")
        self.state_path = state_path
        parent = os.path.dirname(os.path.abspath(state_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        if os.path.exists(state_path):
            self._load()
        else:
            self.state = STATE_CLOSED
            self.consecutive_failures = 0
            self.consecutive_successes = 0
            self.tripped_at: str | None = None
            self.last_probe_at: str | None = None
            self.cooldown_hours = DEFAULT_COOLDOWN_HOURS
            self._save()

    def record_probe(self, ok: bool) -> None:
        """记一次 NCBI 探针结果，并按契约迁移状态。失败则内存与磁盘都保持原样。"""
        if type(ok) is not bool:
            raise TypeError("ok 必须是 bool")
        snapshot = self._snapshot()
        try:
            self._apply_probe(ok)
            self._save()
        except Exception:
            self._restore(snapshot)
            raise

    def route(self) -> str:
        """CLOSED/HALF_OPEN → ncbi；OPEN → epmc。无副作用。"""
        if self.state == STATE_OPEN:
            return "epmc"
        if self.state == STATE_CLOSED or self.state == STATE_HALF_OPEN:
            return "ncbi"
        raise BreakerStateError(f"非法 state: {self.state!r}")

    def _snapshot(self) -> dict:
        return {
            "state": self.state,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "tripped_at": self.tripped_at,
            "last_probe_at": self.last_probe_at,
            "cooldown_hours": self.cooldown_hours,
        }

    def _restore(self, snapshot: dict) -> None:
        self.state = snapshot["state"]
        self.consecutive_failures = snapshot["consecutive_failures"]
        self.consecutive_successes = snapshot["consecutive_successes"]
        self.tripped_at = snapshot["tripped_at"]
        self.last_probe_at = snapshot["last_probe_at"]
        self.cooldown_hours = snapshot["cooldown_hours"]

    def _cooldown_elapsed(self, now: datetime) -> bool:
        if self.state != STATE_OPEN or self.tripped_at is None:
            return False
        elapsed = now - _from_iso(self.tripped_at)
        return elapsed >= timedelta(hours=self.cooldown_hours)

    def _enter_half_open(self) -> None:
        self.state = STATE_HALF_OPEN
        self.consecutive_failures = 0
        self.consecutive_successes = 0

    def _promote_if_cooled(self) -> bool:
        """冷却已满则落盘为 HALF_OPEN。未满或不是 OPEN 时不写文件。"""
        now = _utcnow()
        if not self._cooldown_elapsed(now):
            return False
        snapshot = self._snapshot()
        try:
            self._enter_half_open()
            self._save()
        except Exception:
            self._restore(snapshot)
            raise
        return True

    def _apply_probe(self, ok: bool) -> None:
        now = _utcnow()
        # OPEN 且冷却满：本次调用先升 HALF_OPEN，再把 ok 记到半开态上。
        if self._cooldown_elapsed(now):
            self._enter_half_open()
        self.last_probe_at = _to_iso(now)

        if self.state == STATE_CLOSED:
            if ok:
                self.consecutive_failures = 0
                self.consecutive_successes = 0
            else:
                self.consecutive_successes = 0
                self.consecutive_failures += 1
                if self.consecutive_failures >= _TRIP_FAILURES:
                    self.state = STATE_OPEN
                    self.tripped_at = _to_iso(now)
            return

        if self.state == STATE_HALF_OPEN:
            if ok:
                self.consecutive_failures = 0
                self.consecutive_successes += 1
                if self.consecutive_successes >= _CLOSE_SUCCESSES:
                    self.state = STATE_CLOSED
                    self.consecutive_failures = 0
                    self.consecutive_successes = 0
                    self.tripped_at = None
            else:
                self.state = STATE_OPEN
                self.tripped_at = _to_iso(now)
                self.consecutive_failures = 1
                self.consecutive_successes = 0
            return

        # 仍是 OPEN：冷却未满。成功也不准提前复位，避免熔断抖动。
        return

    def _load(self) -> None:
        with open(self.state_path, encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise BreakerStateError("状态文件根必须是 JSON 对象")
        missing = [key for key in _STATE_KEYS if key not in data]
        if missing:
            raise BreakerStateError(f"状态文件缺字段: {missing}")
        state = data["state"]
        if state not in _STATES:
            raise BreakerStateError(f"非法 state: {state!r}")
        failures = data["consecutive_failures"]
        successes = data["consecutive_successes"]
        cooldown = data["cooldown_hours"]
        if type(failures) is not int or failures < 0:
            raise BreakerStateError("consecutive_failures 必须是非负整数")
        if type(successes) is not int or successes < 0:
            raise BreakerStateError("consecutive_successes 必须是非负整数")
        if type(cooldown) is not int or cooldown <= 0:
            raise BreakerStateError("cooldown_hours 必须是正整数")
        for key in ("tripped_at", "last_probe_at"):
            value = data[key]
            if value is not None and not isinstance(value, str):
                raise BreakerStateError(f"{key} 必须是字符串或 null")
            if isinstance(value, str):
                _from_iso(value)
        if state == STATE_OPEN and data["tripped_at"] is None:
            raise BreakerStateError("OPEN 必须带 tripped_at")
        self.state = state
        self.consecutive_failures = failures
        self.consecutive_successes = successes
        self.tripped_at = data["tripped_at"]
        self.last_probe_at = data["last_probe_at"]
        self.cooldown_hours = cooldown

    def _save(self) -> None:
        payload = self._snapshot()
        parent = os.path.dirname(os.path.abspath(self.state_path)) or "."
        fd, tmp_path = tempfile.mkstemp(prefix=".dualsource-", suffix=".tmp", dir=parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, self.state_path)
        except Exception:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            raise


def decide_route(
    esearch_ok: bool, efetch_ok: bool, breaker: CircuitBreaker,
    record_probe: bool = True,
) -> tuple[str, str]:
    """返回 (route, mode)，mode 为 normal / patch / full_epmc。

    判定用的是调用 record_probe 之前的状态：把 CLOSED 打成 OPEN 的那一次仍返回
    patch，下一次才是 full_epmc。esearch 失败不记探针，避免检索故障烧掉 efetch 熔断计数。
    record_probe=False 时只判路由、不记探针（main 已记过同轮探针，fallback 禁同日双记）。
    """
    if not isinstance(breaker, CircuitBreaker):
        raise TypeError("breaker 必须是 CircuitBreaker")
    if type(esearch_ok) is not bool or type(efetch_ok) is not bool:
        raise TypeError("esearch_ok 与 efetch_ok 必须是 bool")
    if type(record_probe) is not bool:
        raise TypeError("record_probe 必须是 bool")

    if not esearch_ok:
        return ("epmc", "full_epmc")

    if breaker.state == STATE_OPEN:
        # 冷却未满：整次走 EPMC，且不把本次 efetch 结果记成探针（否则会抖动或误复位）。
        if not breaker._promote_if_cooled():
            return ("epmc", "full_epmc")

    if efetch_ok:
        if record_probe:
            breaker.record_probe(True)
        return ("ncbi", "normal")
    if record_probe:
        breaker.record_probe(False)
    return ("ncbi", "patch")


def _union_keep_order(existing_items: object, new_items: object) -> list:
    if existing_items is None:
        existing_items = []
    if new_items is None:
        new_items = []
    if not isinstance(existing_items, list) or not isinstance(new_items, list):
        raise TypeError("pub_types 必须是 list")
    merged: list[str] = []
    seen: set[str] = set()
    for item in existing_items + new_items:
        if not isinstance(item, str):
            raise TypeError("pub_types 的每一项必须是 str")
        if item in seen:
            continue
        seen.add(item)
        merged.append(item)
    return merged


def _event_key(event: dict) -> tuple[str, str]:
    kind = event.get("type", "")
    ref = event.get("ref_pmid", "")
    if not isinstance(kind, str) or not isinstance(ref, str):
        raise TypeError("retraction_events 的 type 与 ref_pmid 必须是 str")
    return (kind, ref)


def _merge_events(existing_events: object, new_events: object) -> list:
    if existing_events is None:
        existing_events = []
    if new_events is None:
        new_events = []
    if not isinstance(existing_events, list) or not isinstance(new_events, list):
        raise TypeError("retraction_events 必须是 list")
    merged: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for event in list(existing_events) + list(new_events):
        if not isinstance(event, dict):
            raise TypeError("retraction_events 的每一项必须是 dict")
        key = _event_key(event)
        if key in seen:
            continue
        seen.add(key)
        merged.append(copy.deepcopy(event))
    return merged


def _freeze_first_seen(out: dict, existing: dict, new: dict, now: str) -> None:
    """首次来源与首次时间只在缺失时补一次，之后任何 new 都改不掉。"""
    if "first_seen_source" in existing:
        out["first_seen_source"] = existing["first_seen_source"]
    elif not _blank(existing.get("source")):
        out["first_seen_source"] = existing["source"]
    else:
        out["first_seen_source"] = new.get("source", "")
    if "first_seen_at" in existing and not _blank(existing.get("first_seen_at")):
        out["first_seen_at"] = existing["first_seen_at"]
    else:
        out["first_seen_at"] = now


def merge_record(existing: dict | None, new: dict) -> dict:
    """按 PMID 幂等合并。不修改入参。

    existing 为 None：返回 new 的副本，并写下 first_seen_source / first_seen_at /
    last_fetched_at / last_source。
    existing 已在：字符串字段遇 new 的空串（或缺失）保留旧值；非空新值覆盖。
    retraction_events 按 (type, ref_pmid) 去重，先到先留。pub_types 并集且保先出现的顺序。
    """
    if not isinstance(new, dict):
        raise TypeError("new 必须是 dict")
    now = _to_iso(_utcnow())
    if existing is None:
        out = copy.deepcopy(new)
        source = new.get("source", "")
        out["first_seen_source"] = source
        out["first_seen_at"] = now
        out["last_fetched_at"] = now
        out["last_source"] = source
        return out
    if not isinstance(existing, dict):
        raise TypeError("existing 必须是 dict 或 None")

    out = copy.deepcopy(existing)
    for field in _STRING_FIELDS:
        incoming = new.get(field, "")
        current = out.get(field, "")
        if _blank(incoming) and not _blank(current):
            continue
        if not _blank(incoming):
            out[field] = incoming

    out["pub_types"] = _union_keep_order(out.get("pub_types"), new.get("pub_types"))
    out["retraction_events"] = _merge_events(
        out.get("retraction_events"), new.get("retraction_events")
    )
    _freeze_first_seen(out, existing, new, now)
    incoming_source = new.get("source", "")
    if not _blank(incoming_source):
        out["last_source"] = incoming_source
    elif _blank(out.get("last_source")):
        out["last_source"] = existing.get("source", "")
    out["last_fetched_at"] = now
    return out
