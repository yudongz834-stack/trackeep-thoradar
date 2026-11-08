"""Europe PMC 采集适配器单元测试 (test_epmc_adapter.py)

全 HTTP mock，纯离线，零第三方依赖。
严格覆盖 ThorRadar 双源改造接口契约 v1 模块一全部 🔴 红钉：
1. resultType=core 必带与参数合规 (format=json, pageSize=100)
2. SRC:MED 在 search_day 与 fetch_pmids query 中
3. cursorMark 翻页到底（多页循环、无新增停止、相同 cursor 停止、无 nextCursorMark 停止）
4. 429 读 Retry-After 重试路径（重试成功、超过 3 次抛 EpmcError）
5. 异常路径（网络错误、超时、JSON 解析失败、500 错误均抛 EpmcError，禁静默吞禁返回假空）
6. epmc_fetch_pmids 每批 <=25 个分批循环
7. 摘要清洗（HTML 标签剥净、HTML 实体反转义、空白归一）
8. 期刊字段映射源 journalInfo.journal.{title,nlmid,issn,essn} 全部可缺容错
9. commentCorrectionList 映射为 retraction_events [{"type": ..., "ref_pmid": ...}]
10. Record 规范契约（全 12 字段合规，source 恒为 "epmc"）
"""

import io
import json
import re
import socket
import ssl
import unittest
import urllib.error
import urllib.parse
from email.message import Message
from unittest.mock import MagicMock, call, patch

import epmc_adapter
from epmc_adapter import (
    EPMC_SEARCH_URL,
    EpmcError,
    clean_abstract,
    epmc_fetch_pmids,
    epmc_search_day,
    parse_record,
)


def _make_mock_response(body_dict: dict, status: int = 200) -> MagicMock:
    """构造 mock HTTPResponse 对象。"""
    resp = MagicMock()
    raw_bytes = json.dumps(body_dict).encode("utf-8")
    resp.read.return_value = raw_bytes
    resp.status = status
    msg = Message()
    msg.set_type("application/json")
    resp.headers = msg
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = None
    return resp


def _make_http_error(code: int, reason: str, headers: dict = None) -> urllib.error.HTTPError:
    """构造 mock HTTPError 异常。"""
    msg = Message()
    if headers:
        for k, v in headers.items():
            msg[k] = str(v)
    return urllib.error.HTTPError(
        url="http://test.url",
        code=code,
        msg=reason,
        hdrs=msg,
        fp=io.BytesIO(b"error"),
    )


