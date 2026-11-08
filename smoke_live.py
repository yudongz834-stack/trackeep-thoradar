"""真网冒烟脚本 (smoke_live.py)

独立可跑。直连 Europe PMC API，抓取真实期刊指定日窗文献：
1. 抓 1 个期刊 1 天窗（Chest, ISSN: 0012-3692, 窗口: 2024-01-01 到 2024-01-31）
2. 打印 Record 数与首条摘要前 80 字
3. 验证首条文献通过 epmc_fetch_pmids 批量拉取接口一致性
"""

import sys
from epmc_adapter import epmc_fetch_pmids, epmc_search_day


def main():
    print("=== Europe PMC 采集适配器真网冒烟开始 ===")

    # 1. 抓 1 个胸科顶刊 1 个时间窗口 (Chest)
    issn = "0012-3692"
    date_from = "2024-01-01"
    date_to = "2024-01-31"

    print(f"[1/3] 正在通过 epmc_search_day 检索: ISSN={issn}, 窗口=[{date_from} TO {date_to}]...")
    records = epmc_search_day([issn], date_from, date_to)

    # 2. 打印 Record 数
    print(f"Record 数: {len(records)}")
    if not records:
        print("❌ 错误：真网未返回任何记录，冒烟失败！", file=sys.stderr)
        sys.exit(1)

    # 3. 打印首条记录详情及首条摘要前 80 字
    first = records[0]
    print(f"首条 PMID: {first['pmid']}")
    print(f"首条标题: {first['title']}")
    print(f"首条期刊: {first['journal_title']} (ISSN: {first['issn']})")
    print(f"首条发表日: {first['first_publication_date']} (入库日: {first['first_index_date']})")
    print(f"首条摘要前 80 字: {first['abstract'][:80]}")
    print(f"首条来源标识: {first['source']}")

    # 4. 冒烟校验：首条必须有非空 PMID 与摘要
    if not first["pmid"]:
        print("❌ 错误：首条记录 PMID 为空！", file=sys.stderr)
        sys.exit(1)
    if not first["abstract"]:
        print("❌ 错误：首条记录摘要为空（未带 core 结果）！", file=sys.stderr)
        sys.exit(1)

    # 5. 联动冒烟：通过 epmc_fetch_pmids 按首条 PMID 回拉
    print(f"[2/3] 正在通过 epmc_fetch_pmids 回查 PMID={first['pmid']}...")
    fetched = epmc_fetch_pmids([first["pmid"]])
    if not fetched:
        print(f"❌ 错误：epmc_fetch_pmids 未查到 PMID={first['pmid']}！", file=sys.stderr)
        sys.exit(1)
    print(f"epmc_fetch_pmids 回查成功: PMID={fetched[0]['pmid']}, 标题={fetched[0]['title'][:40]}...")

    print("=== [3/3] Europe PMC 采集适配器真网冒烟全部通过 ===")


if __name__ == "__main__":
    main()
