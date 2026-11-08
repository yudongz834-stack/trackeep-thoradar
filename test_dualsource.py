"""dualsource 契约测试。断言写的是 contract.md 的行为，离线、无第三方依赖。"""

from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import dualsource
from dualsource import (
    BreakerStateError,
    CircuitBreaker,
    decide_route,
    merge_record,
)

_UTC_ISO = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$"
)
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


class Clock:
    def __init__(self) -> None:
        self.t = datetime(2026, 11, 8, 0, 0, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.t

    def advance(self, **kwargs: float) -> datetime:
        self.t = self.t + timedelta(**kwargs)
        return self.t


def parse_utc(text: str) -> datetime:
    if not isinstance(text, str) or _UTC_ISO.fullmatch(text) is None:
        raise AssertionError(f"不是 UTC ISO: {text!r}")
    raw = text[:-1] + "+00:00" if text.endswith("Z") else text
    return datetime.fromisoformat(raw).astimezone(timezone.utc)


def record(**overrides: object) -> dict:
    base = {
        "pmid": "9500320",
        "title": "Ileal-lymphoid-nodular hyperplasia",
        "abstract": "We investigated a consecutive series.",
        "journal_title": "Lancet",
        "nlmid": "2985213R",
        "issn": "0140-6736",
        "essn": "1474-547X",
        "pub_types": ["Journal Article"],
        "first_publication_date": "1998-02-01",
        "first_index_date": "2010-03-09",
        "retraction_events": [],
        "source": "epmc",
    }
    base.update(overrides)
    return base


class DualSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.clock = Clock()
        self._patch = patch("dualsource._utcnow", self.clock)
        self._patch.start()
        self.path = os.path.join(self._tmp.name, "breaker.json")

    def tearDown(self) -> None:
        self._patch.stop()
        self._tmp.cleanup()

    def _disk(self) -> dict:
        with open(self.path, encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertEqual(
            set(data),
            {
                "state",
                "consecutive_failures",
                "consecutive_successes",
                "tripped_at",
                "last_probe_at",
                "cooldown_hours",
            },
        )
        return data

    def _assert_memory_matches_disk(self, breaker: CircuitBreaker) -> None:
        data = self._disk()
        self.assertEqual(data["state"], breaker.state)
        self.assertEqual(data["consecutive_failures"], breaker.consecutive_failures)
        self.assertEqual(data["consecutive_successes"], breaker.consecutive_successes)
        self.assertEqual(data["tripped_at"], breaker.tripped_at)
        self.assertEqual(data["last_probe_at"], breaker.last_probe_at)
        self.assertEqual(data["cooldown_hours"], breaker.cooldown_hours)
        with open(self.path, "rb") as handle:
            self.assertFalse(handle.read().startswith(b"\xef\xbb\xbf"))

    def _trip_open(self) -> CircuitBreaker:
        breaker = CircuitBreaker(self.path)
        breaker.record_probe(False)
        self.assertEqual(breaker.state, "CLOSED")
        self.clock.advance(seconds=1)
        breaker.record_probe(False)
        self.assertEqual(breaker.state, "OPEN")
        self.assertEqual(parse_utc(breaker.tripped_at), self.clock())
        return breaker

    def test_closed_two_consecutive_failures_trip_open(self) -> None:
        breaker = CircuitBreaker(self.path)
        self.assertEqual(breaker.state, "CLOSED")
        self.assertEqual(breaker.route(), "ncbi")
        self.assertEqual(self._disk()["cooldown_hours"], 12)

        breaker.record_probe(False)
        self.assertEqual(breaker.state, "CLOSED")
        self.assertEqual(breaker.consecutive_failures, 1)
        self.assertEqual(breaker.route(), "ncbi")
        self.assertIsNone(breaker.tripped_at)
        self.assertEqual(parse_utc(breaker.last_probe_at), self.clock())

        self.clock.advance(seconds=2)
        breaker.record_probe(False)
        self.assertEqual(breaker.state, "OPEN")
        self.assertEqual(breaker.consecutive_failures, 2)
        self.assertEqual(breaker.consecutive_successes, 0)
        self.assertEqual(breaker.route(), "epmc")
        self.assertEqual(parse_utc(breaker.tripped_at), self.clock())
        self._assert_memory_matches_disk(breaker)

    def test_single_failure_does_not_trip_and_success_resets_streak(self) -> None:
        breaker = CircuitBreaker(self.path)
        breaker.record_probe(False)
        self.clock.advance(seconds=1)
        breaker.record_probe(True)
        self.assertEqual(breaker.state, "CLOSED")
        self.assertEqual(breaker.consecutive_failures, 0)
        self.assertEqual(breaker.route(), "ncbi")
        self.clock.advance(seconds=1)
        breaker.record_probe(False)
        self.assertEqual(breaker.state, "CLOSED")
        self.assertEqual(breaker.consecutive_failures, 1)
        self.assertIsNone(breaker.tripped_at)

    def test_route_does_not_promote_when_cooldown_elapsed(self) -> None:
        breaker = self._trip_open()
        tripped = breaker.tripped_at
        self.clock.advance(hours=12)
        self.assertEqual(breaker.state, "OPEN")
        self.assertEqual(breaker.route(), "epmc")
        self.assertEqual(breaker.tripped_at, tripped)
        self.assertEqual(self._disk()["state"], "OPEN")

        self.clock.advance(microseconds=-1)
        breaker.record_probe(True)
        self.assertEqual(breaker.state, "OPEN")
        self.assertEqual(breaker.consecutive_failures, 2)
        self.assertEqual(breaker.tripped_at, tripped)
        self.assertEqual(parse_utc(breaker.last_probe_at), self.clock())

    def test_open_after_cooldown_next_probe_enters_half_open_first(self) -> None:
        breaker = self._trip_open()
        original_trip = breaker.tripped_at
        self.clock.advance(hours=11)
        breaker.record_probe(True)
        self.assertEqual(breaker.state, "OPEN")
        self.assertEqual(breaker.tripped_at, original_trip)

        self.clock.advance(hours=1)
        self.assertEqual(breaker.route(), "epmc")
        breaker.record_probe(True)
        self.assertEqual(breaker.state, "HALF_OPEN")
        self.assertEqual(breaker.consecutive_successes, 1)
        self.assertEqual(breaker.consecutive_failures, 0)
        self.assertEqual(breaker.route(), "ncbi")
        self.assertEqual(breaker.tripped_at, original_trip)
        self._assert_memory_matches_disk(breaker)

    def test_exact_twelve_hour_boundary_promotes(self) -> None:
        tripped_at = self.clock()
        payload = {
            "state": "OPEN",
            "consecutive_failures": 2,
            "consecutive_successes": 0,
            "tripped_at": tripped_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "last_probe_at": tripped_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "cooldown_hours": 12,
        }
        with open(self.path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle)
        breaker = CircuitBreaker(self.path)
        self.clock.advance(hours=12, microseconds=-1)
        breaker.record_probe(True)
        self.assertEqual(breaker.state, "OPEN")
        self.clock.advance(microseconds=1)
        breaker.record_probe(True)
        self.assertEqual(breaker.state, "HALF_OPEN")
        self.assertEqual(breaker.consecutive_successes, 1)

    def test_half_open_three_successes_close_and_clear_counts(self) -> None:
        breaker = self._trip_open()
        self.clock.advance(hours=12)
        breaker.record_probe(True)
        self.assertEqual(breaker.state, "HALF_OPEN")
        self.assertEqual(breaker.consecutive_successes, 1)
        self.clock.advance(seconds=1)
        breaker.record_probe(True)
        self.assertEqual(breaker.state, "HALF_OPEN")
        self.assertEqual(breaker.consecutive_successes, 2)
        self.assertEqual(breaker.route(), "ncbi")

        reloaded = CircuitBreaker(self.path)
        self.assertEqual(reloaded.state, "HALF_OPEN")
        self.assertEqual(reloaded.consecutive_successes, 2)
        self.clock.advance(seconds=1)
        reloaded.record_probe(True)
        self.assertEqual(reloaded.state, "CLOSED")
        self.assertEqual(reloaded.consecutive_successes, 0)
        self.assertEqual(reloaded.consecutive_failures, 0)
        self.assertIsNone(reloaded.tripped_at)
        self.assertEqual(reloaded.route(), "ncbi")
        self._assert_memory_matches_disk(reloaded)

        again = CircuitBreaker(self.path)
        self.assertEqual(again.state, "CLOSED")
        self.assertEqual(again.consecutive_failures, 0)
        self.assertIsNone(again.tripped_at)

    def test_half_open_one_failure_reopens_and_resets_tripped_at(self) -> None:
        breaker = self._trip_open()
        first_trip = breaker.tripped_at
        self.clock.advance(hours=12)
        breaker.record_probe(True)
        self.clock.advance(seconds=1)
        breaker.record_probe(True)
        self.assertEqual(breaker.consecutive_successes, 2)
        self.assertEqual(breaker.state, "HALF_OPEN")

        self.clock.advance(seconds=1)
        breaker.record_probe(False)
        self.assertEqual(breaker.state, "OPEN")
        self.assertEqual(breaker.route(), "epmc")
        self.assertEqual(breaker.consecutive_failures, 1)
        self.assertEqual(breaker.consecutive_successes, 0)
        self.assertNotEqual(breaker.tripped_at, first_trip)
        self.assertEqual(parse_utc(breaker.tripped_at), self.clock())
        self._assert_memory_matches_disk(breaker)

        self.clock.advance(hours=12, microseconds=-1)
        breaker.record_probe(True)
        self.assertEqual(breaker.state, "OPEN")
        self.clock.advance(microseconds=1)
        breaker.record_probe(True)
        self.assertEqual(breaker.state, "HALF_OPEN")
        self.assertEqual(breaker.consecutive_successes, 1)
        self.assertNotEqual(breaker.state, "CLOSED")

    def test_state_persists_across_instances(self) -> None:
        first = self._trip_open()
        tripped = first.tripped_at
        failures = first.consecutive_failures
        second = CircuitBreaker(self.path)
        self.assertEqual(second.state, "OPEN")
        self.assertEqual(second.consecutive_failures, failures)
        self.assertEqual(second.tripped_at, tripped)
        self.assertEqual(second.cooldown_hours, 12)
        self.assertEqual(second.route(), "epmc")
        self.assertIsNot(first, second)

    def test_honors_persisted_cooldown_hours(self) -> None:
        tripped_at = self.clock()
        payload = {
            "state": "OPEN",
            "consecutive_failures": 2,
            "consecutive_successes": 0,
            "tripped_at": tripped_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "last_probe_at": None,
            "cooldown_hours": 1,
        }
        with open(self.path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle)
        breaker = CircuitBreaker(self.path)
        self.assertEqual(breaker.cooldown_hours, 1)
        self.clock.advance(hours=1, microseconds=-1)
        breaker.record_probe(True)
        self.assertEqual(breaker.state, "OPEN")
        self.clock.advance(microseconds=1)
        breaker.record_probe(True)
        self.assertEqual(breaker.state, "HALF_OPEN")
        self.assertEqual(self._disk()["cooldown_hours"], 1)

    def test_atomic_replace_and_failed_write_keeps_prior(self) -> None:
        breaker = CircuitBreaker(self.path)
        with patch("dualsource.os.replace", wraps=os.replace) as replace:
            breaker.record_probe(False)
        self.assertEqual(replace.call_count, 1)
        source, dest = replace.call_args[0]
        self.assertEqual(os.path.abspath(dest), os.path.abspath(self.path))
        self.assertNotEqual(os.path.abspath(source), os.path.abspath(self.path))
        self.assertFalse(os.path.exists(source))
        self.assertEqual(self._disk()["consecutive_failures"], 1)

        with open(self.path, encoding="utf-8") as handle:
            before = handle.read()
        with patch("dualsource.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                breaker.record_probe(False)
        with open(self.path, encoding="utf-8") as handle:
            after = handle.read()
        self.assertEqual(after, before)
        self.assertEqual(breaker.state, "CLOSED")
        self.assertEqual(breaker.consecutive_failures, 1)
        self.assertIsNone(breaker.tripped_at)
        leftovers = [
            name
            for name in os.listdir(self._tmp.name)
            if name.startswith(".dualsource-")
        ]
        self.assertEqual(leftovers, [])
        reloaded = CircuitBreaker(self.path)
        self.assertEqual(reloaded.state, "CLOSED")
        self.assertEqual(reloaded.consecutive_failures, 1)

    def test_corrupt_state_file_is_not_silently_reset(self) -> None:
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("{not-json")
        with self.assertRaises(json.JSONDecodeError):
            CircuitBreaker(self.path)
        with open(self.path, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "{not-json")

        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump({"state": "CLOSED"}, handle)
        with self.assertRaises(BreakerStateError):
            CircuitBreaker(self.path)

        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "state": "BROKEN",
                    "consecutive_failures": 0,
                    "consecutive_successes": 0,
                    "tripped_at": None,
                    "last_probe_at": None,
                    "cooldown_hours": 12,
                },
                handle,
            )
        with self.assertRaises(BreakerStateError):
            CircuitBreaker(self.path)

    def test_record_probe_rejects_non_bool(self) -> None:
        breaker = CircuitBreaker(self.path)
        with self.assertRaises(TypeError):
            breaker.record_probe(1)  # type: ignore[arg-type]
        self.assertEqual(breaker.consecutive_failures, 0)
        self.assertEqual(self._disk()["consecutive_failures"], 0)

    def test_decide_route_normal_patch_then_subsequent_full_epmc(self) -> None:
        breaker = CircuitBreaker(self.path)
        self.assertEqual(decide_route(True, True, breaker), ("ncbi", "normal"))
        self.assertEqual(breaker.state, "CLOSED")
        self.assertEqual(breaker.consecutive_failures, 0)
        self.assertEqual(parse_utc(breaker.last_probe_at), self.clock())

        self.clock.advance(seconds=1)
        self.assertEqual(decide_route(True, False, breaker), ("ncbi", "patch"))
        self.assertEqual(breaker.state, "CLOSED")
        self.assertEqual(breaker.consecutive_failures, 1)

        self.clock.advance(seconds=1)
        tripped_clock = self.clock()
        self.assertEqual(decide_route(True, False, breaker), ("ncbi", "patch"))
        self.assertEqual(breaker.state, "OPEN")
        self.assertEqual(breaker.consecutive_failures, 2)
        self.assertEqual(parse_utc(breaker.tripped_at), tripped_clock)

        self.clock.advance(seconds=1)
        last_probe = breaker.last_probe_at
        self.assertEqual(decide_route(True, True, breaker), ("epmc", "full_epmc"))
        self.assertEqual(breaker.state, "OPEN")
        self.assertEqual(breaker.consecutive_failures, 2)
        self.assertEqual(breaker.last_probe_at, last_probe)
        self.assertEqual(parse_utc(breaker.tripped_at), tripped_clock)
        self.assertEqual(decide_route(True, False, breaker), ("epmc", "full_epmc"))
        self.assertEqual(breaker.last_probe_at, last_probe)

    def test_decide_route_esearch_failure_does_not_probe(self) -> None:
        breaker = CircuitBreaker(self.path)
        breaker.record_probe(False)
        self.assertEqual(breaker.consecutive_failures, 1)
        self.clock.advance(seconds=1)
        self.assertEqual(decide_route(False, False, breaker), ("epmc", "full_epmc"))
        self.assertEqual(decide_route(False, True, breaker), ("epmc", "full_epmc"))
        self.assertEqual(breaker.state, "CLOSED")
        self.assertEqual(breaker.consecutive_failures, 1)
        self.assertEqual(parse_utc(breaker.last_probe_at), self.clock() - timedelta(seconds=1))

    def test_decide_route_cooled_open_probes_ncbi(self) -> None:
        breaker = self._trip_open()
        self.clock.advance(hours=12)
        self.assertEqual(decide_route(True, True, breaker), ("ncbi", "normal"))
        self.assertEqual(breaker.state, "HALF_OPEN")
        self.assertEqual(breaker.consecutive_successes, 1)
        self.assertEqual(breaker.route(), "ncbi")

        self.clock.advance(seconds=1)
        self.assertEqual(decide_route(True, True, breaker), ("ncbi", "normal"))
        self.assertEqual(breaker.consecutive_successes, 2)
        self.clock.advance(seconds=1)
        self.assertEqual(decide_route(True, True, breaker), ("ncbi", "normal"))
        self.assertEqual(breaker.state, "CLOSED")
        self.assertEqual(breaker.consecutive_successes, 0)
        self.assertEqual(breaker.consecutive_failures, 0)
        self.assertIsNone(breaker.tripped_at)

    def test_decide_route_cooled_probe_failure_returns_patch_then_full_epmc(self) -> None:
        breaker = self._trip_open()
        old_trip = breaker.tripped_at
        self.clock.advance(hours=12)
        self.assertEqual(decide_route(True, False, breaker), ("ncbi", "patch"))
        self.assertEqual(breaker.state, "OPEN")
        self.assertEqual(parse_utc(breaker.tripped_at), self.clock())
        self.assertNotEqual(breaker.tripped_at, old_trip)
        self.clock.advance(seconds=1)
        probe_at = breaker.last_probe_at
        self.assertEqual(decide_route(True, True, breaker), ("epmc", "full_epmc"))
        self.assertEqual(breaker.state, "OPEN")
        self.assertEqual(breaker.last_probe_at, probe_at)

    def test_decide_route_half_open_esearch_failure_does_not_count(self) -> None:
        breaker = self._trip_open()
        self.clock.advance(hours=12)
        decide_route(True, True, breaker)
        self.assertEqual(breaker.state, "HALF_OPEN")
        successes = breaker.consecutive_successes
        self.clock.advance(seconds=1)
        self.assertEqual(decide_route(False, False, breaker), ("epmc", "full_epmc"))
        self.assertEqual(breaker.state, "HALF_OPEN")
        self.assertEqual(breaker.consecutive_successes, successes)

    def test_merge_insert_stamps_first_seen_without_touching_input(self) -> None:
        fresh = record()
        snapshot = json.dumps(fresh, ensure_ascii=False, sort_keys=True)
        out = merge_record(None, fresh)
        self.assertIsNot(out, fresh)
        self.assertEqual(json.dumps(fresh, ensure_ascii=False, sort_keys=True), snapshot)
        self.assertEqual(out["first_seen_source"], "epmc")
        self.assertEqual(out["last_source"], "epmc")
        self.assertEqual(out["first_seen_at"], out["last_fetched_at"])
        self.assertEqual(parse_utc(out["first_seen_at"]), self.clock())
        self.assertEqual(out["abstract"], fresh["abstract"])
        self.assertEqual(out["pmid"], "9500320")
        self.assertNotIn("first_seen_at", fresh)

    def test_merge_empty_string_does_not_clobber_any_string_field(self) -> None:
        existing = merge_record(None, record())
        stamped = existing["first_seen_at"]
        self.clock.advance(minutes=5)
        empty = record()
        for field in _STRING_FIELDS:
            empty[field] = ""
        empty["abstract"] = ""
        out = merge_record(existing, empty)
        for field in _STRING_FIELDS:
            self.assertEqual(out[field], existing[field], field)
        self.assertEqual(out["abstract"], existing["abstract"])
        self.assertNotEqual(out["abstract"], "")
        self.assertEqual(out["first_seen_source"], "epmc")
        self.assertEqual(out["first_seen_at"], stamped)
        self.assertEqual(out["last_source"], "epmc")
        self.assertEqual(parse_utc(out["last_fetched_at"]), self.clock())
        self.assertNotEqual(out["last_fetched_at"], stamped)

        missing = record()
        del missing["abstract"]
        del missing["title"]
        self.clock.advance(seconds=1)
        kept = merge_record(out, missing)
        self.assertEqual(kept["abstract"], existing["abstract"])
        self.assertEqual(kept["title"], existing["title"])

    def test_merge_nonempty_updates_and_freezes_first_seen(self) -> None:
        existing = merge_record(None, record(source="ncbi"))
        self.assertEqual(existing["first_seen_source"], "ncbi")
        first_at = existing["first_seen_at"]
        self.clock.advance(hours=1)
        incoming = record(
            source="epmc",
            title="updated title",
            abstract="updated abstract",
            journal_title="Lancet (London, England)",
            nlmid="2985213R",
            issn="0140-6736",
            essn="1474-547X",
            first_publication_date="1998-02-28",
            first_index_date="2010-03-10",
        )
        out = merge_record(existing, incoming)
        self.assertEqual(out["title"], "updated title")
        self.assertEqual(out["abstract"], "updated abstract")
        self.assertEqual(out["first_publication_date"], "1998-02-28")
        self.assertEqual(out["first_index_date"], "2010-03-10")
        self.assertEqual(out["source"], "epmc")
        self.assertEqual(out["last_source"], "epmc")
        self.assertEqual(out["first_seen_source"], "ncbi")
        self.assertEqual(out["first_seen_at"], first_at)
        self.assertEqual(parse_utc(out["last_fetched_at"]), self.clock())
        self.assertNotEqual(out["last_fetched_at"], first_at)

        poisoned = dict(incoming)
        poisoned["first_seen_source"] = "forged"
        poisoned["first_seen_at"] = "1999-01-01T00:00:00Z"
        self.clock.advance(seconds=1)
        again = merge_record(out, poisoned)
        self.assertEqual(again["first_seen_source"], "ncbi")
        self.assertEqual(again["first_seen_at"], first_at)

    def test_merge_events_dedupe_and_pub_types_union_order(self) -> None:
        existing = merge_record(
            None,
            record(
                pub_types=["Journal Article", "Retracted Publication"],
                retraction_events=[
                    {"type": "Comment in", "ref_pmid": "9500313", "note": "keep"},
                    {"type": "Retraction in", "ref_pmid": "15016483"},
                    {"type": "Retraction in", "ref_pmid": "15016483", "note": "dup-inside"},
                ],
            ),
        )
        incoming = record(
            pub_types=["Retracted Publication", "Letter", "Journal Article"],
            retraction_events=[
                {"type": "Retraction in", "ref_pmid": "15016483", "note": "drop"},
                {"type": "Expression of concern in", "ref_pmid": "21971344"},
                {"type": "Retraction in", "ref_pmid": "20137807"},
                {"type": "Comment in", "ref_pmid": "15016483"},
            ],
        )
        out = merge_record(existing, incoming)
        self.assertEqual(
            out["pub_types"],
            ["Journal Article", "Retracted Publication", "Letter"],
        )
        self.assertEqual(
            [(event["type"], event["ref_pmid"]) for event in out["retraction_events"]],
            [
                ("Comment in", "9500313"),
                ("Retraction in", "15016483"),
                ("Expression of concern in", "21971344"),
                ("Retraction in", "20137807"),
                ("Comment in", "15016483"),
            ],
        )
        self.assertEqual(out["retraction_events"][0]["note"], "keep")
        self.assertNotIn("note", out["retraction_events"][1])

        self.clock.advance(seconds=1)
        twice = merge_record(out, incoming)
        self.assertEqual(twice["pub_types"], out["pub_types"])
        self.assertEqual(
            [(event["type"], event["ref_pmid"]) for event in twice["retraction_events"]],
            [(event["type"], event["ref_pmid"]) for event in out["retraction_events"]],
        )

    def test_merge_does_not_mutate_inputs(self) -> None:
        existing = merge_record(
            None,
            record(
                pub_types=["Journal Article"],
                retraction_events=[{"type": "Retraction in", "ref_pmid": "1"}],
            ),
        )
        incoming = record(
            pub_types=["Letter"],
            retraction_events=[{"type": "Comment in", "ref_pmid": "2"}],
            abstract="",
        )
        existing_types = existing["pub_types"]
        existing_events = existing["retraction_events"]
        incoming_types = incoming["pub_types"]
        incoming_events = incoming["retraction_events"]
        out = merge_record(existing, incoming)
        out["pub_types"].append("Forged")
        out["retraction_events"][0]["type"] = "Forged"
        out["abstract"] = "Forged"
        self.assertEqual(existing["pub_types"], ["Journal Article"])
        self.assertEqual(existing["abstract"], "We investigated a consecutive series.")
        self.assertEqual(existing_events[0]["type"], "Retraction in")
        self.assertIs(existing["pub_types"], existing_types)
        self.assertIs(existing["retraction_events"], existing_events)
        self.assertEqual(incoming["pub_types"], ["Letter"])
        self.assertEqual(incoming["abstract"], "")
        self.assertEqual(incoming_events[0]["type"], "Comment in")
        self.assertIs(incoming["pub_types"], incoming_types)
        self.assertIs(incoming["retraction_events"], incoming_events)
        self.assertIsNot(out["pub_types"], existing_types)
        self.assertIsNot(out["pub_types"], incoming_types)

    def test_merge_existing_raw_record_keeps_its_own_source_as_first_seen(self) -> None:
        raw = record(source="ncbi")
        self.clock.advance(days=1)
        out = merge_record(raw, record(source="epmc", abstract=""))
        self.assertEqual(out["first_seen_source"], "ncbi")
        self.assertEqual(out["source"], "epmc")
        self.assertEqual(out["last_source"], "epmc")
        self.assertEqual(out["abstract"], raw["abstract"])
        self.assertEqual(parse_utc(out["first_seen_at"]), self.clock())
        self.assertEqual(out["first_seen_at"], out["last_fetched_at"])
        self.assertNotIn("first_seen_source", raw)

    def test_empty_state_path_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CircuitBreaker("")


if __name__ == "__main__":
    unittest.main()
