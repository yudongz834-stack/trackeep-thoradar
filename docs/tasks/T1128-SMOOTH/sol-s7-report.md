干了什么｜查清两次 CDN 刷新失败，抓到 `www` 的公网 TLS 问题，补足刷新传播的本地验真等待。\
PI 怎么亲手验｜重发后打开 GitHub Actions 的 `Publish and verify site` 日志，看到刷新任务回执及双域各四条 `Verified` 就算发布验真通过。\
还剩什么坑｜发布用 RAM 用户待授权，`www` 的公网接入仍待 PI 确认和处理，双域线上验收尚未完成。

# T1128-SMOOTH-S7 发布诊断

## 结论

| 证据 | 根因与处理 |
| --- | --- |
| Run `46129122449` 返回 `InvalidDomain.NotFound` | 任务书载明 `www.thoradar.online` 不在当前 CDN 账号的可管理域名下。双域混在一个请求中，服务拒绝了整批。 |
| Run `46130068894` 返回 `Forbidden.RAM`，`AuthAction=cdn:RefreshObjectCaches`，身份类型 `SubUser` | 此时刷新只提交主域。隐式拒绝表明该请求缺少匹配的有效 Allow，需给实际发布用 RAM 用户授予该动作和主域资源。已通过的 OSS 操作使用另一组权限。 |

