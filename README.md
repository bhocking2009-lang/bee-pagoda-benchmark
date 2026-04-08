# Bee Pagoda Benchmark

A professional Linux benchmark suite with a modern native desktop GUI built on **PySide6 / Qt6**.

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

- Linux (x86-64)
- Python 3.12+
- PySide6 (`pip install PySide6`)
- Benchmark tools (sysbench, ffmpeg, 7z, etc.) — optional, degrades gracefully

---

## Quick Start

### Run from source

```bash
# Clone and set up
git clone https://github.com/bhocking2009-lang/bee-pagoda-benchmark
cd bee-pagoda-benchmark
python3 -m venv .venv
source .venv/bin/activate
pip install PySide6
pip install -e .

# Launch the GUI
bee-pagoda
# or:
python -m app.gui.main

# CLI-only run
bee-pagoda-cli balanced --categories cpu,memory
# or directly:
./run_suite.sh balanced --categories cpu,memory
```

### Install benchmark dependencies

```bash
bash scripts/install_dependencies.sh
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
│   ├── bench_cpu.sh
│   ├── bench_gpu_compute.sh
│   ├── bench_gpu_game.sh
│   ├── bench_ai.sh
│   ├── bench_memory.sh
│   ├── bench_storage.sh
│   ├── preflight_check.sh
│   ├── generate_report.py
│   └── install_dependencies.sh
├── profiles/
│   ├── quick.env            ← ~2 min
│   ├── balanced.env         ← ~8 min  (default)
│   └── deep.env             ← ~25 min
├── reports/                 ← Output run directories
├── packaging/
│   ├── bee-pagoda-benchmark.desktop
│   ├── build-appimage.sh
│   └── build-deb.sh
├── run_suite.sh             ← Orchestrator (usable headlessly)
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

```bash
# Build AppImage
bash packaging/build-appimage.sh

# Build .deb
bash packaging/build-deb.sh
```

Output goes to `dist/`.

---

## Config & Logs

| Path | Purpose |
|---|---|
| `~/.local/share/bee-pagoda-benchmark/logs/app.log` | GUI application log |
| `reports/history.json` | Run history index |
| `profiles/*.env` | Benchmark profile parameters |

---

## License

MIT
