**干了什么**　把发布闸切到短域唯一。只刷新主域四个地址，独立验真 `www` 的永久跳转和两个退役入口。  
**PI 怎么亲手验**　打开下方 `deploy.json`，按 Ctrl+F 搜索 `?from=www HTTP=301 Location=https://thoradar.online/?from=www`，看到查询参数随跳转保留即可。  
**还剩什么坑**　截至 2026-11-28 20:08，M3 公网回读报告尚未送达。生产放行仍待 M3 和 R2 独立复核。

# T1128-SMOOTH-S12 交付报告

席位 `codex-gpt`，Run `model=gpt-6.2-sol`，签发为 2026-11-28 G18。隔离工作树位于 `.git/t1128-s12-worktree`，基底是 `af3f2775855bb99aeb5c3262cb2738a889b60d70` 加主树现有 S7 三文件差异。补丁以该 S7 状态为应用基线。旧 S11 补丁未纳入。

## 结论与改动清单

- `.github/workflows/deploy_oss.yml` 保留现有 OSS 逐件上传、worker `no-store`、首页最后上传的顺序。正常发布使用 `sw.js`，主域退役发布在 `/sw.js` 放 `sw-retire.js`。刷新命令只提交主域 `/`、`/index.html`、`/sw.js`、`/sw-retire.js`。
- 发布后用公网 HEAD 响应验真。主域四件均须 `200` 且 `Content-MD5` 匹配本次 Git 文件。`www` 的 `/`、`/index.html`、`/?from=www` 必须返回 `301` 或 `308` 和精确的短域同路径、同查询 `Location`。`www` 两 worker 直接响应 `200`，两种发布模式均以退役文件的 `Content-MD5` 验收。两域 worker 同查 JavaScript MIME 和 `no-store`。`Publish verified on both domains` 在上述九次检查都成功后输出。
- `tests/smooth/verify-deploy.mjs` 与 `tests/smooth/deploy-mock.mjs` 模拟两种发布、跳转、旧 worker 退出、刷新和上传故障。正常与退役各断言恰好一次刷新请求，参数仅含主域四地址。短域 `/sw.js` 在六分钟传播场景中第 12 次验证才成功，模拟等待为两次 5 秒、九次 40 秒，共 370 秒。
- `docs/tasks/T1128-SMOOTH/release-contract.md` 落定 G18 验收模型。双域源站预检仍逐验 SNI 和 `200`，公网结果由独立检查决定。

[完整增量补丁](online-release/sol-s12/canonical.patch)

## 本地验证

在隔离工作树用 Node v24.14.0 和 Git Bash 跑完整发布模拟。原始输出如下。

```powershell
$ev = 'docs/tasks/T1128-SMOOTH/online-release/sol-s12'
node tests/smooth/verify-deploy.mjs "$ev/deploy.json"
# SUMMARY {"passed":27,"failed":0}
# exit=0
node tests/smooth/verify-deploy.mjs "$ev/baseline-s7.json" "$ev/baseline-s7.yml"
# SUMMARY {"passed":10,"failed":17}
# exit=1
```

S7 在新模拟中把 `www` 根路径的永久跳转当成对象验真失败。S12 在两种发布模式都跑通，查询样本的原始输出如下。

```text
Verified https://www.thoradar.online/?from=www HTTP=301 Location=https://thoradar.online/?from=www
Publish verified on both domains
```

完整输出与命令跟踪见 [deploy.json](online-release/sol-s12/deploy.json)、[stdout](online-release/sol-s12/deploy.stdout.txt)、[stderr](online-release/sol-s12/deploy.stderr.txt)、[exit](online-release/sol-s12/deploy.exit.txt)、[S7 基线 JSON](online-release/sol-s12/baseline-s7.json) 和 [S7 stderr](online-release/sol-s12/baseline-s7.stderr.txt)。

### 负对照

每组在独立的 YAML 副本撤防后跑同一套测试。各组 `summary.json` 包含准确的替换内容、实际命令、套件退出码和场景退出码。同目录留有候选 YAML 与完整 stdout、stderr、JSON。

