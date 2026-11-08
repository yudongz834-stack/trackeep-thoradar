"""Europe PMC 采集适配器 (epmc_adapter.py)

实现 ThorRadar 双源改造接口契约 v1 模块一：
- epmc_search_day(issns, date_from, date_to) -> list[Record]
- epmc_fetch_pmids(pmids) -> list[Record]
- EpmcError: 自定义异常
- EPMC_SEARCH_URL: 常量
- 摘要清洗: 剥 HTML 标签 + HTML 实体反转义 + 空白归一
- 节流: 请求间 sleep >= 0.3s; HTTP 429 读 Retry-After 等待重试 (最多 3 次); 超时 30s
- 期刊字段容错映射
- 纯 Python 标准库，零第三方依赖
"""

import html
import json
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

# 常量（契约正本规定）
EPMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

# 运行参数
DEFAULT_TIMEOUT = 30.0
THROTTLE_INTERVAL = 0.3
MAX_429_RETRIES = 3
MAX_TRANSIENT_RETRIES = 3        # 5xx/断连/超时 有界退避重试（2026-11-08 对拍判例）
TRANSIENT_BACKOFF_BASE = 2.0    # 退避基数秒：2s→4s→6s
FETCH_BATCH_SIZE = 25
PAGE_SIZE = 100
DEFAULT_USER_AGENT = "ThorRadar/1.0 (EPMC Adapter)"


class EpmcError(Exception):
    """Europe PMC 采集与解析自定义异常。

    契约规定：网络/解析失败抛 EpmcError(msg)，禁静默吞禁返回假空。
    """
    pass


# 节流时间戳记录
_last_request_time: float = 0.0


def _throttle(min_interval: float = THROTTLE_INTERVAL) -> None:
    """保证请求间 sleep >= min_interval 秒。"""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _last_request_time = time.time()


def _parse_retry_after(header_val: Optional[str], default: float = 2.0) -> float:
    """解析 HTTP 429 Retry-After 响应头（秒数）。"""
    if not header_val:
        return default
    try:
        val = float(header_val.strip())
        return max(0.1, val)
    except (ValueError, TypeError):
        return default


def _is_transient(reason: str) -> bool:
    """瞬态网络故障判定：断连/重置/EOF/超时类（区分于 DNS 解析失败等持久性错误）。"""
    r = str(reason).lower()
    marks = (
        "unexpected_eof", "connection reset", "connection aborted",
        "timed out", "timeout", "temporarily unavailable",
        "connection refused", "10054", "10060",
    )
    return any(m in r for m in marks)


def clean_abstract(raw: Optional[str]) -> str:
    """摘要清洗：剥 HTML 标签 + HTML 实体反转义 + 空白归一。

    若输入为空或 None，返回空串 ""。
    """
    if not raw:
        return ""
    # 🔴 判例 42976224：实体编码的标签（&lt;sub&gt;）会先变回 <sub>——必须
    # 「解转义→剥标签」迭代到稳定（通常 1~2 轮），单轮顺序会留活标签。
    text = str(raw)
    for _ in range(3):
        stripped = re.sub(r"<[^>]+>", " ", text)
        unescaped = html.unescape(stripped)
        if unescaped == text:
            break
        text = unescaped
    # 空白归一（包括 \r, \n, \t, \xa0 等全折叠为单空格并 strip）
    text = " ".join(text.split())
    return text


