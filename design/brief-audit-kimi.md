# 审计席任务书（Kimi K3 · 终版总表独立审计）

## 委任状（五行简化版）
- 轨道位置：trackeep-thoradar（胸科雷达）→ 一次性审计席（不进登记册）
- R 级：R1——只允许新建一个报告文件 `D:\trackeep-thoradar\design\终表审计-kimi.md`
- 判级理由：纯只读审计＋一份报告，被审对象零改动
- 签发：Orchestrator（coordinator），2026-10-18，PI 口谕「保质保量，把表格交出来」

## 你审什么
被审对象：`D:\trackeep-thoradar\期刊表\Thoradar确定期刊-终版总表.xlsx`（复审轮：上一轮 FAIL 已修复，341 行，sheet「确定期刊」＋「说明」页）
对照真值（全部只读）：
- `期刊表\2025年中科院大类分区期刊排名汇总表.xlsx`（定档真值）
- `期刊表\最新IF 2025 全.xlsx`（IF/JCR 真值）
- `design\identity-draft-gemini.json`＋`identity-draft-gemini-j4.json`（NLM 身份真值）
- PI 圈定种 60 本（种子名册文件已按 PI 令剔除，仅存于建库 git 历史）

## 审计清单（逐项过，给出 过/不过＋证据）
1. **行数与分档**：数据行=341；S=14/A=179/B=133/C=15；S 档 14 本名单逐一列出核对；并复核上一轮 FAIL 的两项 critical 已消除——34 行重复是否清零（全称/缩写/NLM ID 三维查重）＋BJS 行是否已矫正（British Journal of Surgery / Br J Surg / 0372553 / 1区 / A）。
2. **档位规则抽样**：随机抽 20 本（每档至少 3 本），按「S14 名单外：1区/2区→A、3区→B、4区或未收录→C」复算档位，与表内档位比对。
3. **禁编造检查**：IF 列只能是非负数字或「—」；5年IF 列必须全为「—」；发现任何可疑编造数字即 critical。
4. **身份数据对拍**：抽 20 本的 NLM ID 与 identity 两份 JSON 比对（纯数字 ID 已统一补足 7 位前导零）；「Nature/Science=0410462/0404511、BMJ=8900488、CA=0370647」四本必查。
5. **重复检查**：期刊全称与 PubMed 缩写两个维度各查一遍碰撞。
6. **旗舰在位**：CA-A Cancer Journal for Clinicians、Cell、Nature、Science、BMJ、The Lancet、NEJM 六本以上点名核在位与档位。
7. **说明页一致性**：说明页写的分档统计与实际行数一致。

## 输出（唯一允许写的文件）
`D:\trackeep-thoradar\design\终表审计-kimi.md`：
- 头部三行：审计时间 / 审计版本（文件大小+行数）/ 结论（PASS / PASS-with-notes / FAIL）
- 逐项清单结果（过/不过＋证据数字）
- 发现项分级：critical（影响字典正确性）/ minor（显示瑕疵）/ 建议
- 未覆盖开口清单（你没来得及查的部分如实列）

## 禁区
- 只写上述一个报告文件；被审对象与全部真值文件只读；禁 git；禁联网
- Python 用 `E:/Python/python.exe -X utf8 -I`（openpyxl 可用）；bash 路径正斜杠
