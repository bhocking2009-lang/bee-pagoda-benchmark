<#
.SYNOPSIS
    Bee Pagoda Benchmark — Windows orchestrator.

.DESCRIPTION
    Parallel to run_suite.sh on Linux. Runs the PowerShell benchmark
    scripts under scripts\windows\ and collects results in a timestamped
    report folder under reports\.

.PARAMETER Profile
    Benchmark profile: quick, balanced, deep.  Default: balanced.

.PARAMETER Categories
    Comma-separated category list, e.g. "cpu,memory,disk".
    Omit or pass "all" to run all categories.

.PARAMETER SkipPreflight
    Skip the dependency preflight check.

.PARAMETER Python
    Explicit path to the Python interpreter to use (e.g. ".venv\Scripts\python.exe").

.EXAMPLE
    .\run_suite.ps1
    .\run_suite.ps1 -Profile quick -Categories cpu,memory
    .\run_suite.ps1 -Profile deep -SkipPreflight
#>

[CmdletBinding()]
param(
    [string]$Profile     = "balanced",
    [string]$Categories  = "all",
    [switch]$SkipPreflight,
    [string]$Python      = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path

# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

function Write-Progress-Event {
    param([string]$Event, [string]$Category="", [string]$Status="", [string]$Message="")
    $obj = [ordered]@{
        event    = $Event
        category = $Category
        status   = $Status
        message  = $Message
        ts       = (Get-Date -Format "o")
    }
    Write-Output (($obj | ConvertTo-Json -Compress))
}

function Resolve-PythonBin {
    if ($Python -ne "") { return $Python }
    $envPy = $env:BENCH_PYTHON
    if ($envPy -and (Test-Path $envPy)) { return $envPy }

    foreach ($candidate in @(
        "$ROOT\.venv\Scripts\python.exe",
        "$ROOT\.venv312\Scripts\python.exe"
    )) {
        if (Test-Path $candidate) { return $candidate }
    }
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) { return $py.Source }
    $py3 = Get-Command python3 -ErrorAction SilentlyContinue
    if ($py3) { return $py3.Source }
    return $null
}

function Create-RunDir {
    param([string]$BaseDir, [string]$ProfileName)
    $ts = Get-Date -Format "yyyyMMdd-HHmmss"
    for ($i = 0; $i -lt 50; $i++) {
        $rand = '{0:x4}' -f (Get-Random -Maximum 65536)
        $suffix = "$([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())-$rand"
        $dir = Join-Path $BaseDir "run-$ts-$ProfileName-$suffix"
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path (Join-Path $dir "raw") -Force | Out-Null
            return $dir
        }
        Start-Sleep -Milliseconds 20
    }
    throw "Unable to create unique run directory under $BaseDir"
}

function Load-Profile {
    param([string]$ProfileFile)
    Get-Content $ProfileFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -eq "" -or $line.StartsWith("#")) { return }
        if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            $key = $Matches[1]
            $val = $Matches[2].Trim()
            if (-not (Test-Path "env:$key")) {
                Set-Item -Path "env:$key" -Value $val
            }
        }
    }
}

