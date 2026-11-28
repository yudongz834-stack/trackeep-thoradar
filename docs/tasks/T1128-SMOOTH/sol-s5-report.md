**干了什么**　接好了正常发布、退役发布、双域刷新验真和前置 CI。C1 候选的本机模拟与核心回归均通过。\
**PI 怎么亲手验**　打开[发布模拟原始输出](sol-s5/deploy.stdout.txt)，看到 `PASS normal`、`PASS retire` 和末行 `"passed":18,"failed":0` 即为本机模拟通过。\
**还剩什么坑**　保留现有主分支的日报数据后，固定基线会阻止部署。主控须裁定日报基线后才能放行发布，Astra 独立复核和 PI 线上验收也待完成。

## 地图影响

⑥ Sol S5 已交付隔离工作树候选、原始证据和[增量补丁](sol-s5/candidate.diff)。C1 首页、正常 worker、退役 worker 的 SHA-256 与开工记录及委任状逐件一致。补丁只含四个施工文件，可叠在 C1 候选上。[开工哈希](sol-s5/hashes-before.json) · [收尾哈希](sol-s5/hashes-after.stdout.txt) · [补丁检查退出码](sol-s5/patch.run.json)

## 改动清单

- [部署工作流](../../../.github/workflows/deploy_oss.yml)新增 `smooth-verify`，用 Windows、全历史和 Node 24 依次跑发布检查、源码、S1/S2/S3 和 UX。检查与上传显式使用同一 `github.sha`。部署依赖闸门，发布任务通过同一并发组串行执行。
- `/sw-retire.js` 始终上传仓内退役 worker。`retire=true` 时 `/sw.js` 也上传该文件，默认模式上传仓内 `sw.js`。两个 worker 均强制覆盖，带 `application/javascript` 和 `no-store`。首页以原有 `public, max-age=60, s-maxage=3600` 最后上传。
- 保留双域直连 HTTPS 预检。固定 Aliyun CLI `v3.5.4` 并校验 SHA-256，通过 OSS secret 的 CLI 环境别名刷新双域四条路径。每次提交八个 URL，最多两次调用，要求返回 `RefreshTaskId`。随后逐 URL 轮询 HTTP 200 和对应本地文件的 Content-MD5，另查两个 worker 的 MIME 和 `no-store`，全部通过才输出完成。
- [发布测试](../../../tests/smooth/verify-deploy.mjs)从 YAML 提取实际 Bash，使用[假命令](../../../tests/smooth/deploy-mock.mjs)回放。`verify-source` 只增加 `.github/workflows/deploy_oss.yml` 这一个白名单条目。既有浏览器试卷照原入口和判据执行。

## 验证状态

Windows 11 Pro x64 `10.0.26300`、Node `24.14.0`、Chrome `158.0.8127.88`、Git Bash `5.2.37`。浏览器使用隔离配置和本机回环服务。发布模拟使用合成凭证及应答。表中退出码来自每条原命令的捕获记录。

