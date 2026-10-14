# Install only the source-pinned pnpm into ignored workspace runtime, never globally.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$manifest = Get-Content -LiteralPath (Join-Path $root 'vendor/openclaw/package.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.packageManager -notmatch '^pnpm@(\d+\.\d+\.\d+)\+sha512\.([0-9a-f]+)$') { throw 'Unsupported source packageManager pin' }
$version = $Matches[1]
$hex = $Matches[2]
$bytes = New-Object byte[] ($hex.Length / 2)
for ($i = 0; $i -lt $bytes.Length; $i++) { $bytes[$i] = [Convert]::ToByte($hex.Substring($i * 2, 2), 16) }
$expected = 'sha512-' + [Convert]::ToBase64String($bytes)
$destination = Join-Path $root ('runtime/toolchains/pnpm-' + $version)
$entry = Join-Path $destination 'node_modules/pnpm/pnpm'
$lock = Join-Path $destination 'package-lock.json'
if (-not (Test-Path -LiteralPath $entry)) {
    if (Test-Path -LiteralPath $destination) { throw 'Incomplete/existing tool directory; inspect it before retrying' }
    $metadata = & npm.cmd view ('pnpm@' + $version) dist.integrity --json
    if ($LASTEXITCODE -ne 0) { throw 'Registry integrity query failed' }
    $actual = $metadata | ConvertFrom-Json
    if ($actual -ne $expected) { throw 'Registry integrity differs from pinned source manifest' }
    [void][IO.Directory]::CreateDirectory($destination)
    & npm.cmd install --prefix $destination --ignore-scripts --no-audit --no-fund --save-exact ('pnpm@' + $version)
    if ($LASTEXITCODE -ne 0) { throw 'Project-local pnpm install failed' }
}
# Windows PowerShell 5 cannot ConvertFrom-Json an npm lock containing the empty package key.
$lockedIntegrity = & node -p "require(process.argv[1]).packages['node_modules/pnpm'].integrity" $lock
if ($LASTEXITCODE -ne 0) { throw 'Cannot read installed npm lock integrity' }
if ($lockedIntegrity.Trim() -ne $expected) { throw 'Installed lock integrity does not match the source pin' }
$observed = & node $entry --version
if ($LASTEXITCODE -ne 0 -or $observed.Trim() -ne $version) { throw 'Local pnpm version check failed' }
Write-Output ('PNPM_LOCAL_VERSION=' + $observed.Trim())
Write-Output ('PNPM_LOCAL_ENTRY=' + $entry)
Write-Output 'SOURCE_INTEGRITY_MATCH=PASS'
Write-Output 'Global package manager unchanged; OpenClaw dependencies not installed.'
