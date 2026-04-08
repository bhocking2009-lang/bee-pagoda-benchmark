<#
.SYNOPSIS
    Windows Preflight Dependency Check.

.DESCRIPTION
    Checks all tools and Python packages required by the benchmark suite
    and writes a JSON result in the same schema as preflight_check.sh.

.PARAMETER OutJson
    Path where the result JSON will be written.
#>
param([string]$OutJson = "$env:TEMP\bee_bench_preflight.json")

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$PYTHON_BIN = if ($env:BENCH_PYTHON) { $env:BENCH_PYTHON } else { "python" }

$checks  = [System.Collections.Generic.List[object]]::new()
$missing = [System.Collections.Generic.List[string]]::new()
$overall = "ok"

function Find-Tool { param([string]$Name)
    $f = Get-Command $Name -ErrorAction SilentlyContinue
    return if ($f) { $f.Source } else { $null }
}

function Add-ToolCheck {
    param(
        [string]$Name,
        [string]$Label,
        [string]$Category,
        [bool]$Required = $false,
        [string]$InstallHint = "",
        [string]$VersionArg = "--version"
    )
    $path = Find-Tool $Name
    if ($path) {
        try {
            $verOut = & $path $VersionArg 2>&1 | Select-Object -First 1
            $version = ($verOut -replace "[^\d.]", "").Trim().Split(".")[0..2] -join "."
        } catch {
            $version = ""
        }
        $checks.Add([ordered]@{
            name     = $Label
            status   = "ok"
            found    = $true
            path     = $path
            version  = $version
            category = $Category
            hint     = ""
        }) | Out-Null
    } else {
        $status = if ($Required) { "missing" } else { "optional_missing" }
        $checks.Add([ordered]@{
            name     = $Label
            status   = $status
            found    = $false
            path     = ""
            version  = ""
            category = $Category
            hint     = $InstallHint
        }) | Out-Null
        if ($Required) {
            $missing.Add($Label) | Out-Null
            $script:overall = "degraded"
        }
    }
}

function Add-PythonPackageCheck {
    param(
        [string]$Package,
        [string]$ImportName = "",
        [string]$Category  = "python",
        [bool]$Required    = $false,
        [string]$InstallHint = ""
    )
    if ($ImportName -eq "") { $ImportName = $Package }
    $pyCheck = @"
import sys, json
try:
    import importlib.metadata as meta
    try:
        v = meta.version('$Package')
    except Exception:
        import $ImportName
        v = getattr($ImportName, '__version__', 'ok')
    print(json.dumps({'status': 'ok', 'version': v}))
except Exception as e:
    print(json.dumps({'status': 'missing', 'version': '', 'error': str(e)}))
"@
    try {
        $out = & $PYTHON_BIN -c $pyCheck 2>&1
        $res = $out | ConvertFrom-Json -ErrorAction SilentlyContinue
        $found   = $res -and $res.status -eq "ok"
        $version = if ($res) { $res.version } else { "" }
    } catch {
        $found   = $false
        $version = ""
    }
    $status = if ($found) { "ok" } else { if ($Required) { "missing" } else { "optional_missing" } }
    $checks.Add([ordered]@{
        name     = $Package
        status   = $status
        found    = $found
        path     = $PYTHON_BIN
        version  = $version
        category = $Category
        hint     = if ($found) { "" } else { $InstallHint }
    }) | Out-Null
    if (-not $found -and $Required) {
        $missing.Add($Package) | Out-Null
        $script:overall = "degraded"
    }
}

# ──────────────────────────────────────────────────────────────────────
# Python interpreter
# ──────────────────────────────────────────────────────────────────────

$pyPath = Find-Tool "python"
if (-not $pyPath) { $pyPath = Find-Tool "python3" }
if ($pyPath) {
    $pyVer = & $pyPath --version 2>&1
    $checks.Add([ordered]@{
        name     = "Python"
        status   = "ok"
        found    = $true
        path     = $pyPath
        version  = $pyVer.ToString().Trim()
        category = "runtime"
        hint     = ""
    }) | Out-Null
} else {
    $checks.Add([ordered]@{
        name     = "Python"
        status   = "missing"
        found    = $false
        path     = ""
        version  = ""
        category = "runtime"
        hint     = "Download from https://www.python.org/downloads/"
    }) | Out-Null
    $overall = "failed"
}

# PowerShell version
$psVer = $PSVersionTable.PSVersion.ToString()
$checks.Add([ordered]@{
    name     = "PowerShell"
    status   = "ok"
    found    = $true
    path     = (Get-Command powershell -ErrorAction SilentlyContinue)?.Source
    version  = $psVer
    category = "runtime"
    hint     = ""
}) | Out-Null

# ──────────────────────────────────────────────────────────────────────
# CLI tools
# ──────────────────────────────────────────────────────────────────────

Add-ToolCheck "7z"         "7-Zip (7z)"      "cpu"     $false "winget install 7zip.7zip"
Add-ToolCheck "ffmpeg"     "FFmpeg"          "cpu"     $false "winget install Gyan.FFmpeg"
Add-ToolCheck "nvidia-smi" "NVIDIA SMI"      "gpu"     $false "Install NVIDIA drivers"
Add-ToolCheck "vulkaninfo" "Vulkan Info"     "gpu"     $false "Install Vulkan SDK from https://vulkan.lunarg.com/"
Add-ToolCheck "git"        "Git"             "dev"     $false "winget install Git.Git"
Add-ToolCheck "curl"       "curl"            "network" $false "Built into Windows 10+"

# ──────────────────────────────────────────────────────────────────────
# Python packages
# ──────────────────────────────────────────────────────────────────────

Add-PythonPackageCheck "numpy"        "numpy"        "python" $true  "pip install numpy"
Add-PythonPackageCheck "onnxruntime"  "onnxruntime"  "ai"     $false "pip install onnxruntime"
Add-PythonPackageCheck "torch"        "torch"        "ai"     $false "pip install torch --index-url https://download.pytorch.org/whl/cu121"
Add-PythonPackageCheck "moderngl"     "moderngl"     "gpu"    $false "pip install moderngl"
Add-PythonPackageCheck "PySide6"      "PySide6"      "gui"    $true  "pip install PySide6"
Add-PythonPackageCheck "onnx"         "onnx"         "ai"     $false "pip install onnx"

# ──────────────────────────────────────────────────────────────────────
# Write result
# ──────────────────────────────────────────────────────────────────────

$result = [ordered]@{
    status         = $overall
    platform       = "windows"
    checks         = $checks
    missing        = $missing
    notes          = if ($missing.Count -gt 0) {
                         "Missing required tools: $($missing -join ', ')"
                     } else { "" }
    schema_version = "1.0"
    ts             = (Get-Date -Format "o")
}

$result | ConvertTo-Json -Depth 8 | Set-Content -Path $OutJson -Encoding UTF8
Write-Host "[Preflight] Done. Status=$overall -> $OutJson"

if ($overall -ne "ok") {
    Write-Warning "Some dependencies are missing or degraded. See $OutJson"
    exit 1
}
exit 0
