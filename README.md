# Bee Pagoda Benchmark

A professional **cross-platform** (Linux + Windows) benchmark suite with a modern native desktop GUI built on **PySide6 / Qt6**.

## Features

| Category | Backends |
|---|---|
| CPU | sysbench · openssl · ffmpeg |
| GPU Compute | clpeak · hashcat |
| GPU Graphics | game-style offscreen workload |
| AI | llama.cpp · PyTorch · ONNX Runtime |
| Memory | mbw · stream |
| Storage | fio · dd |

**GUI highlights:**
- Dark-first native desktop look — not a browser panel
- Live benchmark monitoring with per-category status badges
- Results viewer with charts, AI backend breakdown, and export
- Run history with search and multi-run comparison
- Dependency preflight screen with copy-to-clipboard install guidance
- Profile-based runs: quick / balanced / deep

---

## Requirements

### Linux
- Linux x86-64 (Ubuntu 22.04+, Fedora 38+, Arch, etc.)
- Python 3.12+
- PySide6 (`pip install PySide6`)
- Benchmark tools (ffmpeg, 7z, sysbench, etc.) — optional, degrades gracefully

### Windows
- Windows 10 (1809+) or Windows 11 — x86-64
- Python 3.12+
- PowerShell 5.1+ (built-in) or PowerShell 7
- PySide6 (`pip install PySide6`)
- Benchmark tools (7-Zip, FFmpeg, etc.) — optional, degrades gracefully

---

## Quick Start

### Linux — run from source

```bash
git clone https://github.com/bhocking2009-lang/bee-pagoda-benchmark
cd bee-pagoda-benchmark
python3 -m venv .venv
source .venv/bin/activate
pip install PySide6
pip install -e .

# Launch the GUI
bee-pagoda

# CLI-only run
bee-pagoda-cli balanced --categories cpu,memory
# or directly:
./run_suite.sh balanced --categories cpu,memory
```

### Linux — install benchmark dependencies

```bash
bash scripts/install_dependencies.sh
```

### Windows — run from source

```powershell
git clone https://github.com/bhocking2009-lang/bee-pagoda-benchmark
cd bee-pagoda-benchmark
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install PySide6
pip install -e .

# Launch the GUI
bee-pagoda

# CLI-only run
bee-pagoda-cli balanced --categories cpu,memory
# or directly via PowerShell:
.\run_suite.ps1 -Profile balanced -Categories cpu,memory
```

### Windows — install benchmark dependencies

```powershell
# Run as Administrator for system-wide installs
.\scripts\windows\install_dependencies.ps1
```

### Windows — build installer

```powershell
# Step 1: Build standalone .exe bundle
.\packaging\build-windows.ps1

# Step 2 (optional): Build Windows installer with Inno Setup
iscc packaging\bee-pagoda-benchmark.iss
```

---

## Directory Structure