Run 结果和 OSS 上传为委任状提供的已确认事实。现行工作流先做双域源站 HTTPS 预检，再刷新主域的 `/`、`/index.html`、`/sw.js`、`/sw-retire.js`。随后对公网双域八个地址逐项要求 HTTP 200 和对应发布文件的 `Content-MD5`，worker 还须具备 JavaScript MIME 和 `no-store`。刷新提交范围应遵从当前账号的域名管理权，验收范围应涵盖两个面向用户的 HTTPS 主机名。[刷新 API 授权表](https://help.aliyun.com/zh/cdn/developer-reference/api-cdn-2018-05-10-refreshobjectcaches) · [RAM 权限判定](https://help.aliyun.com/zh/ram/policy-evaluation-process)

## PI 操作单

1. 在 RAM 控制台打开 **权限管理 → 权限策略 → 创建权限策略 → 脚本编辑**，用下方 JSON 创建自定义策略。把 `<CDN_OWNER_ACCOUNT_ID>` 换成管理 `thoradar.online` 的阿里云主账号 ID，随后在 **身份管理 → 用户 → 新增授权** 选发布 SubUser 和该自定义策略。授权面板用账号级别，具体资源由策略限定到主域。API 授权表只列必选的域名资源，无关联操作。若仍报隐式拒绝，核实实际调用身份、资源 ARN 和适用的权限边界。[创建自定义策略](https://help.aliyun.com/zh/ram/create-a-custom-policy) · [为 RAM 用户授权](https://help.aliyun.com/zh/ram/user-guide/grant-permissions-to-the-ram-user) · [刷新 API 授权表](https://help.aliyun.com/zh/cdn/developer-reference/api-cdn-2018-05-10-refreshobjectcaches)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["cdn:RefreshObjectCaches"],
      "Resource": ["acs:cdn:*:<CDN_OWNER_ACCOUNT_ID>:domain/thoradar.online"]
    }
  ]
}
```

2. 在 CDN 控制台的 **域名管理** 核对 `www.thoradar.online` 的归属、专属 CNAME、HTTPS 状态和回源。公网 TLS 仍失败时，先由该域名的管理方恢复接入。若发现尚未接入，添加 `www` 加速域名，为其启用覆盖 `www` 的证书，按控制台给的 CNAME 配置 DNS，并核对回源指向相同站点。若被其他账号管理，联系该管理方处理或办理迁移。公网 TLS 恢复后若仍只有 `www` 返回旧 MD5，由其管理方按同四个 URL 刷新。若两个域迁入同一账号且确认已启用共享缓存，可实测主域刷新能否一起生效。保留八项验真。[CNAME 排障](https://help.aliyun.com/zh/cdn/support/cname-faq) · [快速接入 CDN](https://help.aliyun.com/zh/cdn/getting-started/quick-access-to-alibaba-cloud-cdn/) · [共享缓存刷新规则](https://help.aliyun.com/zh/cdn/user-guide/refresh-and-prefetch-resources)

3. 若重发当前已发布版本，打开 GitHub Actions 的 run `46130068894`，点 **Re-run jobs → Re-run failed jobs**，它会使用原 SHA 和 ref。若要带上本交付的等待修复，由 PI 先发布纳入补丁的目标 ref，再从 **Deploy to Aliyun OSS → Run workflow** 发起新 run，正常发布保持 `retire=false`。看到刷新任务回执、八条 `Verified` 和 `Publish verified on both domains` 才签发布验真。授权、接入调整和重发由 PI 执行。[重跑 GitHub Actions 作业](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs)

## 公开读测与共享判断

2026-11-28 17:32–17:34（UTC+8），Google 和 Cloudflare 公共 DNS 均给出主域与 `www` 指向 `thoradar.online.w.kunlunaq.com.`。主域公网上采到的四个 HEAD 响应均为 200，MD5 与基底 Git blob 一致，worker 的 MIME 和缓存头也符合发布要求。`www` 四个公网 HEAD 均在 TLS 握手阶段失败。对同一个公共节点切换 SNI，主域握手成功，`www` 收到握手失败告警。用工作流的源站预检路由对两个主机名做根路径 GET，则都得到 AliyunOSS 200 和同一 MD5。源站根路径的 **HEAD** 两域均为 403，预检实际使用 **GET**。

共用一条 CNAME 只能说明两域的 DNS 指向同一入口。阿里云的共享缓存需同一账号内配置，届时关联域名可随主域一起失效。本次公网采样只验证到主域四项，`www` 的缓存内容因 TLS 失败无法读取，主域刷新是否带动 `www` 留给真实重发后实测。TLS 的控制台配置根因也待 PI 核实。[共享缓存工作方式](https://www.alibabacloud.com/help/en/cdn/user-guide/configure-shared-cache) · [刷新与预热注意事项](https://help.aliyun.com/zh/cdn/user-guide/refresh-and-prefetch-resources)

### 公共读测命令与输出摘录

分别替换以下命令的主机名、路径和公共 DNS 查询名。DoH 输出按 `Answer` 提取名称、类型、TTL 和数据。HTTP 输出保留状态及发布相关头。

```powershell
curl.exe -q -fsS --connect-timeout 4 --max-time 10 -H 'accept: application/dns-json' 'https://dns.google/resolve?name=thoradar.online&type=A'
curl.exe -q -fsS --connect-timeout 4 --max-time 10 -H 'accept: application/dns-json' 'https://cloudflare-dns.com/dns-query?name=thoradar.online&type=A'
curl.exe -q -sS -I -H 'Accept-Encoding: identity' --connect-timeout 5 --max-time 10 https://thoradar.online/
curl.exe -q -sS -I -H 'Accept-Encoding: identity' --connect-timeout 5 --max-time 10 --resolve 'www.thoradar.online:443:120.233.24.20' https://www.thoradar.online/
curl.exe -q -sS -o NUL -D - -H 'Accept-Encoding: identity' --connect-timeout 5 --max-time 12 --connect-to 'www.thoradar.online:443:thoradar-online.cn-shenzhen.taihangtop.cn:443' https://www.thoradar.online/
```

```text
Google DoH (thoradar.online, www.thoradar.online): exit=0 each
thoradar.online. 5 600 thoradar.online.w.kunlunaq.com.
www.thoradar.online. 5 600 thoradar.online.w.kunlunaq.com.
thoradar.online.w.kunlunaq.com. 1 60 120.233.24.20
Cloudflare DoH (thoradar.online, www.thoradar.online): exit=0 each
thoradar.online 5 600 thoradar.online.w.kunlunaq.com.
www.thoradar.online 5 600 thoradar.online.w.kunlunaq.com.

default thoradar.online/
HTTP/1.1 200 OK
Server: Tengine
Content-MD5: 80mggny6RjRXP9Uw4zglxQ==
exit=0
default thoradar.online/index.html
HTTP/1.1 200 OK
Content-MD5: 80mggny6RjRXP9Uw4zglxQ==
exit=0
default thoradar.online/sw.js
HTTP/1.1 200 OK
Content-Type: application/javascript
Cache-Control: no-store
Content-MD5: nrgKbeazqBXvILkgAlssIg==
exit=0
default thoradar.online/sw-retire.js
HTTP/1.1 200 OK
Content-Type: application/javascript
Cache-Control: no-store
Content-MD5: xviHOEexQQLp0q41sv2uuA==
exit=0