def parse_record(item: Dict[str, Any]) -> Dict[str, Any]:
    """将 Europe PMC 单条 JSON 记录解析为规范 Record dict。

    Record 契约：
    Record = {
      "pmid": str,                    # 身份证号，合并唯一键
      "title": str,
      "abstract": str,                # 纯文本（HTML剥净），可空串
      "journal_title": str,
      "nlmid": str,                   # 可空
      "issn": str,                    # 纸本 ISSN，可空
      "essn": str,                    # 电子 ISSN，可空
      "pub_types": list[str],
      "first_publication_date": str,  # YYYY-MM-DD，可空
      "first_index_date": str,        # YYYY-MM-DD，可空
      "retraction_events": list[dict],# 每项 {"type": str, "ref_pmid": str}，出自 commentCorrectionList
      "source": str,                  # 恒 "epmc"
    }
    """
    if not isinstance(item, dict):
        raise EpmcError(f"Expected dict for article item, got {type(item).__name__}")

    # 1. pmid
    pmid = str(item.get("pmid") or item.get("id") or item.get("ext_id") or "").strip()

    # 2. title（🔴 判例 42976224：EPMC 题名含 XML 标记/实体（&lt;sub&gt;q&lt;/sub&gt;），
    #    不清洗＝脏字符入库。题名与摘要同受污染，共用 clean_abstract 管线）
    title = clean_abstract(item.get("title"))

    # 3. abstract（纯文本，HTML剥净，空白归一，可空串）
    raw_abstract = item.get("abstractText") or item.get("abstract") or ""
    abstract = clean_abstract(raw_abstract)

    # 4-7. 期刊字段映射源：journalInfo.journal.{title,nlmid,issn,essn}（全部可缺，缺＝空串不炸）
    journal_info = item.get("journalInfo")
    if not isinstance(journal_info, dict):
        journal_info = {}
    journal = journal_info.get("journal")
    if not isinstance(journal, dict):
        journal = {}

    journal_title = clean_abstract(journal.get("title") or item.get("journal_title") or "")
    nlmid = str(journal.get("nlmid") or item.get("nlmid") or "").strip()
    issn = str(journal.get("issn") or item.get("issn") or "").strip()
    essn = str(journal.get("essn") or item.get("essn") or "").strip()

    # 8. pub_types: list[str]
    pub_types: List[str] = []
    pub_type_list = item.get("pubTypeList")
    if isinstance(pub_type_list, dict):
        pts = pub_type_list.get("pubType", [])
        if isinstance(pts, list):
            pub_types = [str(p).strip() for p in pts if str(p).strip()]
        elif isinstance(pts, str) and pts.strip():
            pub_types = [pts.strip()]
    elif isinstance(pub_type_list, list):
        pub_types = [str(p).strip() for p in pub_type_list if str(p).strip()]

    # 9. first_publication_date: YYYY-MM-DD，可空
    first_pub_date = str(
        item.get("firstPublicationDate")
        or item.get("first_publication_date")
        or item.get("printPublicationDate")
        or ""
    ).strip()

    # 10. first_index_date: YYYY-MM-DD，可空
    first_idx_date = str(
        item.get("firstIndexDate") or item.get("first_index_date") or ""
    ).strip()

    # 10a. 契约增遗（M 席集成补遗 2026-11-08）：doi/pmcid/author_string/affiliation
    #      —— engine 侧 record_to_article 消费（authors 进精选流展示、doi 进跨天去重账本）
    doi = str(item.get("doi") or "").strip()
    pmcid = str(item.get("pmcid") or "").strip()
    author_string = str(item.get("authorString") or "").strip()
    affiliation = str(item.get("affiliation") or "").strip()

    # 11. retraction_events: 每项 {"type": str, "ref_pmid": str}，出自 commentCorrectionList
    retraction_events: List[Dict[str, str]] = []
    cc_list = item.get("commentCorrectionList")
    if isinstance(cc_list, dict):
        corrections = cc_list.get("commentCorrection", [])
        if isinstance(corrections, dict):
            corrections = [corrections]
        if isinstance(corrections, list):
            for cc in corrections:
                if isinstance(cc, dict):
                    event_type = str(cc.get("type") or "").strip()
                    ref_id = str(cc.get("id") or cc.get("ref_pmid") or "").strip()
                    retraction_events.append({
                        "type": event_type,
                        "ref_pmid": ref_id,
                    })

    # 12. source: 恒 "epmc"
    return {
        "pmid": pmid,
        "title": title,
        "abstract": abstract,
        "journal_title": journal_title,
        "nlmid": nlmid,
        "issn": issn,
        "essn": essn,
        "pub_types": pub_types,
        "first_publication_date": first_pub_date,
        "first_index_date": first_idx_date,
        "retraction_events": retraction_events,
        "doi": doi,
        "pmcid": pmcid,
        "author_string": author_string,
        "affiliation": affiliation,
        "source": "epmc",
    }


