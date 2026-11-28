**干了什么**　独立重跑 G18 发布候选，正本模拟 27/27；复现了 Git blob MD5 基准偏差，并找到一个错主机回归测试缺口。  
**PI 怎么亲手验**　打开[核验回执](review-results.txt)，看开头三条记录：首页 Git blob 的 MD5 以 `80mg` 开头，脚本实际接受的 MD5 以 `OoYT` 开头。  
**还剩什么坑**　Git blob 验真待修，错主机缺专门用例，首页 MIME 的验收范围待明确；M3 公网回读报告截至取证时尚未送达。

# T1128-SMOOTH-A5 · G18 单正式域名发布候选独立复核

**结论：R2 有发现，候选未通过全部独立判据。** 正常和退役发布均只刷新短域四地址。两条 `www` worker 退役入口、永久跳转、上传失败阻断和 370 秒传播等待均有本地执行证据。判据 2 要求以 Git blob 为基准，当前工作流的期望值随检出字节变化。生产状态待 M3 和 PI 的真实发布验收。

复核席位 `codex-gpt`，委任版本键 `model=gpt-6.2-astra`，新会话独立执行。对象为主树 `af3f2775855bb99aeb5c3262cb2738a889b60d70` 加已整合的工作区改动。对工作流、两个模拟脚本、合同与三件产品在复跑前后核对了 SHA-256。被审材料为 [Sol S12 报告](../sol-s12-canonical-report.md)、[增量补丁](../online-release/sol-s12/canonical.patch)、[主控复跑](../online-release/main-s12-deploy.json) 和 [S12 汇总](../online-release/sol-s12/mutation-summary.json)。

## 发现与最小复现

### 高 · 发布验真从检出文件计算 MD5，未绑定发布提交的 blob