function Run-BenchmarkScript {
    param(
        [string]$Category,
        [string]$Script,
        [string]$OutJson,
        [string]$RunDir
    )
    Write-Progress-Event -Event "category_start" -Category $Category -Status "running"
    $logFile = Join-Path $RunDir "${Category}.log"
    try {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $Script $OutJson 2>&1 |
            Tee-Object -FilePath $logFile
        $exit = $LASTEXITCODE
        if ($exit -eq 0) {
            Write-Progress-Event -Event "category_done" -Category $Category -Status "ok"
        } else {
            Write-Progress-Event -Event "category_done" -Category $Category -Status "failed" `
                -Message "exit code $exit"
        }
    } catch {
        Write-Progress-Event -Event "category_done" -Category $Category -Status "failed" `
            -Message $_.Exception.Message
    }
}

# ──────────────────────────────────────────────────────────────────────
# Validate profile
# ──────────────────────────────────────────────────────────────────────

$ProfileFile = Join-Path $ROOT "profiles\$Profile.env"
if (-not (Test-Path $ProfileFile)) {
    Write-Error "Profile not found: $ProfileFile"
    Write-Host "Available profiles:"
    Get-ChildItem "$ROOT\profiles\*.env" | ForEach-Object { $_.BaseName }
    exit 2
}

Load-Profile -ProfileFile $ProfileFile

$env:BENCH_PYTHON = Resolve-PythonBin
if (-not $env:BENCH_PYTHON) {
    Write-Error "Python interpreter not found. Install Python 3.10+ or set BENCH_PYTHON."
    exit 2
}

Write-Host "[INFO] Python: $env:BENCH_PYTHON"
Write-Host "[INFO] Profile: $Profile"
Write-Host "[INFO] Categories: $Categories"

# ──────────────────────────────────────────────────────────────────────
# Create run directory
# ──────────────────────────────────────────────────────────────────────

$ReportsDir = Join-Path $ROOT "reports"
New-Item -ItemType Directory -Path $ReportsDir -Force | Out-Null

$RunDir = Create-RunDir -BaseDir $ReportsDir -ProfileName $Profile
$RawDir = Join-Path $RunDir "raw"

Write-Progress-Event -Event "run_start" -Message "Run directory: $RunDir"
Write-Host "[INFO] Run directory: $RunDir"

$env:BENCH_RUN_DIR = $RunDir
$env:BENCH_PROFILE  = $Profile

# ──────────────────────────────────────────────────────────────────────
# Preflight
# ──────────────────────────────────────────────────────────────────────

if (-not $SkipPreflight) {
    $PreflightScript = Join-Path $ROOT "scripts\windows\preflight_check.ps1"
    $PreflightJson   = Join-Path $RawDir "preflight.json"
    if (Test-Path $PreflightScript) {
        Write-Progress-Event -Event "category_start" -Category "preflight" -Status "running"
        try {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $PreflightScript `
                -OutJson $PreflightJson 2>&1
            Write-Progress-Event -Event "category_done" -Category "preflight" -Status "ok"
        } catch {
            Write-Progress-Event -Event "category_done" -Category "preflight" -Status "degraded" `
                -Message $_.Exception.Message
        }
    } else {
        Write-Warning "preflight_check.ps1 not found — skipping"
    }
}

# ──────────────────────────────────────────────────────────────────────
# Resolve which categories to run
# ──────────────────────────────────────────────────────────────────────

$AllCategories = @("cpu", "gpu_compute", "gpu_game", "ai", "memory", "disk")

if ($Categories -eq "all" -or $Categories -eq "") {
    $SelectedCategories = $AllCategories
} else {
    $SelectedCategories = $Categories.Split(",") | ForEach-Object { $_.Trim().ToLower() }
    # Expand "gpu" shorthand to both gpu sub-categories
    if ($SelectedCategories -contains "gpu") {
        $SelectedCategories = ($SelectedCategories | Where-Object { $_ -ne "gpu" }) +
                              @("gpu_compute", "gpu_game")
    }
    # Expand "storage" to "disk"
    $SelectedCategories = $SelectedCategories | ForEach-Object {
        if ($_ -eq "storage") { "disk" } else { $_ }
    }
}

$ScriptsDir = Join-Path $ROOT "scripts\windows"

$CategoryScripts = @{
    cpu         = "bench_cpu.ps1"
    gpu_compute = "bench_gpu_compute.ps1"
    gpu_game    = "bench_gpu_game.ps1"
    ai          = "bench_ai.ps1"
    memory      = "bench_memory.ps1"
    disk        = "bench_storage.ps1"
}

# ──────────────────────────────────────────────────────────────────────
# Run benchmarks
# ──────────────────────────────────────────────────────────────────────

$OverallStatus = "ok"

foreach ($cat in $SelectedCategories) {
    if (-not $CategoryScripts.ContainsKey($cat)) {
        Write-Warning "Unknown category '$cat' — skipping"
        continue
    }
    $script = Join-Path $ScriptsDir $CategoryScripts[$cat]
    $outJson = Join-Path $RawDir "$cat.json"

    if (-not (Test-Path $script)) {
        Write-Warning "Script not found for '$cat': $script — skipping"
        Write-Progress-Event -Event "category_done" -Category $cat -Status "skipped" `
            -Message "script not found"
        continue
    }

    try {
        Run-BenchmarkScript -Category $cat -Script $script -OutJson $outJson -RunDir $RunDir
    } catch {
        Write-Warning "Category '$cat' failed: $_"
        $OverallStatus = "degraded"
    }
}

# ──────────────────────────────────────────────────────────────────────
# Generate report via Python
# ──────────────────────────────────────────────────────────────────────

$GenerateReport = Join-Path $ROOT "scripts\generate_report.py"
if (Test-Path $GenerateReport) {
    Write-Progress-Event -Event "generating_report"
    $ReportDir = Join-Path $RunDir "report"
    New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null
    try {
        & $env:BENCH_PYTHON $GenerateReport $RunDir $ReportDir 2>&1
    } catch {
        Write-Warning "Report generation failed: $_"
    }
}

# Write run manifest
$Manifest = [ordered]@{
    run_id        = Split-Path -Leaf $RunDir
    profile       = $Profile
    categories    = $SelectedCategories
    overall_status = $OverallStatus
    run_dir       = $RunDir
    generated_at  = (Get-Date -Format "o")
    platform      = "windows"
    schema_version = "1.0"
}
$Manifest | ConvertTo-Json -Depth 3 | Set-Content -Path (Join-Path $RunDir "run_manifest.json") -Encoding UTF8

Write-Progress-Event -Event "run_done" -Status $OverallStatus -Message "Run complete: $RunDir"
Write-Host "[INFO] Run complete: $RunDir"
Write-Host "[INFO] Overall status: $OverallStatus"
exit 0
