"""
Script 01 — GPU Verification on AICR
--------------------------------------
Run this at the TOP of every GPU job to confirm you received the hardware you
requested and that CUDA is reachable.  Takes under 5 seconds.

On AICR you will see either an NVIDIA B200 (b200-* partitions) or an
NVIDIA RTX PRO 6000 (rtx-* partitions).  The output tells you which you got,
how much VRAM is available, and whether SLURM isolated the GPU correctly.

Usage (interactive devel session):
    srun -p b200-devel -N 1 -n 1 -c 4 --mem=16G --gres=gpu:1 --time=00:30:00 --pty bash
    module load cuda/13.1 miniforge3/25.3.0-3
    source activate <your_env>
    python 01_gpu_verify.py

Expected output on a B200 node:
    GPU 0: NVIDIA B200   192.0 GB   SMs: 160
"""

import os
import subprocess
import sys

try:
    import torch
except ImportError:
    print("PyTorch is not installed in this environment.")
    print("Activate your conda environment first:")
    print("  module load miniforge3/25.3.0-3")
    print("  source activate <your_env>")
    sys.exit(1)

SEP = "=" * 58

print(SEP)
print("  GPU VERIFICATION REPORT — AICR")
print(SEP)

# ── 1. CUDA availability ──────────────────────────────────────────────────────
cuda_ok = torch.cuda.is_available()
print(f"\n[1] CUDA available  : {cuda_ok}")
print(f"    PyTorch version  : {torch.__version__}")

if not cuda_ok:
    print("\n  CUDA is NOT available.  Most likely causes:")
    print("  (a) You are on a login node — request a compute node:")
    print("      srun -p b200-devel -N 1 -n 1 -c 4 --mem=16G --gres=gpu:1 \\")
    print("           --time=01:00:00 --pty bash")
    print("  (b) The CUDA module was not loaded:")
    print("      module load cuda/13.1")
    print("  (c) Your --gres directive in the SLURM script has a typo.")
    print()
    print("  ⚠  AICR REMINDER: The idle-GPU cancellation process watches for")
    print("     jobs that hold a GPU but do nothing.  Fix this before submitting")
    print("     to a batch partition.")
    print(SEP)
    sys.exit(0)

# ── 2. Enumerate GPUs ─────────────────────────────────────────────────────────
gpu_count = torch.cuda.device_count()
print(f"\n[2] GPU count       : {gpu_count}")

for i in range(gpu_count):
    p = torch.cuda.get_device_properties(i)
    vram_gb = p.total_memory / 1024 ** 3
    print(f"    GPU {i}: {p.name}")
    print(f"           VRAM : {vram_gb:.1f} GB")
    print(f"           SMs  : {p.multi_processor_count}")

    # Sanity-check the expected AICR GPUs
    name_lower = p.name.lower()
    if "b200" in name_lower:
        print(f"           ✓  Blackwell B200 — supports FP32 / BF16 / FP8")
        print(f"              Tip: BF16 is the practical default; FP8 via torchao")
    elif "rtx" in name_lower and ("6000" in p.name or "pro" in name_lower):
        print(f"           ✓  RTX PRO 6000 Blackwell — supports FP32 / BF16 / FP8")
    else:
        print(f"           ⚠  Unrecognised GPU for AICR — check your partition")

# ── 3. CUDA_VISIBLE_DEVICES ───────────────────────────────────────────────────
cvd = os.environ.get("CUDA_VISIBLE_DEVICES", "NOT SET")
print(f"\n[3] CUDA_VISIBLE_DEVICES : {cvd}")
if cvd == "NOT SET":
    print("    (normal in an srun interactive session without explicit SLURM binding)")

# ── 4. Cross-verify with nvidia-smi ──────────────────────────────────────────
print("\n[4] nvidia-smi cross-check:")
try:
    result = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,name,memory.total,memory.free,power.limit,uuid",
            "--format=csv,noheader",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        for line in result.stdout.strip().splitlines():
            print(f"    {line}")
    else:
        print("    nvidia-smi returned a non-zero exit code.")
except FileNotFoundError:
    print("    nvidia-smi not found — load the CUDA module first.")

# ── 5. Tensor round-trip test ─────────────────────────────────────────────────
print("\n[5] Tensor round-trip (CPU → GPU → CPU):")
try:
    x = torch.tensor([1.0, 2.0, 3.0]).cuda()
    y = (x * 2).cpu()
    print(f"    Input  : [1.0, 2.0, 3.0]")
    print(f"    Output : {y.tolist()}  ✓")
except Exception as exc:
    print(f"    FAILED: {exc}")

# ── 6. AICR-specific policy reminder ─────────────────────────────────────────
print()
print(SEP)
print("  AICR POLICY REMINDERS")
print(SEP)
print("  • Idle GPU policy : A background process CANCELS jobs that hold a GPU")
print("    without running kernels.  Always confirm utilisation > 0% early in")
print("    your job.  Use `nvidia-smi` or `nvitop` in a second terminal.")
print()
print("  • Devel partitions: b200-devel / rtx-devel  (≤4 h, interactive)")
print("    Batch partitions: b200-batch / rtx-batch  (≤24 h, sbatch only)")
print()
print("  • Run this script at the START of every job — it takes <5 seconds.")
print()
print("  All checks complete.")
print(SEP)