[工作流第 236 行](../../../../.github/workflows/deploy_oss.yml#L236) 用 `openssl dgst -md5 -binary "$source"` 读取检出文件。[验收脚本第 184 行](../../../../tests/smooth/verify-deploy.mjs#L184) 将同一工作区文件复制进模拟环境，[模拟器第 59、65 行](../../../../tests/smooth/deploy-mock.mjs#L59) 再用该文件生成响应头。Git 的换行转换就足以让两边一致而偏离发布提交。

| 首页输入 | HEAD blob 的 MD5 | 当前工作区的 MD5 |
| --- | --- | --- |
| 同一 Git 对象 `7ee203a5111a144e8c5ad3c7db2baea00b03b61c` | `80mggny6RjRXP9Uw4zglxQ==`（LF） | `OoYTQN1+/i5YpdPcDG8kEg==`（CRLF） |

最小复现使用候选原有的 `verify_object`，给短域根路径回固定的模拟 HEAD。正本在当前检出字节下收到 Git blob 的 MD5 后重试 12 次、退出 1；仅把响应 MD5 换成工作区值便退出 0。`/index.html` 同样复现。用 `git cat-file blob HEAD:index.html` 的原始字节作为本地文件，两种响应的判定恰好翻转。Sol 的健康日志中两件 worker 也接受过其 CRLF 检出的 MD5。此项阻断“已按 Git blob 验真”的结论；线上实际字节差异未复现。修复验收应由发布提交的原始 blob 提供独立期望值，并用检出字节不同的样本验证。[原始响应、Bash 输入与退出码](focused.json) · [Git 命令和既有记录](audit.txt)

### 中 · 删除跳转主机比较，发布套件仍全绿

[模拟器第 41–44 行](../../../../tests/smooth/deploy-mock.mjs#L41) 的 `www-redirect-wrong-location` 只改路径，构造的目标主机恒为短域。[验收脚本第 271 行](../../../../tests/smooth/verify-deploy.mjs#L271) 覆盖了错路径和丢查询。[正本第 204 行](../../../../.github/workflows/deploy_oss.yml#L204) 会比较完整 Location，本次单独核实它能拒绝错主机。

最小复现仅在隔离 YAML 中移除主机比较，保留状态、Location 数量、路径和查询检查。完整套件仍为 27/27、退出 0。向原函数输入同一个本地 `308`，Location 为 `https://other.invalid/?from=www`，正本退出 1，变异退出 0。新增用例可以沿用这一响应，要求正本判红、撤掉主机检查后套件判红。[改动差异](skip-host.diff) · [完整套件](skip-host.json) · [错主机单项](focused.json)

### 验收范围 · 首页错误 MIME 会通过

[工作流第 188、245 行](../../../../.github/workflows/deploy_oss.yml#L188) 只给 worker 检查 MIME。对短域 `/` 和 `/index.html` 返回 `200`、正确的 Git blob MD5 和 `Content-Type: application/octet-stream`，两项均输出 `Verified`、退出 0。给任一 `www` worker 返回正确退役 MD5 和 `text/html`，则重试 12 次、退出 1。按本单判据 4 的“坏 MIME 均判红”覆盖首页理解，此项为中等缺口；[现行合同第 10–11 行](../release-contract.md#L10) 仅明确要求 worker 的 JavaScript MIME。两种对象的实测行为均已列明。[独立响应原文](focused.json)

## 验证状态

Node v24.14.0、Git Bash。本次从主树逐字节复制候选到系统临时目录。每组变异各取正本副本，使用相同的 `verify-deploy.mjs` 和 `deploy-mock.mjs`，分别写新结果。每个 `.run.json` 记录原命令、工作目录、起止时刻和退出码。

| 独立执行 | 通过 / 失败 | 退出码 | 直接观察 |
| --- | ---: | ---: | --- |
| [正本](canonical.json) | 27 / 0 | 0 | 27 条测试结果和 23 个模拟场景的退出码、stdout、stderr、调用记录均与主控 JSON 一致 |
| [允许 302](allow-302.json) | 26 / 1 | 1 | `www-redirect-302` 场景从退出 1 变为 0，套件准确报 `deployment exited 0` |
| [www 使用当前模式的 worker](www-active.json) | 21 / 6 | 1 | 正常模式下错误的正常 worker 被接受，`www-active-worker` 场景从退出 1 变为 0；原有健康场景在该 URL 判红 |
| [只比较路径和查询](skip-host.json) | 27 / 0 | 0 | 完整套件漏过变异；额外的错主机输入区分了正本与变异 |
| [源码不变量 `--ci`](source.json) | 5 / 0 | 0 | 日报数据、初始化与合并、写域、语法和 Git 检查通过 |

两组预期失败均直接来自发布行为变化。以下为原始 stderr；完整命令见[正本回执](canonical.run.json)、[302 回执](allow-302.run.json)、[worker 回执](www-active.run.json) 和[主机比较回执](skip-host.run.json)。[正本全部 27 项 stdout](canonical.stdout.txt) · [302 stderr](allow-302.stderr.txt) · [worker stderr](www-active.stderr.txt)

```text
FAIL post-publish verification rejects www-redirect-302: deployment exited 0
FAIL post-publish verification rejects www-active-worker: deployment exited 0
```

- **刷新与上传。** 正常、退役各调用一次 `RefreshObjectCaches`，ObjectPath 精确为短域 `/`、`/index.html`、`/sw.js`、`/sw-retire.js`。两模式均先传退役入口，再传当前模式的 `/sw.js`，最后传首页。模拟 `/sw.js` 上传出错，退出 1，首页上传和刷新均为 0 次。[两种模式及断点的调用记录](review-results.txt)
- **响应。** 健康场景两模式各完成短域四次对象 HEAD、`www` 三次跳转 HEAD 和两次退役 worker HEAD。根、index、带查询样本分别回 301、308、301，Location 保留路径和查询。200 同内容、302、错路径、丢查询均在正本判红；错主机另以独立响应判红。两条 `www` worker 的独立样本各自只接受直接 200、退役 MD5、JS、no-store，分别拒绝正常 worker、HTML MIME、可缓存响应和跳转；套件另覆盖 404 及 HEAD 网络错误。[完整跟踪](canonical.json) · [两条退役入口定向检查](focused.json)
- **传播。** 短域 `/sw.js` 在第 12 次 HEAD 成功。sleep 调用为两次 5 秒、九次 40 秒，累计 370 秒。这是模拟时钟的等待量。[等待与调用次数](review-results.txt)
- **补丁与产品。** 从 HEAD 的四个 blob 依次重放 S7、S12，四个结果逐字节匹配当前候选对应的 Git 内容。S12 涉及工作流、合同和两个模拟脚本，共 4 文件、140 增、59 删。`git diff HEAD --exit-code -- index.html sw.js sw-retire.js` 退出 0，三件产品逐个核对 `git hash-object --path` 与 `HEAD:<文件>` 相等。Sol 报告 17/17 个链接可读；S7 基线、S12 正本和七组旧变异的候选、汇总、场景退出码及日志已按各自适用项交叉核对。[命令与输出](audit.txt) · [输入指纹](snapshot-sha256.txt)

### 在仓根重放一个关键判定

下列 PowerShell 命令使用本单保存的原函数与固定响应头，curl 和 sleep 均由 Bash 函数模拟。命令重放以 Git blob 为基准的首页响应，可观察到两种 MD5 和退出码 1。将样本名换成 `canonical_wrong-host-only` 或 `skip-host_wrong-host-only` 即可重放错主机的 1 / 0 对照。

```powershell
@'
import json, os, subprocess, sys
from pathlib import Path
cases = json.loads(Path("docs/tasks/T1128-SMOOTH/astra-v5/focused.json").read_bytes())
p = next(item for item in cases if item["name"] == sys.argv[1])
env = {k: os.environ[k] for k in ("PATH","SystemRoot","TEMP","TMP") if k in os.environ}
env["A5_RESPONSE"] = p["response"]
r = subprocess.run(p["command"], input=p["bashStdin"].encode(), env=env)
print("exit=" + str(r.returncode))
'@ | python - 'working-expectation_git-response /'
```

## 未验范围与地图影响

截至 2026-11-28 20:23（+08:00），`Test-Path -LiteralPath 'docs/tasks/T1128-SMOOTH/mimo-m3-canonical-report.md'` 输出 `False`。本单覆盖本地发布与无浏览器源码回归。真实浏览器、S1/S2/S3 与 UX 浏览器回归、旧访客退出、公网 CDN/RAM、真实刷新和发布均在本次范围外。本地证据无法确定生产端现状。[状态回执](review-results.txt)

地图建议主控记录“⑧ A5 唯一独立复核已交付，有发现；Git blob 验真待修，M3 公网回读待收”。修复沿本单证据验收，不另开循环送审。A5 交付仅写入 `docs/tasks/T1128-SMOOTH/astra-v5/` 与系统临时目录，任务地图归主控回填。

DELIVERY-T1128-SMOOTH-A5
本次独立复核重跑了发布模拟和三组变异，核实短域刷新与旧 worker 退役行为，并复现了 Git blob 验真偏差、错主机回归漏判和首页 MIME 放行。
