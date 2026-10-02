#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
#  GPU Training — Environment Setup (Explorer)
#  GPU Performance Optimization on Explorer
#
#  Run this script ONCE to create the Python virtual environment used
#  throughout the training demos.
#
#  Steps:
#    1. Get an interactive GPU node:
#         srun --partition=gpu-short --gres=gpu:v100-sxm2:1 --cpus-per-task=4 --mem=16G \
#              --time=01:00:00 --pty bash
#
#    2. Run this script from your scratch directory (the system python3 is used —
#       this cluster has no python module, and PyTorch's CUDA runtime ships in
#       the wheels, so no CUDA module is required either):
#         cd /scratch/$USER
#         git clone https://github.com/northeastern-rc-training/Optimizing-GPU-Usage-on-Explorer.git
#         cd Optimizing-GPU-Usage-on-Explorer
#         chmod +x setup_env.sh
#         ./setup_env.sh
#
#    3. Activate the environment:
#         source gpu_training_env/bin/activate
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

VENV_DIR="gpu_training_env"

echo "======================================================="
echo "  GPU Training — Environment Setup (Explorer)"
echo "======================================================="

# ── Prerequisites ─────────────────────────────────────────────────────────────
echo ""
echo "Checking prerequisites ..."

if ! command -v python3 &>/dev/null; then
    echo ""
    echo "ERROR: python3 not found."
    echo "This cluster has no python module; python3 is expected to be on PATH."
    echo "Check with:  command -v python3  &&  python3 --version"
    exit 1
fi

echo "python3 : $(python3 --version)"
echo ""
echo "Note: PyTorch's CUDA runtime is bundled with the pip wheels installed below,"
echo "so no CUDA module is required.  You only need a GPU node (the NVIDIA driver"
echo "is always present there) to actually use the GPU."
echo ""

# ── Create venv (skip if it already exists) ───────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "[1/4] Creating virtual environment: $VENV_DIR"
    python3 -m venv "$VENV_DIR"
else
    echo "[1/4] Virtual environment already exists: $VENV_DIR"
    echo "      (Delete it with 'rm -rf $VENV_DIR' to rebuild from scratch.)"
fi

# ── Activate ──────────────────────────────────────────────────────────────────
source "$VENV_DIR/bin/activate"
echo "[2/4] Activated: $(which python)"

pip install --quiet --upgrade pip

# ── Install PyTorch ───────────────────────────────────────────────────────────
# On Explorer (GPU node), the default CUDA-enabled wheels work:
#   pip install torch torchvision torchaudio
# For CPU-only testing (local machine / login node), use:
#   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
echo "[3/4] Installing PyTorch (CUDA-enabled wheels. This might take a while) ..."
pip install torch torchvision torchaudio

# ── Install profiling / monitoring tools ──────────────────────────────────────
# nvitop        : live GPU dashboard (Section 2)
# tensorboard   : view PyTorch Profiler traces (Section 3)
# nvidia-ml-py  : NVML bindings for live utilisation sampling (Section 5, script 06)
# matplotlib    : optional plotting
echo "[4/4] Installing profiling and monitoring tools ..."
pip install --quiet nvitop tensorboard nvidia-ml-py matplotlib numpy

echo ""
echo "======================================================="
echo "  Environment setup complete."
echo "======================================================="
echo ""
echo "Activate with:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "Quick verification (run on a GPU node):"
echo "  python -c \"import torch; print(torch.cuda.is_available())\""
echo "  python scripts/01_gpu_verify.py"
echo ""
echo "IMPORTANT — run from /scratch, not /home:"
echo "  cd /scratch/\$USER/Optimizing-GPU-Usage-on-Explorer"
echo "  source $VENV_DIR/bin/activate"
echo "  python scripts/01_gpu_verify.py"
echo "======================================================="