def _http_get_json(
    params: Dict[str, str],
    timeout: float = DEFAULT_TIMEOUT,
    base_url: str = EPMC_SEARCH_URL,
    max_429_retries: int = MAX_429_RETRIES,
) -> Dict[str, Any]:
    """底层 HTTP 请求：节流＋429 按 Retry-After 重试＋瞬态故障（5xx/断连/超时）有界退避重试。

    🔴 实测判例（2026-11-08 对拍）：EPMC 对连发负载会瞬断 SSL 连接
    （UNEXPECTED_EOF_WHILE_READING）——不重试＝整轮采集被一颗瞬态雷炸掉。
    """
    query_str = urllib.parse.urlencode(params)
    url = f"{base_url}?{query_str}"

    retries_429 = 0
    retries_transient = 0
    while True:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "application/json",
            },
        )
        _throttle()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", 200)
                if status != 200:
                    raise EpmcError(f"HTTP request returned non-200 status {status}")

                raw_body = resp.read()
                try:
                    encoding = (
                        resp.headers.get_content_charset("utf-8")
                        if resp.headers
                        else "utf-8"
                    )
                except Exception:
                    encoding = "utf-8"

                if isinstance(raw_body, bytes):
                    text = raw_body.decode(encoding or "utf-8")
                else:
                    text = str(raw_body)

                try:
                    data = json.loads(text)
                except Exception as json_err:
                    raise EpmcError(
                        f"Failed to parse Europe PMC JSON response: {json_err}"
                    ) from json_err

                if not isinstance(data, dict):
                    raise EpmcError(
                        f"Expected JSON object from Europe PMC, got {type(data).__name__}"
                    )

                return data

        except urllib.error.HTTPError as err:
            if err.code == 429:
                if retries_429 < max_429_retries:
                    retries_429 += 1
                    retry_header = (
                        err.headers.get("Retry-After") if err.headers else None
                    )
                    wait_seconds = _parse_retry_after(retry_header)
                    time.sleep(wait_seconds)
                    continue
                raise EpmcError(
                    f"HTTP 429 Rate Limit exceeded after {retries_429} retries"
                ) from err
            if 500 <= err.code < 600 and retries_transient < MAX_TRANSIENT_RETRIES:
                retries_transient += 1
                time.sleep(TRANSIENT_BACKOFF_BASE * retries_transient)
                continue
            raise EpmcError(
                f"HTTP {err.code} error from Europe PMC: {err.reason}"
            ) from err

        except urllib.error.URLError as err:
            reason = str(getattr(err, "reason", err))
            if _is_transient(reason) and retries_transient < MAX_TRANSIENT_RETRIES:
                retries_transient += 1
                time.sleep(TRANSIENT_BACKOFF_BASE * retries_transient)
                continue
            raise EpmcError(f"Network URLError from Europe PMC: {getattr(err, 'reason', err)}") from err

        except (socket.timeout, TimeoutError) as err:
            if retries_transient < MAX_TRANSIENT_RETRIES:
                retries_transient += 1
                time.sleep(TRANSIENT_BACKOFF_BASE * retries_transient)
                continue
            raise EpmcError(
                f"Request to Europe PMC timed out ({timeout}s): {err}"
            ) from err

        except EpmcError:
            raise

        except Exception as err:
            raise EpmcError(f"Unexpected error querying Europe PMC: {err}") from err