class TestEpmcAdapter(unittest.TestCase):
    """ Europe PMC 适配器单元测试集。"""

    def setUp(self):
        # 重置节流时间戳
        epmc_adapter._last_request_time = 0.0

    # -------------------------------------------------------------------------
    # 钉 1 & 2: SRC:MED 在 query 里，必带 resultType=core + format=json + pageSize=100
    # -------------------------------------------------------------------------
    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_search_day_query_construction_and_core_params(self, mock_urlopen, mock_sleep):
        """🔴 红钉：search_day 包含 SRC:MED、必带 resultType=core、format=json、pageSize=100。"""
        sample_resp = {
            "hitCount": 1,
            "nextCursorMark": None,
            "resultList": {
                "result": [
                    {
                        "id": "12345",
                        "title": "Sample Article",
                        "abstractText": "Sample Abstract",
                        "journalInfo": {
                            "journal": {
                                "title": "Test Journal",
                                "nlmid": "101010",
                                "issn": "0000-0001",
                                "essn": "0000-0002",
                            }
                        },
                        "firstIndexDate": "2024-01-02",
                        "firstPublicationDate": "2024-01-01",
                    }
                ]
            },
        }
        mock_urlopen.return_value = _make_mock_response(sample_resp)

        records = epmc_search_day(["0000-0001"], "2024-01-01", "2024-01-02")
        self.assertEqual(len(records), 1)

        # 校验发出的 HTTP Request
        self.assertEqual(mock_urlopen.call_count, 1)
        req = mock_urlopen.call_args[0][0]
        parsed_url = urllib.parse.urlparse(req.full_url)
        params = urllib.parse.parse_qs(parsed_url.query)

        # 🔴 红钉断言：resultType=core, format=json, pageSize=100
        self.assertEqual(params.get("resultType"), ["core"])
        self.assertEqual(params.get("format"), ["json"])
        self.assertEqual(params.get("pageSize"), ["100"])

        # 🔴 红钉断言：SRC:MED 在 query 里，且包含日期窗与 ISSN 语法
        query = params.get("query", [""])[0]
        self.assertTrue(query.startswith("SRC:MED AND"))
        self.assertIn("ISSN:0000-0001", query)
        self.assertIn("(FIRST_IDATE:[2024-01-01 TO 2024-01-02])", query)

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_search_day_multiple_issns(self, mock_urlopen, mock_sleep):
        """测试多 ISSN 检索表达式正确拼接 (ISSN:i1 OR ISSN:i2)。"""
        sample_resp = {"hitCount": 0, "resultList": {"result": []}}
        mock_urlopen.return_value = _make_mock_response(sample_resp)

        records = epmc_search_day(["0012-3692", "0040-6376"], "2024-01-01", "2024-01-05")
        self.assertEqual(records, [])

        req = mock_urlopen.call_args[0][0]
        params = urllib.parse.parse_qs(urllib.parse.urlparse(req.full_url).query)
        query = params.get("query", [""])[0]
        self.assertIn("(ISSN:0012-3692 OR ISSN:0040-6376)", query)
        self.assertIn("(FIRST_IDATE:[2024-01-01 TO 2024-01-05])", query)

    # -------------------------------------------------------------------------
    # 钉 3: cursorMark 分页翻到底
    # -------------------------------------------------------------------------
    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_search_day_cursormark_pagination_to_end(self, mock_urlopen, mock_sleep):
        """🔴 红钉：cursorMark 分页翻到底（响应 nextCursorMark 与 cursorMark 循环，直到相同）。"""
        page1 = {
            "hitCount": 3,
            "nextCursorMark": "cursor_page2",
            "resultList": {
                "result": [
                    {"id": "101", "title": "Art 1"},
                    {"id": "102", "title": "Art 2"},
                ]
            },
        }
        page2 = {
            "hitCount": 3,
            "nextCursorMark": "cursor_page2",  # cursor 与请求相同，触发翻到底停止
            "resultList": {
                "result": [
                    {"id": "103", "title": "Art 3"},
                ]
            },
        }
        mock_urlopen.side_effect = [
            _make_mock_response(page1),
            _make_mock_response(page2),
        ]

        records = epmc_search_day(["0012-3692"], "2024-01-01", "2024-01-02")
        self.assertEqual(len(records), 3)
        self.assertEqual([r["pmid"] for r in records], ["101", "102", "103"])
        self.assertEqual(mock_urlopen.call_count, 2)

        # 验证两次请求传的 cursorMark 参数
        req1 = mock_urlopen.call_args_list[0][0][0]
        params1 = urllib.parse.parse_qs(urllib.parse.urlparse(req1.full_url).query)
        self.assertEqual(params1.get("cursorMark"), ["*"])

        req2 = mock_urlopen.call_args_list[1][0][0]
        params2 = urllib.parse.parse_qs(urllib.parse.urlparse(req2.full_url).query)
        self.assertEqual(params2.get("cursorMark"), ["cursor_page2"])

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_cursormark_stop_on_empty_items(self, mock_urlopen, mock_sleep):
        """🔴 红钉：当返回页无新增条目 (resultList.result 为空) 时正常结束翻页。"""
        page1 = {
            "hitCount": 1,
            "nextCursorMark": "cursor_xyz",
            "resultList": {"result": [{"id": "201", "title": "Art 201"}]},
        }
        page2 = {
            "hitCount": 1,
            "nextCursorMark": "cursor_xyz2",
            "resultList": {"result": []},  # 无新增
        }
        mock_urlopen.side_effect = [
            _make_mock_response(page1),
            _make_mock_response(page2),
        ]

        records = epmc_search_day(["0012-3692"], "2024-01-01", "2024-01-02")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["pmid"], "201")
        self.assertEqual(mock_urlopen.call_count, 2)

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_cursormark_stop_on_none_next_cursor(self, mock_urlopen, mock_sleep):
        """当 nextCursorMark 为 None 时正常终止翻页。"""
        page1 = {
            "hitCount": 1,
            "nextCursorMark": None,
            "resultList": {"result": [{"id": "301", "title": "Art 301"}]},
        }
        mock_urlopen.return_value = _make_mock_response(page1)

        records = epmc_search_day(["0012-3692"], "2024-01-01", "2024-01-02")
        self.assertEqual(len(records), 1)
        self.assertEqual(mock_urlopen.call_count, 1)

    # -------------------------------------------------------------------------
    # 钉 4: epmc_fetch_pmids 逐条单查（2026-11-08 实测判例：EXT_ID 不支持 OR 组，
    #       批量 OR 在 EPMC API 静默归零——对拍实测 91/197 漏检。禁再引入批量写法）
    # -------------------------------------------------------------------------
    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_fetch_pmids_one_query_per_pmid(self, mock_urlopen, mock_sleep):
        """🔴 红钉：epmc_fetch_pmids 逐 PMID 单查，query 不得含 OR 组。"""
        pmids = [str(1000 + i) for i in range(60)]

        def side_effect(req, timeout=30):
            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(req.full_url).query)
            query = parsed.get("query", [""])[0]
            ext_ids = re.findall(r"EXT_ID:(\w+)", query)
            results = [{"id": pmid, "title": f"Title {pmid}"} for pmid in ext_ids]
            return _make_mock_response({"hitCount": len(results), "resultList": {"result": results}})

        mock_urlopen.side_effect = side_effect

        records = epmc_fetch_pmids(pmids)
        self.assertEqual(len(records), 60)
        self.assertEqual(mock_urlopen.call_count, 60)  # 60 PMID＝60 次单查

        # 每次 query：恰 1 个 EXT_ID、无 OR、SRC:MED 前缀在
        for call in mock_urlopen.call_args_list:
            req = call[0][0]
            q = urllib.parse.parse_qs(urllib.parse.urlparse(req.full_url).query)["query"][0]
            self.assertTrue(q.startswith("SRC:MED AND EXT_ID:"))
            self.assertNotIn(" OR ", q, "禁 OR 组（EPMC EXT_ID 批量 OR 静默漏检判例）")
            self.assertEqual(q.count("EXT_ID:"), 1)

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_fetch_pmids_dedup_and_order(self, mock_urlopen, mock_sleep):
        """重复 PMID 去重、返回按输入顺序。"""
        def side_effect(req, timeout=30):
            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(req.full_url).query)
            q = parsed.get("query", [""])[0]
            ext = re.findall(r"EXT_ID:(\w+)", q)[0]
            rec = {"id": ext, "title": f"Title {ext}"}
            return _make_mock_response({"hitCount": 1, "resultList": {"result": [rec]}})

        mock_urlopen.side_effect = side_effect
        records = epmc_fetch_pmids(["A", "B", "A", "C"])
        self.assertEqual(len(records), 3)
        self.assertEqual([r["pmid"] for r in records], ["A", "B", "C"])
        self.assertEqual(mock_urlopen.call_count, 3)

    # -------------------------------------------------------------------------
    # 钉 5: 摘要清洗（剥 HTML 标签 + HTML 实体反转义 + 空白归一）
    # -------------------------------------------------------------------------
    def test_clean_abstract_comprehensive(self):
        """🔴 红钉：摘要清洗剥 HTML 标签＋HTML 实体反转义＋空白归一。"""
        raw = (
            "<h4>Background</h4>\n"
            "<p>Children with &amp; without Crohn&#39;s disease &lt;Group A&gt;.</p>\n"
            "   <b>Results:</b> 100% improved&nbsp;after therapy.   \t\r\n"
        )
        cleaned = clean_abstract(raw)
        # 2026-11-08 判据修订（判例 42976224）：实体编码的真标签（&lt;sub&gt;）常见于
        # 生物题名/摘要，文本尖括号对（&lt;Group A&gt;）罕见——判别式选择「迭代解转义→
        # 剥标签到稳定」；代价＝文本尖括号对被当伪标签剥除（本例 Group A 消失），已知取舍。
        expected = "Background Children with & without Crohn's disease . Results: 100% improved after therapy."
        self.assertEqual(cleaned, expected)

    def test_clean_abstract_empty_and_none(self):
        """摘要清洗容错：None 或空串安全返回空串 ""。"""
        self.assertEqual(clean_abstract(None), "")
        self.assertEqual(clean_abstract(""), "")
        self.assertEqual(clean_abstract("   \n\t  "), "")

    # -------------------------------------------------------------------------
    # 钉 6: 429 Retry-After 重试路径（最多 3 次）
    # -------------------------------------------------------------------------
    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_http_429_retry_success(self, mock_urlopen, mock_sleep):
        """🔴 红钉：HTTP 429 读 Retry-After 头等待重试，重试成功返回数据。"""
        err_429 = _make_http_error(429, "Too Many Requests", {"Retry-After": "1.5"})
        success_resp = {
            "hitCount": 1,
            "nextCursorMark": None,
            "resultList": {"result": [{"id": "999", "title": "Success"}]},
        }

        mock_urlopen.side_effect = [err_429, _make_mock_response(success_resp)]

        records = epmc_search_day(["0012-3692"], "2024-01-01", "2024-01-02")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["pmid"], "999")
        self.assertEqual(mock_urlopen.call_count, 2)
        # 验证读取 Retry-After 头并进行了 sleep
        mock_sleep.assert_any_call(1.5)

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_http_429_max_retries_exceeded_raises_epmc_error(self, mock_urlopen, mock_sleep):
        """🔴 红钉：HTTP 429 超过 3 次重试后抛出 EpmcError，禁假空禁静默。"""
        err_429 = _make_http_error(429, "Too Many Requests", {"Retry-After": "0.5"})
        # 连续 4 次 429
        mock_urlopen.side_effect = [err_429, err_429, err_429, err_429]

        with self.assertRaises(EpmcError) as ctx:
            epmc_search_day(["0012-3692"], "2024-01-01", "2024-01-02")
        self.assertIn("429", str(ctx.exception))
        self.assertEqual(mock_urlopen.call_count, 4)

    # -------------------------------------------------------------------------
    # 钉 7: 异常路径（网络/解析/HTTP错误均抛 EpmcError，禁静默吞禁假空）
    # -------------------------------------------------------------------------
    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_network_url_error_raises_epmc_error(self, mock_urlopen, mock_sleep):
        """🔴 红钉：网络错误抛 EpmcError。"""
        mock_urlopen.side_effect = urllib.error.URLError("DNS resolution failed")
        with self.assertRaises(EpmcError) as ctx:
            epmc_search_day(["0012-3692"], "2024-01-01", "2024-01-02")
        self.assertIn("Network URLError", str(ctx.exception))

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_timeout_raises_epmc_error(self, mock_urlopen, mock_sleep):
        """🔴 红钉：超时抛 EpmcError。"""
        mock_urlopen.side_effect = socket.timeout("timed out")
        with self.assertRaises(EpmcError) as ctx:
            epmc_fetch_pmids(["9500320"])
        self.assertIn("timed out", str(ctx.exception))

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_invalid_json_raises_epmc_error(self, mock_urlopen, mock_sleep):
        """🔴 红钉：解析失败（非合法 JSON）抛 EpmcError。"""
        bad_resp = MagicMock()
        bad_resp.read.return_value = b"<html>502 Bad Gateway</html>"
        bad_resp.status = 200
        bad_resp.headers = None
        bad_resp.__enter__.return_value = bad_resp
        bad_resp.__exit__.return_value = None
        mock_urlopen.return_value = bad_resp

        with self.assertRaises(EpmcError) as ctx:
            epmc_search_day(["0012-3692"], "2024-01-01", "2024-01-02")
        self.assertIn("JSON", str(ctx.exception))

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_http_500_raises_epmc_error(self, mock_urlopen, mock_sleep):
        """🔴 红钉：服务器 500 错误抛 EpmcError。"""
        mock_urlopen.side_effect = _make_http_error(500, "Internal Server Error")
        with self.assertRaises(EpmcError) as ctx:
            epmc_search_day(["0012-3692"], "2024-01-01", "2024-01-02")
        self.assertIn("HTTP 500", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 钉 8: 期刊字段映射源 journalInfo.journal.{title,nlmid,issn,essn}（全部可缺，缺＝空串不炸）
    # -------------------------------------------------------------------------
    def test_journal_fields_mapping_and_missing_tolerance(self):
        """🔴 红钉：期刊字段全部可缺，缺＝空串不炸。"""
        # 情况 A: 完整字段
        item_full = {
            "id": "111",
            "title": "Title 1",
            "journalInfo": {
                "journal": {
                    "title": "Chest",
                    "nlmid": "0370625",
                    "issn": "0012-3692",
                    "essn": "1931-3543",
                }
            },
        }
        rec_full = parse_record(item_full)
        self.assertEqual(rec_full["journal_title"], "Chest")
        self.assertEqual(rec_full["nlmid"], "0370625")
        self.assertEqual(rec_full["issn"], "0012-3692")
        self.assertEqual(rec_full["essn"], "1931-3543")

        # 情况 B: journalInfo 缺失
        item_missing_ji = {"id": "222", "title": "Title 2"}
        rec_missing_ji = parse_record(item_missing_ji)
        self.assertEqual(rec_missing_ji["journal_title"], "")
        self.assertEqual(rec_missing_ji["nlmid"], "")
        self.assertEqual(rec_missing_ji["issn"], "")
        self.assertEqual(rec_missing_ji["essn"], "")

        # 情况 C: journal 字典内字段均为 None
        item_none_fields = {
            "id": "333",
            "journalInfo": {"journal": {"title": None, "nlmid": None, "issn": None, "essn": None}},
        }
        rec_none = parse_record(item_none_fields)
        self.assertEqual(rec_none["journal_title"], "")
        self.assertEqual(rec_none["nlmid"], "")
        self.assertEqual(rec_none["issn"], "")
        self.assertEqual(rec_none["essn"], "")

    # -------------------------------------------------------------------------
    # 钉 9: commentCorrectionList 映射 retraction_events
    # -------------------------------------------------------------------------
    def test_retraction_events_mapping(self):
        """🔴 红钉：retraction_events 每项 {"type": str, "ref_pmid": str}，出自 commentCorrectionList。"""
        item = {
            "id": "9500320",
            "title": "Wakefield Lancet Paper",
            "commentCorrectionList": {
                "commentCorrection": [
                    {
                        "source": "MED",
                        "id": "15016483",
                        "reference": "Lancet. 2004 Mar 6;363(9411):750.",
                        "type": "Retraction in",
                        "orderIn": 23,
                    },
                    {
                        "source": "MED",
                        "id": "21971344",
                        "reference": "Eur J Gastroenterol Hepatol. 2011 Nov;23(11):1082.",
                        "type": "Expression of concern in",
                        "orderIn": 29,
                    },
                ]
            },
        }
        rec = parse_record(item)
        events = rec["retraction_events"]
        self.assertEqual(len(events), 2)
        self.assertEqual(
            events,
            [
                {"type": "Retraction in", "ref_pmid": "15016483"},
                {"type": "Expression of concern in", "ref_pmid": "21971344"},
            ],
        )

    def test_retraction_events_missing_or_single_dict(self):
        """retraction_events 在缺失或单项 dict 时的容错。"""
        # 缺失 commentCorrectionList
        rec1 = parse_record({"id": "1"})
        self.assertEqual(rec1["retraction_events"], [])

        # 单项 dict
        rec2 = parse_record({
            "id": "2",
            "commentCorrectionList": {
                "commentCorrection": {"type": "Retraction in", "id": "9999"}
            },
        })
        self.assertEqual(rec2["retraction_events"], [{"type": "Retraction in", "ref_pmid": "9999"}])

    # -------------------------------------------------------------------------
    # 钉 10: Record 字段契约全 12 字段完整性
    # -------------------------------------------------------------------------
    def test_record_schema_12_fields(self):
        """验证 Record 字典严格满足契约 12 字段规范与类型。"""
        item = {
            "id": "42971506",
            "title": "Novel therapy for lung cancer",
            "abstractText": "<p>Trial results are promising.</p>",
            "journalInfo": {
                "journal": {
                    "title": "Journal of Thoracic Oncology",
                    "nlmid": "101274235",
                    "issn": "1556-0864",
                    "essn": "1556-1380",
                }
            },
            "pubTypeList": {"pubType": ["Journal Article", "Clinical Trial"]},
            "firstPublicationDate": "2026-11-02",
            "firstIndexDate": "2026-11-03",
            "commentCorrectionList": {"commentCorrection": []},
        }
        rec = parse_record(item)

        # 契约 12 个键
        required_keys = {
            "pmid",
            "title",
            "abstract",
            "journal_title",
            "nlmid",
            "issn",
            "essn",
            "pub_types",
            "first_publication_date",
            "first_index_date",
            "retraction_events",
            # 契约增遗（M 席 2026-11-08）：engine 映射消费四字段
            "doi",
            "pmcid",
            "author_string",
            "affiliation",
            "source",
        }
        self.assertEqual(set(rec.keys()), required_keys)

        # 字段类型与内容断言
        self.assertEqual(rec["pmid"], "42971506")
        self.assertEqual(rec["title"], "Novel therapy for lung cancer")
        self.assertEqual(rec["abstract"], "Trial results are promising.")
        self.assertEqual(rec["journal_title"], "Journal of Thoracic Oncology")
        self.assertEqual(rec["nlmid"], "101274235")
        self.assertEqual(rec["issn"], "1556-0864")
        self.assertEqual(rec["essn"], "1556-1380")
        self.assertEqual(rec["pub_types"], ["Journal Article", "Clinical Trial"])
        self.assertEqual(rec["first_publication_date"], "2026-11-02")
        self.assertEqual(rec["first_index_date"], "2026-11-03")
        self.assertEqual(rec["retraction_events"], [])
        self.assertEqual(rec["source"], "epmc")  # 恒 "epmc"

    # -------------------------------------------------------------------------
    # 额外边界测试：空输入与节流逻辑
    # -------------------------------------------------------------------------
    def test_empty_inputs_return_empty_lists(self):
        """空 ISSN 或空 PMID 列表直接返回 []，不产生网络请求。"""
        self.assertEqual(epmc_search_day([], "2024-01-01", "2024-01-02"), [])
        self.assertEqual(epmc_search_day(["  "], "2024-01-01", "2024-01-02"), [])
        self.assertEqual(epmc_fetch_pmids([]), [])
        self.assertEqual(epmc_fetch_pmids(["   "]), [])

    @patch("time.sleep")
    def test_throttling_sleep_called_when_rapid(self, mock_sleep):
        """节流测试：短时间内发起两次请求必定触发 sleep。"""
        epmc_adapter._last_request_time = 100.0
        with patch("time.time", side_effect=[100.1, 100.3]):
            epmc_adapter._throttle(min_interval=0.3)
            # 100.1 - 100.0 = 0.1 < 0.3，应 sleep(0.2)
            mock_sleep.assert_called_once()
            slept = mock_sleep.call_args[0][0]
            self.assertAlmostEqual(slept, 0.2, places=2)

    def test_constants_contract(self):
        """契约常量存在且正确。"""
        self.assertEqual(
            EPMC_SEARCH_URL,
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        )


if __name__ == "__main__":
    unittest.main()


class TestContractAddendum(unittest.TestCase):
    """契约增遗（M 席 2026-11-08）：doi/pmcid/author_string/affiliation 四字段映射。"""

    def test_addendum_fields_mapped_from_core(self):
        from epmc_adapter import parse_record
        item = {"pmid": "33184242", "title": "T", "doi": "10.1056/NEJMoa2034577",
                "pmcid": "PMC7948579", "authorString": "Suring DTR, et al.",
                "affiliation": "Dana-Farber Cancer Institute, Boston, USA"}
        rec = parse_record(item)
        for k, v in (("doi", "10.1056/NEJMoa2034577"), ("pmcid", "PMC7948579"),
                     ("author_string", "Suring DTR, et al."),
                     ("affiliation", "Dana-Farber Cancer Institute, Boston, USA")):
            # 🔴 红钉：增遗字段缺源＝空串不炸，有源＝逐字映射
            self.assertEqual(rec[k], v, f"增遗字段 {k} 映射错误")

    def test_addendum_fields_absent_are_empty_not_crash(self):
        from epmc_adapter import parse_record
        rec = parse_record({"pmid": "1", "title": "x"})
        self.assertEqual(rec["doi"], "")
        self.assertEqual(rec["pmcid"], "")
        self.assertEqual(rec["author_string"], "")
        self.assertEqual(rec["affiliation"], "")


class TestTransientRetry(unittest.TestCase):
    """瞬态故障有界重试（2026-11-08 对拍判例：SSL 瞬断不重试＝整轮被炸）。"""

    def _ok_response(self):
        body = json.dumps({"hitCount": 1, "resultList": {"result": [{"id": "1", "title": "T"}]}})
        resp = MagicMock()
        resp.status = 200
        resp.headers = Message()
        resp.headers["Content-Type"] = "application/json; charset=utf-8"
        resp.read.return_value = body.encode("utf-8")
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_ssl_eof_retried_then_success(self, mock_urlopen, mock_sleep):
        """两次 SSL 瞬断后第三次成功＝拿到数据（重试 2 次）。"""
        err = urllib.error.URLError(ssl.SSLError("UNEXPECTED_EOF_WHILE_READING"))
        mock_urlopen.side_effect = [err, err, self._ok_response()]
        recs = epmc_fetch_pmids(["1001"])
        self.assertEqual(len(recs), 1)
        self.assertEqual(mock_urlopen.call_count, 3)
        # 判据：含 ≥2 次 ≥2s 的退避睡眠（节流闸自身的亚秒睡不算）
        backoffs = [c.args[0] for c in mock_sleep.call_args_list
                    if c.args and isinstance(c.args[0], (int, float)) and c.args[0] >= 2.0]
        self.assertGreaterEqual(len(backoffs), 2)

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_persistent_ssl_eof_raises_after_bounded_retries(self, mock_urlopen, mock_sleep):
        """持续瞬断＝3 次重试后 EpmcError（有界，不无限等）。"""
        err = urllib.error.URLError(ssl.SSLError("UNEXPECTED_EOF_WHILE_READING"))
        mock_urlopen.side_effect = err
        with self.assertRaises(EpmcError):
            epmc_fetch_pmids(["1001"])
        self.assertEqual(mock_urlopen.call_count, 4)  # 首次＋3 重试

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_http_503_retried_then_success(self, mock_urlopen, mock_sleep):
        err = urllib.error.HTTPError("http://x", 503, "Service Unavailable", Message(), io.BytesIO(b""))
        mock_urlopen.side_effect = [err, self._ok_response()]
        recs = epmc_fetch_pmids(["1002"])
        self.assertEqual(len(recs), 1)
        self.assertEqual(mock_urlopen.call_count, 2)

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_persistent_dns_error_not_retried(self, mock_urlopen, mock_sleep):
        """DNS 解析失败＝持久性错误，不浪费重试直接抛。"""
        err = urllib.error.URLError("Name or service not known")
        mock_urlopen.side_effect = err
        with self.assertRaises(EpmcError):
            epmc_fetch_pmids(["1003"])
        self.assertEqual(mock_urlopen.call_count, 1)


class TestTitleCleaning(unittest.TestCase):
    """题名清洗（2026-11-08 对拍判例 42976224：EPMC 题名含 XML 标记/实体）。"""

    def test_title_markup_cleaned(self):
        from epmc_adapter import parse_record
        rec = parse_record({"pmid": "1", "title": "G&lt;sub&gt;q&lt;/sub&gt;-coupled receptors &amp; cAMP &lt;i&gt;in vivo&lt;/i&gt;"})
        # 剥标签以空格垫（防词粘连）→ 下标内容呈空格分隔，空白归一后如下
        self.assertEqual(rec["title"], "G q -coupled receptors & cAMP in vivo")

    def test_journal_title_markup_cleaned(self):
        from epmc_adapter import parse_record
        rec = parse_record({"pmid": "2", "title": "T",
                            "journalInfo": {"journal": {"title": "Critical care (London, England)&reg;"}}})
        self.assertEqual(rec["journal_title"], "Critical care (London, England)®")