default www.thoradar.online/
curl: (35) schannel: next InitializeSecurityContext failed: SEC_E_ILLEGAL_MESSAGE (0x80090326) - This error usually occurs when a fatal SSL/TLS alert is received (e.g. handshake failed). More detail may be available in the Windows System event log.
exit=35

GET preflight thoradar.online
HTTP/1.1 200 OK
Server: AliyunOSS
Content-MD5: 80mggny6RjRXP9Uw4zglxQ==
exit=0
GET preflight www.thoradar.online
HTTP/1.1 200 OK
Server: AliyunOSS
Content-MD5: 80mggny6RjRXP9Uw4zglxQ==
exit=0
thoradar.online TLSv1.3 (('DNS', 'thoradar.online'), ('DNS', 'www.thoradar.online'))
www.thoradar.online SSLError [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:1032)
```

TLS 对照用 `python -`，对两个主机名分别执行 `ssl.create_default_context().wrap_socket(socket.create_connection(('120.233.24.20', 443), timeout=6), server_hostname=host)`，记录协议和证书 DNS SAN，或记录异常。脚本捕获两次握手结果后退出 0。

Git blob 的摘要通过 Python 执行 `subprocess.check_output(['git', 'show', f'HEAD:{name}'])` 读取字节，再做 `base64.b64encode(hashlib.md5(blob).digest())`。Windows 工作树为 CRLF，发布文件以 Git 中的 LF 字节核对。

```text
index.html: working=OoYTQN1+/i5YpdPcDG8kEg== blob=80mggny6RjRXP9Uw4zglxQ== equal=false
sw.js: working=PtS2flhNDSuEGKZMQnTBgA== blob=nrgKbeazqBXvILkgAlssIg== equal=false
sw-retire.js: working=MSJ4HyjS+aYOiDEIzH80tA== blob=xviHOEexQQLp0q41sv2uuA== equal=false
exit=0
```

## 本地修复与改动清单

- `.github/workflows/deploy_oss.yml` 原先各 URL 在快响应场景仅有 55 秒净等待。阿里云预估刷新从提交到生效约 5–6 分钟。现保留 12 次探测，前两次各等 5 秒，随后间隔 40 秒，末次前累计至少 370 秒净等待。RAM 错误与此独立。真实刷新延迟尚未复现，本地用六分钟传播的模拟验证这一时间窗。[刷新 API 注意事项](https://help.aliyun.com/zh/cdn/developer-reference/api-cdn-2018-05-10-refreshobjectcaches)
- `tests/smooth/deploy-mock.mjs` 与 `tests/smooth/verify-deploy.mjs` 加入六分钟后才返回当前 MD5 的样本。正常发布、退役发布、四项刷新、八项验真和持续陈旧失败仍由原有模拟覆盖。
- 附件 [sol-s7.patch](sol-s7.patch) 是以上三件的完整 diff。基底 `af3f2775855bb99aeb5c3262cb2738a889b60d70`，本地隔离工作树 detached HEAD。

## 本地验证状态

Node `v24.14.0`。先以原脚本和原夹具跑发布模拟，再用改动后的夹具跑旧脚本及修订脚本。测试执行实际工作流 Bash，OSS、CDN、HTTP 和等待均由夹具接管。命令中的目录代表每次实际创建的独立临时目录。

| 命令 | 状态 |
| --- | --- |
| `node tests/smooth/verify-deploy.mjs docs/tasks/T1128-SMOOTH/sol-s7-deploy.json`，原基底和原夹具，结果已移至临时目录 | 退出 0，18/18 |
| `node tests/smooth/verify-deploy.mjs <temp>/www-in-refresh.json <temp>/www-in-refresh.yml`，将刷新提交改为双域八项，原夹具 | 退出 1，16/18，正常与退役的刷新范围断言均变红 |
| `node tests/smooth/verify-deploy.mjs <temp>/before.json <temp>/before.yml`，旧工作流与新夹具 | 退出 1，17/18，唯一失败是六分钟传播样本 |
| `node tests/smooth/verify-deploy.mjs <temp>/deploy.json`，修订工作流与新夹具 | 退出 0，18/18 |
| `node tests/smooth/verify-deploy.mjs <temp>/skip-www.json <temp>/skip-www.yml`，把公网验真循环改为只验主域 | 退出 1，8/18，测试抓住了跳过 `www` 导致的误绿 |

每个负对照用 `Copy-Item -LiteralPath .github/workflows/deploy_oss.yml -Destination <temp>/<candidate>.yml` 备份工作流，再对临时副本做单行替换。换回原始等待用的是在修改前复制的 `before.yml`。两件域名变异的 `git diff --no-index` 均退出 1，单行变异如下。

```diff
-          refresh_paths=$(printf 'https://thoradar.online%s\n' "${paths[@]}")
+          refresh_paths=$(printf '%s\n' "${urls[@]}")
```

```diff
-          for url in "${urls[@]}"; do
+          for url in ${refresh_paths}; do
```

模拟和负对照的必要原始输出如下。日志中的任务回执是夹具值。

```text
FAIL normal uploads workers then index, refreshes four owned CDN URLs and verifies eight URLs: Expected values to be strictly deep-equal:
FAIL retire uploads workers then index, refreshes four owned CDN URLs and verifies eight URLs: Expected values to be strictly deep-equal:
SUMMARY {"passed":16,"failed":2}
mutation_test_exit=1

