$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../../..')).Path
$destination = Join-Path $PSScriptRoot 'no-data-validation'
$files = @('.json', '.stdout.txt', '.stderr.txt', '.run.json')
foreach ($extension in $files) {
    if (Test-Path -LiteralPath "$destination$extension") {
        throw "Evidence already exists at $destination$extension"
    }
}

$candidatePath = Join-Path $root 'sw.js'
$candidate = [IO.File]::ReadAllText($candidatePath)
$start = $candidate.IndexOf('  const block = html.slice(dataStart, end).trim();', [StringComparison]::Ordinal)
$end = $candidate.IndexOf('  return { response, html };', [StringComparison]::Ordinal)
if ($start -lt 0 -or $end -le $start) { throw 'Could not isolate the new data validation' }
$deleted = $candidate.Substring($start, $end - $start)
if (-not $deleted.Contains('JSON.parse(declaration[1])')) { throw 'Mutation did not remove JSON.parse' }
$temporaryWorker = Join-Path ([IO.Path]::GetTempPath()) ('thoradar-sol-s3-' + [guid]::NewGuid() + '.js')

try {
    [IO.File]::WriteAllText($temporaryWorker, $candidate.Remove($start, $end - $start))
    $test = Join-Path $root 'tests/smooth/verify-s3.mjs'
    $command = @('node', $test, "$destination.json", $temporaryWorker)
    $metadata = [ordered]@{
        command = $command
        candidateSha256 = (Get-FileHash -LiteralPath $candidatePath).Hash.ToLowerInvariant()
        mutatedSha256 = (Get-FileHash -LiteralPath $temporaryWorker).Hash.ToLowerInvariant()
        deleted = $deleted
    }
    node $test "$destination.json" $temporaryWorker 1> "$destination.stdout.txt" 2> "$destination.stderr.txt"
    $metadata.exitCode = $LASTEXITCODE
    $metadata | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$destination.run.json" -Encoding utf8
    $result = Get-Content -Raw -LiteralPath "$destination.json" | ConvertFrom-Json
    $neon = $result.checks | Where-Object name -eq 'neon-empty-markers-stub'
    if ($metadata.exitCode -ne 1 -or $result.summary.failed -ne 5 -or $result.summary.passed -ne 1 -or
        -not $neon -or $neon.pass -or $neon.detail.after.sha256 -ne $result.fixtures.'neon-empty-markers-stub'.sha256) {
        throw 'Expected the five rejected responses to re-enter the cache when validation was removed'
    }
    Get-Content -LiteralPath "$destination.stdout.txt" | Select-String '^SUMMARY'
    Write-Output "Mutation exit $($metadata.exitCode); 156-byte Neon response replaced the healthy cache"
} finally {
    Remove-Item -LiteralPath $temporaryWorker -ErrorAction SilentlyContinue
}