| 验证 | 结果 | 退出码 | 原始证据 |
| --- | --- | ---: | --- |
| 发布静态与 Bash 模拟 | 18 通过 | 0 | [stdout](sol-s5/deploy.stdout.txt) · [stderr](sol-s5/deploy.stderr.txt) · [JSON，含各模拟子进程输出和调用参数](sol-s5/deploy.json) · [命令](sol-s5/deploy.run.json) |
| 删掉 MD5 比较 | 16 通过，2 失败 | 1 | [stdout](sol-s5/no-md5.stdout.txt) · [stderr](sol-s5/no-md5.stderr.txt) · [JSON](sol-s5/no-md5.json) · [命令与删除内容](sol-s5/no-md5.run.json) |
| `verify-source` | 5 通过 | 0 | [stdout](sol-s5/source.stdout.txt) · [stderr](sol-s5/source.stderr.txt) · [JSON](sol-s5/source.json) · [命令](sol-s5/source.run.json) |
| S1 | 9 通过 | 0 | [stdout](sol-s5/s1.stdout.txt) · [stderr](sol-s5/s1.stderr.txt) · [JSON](sol-s5/s1.json) |
| S2 | 24 通过 | 0 | [stdout](sol-s5/s2.stdout.txt) · [stderr](sol-s5/s2.stderr.txt) · [JSON](sol-s5/s2.json) |
| S3 | 9 通过 | 0 | [stdout](sol-s5/s3.stdout.txt) · [stderr](sol-s5/s3.stderr.txt) · [JSON](sol-s5/s3.json) |
| UX | 46 通过 | 0 | [stdout](sol-s5/ux.stdout.txt) · [stderr](sol-s5/ux.stderr.txt) · [量测 JSON](sol-s5/ux-measurements/) |
| YAML 语法 | 解析通过 | 0 | [stdout](sol-s5/yaml.stdout.txt) · [stderr](sol-s5/yaml.stderr.txt) · [命令](sol-s5/yaml.run.json) |
| Git 差异 | `diff --check` 和补丁反向应用检查均通过 | 0 | [补丁统计](sol-s5/patch-1.stdout.txt) · [命令和退出码](sol-s5/patch.run.json) |
| 浏览器进程复查 | 记录中的 19 个 PID 均已退出 | 0 | [stdout](sol-s5/process-recheck.stdout.txt) · [命令和 PID 清单](sol-s5/process-recheck.run.json) |

[四项浏览器回归命令和退出码](sol-s5/browser-suites.run.json)。负对照只改临时 YAML。撤掉 `md5 != expected` 后，错误摘要被模拟发布接受且退出 0，陈旧摘要也跳过了重试。两条断言都报错。

## 遗留风险

- **日报发布阻断已复现。** 本地的 `origin/main` 已有日报提交 `28131f3`。在临时副本保留该提交的 API、数据、feed 和首页 `SITE_DATA` 后，`verify-source` 在 `official-data`、`write-scope` 失败，3 通过 / 2 失败，退出 1。独立执行同一 UX 入口得到 43 通过 / 3 失败，F8a–F8c 均因数据差分变红，退出 1。部署闸会在源码步骤停住。批准日报使用的基线与写域后才能恢复自动发布。[复现脚本](sol-s5/reproduce-daily.mjs) · [运行记录](sol-s5/daily.run.json) · [源码 stdout](sol-s5/daily-source.stdout.txt) · [源码 stderr](sol-s5/daily-source.stderr.txt) · [UX stdout](sol-s5/daily-ux.stdout.txt) · [UX stderr](sol-s5/daily-ux.stderr.txt)
- GitHub 托管 runner、真实 OSS/CDN 响应、CDN 刷新权限和缓存传播待实测。上传后的预检、刷新或验真失败会把 job 判红，此时 OSS 可能已有写入。通过闸门的下一次默认发布会把 `/sw.js` 恢复为正常 worker。
- 首次日报复现时 Windows 的 GNU tar 把绝对路径盘符 `D:` 解释成远端归档主机，解析失败。改为在临时目录内使用相对归档名后复跑。正式 OSS/CDN、线上 URL 和生产凭证未参与。[首次 stderr](sol-s5/daily-archive-first.stderr.txt) · [首次退出码](sol-s5/daily-archive-first.run.json)
- 本机安全策略以 `blocked by policy` 拒绝删除一个 UX 临时输出目录。量测 JSON 已归档，日志记录的浏览器 PID 已全部退出，临时目录留在 `$env:TEMP`。

## 地图终态

⑥ 隔离候选和本机证据已交付，日报基线待裁定。⑦ Astra 独立复核待主控安排。⑧ 实际发布、退役演练和线上验收待 PI 授权动作及复核放行。任务地图由主控回填。[唯一任务地图](/D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/task-map.md)

DELIVERY-T1128-SMOOTH-S5
已交付正常和退役发布接线与本机证据，并复现现有固定基线对日报发布的阻断。