FAIL stale CDN content is polled again, including a six-minute propagation delay: Verification failed for https://www.thoradar.online/sw.js
SUMMARY {"passed":17,"failed":1}
exit=1
{"status":1,"mockSleeps":[5,5,5,5,5,5,5,5,5,5,5],"simulatedSeconds":55.0}

PASS stale CDN content is polled again, including a six-minute propagation delay
PASS post-publish verification rejects wrong-md5
SUMMARY {"passed":18,"failed":0}
exit=0
Verified https://www.thoradar.online/sw.js HTTP=200 Content-MD5=MSJ4HyjS+aYOiDEIzH80tA== expected=MSJ4HyjS+aYOiDEIzH80tA== MIME=application/javascript Cache-Control=,max-age=0, no-store
Publish verified on both domains
{"scenario":"stale-during-propagation-retire","status":0,"mockSleeps":[5,5,40,40,40,40,40,40,40,40,40],"simulatedSeconds":370.0,"refreshPaths":"https://thoradar.online/\nhttps://thoradar.online/index.html\nhttps://thoradar.online/sw.js\nhttps://thoradar.online/sw-retire.js","heads":["https://thoradar.online/","https://thoradar.online/index.html","https://thoradar.online/sw.js","https://thoradar.online/sw-retire.js","https://www.thoradar.online/","https://www.thoradar.online/index.html","https://www.thoradar.online/sw.js","https://www.thoradar.online/sw-retire.js"]}
Waiting for https://www.thoradar.online/sw.js (12/12) HTTP=200 Content-MD5=3tvOZPT7xwwSP0Ha5IXs2w== expected=MSJ4HyjS+aYOiDEIzH80tA== MIME=application/javascript Cache-Control=,max-age=0, no-store
Verification failed for https://www.thoradar.online/sw.js

FAIL post-publish verification rejects wrong-md5: deployment exited 0
SUMMARY {"passed":8,"failed":10}
mutation_test_exit=1
```

变更范围核验命令及对应输出。

```powershell
git --no-pager diff --check
git --no-pager diff --exit-code -- index.html sw.js sw-retire.js data/
git apply --check --reverse 'docs/tasks/T1128-SMOOTH/sol-s7.patch'
```

```text
diff_check_exit=0
site_files_diff_exit=0
patch_reverse_check_exit=0
```

## 地图影响与终态

轨道⑧可回填本地诊断和轮询修复，发布线上仍是 `in-progress-cdn-repair`。当前证据覆盖托管 runner 原有全闸及 OSS 上传、主域公网样本和本地发布模拟。遗留项是 PI 的 RAM 授权、`www` 公网 TLS 恢复、双域真实 MD5、真实刷新传播和原地图规定的后续线上体验验收。正式地图由派单方更新，R2 本地变更待其安排独立复核。本单完成本地诊断、修订和交付，线上变更由 PI 执行。

DELIVERY-T1128-SMOOTH-S7
查清了两种刷新失败，交付主域最小 RAM 策略和 `www` 处理单，并在隔离树验证了刷新等待修复。
