# Forward arguments to the source-pinned project-local pnpm, in the OpenClaw checkout.
param([Parameter(ValueFromRemainingArguments=$true)][string[]]$PnpmArguments)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$source = Join-Path $root 'vendor/openclaw'
$manifest = Get-Content -LiteralPath (Join-Path $source 'package.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.packageManager -notmatch '^pnpm@(\d+\.\d+\.\d+)\+') { throw 'Unsupported source packageManager pin' }
$entry = Join-Path $root ('runtime/toolchains/pnpm-' + $Matches[1] + '/node_modules/pnpm/pnpm')
if (-not (Test-Path -LiteralPath $entry)) { throw 'Run scripts/setup-openclaw-pnpm.ps1 before using the wrapper' }
Push-Location $source
try {
    & node $entry @PnpmArguments
    $code = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $code
