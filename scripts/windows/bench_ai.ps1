<#
.SYNOPSIS
    Windows AI Benchmark — llama.cpp, ONNX Runtime, PyTorch inference.

.PARAMETER OutJson
    Path where the result JSON will be written.
#>
param([string]$OutJson = "$env:TEMP\bee_bench_ai.json")

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$PYTHON_BIN = if ($env:BENCH_PYTHON) { $env:BENCH_PYTHON } else { "python" }

$status           = "skipped"
$credible_ai_mode = $false
$composite_tps    = $null
$notes            = [System.Collections.Generic.List[string]]::new()
$backends         = [ordered]@{}

function Find-Tool { param([string[]]$Names)
    foreach ($n in $Names) {
        $f = Get-Command $n -ErrorAction SilentlyContinue
        if ($f) { return $f.Source }
    }; return $null
}

# ──────────────────────────────────────────────────────────────────────
# llama.cpp / llama-bench (native binary)
# ──────────────────────────────────────────────────────────────────────

$llamaBench = Find-Tool @("llama-bench", "llama-bench.exe")
if ($llamaBench) {
    Write-Host "[AI] Running llama-bench..."
    try {
        $out = & $llamaBench -t 4 -pg 512,128 2>&1
        $tpsMatch = [regex]::Match(($out -join "`n"), "(\d+\.\d+)\s+tokens/s")
        if ($tpsMatch.Success) {
            $tps = [double]$tpsMatch.Groups[1].Value
            $backends["llama_cpp"] = [ordered]@{
                status     = "ok"
                tool       = $llamaBench
                prompt_tps = $tps
                notes      = "llama-bench native"
            }
            $credible_ai_mode = $true
            $composite_tps    = $tps
            $status           = "ok"
        } else {
            $backends["llama_cpp"] = [ordered]@{
                status = "degraded"
                tool   = $llamaBench
                notes  = "llama-bench ran but tps could not be parsed"
            }
        }
    } catch {
        $backends["llama_cpp"] = [ordered]@{ status = "failed"; notes = "$_" }
    }
} else {
    $backends["llama_cpp"] = [ordered]@{ status = "skipped"; notes = "llama-bench not found" }
    $notes.Add("llama-bench not found; install llama.cpp for native AI benchmark")
}

# ──────────────────────────────────────────────────────────────────────
# ONNX Runtime
# ──────────────────────────────────────────────────────────────────────

$onnxScript = @'
import json, time, sys
result = {"status": "skipped", "backend": "onnxruntime", "notes": ""}
try:
    import onnxruntime as ort
    import numpy as np
    result["ort_version"] = ort.__version__
    providers = ort.get_available_providers()
    result["providers"] = providers

    # Synthetic ONNX model benchmark
    import onnx
    from onnx import helper, TensorProto
    from onnx.helper import make_tensor_value_info, make_node, make_graph, make_model

    X = make_tensor_value_info("X", TensorProto.FLOAT, [1, 3, 224, 224])
    Y = make_tensor_value_info("Y", TensorProto.FLOAT, [1, 3, 224, 224])
    node = make_node("Relu", ["X"], ["Y"])
    graph = make_graph([node], "test", [X], [Y])
    model = make_model(graph)
    model.opset_import[0].version = 17

    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(suffix=".onnx", delete=False)
    tmp.write(model.SerializeToString()); tmp.close()

    sess = ort.InferenceSession(tmp.name, providers=providers[:1])
    data = np.random.randn(1, 3, 224, 224).astype(np.float32)

    RUNS = 200
    t0 = time.perf_counter()
    for _ in range(RUNS):
        sess.run(None, {"X": data})
    elapsed = time.perf_counter() - t0
    os.unlink(tmp.name)

    result["inferences_per_sec"] = round(RUNS / elapsed, 2)
    result["provider_used"]      = providers[0] if providers else "CPUExecutionProvider"
    result["status"]             = "ok"
except ImportError:
    result["notes"] = "onnxruntime not installed; pip install onnxruntime"
except Exception as e:
    result["status"] = "failed"
    result["notes"]  = str(e)
print(json.dumps(result))
'@

try {
    $onnxOut = & $PYTHON_BIN -c $onnxScript 2>&1
    $onnxResult = $onnxOut | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($onnxResult) {
        $backends["onnxruntime"] = $onnxResult
        if ($onnxResult.status -eq "ok" -and $status -eq "skipped") {
            $status = "degraded"   # ONNX synthetic, not credible_ai_mode
        }
    }
} catch {
    $backends["onnxruntime"] = [ordered]@{ status = "failed"; notes = "$_" }
}

# ──────────────────────────────────────────────────────────────────────
# PyTorch inference
# ──────────────────────────────────────────────────────────────────────

$torchScript = @'
import json, time, sys
result = {"status": "skipped", "backend": "pytorch", "notes": ""}
try:
    import torch
    import torch.nn as nn
    result["torch_version"] = torch.__version__
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    result["device"] = str(device)

    model = nn.Sequential(
        nn.Linear(512, 1024), nn.ReLU(),
        nn.Linear(1024, 512), nn.ReLU(),
        nn.Linear(512, 10)
    ).to(device)
    model.eval()

    x = torch.randn(32, 512, device=device)
    RUNS = 500
    with torch.no_grad():
        t0 = time.perf_counter()
        for _ in range(RUNS):
            _ = model(x)
        if device.type == "cuda":
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - t0

    result["inferences_per_sec"] = round(RUNS / elapsed, 2)
    result["status"]             = "ok"
except ImportError:
    result["notes"] = "torch not installed; pip install torch"
except Exception as e:
    result["status"] = "failed"
    result["notes"]  = str(e)
print(json.dumps(result))
'@

try {
    $torchOut = & $PYTHON_BIN -c $torchScript 2>&1
    $torchResult = $torchOut | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($torchResult) {
        $backends["pytorch"] = $torchResult
        if ($torchResult.status -eq "ok" -and $status -eq "skipped") {
            $status = "degraded"
        }
    }
} catch {
    $backends["pytorch"] = [ordered]@{ status = "failed"; notes = "$_" }
}

# ──────────────────────────────────────────────────────────────────────
# Write result
# ──────────────────────────────────────────────────────────────────────

$result = [ordered]@{
    bench             = "ai"
    status            = $status
    credible_ai_mode  = $credible_ai_mode
    composite_tps     = $composite_tps
    backends          = $backends
    notes             = ($notes | Out-String).Trim()
    schema_version    = "1.0"
    platform          = "windows"
    ts                = (Get-Date -Format "o")
}

$result | ConvertTo-Json -Depth 8 | Set-Content -Path $OutJson -Encoding UTF8
Write-Host "[AI] Done. Status=$status CredibleAI=$credible_ai_mode -> $OutJson"
exit 0
