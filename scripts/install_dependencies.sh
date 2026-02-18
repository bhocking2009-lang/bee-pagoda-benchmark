#!/usr/bin/env bash
set -euo pipefail

# Installs optional benchmark dependencies using detected package manager.
# Safe to rerun (idempotent).

PM=""
if command -v apt-get >/dev/null 2>&1; then
  PM="apt"
elif command -v dnf >/dev/null 2>&1; then
  PM="dnf"
elif command -v pacman >/dev/null 2>&1; then
  PM="pacman"
fi

if [[ -z "$PM" ]]; then
  echo "[WARN] No supported package manager found (apt/dnf/pacman)."
  echo "[INFO] Please install tools manually: jq python3 sysbench glmark2 vkmark clpeak fio p7zip ffmpeg tinymembench hashcat"
  exit 0
fi

install_apt() {
  sudo apt-get update
  sudo apt-get install -y \
    jq python3 python3-venv python3-pip bc coreutils procps \
    sysbench glmark2 vkmark clpeak vulkan-tools mesa-utils \
    fio p7zip-full ffmpeg tinymembench hashcat
}

install_dnf() {
  sudo dnf install -y \
    jq python3 python3-pip bc coreutils procps-ng \
    sysbench glmark2 vkmark clpeak vulkan-tools mesa-demos \
    fio p7zip ffmpeg tinymembench hashcat
}

install_pacman() {
  sudo pacman -Sy --noconfirm \
    jq python python-pip bc coreutils procps-ng \
    sysbench glmark2 vkmark clpeak vulkan-tools mesa-demos \
    fio p7zip ffmpeg tinymembench hashcat
}

echo "[INFO] Using package manager: $PM"
case "$PM" in
  apt) install_apt ;;
  dnf) install_dnf ;;
  pacman) install_pacman ;;
esac

echo "[INFO] Preparing optional AI Python stack in local .venv"
python3 -m venv .venv || true
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install --upgrade numpy

PY_MM="$(python - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"

echo "[INFO] Python in .venv: ${PY_MM}"
if [[ "$PY_MM" == "3.14" ]]; then
  echo "[WARN] Python 3.14 may not have stable torch wheels yet; prefer Python 3.12/3.13 for AI proxy deps"
fi

if command -v nvidia-smi >/dev/null 2>&1; then
  echo "[INFO] NVIDIA runtime detected; attempting onnxruntime-gpu, falling back to onnxruntime"
  python -m pip install --upgrade onnxruntime-gpu || python -m pip install --upgrade onnxruntime || true
else
  python -m pip install --upgrade onnxruntime || true
fi

python -m pip install --upgrade torch || true

echo "[INFO] AI stack guidance:"
echo "  - Credible AI mode requires llama.cpp + GGUF (AI_MODEL_PATH=/abs/model.gguf)"
echo "  - llama-bench path: PATH or ./llama.cpp/build/bin/llama-bench"
echo "  - Optional proxy deps: torch, onnxruntime (CPU) / onnxruntime-gpu (NVIDIA)"
echo "  - If torch install fails on Python 3.14, create a 3.12 venv and pass --python /path/to/python"

echo "[OK] Dependency installation complete."
