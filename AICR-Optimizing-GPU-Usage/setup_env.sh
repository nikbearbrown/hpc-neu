#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
#  AICR Workshop on GPU Optimization - Environment Setup
#  GPU Profiling and Optimization on AICR
#
#  Run this script ONCE on a b200-devel or rtx-devel node to create the conda
#  environment used throughout the training demos.
#
#  Steps:
#    1. Get an interactive GPU node:
#         srun -p b200-devel -N 1 -n 1 -c 8 --mem=32G --gres=gpu:1 \
#              --time=01:00:00 --pty bash
#
#    2. Load the required modules:
#         module load cuda/13.1
#         module load miniforge3/25.3.0-3
#
#    3. Run this script from your scratch directory:
#         cd /scratch/$USER
#         git clone git@github.com:northeastern-rc-training/AICR-Optimizing-GPU-Usage.git
#         cd AICR-Optimizing-GPU-Usage
#         chmod +x setup_env.sh
#         ./setup_env.sh
#
#    4. Activate the environment:
#         source activate aicr_gpu_workshop
#
#  After setup you can also add this to your ~/.bashrc so modules load
#  automatically in future sessions (optional):
#    module load cuda/13.1
#    module load miniforge3/25.3.0-3
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

ENV_NAME="aicr_gpu_workshop"

echo "======================================================="
echo "  AICR Workshop 2 — Environment Setup"
echo "======================================================="

# Confirm we are in the right place
echo ""
echo "Checking prerequisites ..."

if ! command -v conda &>/dev/null; then
    echo ""
    echo "ERROR: conda not found."
    echo "Load the module first:  module load miniforge3/25.3.0-3"
    exit 1
fi

if ! command -v nvcc &>/dev/null; then
    echo ""
    echo "WARNING: nvcc not found.  PyTorch will still install but CUDA"
    echo "kernels may not compile.  Load the module:"
    echo "  module load cuda/13.1"
fi

echo "conda found : $(conda --version)"
echo "nvcc        : $(nvcc --version 2>/dev/null | head -1 || echo 'not loaded')"
echo ""

# ── Create environment ────────────────────────────────────────────────────────
if conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
    echo "Environment '$ENV_NAME' already exists — skipping creation."
    echo "(Delete it first with 'conda env remove -n $ENV_NAME' to rebuild from scratch.)"
else
    echo "Creating conda environment: $ENV_NAME ..."
    echo "(This can take 3–5 minutes on first install)"
    echo ""
    conda create -y -n "$ENV_NAME" python=3.11
fi

# ── Install packages ──────────────────────────────────────────────────────────
echo "Installing PyTorch (CUDA 12.8 build) and dependencies ..."
conda run -n "$ENV_NAME" pip install \
    torch \
    torchvision \
    torchaudio \
    --index-url https://download.pytorch.org/whl/cu128

echo "Installing profiling and monitoring tools ..."
conda run -n "$ENV_NAME" pip install \
    nvitop \
    tensorboard \
    matplotlib \
    numpy

echo ""
echo "======================================================="
echo "  Environment setup complete."
echo "======================================================="
echo ""
echo "Activate with:"
echo "  source activate $ENV_NAME"
echo ""
echo "Quick verification (run on a GPU node):"
echo "  python -c \"import torch; print(torch.cuda.is_available())\""
echo "  python scripts/01_gpu_verify.py"
echo ""
echo "IMPORTANT — run scripts from /scratch, not /home:"
echo "  cd /scratch/\$USER/<repo-name>"
echo "  source activate $ENV_NAME"
echo "  python scripts/01_gpu_verify.py"
echo ""
echo "The scratch directory has a 30-day purge policy."
echo "Save important outputs to /work/neu/\$PROJECT before they expire."
echo "======================================================="
