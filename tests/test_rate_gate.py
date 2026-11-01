#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NCBI 限流闸回归（2026-11-02 实弹 429 修因）。

旧态：六线程裸并发打 esearch，瞬时速率远超带 key 3 req/s 上限→单跑 20 刊 429
（旧全册时代一晚 3,015 条 429 风暴）。修＝_get 唯一出口上的类级共享闸
（带 key 0.35s/请求、无 key 3.1s），任何 Collector 实例同闸。
"""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import thoradar_engine as eng  # noqa: E402


class RateGateTests(unittest.TestCase):
    def test_gate_shared_across_instances_enforces_gap(self):
        """带 key 连续两发（跨实例）实际间隔 ≥0.3s——类级闸的机械保证。"""
        eng.Collector._RATE_LAST = 0.0            # 复位防跨测试污染
        try:
            c1, c2 = eng.Collector(), eng.Collector()
            self.assertTrue(c1.api_key == c2.api_key)  # 同环境同钥匙形态
            t0 = time.monotonic()
            eng.Collector._throttle("k")
            eng.Collector._throttle("k")          # 第二发必须排队
            self.assertGreaterEqual(time.monotonic() - t0, 0.30)
        finally:
            eng.Collector._RATE_LAST = 0.0

    def test_get_sleeps_longer_on_429(self):
        """429 专属长退避（6s 起）vs 普通错 2s 起——限流响应不能等长重试。"""
        import urllib.error
        import unittest.mock as mock
        calls = {"n": 0}

        def boom(url, timeout=60):                # 前两发 429，第三发成功
            import io
            calls["n"] += 1
            if calls["n"] < 3:
                raise urllib.error.HTTPError(url, 429, "Too Many Requests", {}, None)
            return io.BytesIO(b"<ok/>")

        c = eng.Collector()
        c.api_key = "k"
        sleeps: list[float] = []
        with mock.patch.object(eng.Collector, "_throttle", classmethod(lambda cls, k: None)), \
             mock.patch.object(urllib.request, "urlopen", boom), \
             mock.patch.object(eng.time, "sleep", sleeps.append):
            out = c._get("https://example/eutils/esearch.fcgi?x=1")
        self.assertEqual(out, b"<ok/>")
        self.assertEqual(sleeps, [6.0, 12.0])     # 6×(1,2)：429 长退避而非 2/4


if __name__ == "__main__":
    unittest.main()
