<#
.SYNOPSIS
    Windows GPU Graphics/Game Benchmark — DirectX feature-level check,
    Vulkan info, and a Python-based offscreen rendering stress test.

.PARAMETER OutJson
    Path where the result JSON will be written.
#>
param([string]$OutJson = "$env:TEMP\bee_bench_gpu_game.json")

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$PYTHON_BIN = if ($env:BENCH_PYTHON) { $env:BENCH_PYTHON } else { "python" }
$GPU_MODE   = if ($env:GPU_GAME_MODE) { $env:GPU_GAME_MODE } else { "offscreen" }

$status   = "skipped"
$fps      = $null
$notes    = [System.Collections.Generic.List[string]]::new()
$subtests = [ordered]@{}
$gpuModel = ""
$backend  = "unknown"

function Find-Tool { param([string[]]$Names)
    foreach ($n in $Names) {
        $f = Get-Command $n -ErrorAction SilentlyContinue
        if ($f) { return $f.Source }
    }; return $null
}

# ──────────────────────────────────────────────────────────────────────
# GPU identification
# ──────────────────────────────────────────────────────────────────────

try {
    $cimGpu = Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue |
              Select-Object -First 1 Name, AdapterRAM, DriverVersion, CurrentRefreshRate
    if ($cimGpu) {
        $gpuModel = $cimGpu.Name
        $gpuUpper = $gpuModel.ToUpper()
        if     ($gpuUpper -match "NVIDIA")  { $backend = "nvidia" }
        elseif ($gpuUpper -match "AMD|RADEON") { $backend = "amd" }
        elseif ($gpuUpper -match "INTEL")   { $backend = "intel" }
        $subtests["gpu_info"] = [ordered]@{
            status         = "ok"
            model          = $gpuModel
            vram_mb        = if ($cimGpu.AdapterRAM) { [int]($cimGpu.AdapterRAM / 1MB) } else { 0 }
            driver_version = $cimGpu.DriverVersion
            refresh_hz     = $cimGpu.CurrentRefreshRate
            source         = "Win32_VideoController"
        }
    }
} catch {
    $notes.Add("GPU info query failed: $_")
}

# ──────────────────────────────────────────────────────────────────────
# DirectX feature level check via dxdiag
# ──────────────────────────────────────────────────────────────────────

$dxdiag = Find-Tool @("dxdiag")
if ($dxdiag) {
    try {
        $dxFile = Join-Path $env:TEMP "bee_dxdiag.txt"
        & $dxdiag /t $dxFile /whql:off 2>&1 | Out-Null
        # Wait for dxdiag to finish (it runs async)
        $waited = 0
        while (-not (Test-Path $dxFile) -and $waited -lt 15) {
            Start-Sleep -Seconds 1; $waited++
        }
        if (Test-Path $dxFile) {
            $dxContent = Get-Content $dxFile -Raw
            $featureLevel = if ($dxContent -match "Feature Levels:\s+(.+)") { $Matches[1].Trim() } else { "" }
            $dxVersion    = if ($dxContent -match "DirectX Version:\s+(.+)") { $Matches[1].Trim() } else { "" }
            $subtests["directx"] = [ordered]@{
                status         = "ok"
                dx_version     = $dxVersion
                feature_levels = $featureLevel
            }
            $status = "degraded"  # dxdiag is info only, not a workload
        }
    } catch {
        $notes.Add("dxdiag failed: $_")
    }
}

# ──────────────────────────────────────────────────────────────────────
# Vulkan info via vulkaninfo (if installed)
# ──────────────────────────────────────────────────────────────────────

$vulkanInfo = Find-Tool @("vulkaninfo")
if ($vulkanInfo) {
    try {
        $vkOut = & $vulkanInfo --summary 2>&1 | Select-String "GPU id|deviceName|apiVersion" |
                 Select-Object -First 6
        $subtests["vulkan"] = [ordered]@{
            status = "ok"
            info   = ($vkOut -join "`n").Trim()
        }
    } catch {
        $notes.Add("vulkaninfo failed: $_")
    }
}

# ──────────────────────────────────────────────────────────────────────
# Python offscreen rendering stress test via PyOpenGL / moderngl
# ──────────────────────────────────────────────────────────────────────

$glBenchScript = @'
import json, sys, time
result = {"status": "skipped", "notes": "", "backend": "offscreen"}
try:
    import moderngl
    ctx = moderngl.create_standalone_context()
    w, h = 1920, 1080
    fbo = ctx.simple_framebuffer((w, h))
    fbo.use()

    prog = ctx.program(
        vertex_shader="""
            #version 330
            in vec2 in_vert;
            void main() { gl_Position = vec4(in_vert, 0.0, 1.0); }
        """,
        fragment_shader="""
            #version 330
            out vec4 fragColor;
            void main() { fragColor = vec4(0.1, 0.5, 0.9, 1.0); }
        """,
    )
    vbo = ctx.buffer(b"\xff" * 24)
    vao = ctx.vertex_array(prog, [(vbo, "2f", "in_vert")])

    FRAMES = 500
    t0 = time.perf_counter()
    for _ in range(FRAMES):
        ctx.clear(0.0, 0.0, 0.0)
        vao.render(moderngl.TRIANGLES)
    elapsed = time.perf_counter() - t0
    result["fps"]    = round(FRAMES / elapsed, 2)
    result["frames"] = FRAMES
    result["status"] = "ok"
except ImportError:
    result["notes"] = "moderngl not installed; pip install moderngl"
except Exception as e:
    result["status"] = "failed"
    result["notes"]  = str(e)
print(json.dumps(result))
'@

try {
    $glOut = & $PYTHON_BIN -c $glBenchScript 2>&1
    $glResult = $glOut | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($glResult) {
        $subtests["opengl_offscreen"] = $glResult
        if ($glResult.status -eq "ok") {
            $fps    = $glResult.fps
            $status = "ok"
        } elseif ($status -eq "skipped") {
            $status = "degraded"
            $notes.Add($glResult.notes)
        }
    }
} catch {
    $subtests["opengl_offscreen"] = [ordered]@{ status = "failed"; notes = "$_" }
}

# ──────────────────────────────────────────────────────────────────────
# Write result
# ──────────────────────────────────────────────────────────────────────

$result = [ordered]@{
    bench          = "gpu_game"
    status         = $status
    fps            = $fps
    gpu_model      = $gpuModel
    gpu_mode       = $GPU_MODE
    backend        = $backend
    subtests       = $subtests
    notes          = ($notes | Out-String).Trim()
    schema_version = "1.0"
    platform       = "windows"
    ts             = (Get-Date -Format "o")
}

$result | ConvertTo-Json -Depth 8 | Set-Content -Path $OutJson -Encoding UTF8
Write-Host "[GPU-Game] Done. Status=$status FPS=$fps -> $OutJson"
exit 0
