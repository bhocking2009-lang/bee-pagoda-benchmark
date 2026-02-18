# Linux Benchmark Report

- **Profile:** `quick`
- **Generated (UTC):** `2026-02-18T01:51:53.876990+00:00`
- **Run directory:** `/home/openclaw/.openclaw/workspace/project-linux-benchmark-tool/reports/run-20260217-205121-quick-729979011-52fe`
- **Selected categories:** `cpu`
- **Suite Python interpreter:** `/home/openclaw/.openclaw/workspace/project-linux-benchmark-tool/.venv/bin/python`

## Preflight

- status: degraded
- present: 15
- missing: 0
- version-mismatch: 0
- optional-missing: 1
- interpreter: /home/openclaw/.openclaw/workspace/project-linux-benchmark-tool/.venv/bin/python
- notes: Status classes: present, missing, version-mismatch, optional-missing

| Dependency | Status | Version | Path |
|---|---|---|---|
| python3 | present | 3.14.3 | /home/openclaw/.openclaw/workspace/project-linux-benchmark-tool/.venv/bin/python |
| pip | present | 26.0.1 | /home/openclaw/.openclaw/workspace/project-linux-benchmark-tool/.venv/bin/python |
| torch | optional-missing |  |  |
| onnxruntime | present | 1.24.1 | /home/openclaw/.openclaw/workspace/project-linux-benchmark-tool/.venv/lib/python3.14/site-packages/onnxruntime/__init__.py |
| llama-bench | present | 5 | /home/openclaw/.openclaw/workspace/llama.cpp/build/bin/llama-bench |
| nvcc | present | 12.0 | /usr/bin/nvcc |
| nvidia-smi | present | 590.48.01 | /usr/bin/nvidia-smi |
| clpeak | present | 1.1.2 | /usr/bin/clpeak |
| vkmark | present |  | /usr/bin/vkmark |
| glmark2 | present | 2023.01 | /usr/bin/glmark2 |
| fio | present | 3.36 | /usr/bin/fio |
| sysbench | present | 1.0.20 | /usr/bin/sysbench |
| ffmpeg | present | 8.0.1 | /home/linuxbrew/.linuxbrew/bin/ffmpeg |
| 7z | present |  | /usr/bin/7z |
| tinymembench | present | 6 | /usr/bin/tinymembench |
| hashcat | present | 6.2.6 | /usr/bin/hashcat |

## Status Summary

- ok: 0
- degraded: 0
- skipped: 0
- failed: 1
- missing: 0

## Results

| Category | Status | Benchmark | Key Metrics |
|---|---|---|---|
| cpu | failed | cpu_suite | score=68185.65; baseline:ok; compression:failed; encoding:ok; baseline=sysbench;compression_7z_failed;encoding=ffmpeg_libx264 |

## Exit Semantics
- `0`: selected steps completed without `failed` status
- `1`: one or more selected benchmark steps failed
- `2`: usage/config error
