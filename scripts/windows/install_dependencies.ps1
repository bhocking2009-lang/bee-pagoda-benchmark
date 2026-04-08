<#
.SYNOPSIS
    Windows dependency installer for Bee Pagoda Benchmark.

.DESCRIPTION
    Uses winget and pip to install benchmark dependencies.
    Run as Administrator for system-wide installs.

.PARAMETER PipOnly
    Only install Python packages (skip winget tools).

.PARAMETER WingetOnly
    Only install system tools via winget (skip pip packages).
#>
param(
    [switch]$PipOnly,
    [switch]$WingetOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

function Write-Section { param([string]$Title)
    Write-Host ""
    Write-Host "══════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host "══════════════════════════════════════" -ForegroundColor Cyan
}

function Install-Winget { param([string]$Id, [string]$Label)
    Write-Host "  Installing $Label ($Id)..." -NoNewline
    try {
        $out = winget install --id $Id --silent --accept-package-agreements `
                              --accept-source-agreements 2>&1
        if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq -1978335189) {
            Write-Host " OK" -ForegroundColor Green
        } else {
            Write-Host " WARN (exit $LASTEXITCODE)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host " FAILED: $_" -ForegroundColor Red
    }
}

function Install-Pip { param([string]$Package, [string[]]$ExtraArgs = @())
    Write-Host "  pip install $Package ..." -NoNewline
    try {
        & python -m pip install --upgrade $Package @ExtraArgs 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host " OK" -ForegroundColor Green
        } else {
            Write-Host " WARN (exit $LASTEXITCODE)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host " FAILED: $_" -ForegroundColor Red
    }
}

# ──────────────────────────────────────────────────────────────────────
# System tools (winget)
# ──────────────────────────────────────────────────────────────────────

if (-not $PipOnly) {
    Write-Section "System Tools (winget)"

    $wingetAvailable = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $wingetAvailable) {
        Write-Warning "winget not found. Install App Installer from the Microsoft Store."
    } else {
        Install-Winget "7zip.7zip"     "7-Zip"
        Install-Winget "Gyan.FFmpeg"   "FFmpeg"
        Install-Winget "Git.Git"       "Git"
        Install-Winget "Python.Python.3.12" "Python 3.12"

        Write-Host ""
        Write-Host "  Note: NVIDIA drivers and CUDA must be installed manually."
        Write-Host "  Visit: https://developer.nvidia.com/cuda-downloads"
        Write-Host ""
        Write-Host "  Note: Vulkan SDK (optional, for vulkaninfo):"
        Write-Host "  Visit: https://vulkan.lunarg.com/sdk/home#windows"
    }
}

# ──────────────────────────────────────────────────────────────────────
# Python packages (pip)
# ──────────────────────────────────────────────────────────────────────

if (-not $WingetOnly) {
    Write-Section "Python Packages (pip)"

    # Check Python availability
    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pyCmd) {
        Write-Warning "Python not found. Install Python 3.10+ first."
    } else {
        $pyVer = & python --version 2>&1
        Write-Host "  Using: $pyVer"

        # Core
        Install-Pip "pip" "--upgrade"
        Install-Pip "numpy"
        Install-Pip "PySide6"
        Install-Pip "psutil"

        # AI / ML
        Install-Pip "onnx"
        Install-Pip "onnxruntime"

        # GPU graphics
        Install-Pip "moderngl"

        # PyTorch (CPU-only by default; user can reinstall with CUDA)
        Write-Host ""
        Write-Host "  Installing PyTorch (CPU-only)..." -NoNewline
        & python -m pip install torch torchvision torchaudio 2>&1 | Out-Null
        Write-Host " OK" -ForegroundColor Green

        Write-Host ""
        Write-Host "  For CUDA-accelerated PyTorch, run:" -ForegroundColor Yellow
        Write-Host "    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121" -ForegroundColor Yellow
    }
}

# ──────────────────────────────────────────────────────────────────────
# Final verification
# ──────────────────────────────────────────────────────────────────────

Write-Section "Verification"
$preflightScript = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "preflight_check.ps1"
if (Test-Path $preflightScript) {
    $tmpJson = Join-Path $env:TEMP "bee_install_verify.json"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $preflightScript -OutJson $tmpJson
    if (Test-Path $tmpJson) {
        $pf = Get-Content $tmpJson -Raw | ConvertFrom-Json -ErrorAction SilentlyContinue
        if ($pf) {
            Write-Host ""
            Write-Host "  Overall preflight status: $($pf.status)" -ForegroundColor $(
                if ($pf.status -eq "ok") { "Green" } else { "Yellow" }
            )
            if ($pf.missing -and $pf.missing.Count -gt 0) {
                Write-Host "  Still missing: $($pf.missing -join ', ')" -ForegroundColor Yellow
            }
        }
    }
} else {
    Write-Warning "preflight_check.ps1 not found at $preflightScript"
}

Write-Host ""
Write-Host "Done. Run the benchmark with:" -ForegroundColor Green
Write-Host "  .\run_suite.ps1             (PowerShell orchestrator)" -ForegroundColor Cyan
Write-Host "  bee-pagoda                  (GUI)" -ForegroundColor Cyan
Write-Host "  bee-pagoda-cli              (CLI)" -ForegroundColor Cyan
