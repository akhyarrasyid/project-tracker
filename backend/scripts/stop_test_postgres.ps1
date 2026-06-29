param(
  [string]$RuntimeRoot = (Join-Path $PSScriptRoot "..\.runtime\postgres-test")
)

$ErrorActionPreference = "Stop"

$binDir = "C:\Program Files\PostgreSQL\18\bin"
$pgCtl = Join-Path $binDir "pg_ctl.exe"

if (-not (Test-Path $pgCtl)) {
  throw "Required PostgreSQL binary not found: $pgCtl"
}

$runtimePath = [System.IO.Path]::GetFullPath($RuntimeRoot)
$dataDir = Join-Path $runtimePath "data"

if (-not (Test-Path (Join-Path $dataDir "PG_VERSION"))) {
  Write-Host "Test PostgreSQL cluster not initialized. Nothing to stop."
  exit 0
}

$output = & $pgCtl -D $dataDir -w stop -m fast 2>&1
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
  $details = ($output | Out-String).Trim()
  if ($details -match "no server running") {
    Write-Host "Test PostgreSQL is not running."
    exit 0
  }
  throw "Failed to stop test PostgreSQL.`n$details"
}

Write-Host "Test PostgreSQL stopped."
