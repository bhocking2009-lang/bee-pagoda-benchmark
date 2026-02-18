# Linux Benchmark Report

- **Profile:** `balanced`
- **Generated (UTC):** `2026-02-18T01:50:10.318986+00:00`
- **Run directory:** `/home/openclaw/.openclaw/workspace/project-linux-benchmark-tool/reports/run-20260217-203753-balanced-362017916-7084`
- **Selected categories:** `cpu, gpu_compute, gpu_game, ai, memory, disk`
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

- ok: 3
- degraded: 2
- skipped: 0
- failed: 1
- missing: 0

## Results

| Category | Status | Benchmark | Key Metrics |
|---|---|---|---|
| cpu | failed | cpu_suite | score=43441.99; baseline:ok; compression:failed; encoding:ok; baseline=sysbench;compression_7z_failed;encoding=ffmpeg_libx264 |
| gpu_compute | ok | clpeak | gflops=na;duration_hint=60s |
| gpu_game | degraded | glmark2 | mode=offscreen;glmark2 offscreen failed (context/timeout).;display=:1;session=x11;glmark2=/usr/bin/glmark2 |
| ai | degraded | multi_backend_ai | score=1.0; prompt_tps=37001553.03793248; eval_tps=37001553.03793248; backend=multi; model=synthetic-matmul; backend_sources=llama.cpp:real_model:skipped,onnxruntime:synthetic_proxy:degraded,torch:synthetic_proxy:skipped; composite_formula=composite = sum(weight_b * min(1.0, score_b/reference_b)) / sum(weights for backends with numeric score); Per-backend metrics are primary truth (real_model vs synthetic_proxy labels included); composite is normalized helper score |
| memory | ok | memory_suite | score=95655.43; sysbench_memory:ok; tinymembench:ok; sysbench_memory_ok;tinymembench_ok |
| disk | ok | fio_file_safe | score=2161703; fio_seq:ok; fio_rand4k:ok; fio_seq_ok;fio_rand_ok_qd1_qd16;safe_file=/home/openclaw/.openclaw/workspace/project-linux-benchmark-tool/reports/run-20260217-203753-balanced-362017916-7084/.bench_fio_testfile.bin;test_size=512M;runtime=20 |

## Exit Semantics
- `0`: selected steps completed without `failed` status
- `1`: one or more selected benchmark steps failed
- `2`: usage/config error
