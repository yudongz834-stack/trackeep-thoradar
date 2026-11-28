#Requires -Version 7.0
# PI 亲手执行：修复 dispatch-gate 的组合账路径漂移。先备份，精确替换唯一一行，再跑原闸自检。
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$target = 'D:/claude/hooks/dispatch-gate/trackeep-dispatch-gate.ps1'
$ledgerHome = 'D:/trackeep/trackeep-tools/skill-registry-ledger'
foreach ($name in @('combos-gate.ps1', 'combos.json', 'gen-combos-seed.ps1', 'combos-schema.md')) {
    $path = Join-Path $ledgerHome $name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "组合账正本缺件：$path" }
}
$old = "`$LedgerHome = if (`$env:DISPATCH_GATE_LEDGER_HOME) { `$env:DISPATCH_GATE_LEDGER_HOME } else { 'D:/claude/skill-registry-ledger' }"
$new = "`$LedgerHome = if (`$env:DISPATCH_GATE_LEDGER_HOME) { `$env:DISPATCH_GATE_LEDGER_HOME } else { 'D:/trackeep/trackeep-tools/skill-registry-ledger' }"
$text = [System.IO.File]::ReadAllText($target)
$count = [regex]::Matches($text, [regex]::Escape($old)).Count
if ($count -ne 1) { throw "目标旧路径应恰好出现 1 次，实际 $count 次；未改文件" }
$backupDir = 'D:/claude/_bak/dispatch-gate-path-20261128'
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
$backup = Join-Path $backupDir 'trackeep-dispatch-gate.ps1.before-trackeep-tools'
Copy-Item -LiteralPath $target -Destination $backup -Force
$updated = $text.Replace($old, $new)
[System.IO.File]::WriteAllText($target, $updated, [System.Text.UTF8Encoding]::new($true))
Write-Output "已备份：$backup"
Write-Output "已把组合账默认路径改为：$ledgerHome"
& 'C:/Program Files/PowerShell/7/pwsh.exe' -NoProfile -ExecutionPolicy Bypass -File 'D:/claude/hooks/dispatch-gate/selftest.ps1'
if ($LASTEXITCODE -ne 0) {
    Copy-Item -LiteralPath $backup -Destination $target -Force
    throw "自检失败，已恢复原钩子。备份仍在：$backup"
}
Write-Output '派遣闸路径修复与自检完成。'
