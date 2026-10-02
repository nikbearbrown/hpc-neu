"""
Script 01 — GPU Verification on Explorer
------------------------------------------
Run this at the TOP of every GPU job to confirm you received the hardware you
requested and that CUDA is reachable.  Takes under 5 seconds.

On Explorer you will typically see an NVIDIA V100 (32 GB) or an A100 (80 GB),
depending on the partition and node you land on.  These demos request a V100.
The output tells you which you got, how much VRAM is available, and whether
SLURM isolated the GPU correctly.

Usage (interactive session):
    srun --partition=gpu-short --gres=gpu:v100-sxm2:1 --cpus-per-task=4 --mem=16G \
         --time=00:30:00 --pty bash
    source gpu_training_env/bin/activate
    python scripts/01_gpu_verify.py

Expected output on a V100 node:
    GPU 0: Tesla V100-SXM2-32GB   32.0 GB   SMs: 80
"""

import os
import subprocess
import sys

try:
    import torch
except ImportError:
    print("PyTorch is not installed in this environment.")
    print("Activate the training environment first:")
    print("  source gpu_training_env/bin/activate")
    sys.exit(1)

SEP = "=" * 58

print(SEP)
print("  GPU VERIFICATION REPORT — EXPLORER")
print(SEP)

# ── 1. CUDA availability ──────────────────────────────────────────────────────
cuda_ok = torch.cuda.is_available()
print(f"\n[1] CUDA available  : {cuda_ok}")
print(f"    PyTorch version  : {torch.__version__}")

if not cuda_ok:
    print("\n  CUDA is NOT available.  Most likely causes:")
    print("  (a) You are on a login node — request a compute node:")
    print("      srun --partition=gpu-short --gres=gpu:v100-sxm2:1 --cpus-per-task=4 \\")
    print("           --mem=16G --time=01:00:00 --pty bash")
    print("  (b) The training environment is not activated:")
    print("      source gpu_training_env/bin/activate")
    print("  (c) Your --gres directive in the SLURM script has a typo.")
    print()
    print("  Nothing below this line is meaningful without a GPU.")
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

    # Sanity-check the expected Explorer GPUs and hint at the right precision
    name_lower = p.name.lower()
    if "a100" in name_lower or "h100" in name_lower:
        print(f"           ✓  Ampere/Hopper — use BF16 (no GradScaler needed)")
    elif "v100" in name_lower or "t4" in name_lower:
        print(f"           ✓  Volta/Turing — use FP16 with GradScaler (no BF16 HW)")
    else:
        print(f"           ⚠  Unrecognised GPU — confirm your partition/--gres")

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
    print("    nvidia-smi not found — are you on a GPU node?")

# ── 5. Tensor round-trip test ─────────────────────────────────────────────────
print("\n[5] Tensor round-trip (CPU → GPU → CPU):")
try:
    x = torch.tensor([1.0, 2.0, 3.0]).cuda()
    y = (x * 2).cpu()
    print(f"    Input  : [1.0, 2.0, 3.0]")
    print(f"    Output : {y.tolist()}  ✓")
except Exception as exc:
    print(f"    FAILED: {exc}")

# ── 6. Explorer reminders ─────────────────────────────────────────────────────
print()
print(SEP)
print("  EXPLORER REMINDERS")
print(SEP)
print("  • Profile & develop on the short/interactive partitions:")
print("      gpu-short (2 h), gpu-interactive (2 h), sharing (1 h)")
print("    Submit tuned production jobs with sbatch to:")
print("      gpu (8 h), multigpu (24 h — requires separate access)")
print()
print("  • Confirm utilisation early with `nvidia-smi` or `nvitop` in a")
print("    second terminal.  A loaded-but-idle GPU means wasted allocation.")
print()
print("  • After a batch job finishes, review the utilisation time-series:")
print("      gpu-logs <jobid>")
print()
print("  • Run this script at the START of every job — it takes <5 seconds.")
print()
print("  All checks complete.")
print(SEP)