```
bee-pagoda-benchmark/
├── app/
│   ├── gui/                 ← PySide6 desktop application
│   │   ├── main.py          ← QApplication entry point
│   │   ├── windows/         ← Dashboard, run form, monitor, results, history…
│   │   ├── widgets/         ← Sidebar, log viewer, status badges, charts
│   │   ├── themes/          ← Qt stylesheet (dark theme)
│   │   └── assets/          ← Icons, images
│   ├── core/                ← Python benchmark engine
│   │   ├── runner.py        ← run_suite.sh wrapper + CLI entry point
│   │   ├── process_manager.py ← subprocess with live streaming
│   │   ├── schemas.py       ← Typed result models (dataclasses)
│   │   ├── result_loader.py ← Load JSON from run directories
│   │   ├── history.py       ← JSON-backed run history index
│   │   ├── profiles.py      ← .env profile loader
│   │   └── diagnostics.py   ← CPU/GPU/RAM/OS detection
│   └── services/            ← Orchestration layer
│       ├── benchmark_service.py
│       ├── preflight_service.py
│       └── export_service.py
├── scripts/
│   ├── bench_cpu.sh            ← Linux benchmarks
│   ├── bench_gpu_compute.sh
│   ├── bench_gpu_game.sh
│   ├── bench_ai.sh
│   ├── bench_memory.sh
│   ├── bench_storage.sh
│   ├── preflight_check.sh
│   ├── generate_report.py
│   ├── install_dependencies.sh
│   └── windows/                ← Windows PowerShell benchmarks
│       ├── bench_cpu.ps1
│       ├── bench_gpu_compute.ps1
│       ├── bench_gpu_game.ps1
│       ├── bench_ai.ps1
│       ├── bench_memory.ps1
│       ├── bench_storage.ps1
│       ├── preflight_check.ps1
│       └── install_dependencies.ps1
├── profiles/
│   ├── quick.env               ← ~2 min
│   ├── balanced.env            ← ~8 min  (default)
│   └── deep.env                ← ~25 min
├── reports/                    ← Output run directories
├── packaging/
│   ├── bee-pagoda-benchmark.desktop  ← Linux desktop entry
│   ├── build-appimage.sh             ← Linux AppImage
│   ├── build-deb.sh                  ← Linux .deb
│   ├── build-windows.ps1             ← Windows PyInstaller .exe
│   └── bee-pagoda-benchmark.iss      ← Windows Inno Setup installer
├── run_suite.sh                ← Linux orchestrator (bash)
├── run_suite.ps1               ← Windows orchestrator (PowerShell)
└── pyproject.toml
```

---

## Profiles

| Profile | Duration | Purpose |
|---|---|---|
| `quick` | ~2 min | Sanity checks, CI |
| `balanced` | ~8 min | Everyday benchmarks (default) |
| `deep` | ~25 min | Stable, high-confidence results |

---

## CLI Usage

```bash
# Run all categories with balanced profile
./run_suite.sh balanced

# Run only CPU and memory, quick profile
./run_suite.sh quick --categories cpu,memory

# Skip preflight checks
./run_suite.sh balanced --skip-preflight

# Use a specific Python interpreter
./run_suite.sh balanced --python /usr/bin/python3.12
```

---

## Status Semantics

| Status | Meaning |
|---|---|
| `ok` | Benchmark ran via primary path |
| `degraded` | Fallback path used or partial coverage |
| `skipped` | Dependency missing or intentionally unavailable |
| `failed` | Attempted but did not complete |

---

## Output Formats

Each run produces a timestamped directory under `reports/`:

```
reports/run-20240615-142300-balanced-xxxxx/
├── raw/
│   ├── cpu.json
│   ├── gpu_compute.json
│   ├── gpu_game.json
│   ├── ai.json
│   ├── memory.json
│   ├── disk.json
│   └── preflight.json
└── report/
    ├── summary.json
    ├── summary.md
    └── summary.csv
```

---

## Packaging

### Linux

```bash
# Build AppImage
bash packaging/build-appimage.sh

# Build .deb
bash packaging/build-deb.sh
```

### Windows

```powershell
# Build standalone .exe (PyInstaller)
.\packaging\build-windows.ps1

# Build Windows installer (requires Inno Setup 6)
iscc packaging\bee-pagoda-benchmark.iss
```

Output goes to `dist/`.

---

## Config & Logs

| Platform | Path | Purpose |
|---|---|---|
| Linux | `~/.local/share/bee-pagoda-benchmark/logs/app.log` | GUI log |
| Windows | `%LOCALAPPDATA%\BeePagodaBenchmark\logs\app.log` | GUI log |
| Both | `reports/history.json` | Run history index |
| Both | `profiles/*.env` | Benchmark profile parameters |

---

## Windows Notes

- The Windows orchestrator is `run_suite.ps1` (PowerShell 5.1+).
- PowerShell execution policy must allow local scripts. If needed, run:
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
  ```
- Benchmark scripts live under `scripts\windows\` and produce the same JSON
  schema as the Linux bash scripts, so all GUI views work identically.
- GPU detection uses `nvidia-smi` (if present) and `Win32_VideoController` via CIM.
- AI detection supports llama.cpp, ONNX Runtime, and PyTorch — same as Linux.

---

## License

MIT