def _search_query_all(
    query: str,
    page_size: int = PAGE_SIZE,
    timeout: float = DEFAULT_TIMEOUT,
) -> List[Dict[str, Any]]:
    """以 cursorMark 翻页抓取 query 的全量结果。

    🔴 必带 resultType=core（缺＝无摘要）＋ format=json ＋ pageSize=100
    🔴 cursorMark 分页翻到底（直到无新增或返回页 cursor 与请求相同）
    """
    records: List[Dict[str, Any]] = []
    cursor: str = "*"

    while True:
        params = {
            "query": query,
            "resultType": "core",
            "format": "json",
            "pageSize": str(page_size),
            "cursorMark": cursor,
        }
        data = _http_get_json(params, timeout=timeout)
        result_list = data.get("resultList")
        if not isinstance(result_list, dict):
            # 若结果字典中 hitCount 为 0 且无 resultList，正常终止
            if data.get("hitCount") == 0:
                break
            raise EpmcError("Europe PMC response missing 'resultList'")

        items = result_list.get("result", [])
        if not isinstance(items, list):
            raise EpmcError("Europe PMC response 'result' is not a list")

        # 🔴 无新增或空结果，分页结束
        if not items:
            break

        for item in items:
            records.append(parse_record(item))

        # 🔴 cursorMark 与返回 nextCursorMark 循环
        next_cursor = data.get("nextCursorMark")
        if not next_cursor or next_cursor == cursor:
            break

        cursor = next_cursor

    return records


def epmc_search_day(
    issns: List[str],
    date_from: str,
    date_to: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> List[Dict[str, Any]]:
    """按 ISSN 列表和日期窗口在 Europe PMC 中检索文献并返回 Record 列表。

    - query＝SRC:MED AND (ISSN:<i1> OR ISSN:<i2> ...)，日期窗 (FIRST_IDATE:[date_from TO date_to])
    - 🔴 必带 resultType=core + format=json + pageSize=100
    - 🔴 cursorMark 分页翻到底
    """
    if not issns:
        return []

    # 规范化 ISSN：去重并去空白，保留顺序
    valid_issns: List[str] = []
    seen = set()
    for i in issns:
        s = str(i).strip()
        if s and s not in seen:
            seen.add(s)
            valid_issns.append(s)

    if not valid_issns:
        return []

    issn_subquery = " OR ".join(f"ISSN:{issn}" for issn in valid_issns)
    clean_from = str(date_from).strip()
    clean_to = str(date_to).strip()
    query = f"SRC:MED AND ({issn_subquery}) AND (FIRST_IDATE:[{clean_from} TO {clean_to}])"

    return _search_query_all(query=query, timeout=timeout)


def epmc_fetch_pmids(
    pmids: List[str],
    timeout: float = DEFAULT_TIMEOUT,
) -> List[Dict[str, Any]]:
    """按 PMID 列表逐条抓取 Record 列表。

    - 🔴 实测判例（2026-11-08 对拍）：EPMC 检索 API 的 EXT_ID 字段**不支持 OR 组**——
      单查命中、2 个以上 OR（含逐项加括号）静默归零。故必须逐 PMID 单查，
      节流间隔照常（0.3s）；批量 OR 写法在该 API 是静默漏检，禁再引入。
    """
    if not pmids:
        return []

    # 规范化 PMID：去重并去空白，保留顺序
    valid_pmids: List[str] = []
    seen = set()
    for p in pmids:
        s = str(p).strip()
        if s and s not in seen:
            seen.add(s)
            valid_pmids.append(s)

    if not valid_pmids:
        return []

    all_records: List[Dict[str, Any]] = []
    for pmid in valid_pmids:
        query = f"SRC:MED AND EXT_ID:{pmid}"
        all_records.extend(_search_query_all(query=query, timeout=timeout))

    return all_records
