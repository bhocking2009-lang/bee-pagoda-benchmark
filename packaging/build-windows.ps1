<#
.SYNOPSIS
    Build a standalone Windows .exe using PyInstaller.

.DESCRIPTION
    Creates a self-contained Windows executable for Bee Pagoda Benchmark.
    Output: dist\bee-pagoda-benchmark\bee-pagoda-benchmark.exe

.PARAMETER Version
    App version string. Default: 1.0.0

.PARAMETER Onefile
    Produce a single-file executable instead of a directory bundle.
#>
param(
    [string]$Version  = "1.0.0",
    [switch]$Onefile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent

Push-Location $ROOT

# ──────────────────────────────────────────────────────────────────────
# Prerequisites
# ──────────────────────────────────────────────────────────────────────

Write-Host "[Build] Checking prerequisites..."

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw "Python not found. Install Python 3.10+ first." }

Write-Host "[Build] Installing / upgrading PyInstaller..."
& python -m pip install --upgrade pyinstaller | Out-Null

# ──────────────────────────────────────────────────────────────────────
# Build arguments
# ──────────────────────────────────────────────────────────────────────

$appName  = "bee-pagoda-benchmark"
$mainFile = "app\gui\main.py"
$distDir  = "dist"
$workDir  = "build\pyinstaller"

$args = @(
    $mainFile,
    "--name",          $appName,
    "--distpath",      $distDir,
    "--workpath",      $workDir,
    "--specpath",      "build",
    "--noconfirm",
    "--clean",
    "--windowed",                         # Windows GUI app (no console)
    "--add-data",      "profiles;profiles",
    "--add-data",      "scripts;scripts",
    "--add-data",      "sample-output;sample-output",
    "--hidden-import", "PySide6.QtCharts",
    "--hidden-import", "PySide6.QtSvg",
    "--hidden-import", "app.core",
    "--hidden-import", "app.services",
    "--hidden-import", "app.gui"
)

# Optional: icon (place bee-pagoda.ico in packaging\)
$iconPath = Join-Path $ROOT "packaging\bee-pagoda.ico"
if (Test-Path $iconPath) {
    $args += @("--icon", $iconPath)
}

if ($Onefile) {
    $args += "--onefile"
    Write-Host "[Build] Building single-file executable..."
} else {
    Write-Host "[Build] Building directory bundle..."
}

# ──────────────────────────────────────────────────────────────────────
# Run PyInstaller
# ──────────────────────────────────────────────────────────────────────

Write-Host "[Build] Running PyInstaller..."
& python -m PyInstaller @args

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$exePath = Join-Path $distDir "$appName\$appName.exe"
if (-not (Test-Path $exePath)) {
    $exePath = Join-Path $distDir "$appName.exe"
}

if (Test-Path $exePath) {
    Write-Host ""
    Write-Host "[Build] SUCCESS" -ForegroundColor Green
    Write-Host "[Build] Executable: $exePath" -ForegroundColor Green
} else {
    Write-Warning "[Build] PyInstaller finished but executable not found at expected path."
}

Pop-Location
