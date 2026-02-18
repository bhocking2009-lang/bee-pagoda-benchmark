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
python -m pip install --upgrade pip
python -m pip install --upgrade numpy
python -m pip install --upgrade onnxruntime torch || true

echo "[INFO] AI stack assumptions:"
echo "  - Python virtualenv: $(pwd)/.venv"
echo "  - Python packages: torch, onnxruntime (best-effort install)"
echo "  - llama.cpp benchmark path expected in PATH as llama-bench or at ./llama.cpp/build/bin/llama-bench"
echo "  - Configure AI_MODEL_PATH to a local GGUF file for llama.cpp benchmark"

echo "[OK] Dependency installation complete."
