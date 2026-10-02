"""
Script 05 — Mixed Precision Demo  (FP32 → BF16)
-------------------------------------------------
By default PyTorch uses 32-bit floating point (FP32) for all computations.
Explorer's modern GPUs (A100, H100) have Tensor Cores that run at much higher
throughput in 16-bit formats.

Precision options on Explorer hardware:
  FP32   — default; safe; baseline to compare against
  BF16   — recommended on A100/H100; same numeric range as FP32; no loss
            scaler needed; unlocks Tensor Core throughput; roughly halves
            activation memory
  FP16   — for V100/T4 nodes (which lack BF16 hardware); requires GradScaler
            to prevent gradient underflow

This script compares FP32 and BF16 on wall time, throughput, and VRAM usage.

Usage:
    python 05_mixed_precision_demo.py    (GPU recommended for the speed numbers)
"""

# Postpone annotation evaluation so modern syntax like `torch.dtype | None`
# works on the cluster's system Python (which predates 3.10).
from __future__ import annotations

import time
import torch
import torch.nn as nn
from torch.amp import GradScaler, autocast

DEVICE     = "cuda" if torch.cuda.is_available() else "cpu"
BATCH_SIZE = 128
INPUT_DIM  = 1024
STEPS      = 40

# Pick the mixed-precision format the actual hardware supports:
#   BF16 on A100/H100 (and CPU autocast), FP16 on V100/T4 (no BF16 hardware).
if DEVICE == "cuda" and not torch.cuda.is_bf16_supported():
    AMP_DTYPE = torch.float16
else:
    AMP_DTYPE = torch.bfloat16
AMP_NAME = "BF16" if AMP_DTYPE == torch.bfloat16 else "FP16"

SEP = "=" * 62

print(SEP)
print("  MIXED PRECISION DEMO — EXPLORER")
print(SEP)
print(f"  Device     : {DEVICE}")

if DEVICE == "cuda":
    p = torch.cuda.get_device_properties(0)
    print(f"  GPU        : {p.name}  ({p.total_memory / 1024**3:.1f} GB VRAM)")

print(f"  Batch size : {BATCH_SIZE}")
print(f"  Steps      : {STEPS}")
print()

if DEVICE == "cpu":
    print("  NOTE: Running on CPU — mixed precision has minimal effect here.")
    print("  On an A100 or H100 the BF16 speedup is typically 1.5–3×.")
    print()
elif not torch.cuda.is_bf16_supported():
    print("  NOTE: This GPU has no BF16 hardware (e.g. V100/T4), so this demo")
    print("  uses FP16 with a GradScaler instead — the right choice on V100.")
    print()


# ── Model large enough to show a meaningful memory difference ─────────────────
class WideNet(nn.Module):
    def __init__(self, width: int = 2048, depth: int = 6):
        super().__init__()
        layers: list[nn.Module] = [nn.Linear(width, width), nn.GELU()]
        for _ in range(depth - 1):
            layers += [nn.Linear(width, width), nn.GELU()]
        layers.append(nn.Linear(width, 10))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


model     = WideNet(width=INPUT_DIM).to(DEVICE)
criterion = nn.CrossEntropyLoss()


def run_training(use_amp: bool, amp_dtype: torch.dtype | None, label: str):
    """Train for STEPS steps and return (elapsed_s, peak_vram_mb, samples_per_sec)."""
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
    use_fp16_scaler = use_amp and amp_dtype == torch.float16
    scaler = GradScaler(device=DEVICE) if use_fp16_scaler else None

    if DEVICE == "cuda":
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()

    t0 = time.perf_counter()
    for _ in range(STEPS):
        x = torch.randn(BATCH_SIZE, INPUT_DIM, device=DEVICE)
        y = torch.randint(0, 10, (BATCH_SIZE,), device=DEVICE)
        opt.zero_grad(set_to_none=True)

        if use_amp and amp_dtype is not None:
            with autocast(device_type=DEVICE, dtype=amp_dtype):
                out  = model(x)
                loss = criterion(out, y)
        else:
            out  = model(x)
            loss = criterion(out, y)

        if scaler:
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
        else:
            loss.backward()
            opt.step()

    if DEVICE == "cuda":
        torch.cuda.synchronize()

    elapsed      = time.perf_counter() - t0
    peak_vram_mb = (
        torch.cuda.max_memory_allocated() / 1024 ** 2 if DEVICE == "cuda" else None
    )
    samples_per_s = BATCH_SIZE * STEPS / elapsed
    return elapsed, peak_vram_mb, samples_per_s


print("[1] Running FP32 training ...")
fp32_t, fp32_mem, fp32_tput = run_training(False, None, "FP32")
print(f"    Wall time     : {fp32_t:.2f} s")
print(f"    Throughput    : {fp32_tput:,.0f} samples / s")
if fp32_mem is not None:
    print(f"    Peak VRAM     : {fp32_mem:.0f} MB")
print()

print(f"[2] Running {AMP_NAME} autocast training ...")
amp_t, amp_mem, amp_tput = run_training(True, AMP_DTYPE, AMP_NAME)
print(f"    Wall time     : {amp_t:.2f} s")
print(f"    Throughput    : {amp_tput:,.0f} samples / s")
if amp_mem is not None:
    print(f"    Peak VRAM     : {amp_mem:.0f} MB")
print()

# ── Summary ───────────────────────────────────────────────────────────────────
speedup = fp32_t / amp_t if amp_t > 0 else float("inf")

print(SEP)
print("  SUMMARY")
print(SEP)
print(f"  Speedup  {AMP_NAME} vs FP32   : {speedup:.2f}×")
if fp32_mem is not None and amp_mem is not None:
    reduction_pct = (1.0 - amp_mem / fp32_mem) * 100
    print(f"  VRAM reduction ({AMP_NAME})   : {reduction_pct:.0f}%")
    print(f"  FP32 peak VRAM          : {fp32_mem:.0f} MB")
    print(f"  {AMP_NAME} peak VRAM          : {amp_mem:.0f} MB")

print()
print("  CODE CHANGE — just one context manager:")
print()
print("    # Before (FP32)")
print("    out  = model(x)")
print("    loss = criterion(out, y)")
print("    loss.backward()")
print()
print("    # After (BF16) — add this wrapper only")
print("    from torch.amp import autocast")
print("    with autocast(device_type='cuda', dtype=torch.bfloat16):")
print("        out  = model(x)")
print("        loss = criterion(out, y)")
print("    loss.backward()   # gradients stay FP32 automatically")
print()
print("  PRECISION GUIDE FOR EXPLORER:")
print()
print("  ┌─────────┬────────────────────────────────────────────────┐")
print("  │ BF16    │ Default on A100 / H100.  No GradScaler needed.  │")
print("  │         │ Same dynamic range as FP32.  Activates Tensor  │")
print("  │         │ Core throughput and ~halves activation memory. │")
print("  ├─────────┼────────────────────────────────────────────────┤")
print("  │ FP16    │ Use on V100 / T4 (no BF16 hardware).  Requires │")
print("  │         │ a GradScaler to prevent gradient underflow.    │")
print("  ├─────────┼────────────────────────────────────────────────┤")
print("  │ FP32    │ Debugging / baseline only.  Full precision but │")
print("  │         │ slowest and 2× the memory of 16-bit formats.   │")
print("  └─────────┴────────────────────────────────────────────────┘")
print()
print("  USE BF16 on A100/H100.  Use FP16 (with GradScaler) on V100/T4.")
print(SEP)