```powershell
$runner = 'docs/tasks/T1128-SMOOTH/online-release/sol-s12/run-mutations.mjs'
node $runner www-refresh www-ignore-location
node $runner www-allow-200 www-use-active-worker
node $runner www-allow-302 remove-md5-guard short-wait
```

| 撤防 | 测试汇总 | 失败断言 |
| --- | --- | --- |
| [www-refresh](online-release/sol-s12/www-refresh/summary.json) | 25 通过，2 失败，退出 1 | 正常与退役的刷新地址精确断言 |
| [www-allow-200](online-release/sol-s12/www-allow-200/summary.json) | 25 通过，2 失败，退出 1 | `www-root-200` 和 `www-index-200` |
| [www-allow-302](online-release/sol-s12/www-allow-302/summary.json) | 26 通过，1 失败，退出 1 | `www-redirect-302` |
| [www-ignore-location](online-release/sol-s12/www-ignore-location/summary.json) | 25 通过，2 失败，退出 1 | `www-redirect-wrong-location` 和 `www-redirect-lost-query` |
| [www-use-active-worker](online-release/sol-s12/www-use-active-worker/summary.json) | 21 通过，6 失败，退出 1 | 包括 `www-active-worker` |
| [remove-md5-guard](online-release/sol-s12/remove-md5-guard/summary.json) | 23 通过，4 失败，退出 1 | 包括 `wrong-md5` |
| [short-wait](online-release/sol-s12/short-wait/summary.json) | 26 通过，1 失败，退出 1 | 六分钟传播场景 |

撤掉 MD5 检查后，`wrong-md5-retire` 的发布模拟由退出 `1` 变为 `0`，套件准确报 `FAIL post-publish verification rejects wrong-md5: deployment exited 0`。正本另将 `www /sw.js` 误回正常 worker、HTML 或跳转均判红。汇总见 [mutation-summary.json](online-release/sol-s12/mutation-summary.json)。

### 补丁与产品不变量

```powershell
$wt = '.git/t1128-s12-worktree'
$patch = "$wt/docs/tasks/T1128-SMOOTH/sol-s12-canonical.patch"
git -C $wt diff --check
# exit=0
git diff --check
# exit=0
git apply --check --whitespace=error $patch
# exit=0
git diff HEAD --exit-code -- index.html sw.js sw-retire.js
# exit=0
git -C $wt diff HEAD --exit-code -- index.html sw.js sw-retire.js
# exit=0
```

两树的三件产品 Git blob 都与 HEAD 一致。Windows 主树的两件 worker 为 LF，隔离树检出为 CRLF，首次原始 SHA-256 对比在 `sw.js` 出现差异。通过 `git ls-files --eol` 定位换行差异，再用 `git hash-object --path` 核实三件 Git blob 一致。Git 原件的 `sw.js` MD5 为 `nrgKbeazqBXvILkgAlssIg==`，`sw-retire.js` MD5 为 `xviHOEexQQLp0q41sv2uuA==`。证据见 [Git 检查](online-release/sol-s12/git-checks.txt) 和 [Git blob MD5](online-release/sol-s12/git-blob-md5.txt)。

## 地图影响、遗留风险与终态

- S12 本地施工与证据已交付，R2 独立复核及整合归主控。任务地图以主控回填为准。
- 截至 2026-11-28 20:08（+08:00），`Test-Path -LiteralPath 'docs/tasks/T1128-SMOOTH/mimo-m3-canonical-report.md'` 返回 `False`。`www` 普通路径永久跳转、两条 worker 例外和旧客户端迁移仍待公网回读。本单证据来自本地模拟。
- 轨道⑧整体仍进行中。生产发布由 PI 亲手执行，发布后的公开验收随后进行。

DELIVERY-T1128-SMOOTH-S12
已交付主域唯一刷新、`www` 永久跳转与退役 worker 验真的增量补丁，并保存完整发布模拟和撤防证据。
