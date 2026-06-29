param(
  [string]$RuntimeRoot = (Join-Path $PSScriptRoot "..\.runtime\postgres-test"),
  [int]$Port = 55432,
  [string]$BindAddress = "127.0.0.1",
  [string]$Role = "project_tracker_test",
  [string]$Password = "project_tracker_test",
  [string]$Database = "project_tracker_test"
)

$ErrorActionPreference = "Stop"

$binDir = "C:\Program Files\PostgreSQL\18\bin"
$initdb = Join-Path $binDir "initdb.exe"
$pgCtl = Join-Path $binDir "pg_ctl.exe"
$pgIsReady = Join-Path $binDir "pg_isready.exe"
$psql = Join-Path $binDir "psql.exe"
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))

foreach ($tool in @($initdb, $pgCtl, $pgIsReady, $psql)) {
  if (-not (Test-Path $tool)) {
    throw "Required PostgreSQL binary not found: $tool"
  }
}

$runtimePath = [System.IO.Path]::GetFullPath($RuntimeRoot)
$dataDir = Join-Path $runtimePath "data"
$logDir = Join-Path $runtimePath "logs"
$logFile = Join-Path $logDir "postgres.log"
$pwFile = Join-Path $runtimePath "pwfile.txt"
$envFile = Join-Path $runtimePath "test-env.ps1"

New-Item -ItemType Directory -Force -Path $runtimePath | Out-Null
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Invoke-PgCommand {
  param(
    [string]$Executable,
    [string[]]$Arguments,
    [switch]$AllowFailure
  )

  $output = & $Executable @Arguments 2>&1
  $exitCode = $LASTEXITCODE
  if (-not $AllowFailure -and $exitCode -ne 0) {
    $joined = $Arguments -join " "
    $details = ($output | Out-String).Trim()
    throw "Command failed ($Executable $joined)`n$details"
  }
  return @{
    ExitCode = $exitCode
    Output = $output
  }
}

function Test-TestServerReady {
  $result = Invoke-PgCommand $pgIsReady @("-h", $BindAddress, "-p", "$Port", "-U", $Role, "-d", "postgres") -AllowFailure
  return $result.ExitCode -eq 0
}

function Get-PortOwnerCommandLine {
  $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1

  if (-not $connection) {
    return $null
  }

  $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($connection.OwningProcess)" -ErrorAction SilentlyContinue
  return $process.CommandLine
}

function Stop-StaleWorkspaceCluster {
  $commandLine = Get-PortOwnerCommandLine
  if (-not $commandLine) {
    return
  }

  $normalizedCommandLine = $commandLine.Replace("\", "/")
  $normalizedDataDir = $dataDir.Replace("\", "/")
  $normalizedRepoRoot = $repoRoot.Replace("\", "/")

  if ($normalizedCommandLine -like "*$normalizedDataDir*") {
    return
  }

  if ($normalizedCommandLine -like "*$normalizedRepoRoot*" -and $normalizedCommandLine -like "*postgres.exe*") {
    $matches = [regex]::Match($commandLine, '-D\s+"?([^"]+)"?')
    if ($matches.Success) {
      $staleDataDir = $matches.Groups[1].Value
      Invoke-PgCommand $pgCtl @("-D", $staleDataDir, "-w", "stop", "-m", "fast") | Out-Null
      return
    }
  }

  throw "Port $Port is already in use by another process: $commandLine"
}

Stop-StaleWorkspaceCluster

if (-not (Test-Path (Join-Path $dataDir "PG_VERSION"))) {
  New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
  Set-Content -LiteralPath $pwFile -Value $Password -NoNewline
  Invoke-PgCommand $initdb @(
    "-D", $dataDir,
    "-U", $Role,
    "--pwfile=$pwFile",
    "-A", "scram-sha-256",
    "--auth-host=scram-sha-256",
    "--auth-local=scram-sha-256",
    "--encoding=UTF8"
  ) | Out-Null
}

if (-not (Test-TestServerReady)) {
  Invoke-PgCommand $pgCtl @(
    "-D", $dataDir,
    "-l", $logFile,
    "-w",
    "start",
    "-o", "-p $Port -h $BindAddress"
  ) | Out-Null
}

$env:PGPASSWORD = $Password

$roleCheck = Invoke-PgCommand $psql @(
  "-h", $BindAddress,
  "-p", "$Port",
  "-U", $Role,
  "-d", "postgres",
  "-tAc", "SELECT 1 FROM pg_roles WHERE rolname = '$Role';"
)

if (-not (($roleCheck.Output | Out-String).Trim() -eq "1")) {
  Invoke-PgCommand $psql @(
    "-h", $BindAddress,
    "-p", "$Port",
    "-U", $Role,
    "-d", "postgres",
    "-c", "CREATE ROLE $Role WITH LOGIN SUPERUSER PASSWORD '$Password';"
  ) | Out-Null
}

$dbCheck = Invoke-PgCommand $psql @(
  "-h", $BindAddress,
  "-p", "$Port",
  "-U", $Role,
  "-d", "postgres",
  "-tAc", "SELECT 1 FROM pg_database WHERE datname = '$Database';"
)

if (-not (($dbCheck.Output | Out-String).Trim() -eq "1")) {
  Invoke-PgCommand $psql @(
    "-h", $BindAddress,
    "-p", "$Port",
    "-U", $Role,
    "-d", "postgres",
    "-c", "CREATE DATABASE $Database;"
  ) | Out-Null
}

$health = Invoke-PgCommand $pgIsReady @("-h", $BindAddress, "-p", "$Port", "-U", $Role, "-d", $Database)

$testUrl = "postgresql://${Role}:${Password}@${BindAddress}:${Port}/${Database}"
$adminUrl = "postgresql://${Role}:${Password}@${BindAddress}:${Port}/postgres"

@(
  "`$env:TEST_DATABASE_URL = `"$testUrl`"",
  "`$env:TEST_DATABASE_ADMIN_URL = `"$adminUrl`""
) | Set-Content -LiteralPath $envFile

Write-Host "Test PostgreSQL is ready."
Write-Host "TEST_DATABASE_URL=$testUrl"
Write-Host "TEST_DATABASE_ADMIN_URL=$adminUrl"
Write-Host "Env helper file: $envFile"
Write-Host (($health.Output | Out-String).Trim())
