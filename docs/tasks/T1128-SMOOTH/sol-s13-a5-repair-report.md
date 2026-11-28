**干了什么**　修复 A5 的 Git blob MD5 基准、错主机回归和首页 MIME 验收，在隔离工作树复跑发布模拟并逐项撤闸验证。\
**PI 怎么亲手验**　打开本单核验回执，看到正本 `32/32`，再对照其中 `skip-host` 的 `suite exit=1` 和 `publish exit=0`。 [核验回执](online-release/sol-s13/results.txt)\
**还剩什么坑**　增量补丁待主控整合。真实发布、CDN 与旧访客退出仍待线上验收。

# T1128-SMOOTH-S13 · Astra A5 返修

**结论**　A5 三项均已用原样本关闭。发布模拟 32/32，源码不变量 5/5，交付相对已整合 S12 的四文件增量。施工席位 `codex-gpt`，委任 Run 键 `model=gpt-6.2-sol`。基底为 `af3f2775855bb99aeb5c3262cb2738a889b60d70` 加主树 S12 的四文件状态，施工目录为 `.git/t1128-s13-worktree`。 [A5 报告](astra-v5/report.md) · [S12 主控复跑](online-release/main-s12-deploy.json) · [可应用补丁](online-release/sol-s13/canonical.patch)

## A5 原样本

| A5 发现与响应 | 返修前 | S13 正本 |
|---|---|---|
| CRLF 检出，短域根路径和 `/index.html` 回 Git blob MD5 `80mggny6RjRXP9Uw4zglxQ==` | 每条重试 12 次，退出 1 | 两条均退出 0 |
| 同一份 CRLF 检出，短域根路径和 `/index.html` 回检出文件 MD5 `OoYTQN1+/i5YpdPcDG8kEg==` | 两条均退出 0 | 每条重试 12 次，退出 1 |
| `308 Location: https://other.invalid/?from=www` | 正本退出 1，A5 撤主机比较后套件 27/27 | 重试 12 次，退出 1。同一撤闸让请求通过，并使套件 31/32、退出 1 |
| 短域根路径和 `/index.html` 回 `200`、正确 blob MD5、`application/octet-stream` | 两条均退出 0 | 每条重试 12 次，退出 1。撤掉首页 MIME 检查后两条均放行，套件退出 1 |

定向回放保留 A5 的响应字节、原调用及 Bash 模拟，按场景切换 A5 原函数与 S13 发布函数。正确主机对照仍通过。两条 www worker 在正确退役 MD5、`text/html`、`no-store` 下仍各重试 12 次并判红。 [A5 原始输入](astra-v5/focused.json) · [S13 定向回放原文与退出码](online-release/sol-s13/focused-replay.json)

发布模拟另为首页、普通 worker 和退役 worker 建立 CRLF 检出，逐个断言检出 MD5 与对应 blob 不同。健康响应使用 Git blob 摘要，短域四对象均通过。改回读检出文件的变异在该场景卡在短域根路径，12 次后退出 1。另用不存在的 Git 目录触发真实 Git 读取错误，发布函数输出 `Unable to compute Content-MD5 from HEAD:index.html` 并退出 1，公网对象 HEAD 为 0 次。 [正本发布输出](online-release/sol-s13/deploy.json) · [检出文件变异](online-release/sol-s13/working-tree-md5.json)

## 改动清单

- `.github/workflows/deploy_oss.yml` 用 `git cat-file blob "HEAD:$source"` 的原始字节计算 MD5，读取或计算失败即终止。短域根路径与首页对象须返回 `text/html`。
- `tests/smooth/verify-deploy.mjs` 从 Git 原始字节独立生成健康响应摘要，新增 CRLF 检出、Git 读取失败、错主机和两条首页错误 MIME 共五项。
- `tests/smooth/deploy-mock.mjs` 按 Git blob 摘要提供健康响应，构造 A5 的错主机与正确 MD5 的 octet-stream。www 健康跳转也带 octet-stream，仍按永久跳转状态和完整 Location 通过。
- `docs/tasks/T1128-SMOOTH/release-contract.md` 同步 Git blob、首页 MIME、www 跳转与退役 worker 判据。

## 验证状态

在 Windows、Node v24.14.0、Git Bash 的隔离工作树执行。原 S12 的 27 条测试全部保留并通过，对应 23 个模拟场景的退出码和完整模拟调用跟踪均与 S12 主控记录相同。S13 共执行 28 个模拟场景。 [发布命令](online-release/sol-s13/deploy.run.txt) · [发布 stdout](online-release/sol-s13/deploy.stdout.txt) · [S12 比对结果](online-release/sol-s13/s12-comparison.txt) · [源码检查](online-release/sol-s13/source.json)

| 撤闸或回归动作 | 套件通过 / 失败 | 实测 |
|---|---:|---|
| [改回检出文件 MD5](online-release/sol-s13/working-tree-md5.json) | 8 / 24 | CRLF 发布退出 1。通常模拟也使用这次 Windows 检出的 CRLF 文件，旧逻辑会更早阻断其它场景 |
| [移除主机比较，保留路径及查询](online-release/sol-s13/skip-host.json) | 31 / 1 | 错主机发布退出 0，唯一失败项为错主机用例 |
| [移除首页 MIME 比较](online-release/sol-s13/ignore-homepage-mime.json) | 30 / 2 | 根路径和 `/index.html` 的错误 MIME 发布均退出 0 |
| [把 www 塞回刷新列表](online-release/sol-s13/www-refresh.json) | 30 / 2 | 正常和退役均触发四地址精确断言 |
| [放行 302](online-release/sol-s13/www-allow-302.json) | 31 / 1 | 正本判红，变异发布退出 0 |
| [允许 www 使用正常 worker](online-release/sol-s13/www-active-worker.json) | 25 / 7 | 正本判红，`www-active-worker` 变异发布退出 0 |
| [移除响应 MD5 比较](online-release/sol-s13/skip-md5-comparison.json) | 28 / 4 | 正本判红，`wrong-md5-retire` 变异发布退出 0 |
| [缩短传播等待](online-release/sol-s13/short-propagation.json) | 31 / 1 | 正本在第 12 次 worker HEAD 成功，模拟等待 370 秒。缩短后发布退出 1 |

正本继续拒绝错路径和丢查询，worker 保持 JS MIME 与 `no-store`。正本 stdout 的汇总为 `SUMMARY {"passed":32,"failed":0}`，表中八组变异的套件退出码均为 1。每组具体改动、执行命令、stderr 与命中的场景均存原始回执。 [重放入口](online-release/sol-s13/replay.py) · [核验回执](online-release/sol-s13/results.txt)

`git diff --check` 退出 0。主树及隔离树的 `git diff HEAD --exit-code -- index.html sw.js sw-retire.js` 均退出 0，逐个比较 Git 对象也一致。主树 `git apply --check --whitespace=error` 退出 0。 [Git 命令与原始输出](online-release/sol-s13/git-checks.txt)

## 地图与遗留风险

- **地图影响**　⑧ 的 A5 三项发现可回填本地返修完成，S13 四文件补丁待主控整合。
- **遗留风险**　发布后的真实响应字节、MIME、CDN 配置和旧 www 访客退出仍待线上验收。本单证据为本地模拟及源码检查。本次收卷时主树未见 M3 回读报告。
- **地图终态**　S13 本地交付完成。⑧ 仍为 `in-progress-browser-repair`，按现有地图由主控回填。

DELIVERY-T1128-SMOOTH-S13
本单修复了 A5 的 Git blob MD5、错主机回归和首页 MIME 三项问题，并交付原样回放、撤闸证据与待整合补丁。
