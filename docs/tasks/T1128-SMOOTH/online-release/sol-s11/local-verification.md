# 发布模拟执行记录

从隔离工作树根目录运行，覆盖同一份 S7 基线。三个进程各写独立 stdout、stderr 和 JSON。

| 运行 | 退出码 | 原始汇总 |
| --- | ---: | --- |
| 正本 | 0 | `SUMMARY {"passed":18,"failed":0}` |
| 主域四地址变异 | 1 | `SUMMARY {"passed":16,"failed":2}` |
| 移除 MD5 检查变异 | 1 | `SUMMARY {"passed":16,"failed":2}` |

## 正本命令

```powershell
$dir = 'docs/tasks/T1128-SMOOTH/online-release/sol-s11'
node tests/smooth/verify-deploy.mjs "$dir/deploy.json" 1> "$dir/deploy.stdout.txt" 2> "$dir/deploy.stderr.txt"
$LASTEXITCODE
```

## 变异命令

两次分别替换下列单行并写入系统临时目录，将临时 YAML 作为测试脚本的第二个参数。每次从同一正本重新读入 YAML。输出 JSON 中的 `workflow` 记录当次临时文件路径。

| `$name` | `$good` | `$bad` |
| --- | --- | --- |
| `apex-only` | `refresh_paths=$(printf '%s\n' "${urls[@]}")` | `refresh_paths=$(printf 'https://thoradar.online%s\n' "${paths[@]}")` |
| `without-md5-gate` | `if (status != 200 \|\| md5 != expected) exit 1` | `if (status != 200) exit 1` |

```powershell
$current = [IO.File]::ReadAllText((Resolve-Path -LiteralPath '.github/workflows/deploy_oss.yml').Path)
if (([regex]::Matches($current, [regex]::Escape($good))).Count -ne 1) { throw 'Matched line must be unique' }
$mutation = Join-Path ([IO.Path]::GetTempPath()) ('thoradar-sol-s11-' + $name + '-' + [guid]::NewGuid().ToString('N') + '.yml')
[IO.File]::WriteAllText($mutation, $current.Replace($good, $bad), [Text.UTF8Encoding]::new($false))
try {
    node tests/smooth/verify-deploy.mjs "$dir/$name.json" $mutation 1> "$dir/$name.stdout.txt" 2> "$dir/$name.stderr.txt"
    $LASTEXITCODE
} finally {
    Remove-Item -LiteralPath $mutation
}
```

原始输出保存在 [正本 stdout](deploy.stdout.txt)、[正本 stderr](deploy.stderr.txt)、[主域变异 stdout](apex-only.stdout.txt)、[主域变异 stderr](apex-only.stderr.txt)、[MD5 变异 stdout](without-md5-gate.stdout.txt) 和 [MD5 变异 stderr](without-md5-gate.stderr.txt)。再次执行请使用新的输出目录，测试脚本使用独占创建保护已有 JSON。

本次重验使用相同三条命令，将 `$dir` 设为 `docs/tasks/T1128-SMOOTH/online-release/sol-s11/final-check`，并分别保存进程退出码、stdout、stderr 和 JSON。[正本](final-check/deploy.stdout.txt)、[主域变异](final-check/apex-only.stderr.txt)、[MD5 变异](final-check/without-md5-gate.stderr.txt)、[调用轨迹](final-check/trace-check.txt)、[Git 范围核验](final-check/scope-check.txt)

交付复验使用相同三条命令，将 `$dir` 设为 `docs/tasks/T1128-SMOOTH/online-release/sol-s11/handoff-check`。正本的 JSON、stdout、stderr 和退出码见 [JSON](handoff-check/deploy.json)、[stdout](handoff-check/deploy.stdout.txt)、[stderr](handoff-check/deploy.stderr.txt)、[退出码](handoff-check/deploy.exit.txt)。主域变异见 [JSON](handoff-check/apex-only.json)、[stdout](handoff-check/apex-only.stdout.txt)、[stderr](handoff-check/apex-only.stderr.txt)、[退出码](handoff-check/apex-only.exit.txt)。MD5 变异见 [JSON](handoff-check/without-md5-gate.json)、[stdout](handoff-check/without-md5-gate.stdout.txt)、[stderr](handoff-check/without-md5-gate.stderr.txt)、[退出码](handoff-check/without-md5-gate.exit.txt)。[调用轨迹](handoff-check/trace-check.txt)、[Git 范围核验](handoff-check/scope-check.txt)
