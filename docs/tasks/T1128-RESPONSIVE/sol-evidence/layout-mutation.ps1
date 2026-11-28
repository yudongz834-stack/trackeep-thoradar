$ErrorActionPreference = 'Stop'
$evidence = $PSScriptRoot
$target = (Resolve-Path -LiteralPath (Join-Path $evidence '../../../../index.html')).Path
$backup = Join-Path $evidence 'index.candidate.backup'
$stdout = Join-Path $evidence 'mutation.stdout.txt'
$stderr = Join-Path $evidence 'mutation.stderr.txt'
if (Test-Path -LiteralPath $backup) { throw 'Candidate backup already exists' }

$before = (Get-FileHash -LiteralPath $target).Hash
$source = [IO.File]::ReadAllText($target)
$guard = 'min(100cqw,100cqh,var(--overview-dial-max,420px))'
$mutatedGuard = 'min(100cqw,var(--overview-dial-max,420px))'
if ([regex]::Matches($source, [regex]::Escape($guard)).Count -ne 1) { throw 'Expected one radar height guard' }

Write-Output "Copy-Item -LiteralPath $target -Destination $backup"
Copy-Item -LiteralPath $target -Destination $backup
try {
    [IO.File]::WriteAllText($target, $source.Replace($guard, $mutatedGuard))
    Write-Output "Temporarily removed 100cqh from $guard; SHA256=$((Get-FileHash -LiteralPath $target).Hash)"
    Write-Output "node $evidence/responsive-probe.mjs mutation 1422x800"
    node "$evidence/responsive-probe.mjs" mutation 1422x800 > $stdout 2> $stderr
    $probeExit = $LASTEXITCODE
    Write-Output "mutation exit=$probeExit"
    if ($probeExit -ne 1 -or !(Select-String -LiteralPath $stdout -SimpleMatch 'overview-legend: radar exceeds stage' -Quiet)) {
        throw 'Expected a radar stage assertion failure with the guard removed'
    }
} finally {
    Write-Output "Copy-Item -LiteralPath $backup -Destination $target -Force"
    Copy-Item -LiteralPath $backup -Destination $target -Force
    $after = (Get-FileHash -LiteralPath $target).Hash
    Write-Output "before SHA256=$before; restored SHA256=$after"
    if ($before -ne $after) { throw 'Restored bytes differ from candidate backup' }
    Remove-Item -LiteralPath $backup
}
