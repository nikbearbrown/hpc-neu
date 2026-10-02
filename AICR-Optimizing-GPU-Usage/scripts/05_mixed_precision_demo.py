"""
Script 05 — Mixed Precision Demo  (FP32 → BF16, with FP8 pointer)
-------------------------------------------------------------------
By default PyTorch uses 32-bit floating point (FP32) for all computations.
Both the NVIDIA B200 and RTX PRO 6000 on AICR are Blackwell GPUs with 5th-
generation Tensor Cores that run at much higher throughput in lower-precision
formats.

Precision options on AICR hardware:
  FP32   — default; safe; baseline
  BF16   — recommended starting point; same numeric range as FP32; no loss
            scaler needed; ~2–4× faster matrix ops on Blackwell Tensor Cores;
            roughly halves activation memory
  FP16   — requires GradScaler to prevent underflow; rarely better than BF16
            on modern hardware; not recommended on Blackwell
  FP8    — available on B200 via `torchao` or `transformer_engine`; meaningful
            speedup for large-scale LLM training; more complex to set up;
            mentioned here for awareness, not demonstrated

This script compares FP32 and BF16 on wall time, throughput, and VRAM usage.

Usage:
    python 05_mixed_precision_demo.py    (GPU recommended for the speed numbers)
"""

import time
import torch
import torch.nn as nn
from torch.amp import GradScaler, autocast

DEVICE     = "cuda" if torch.cuda.is_available() else "cpu"
BATCH_SIZE = 128
INPUT_DIM  = 1024
STEPS      = 40

SEP = "=" * 62

print(SEP)
print("  MIXED PRECISION DEMO — AICR (Blackwell)")
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
    print("  On a B200 or RTX PRO 6000 the BF16 speedup is typically 2–4×.")
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

print("[2] Running BF16 autocast training ...")
bf16_t, bf16_mem, bf16_tput = run_training(True, torch.bfloat16, "BF16")
print(f"    Wall time     : {bf16_t:.2f} s")
print(f"    Throughput    : {bf16_tput:,.0f} samples / s")
if bf16_mem is not None:
    print(f"    Peak VRAM     : {bf16_mem:.0f} MB")
print()

# ── Summary ───────────────────────────────────────────────────────────────────
speedup = fp32_t / bf16_t if bf16_t > 0 else float("inf")

print(SEP)
print("  SUMMARY")
print(SEP)
print(f"  Speedup  BF16 vs FP32   : {speedup:.2f}×")
if fp32_mem is not None and bf16_mem is not None:
    reduction_pct = (1.0 - bf16_mem / fp32_mem) * 100
    print(f"  VRAM reduction (BF16)   : {reduction_pct:.0f}%")
    print(f"  FP32 peak VRAM          : {fp32_mem:.0f} MB")
    print(f"  BF16 peak VRAM          : {bf16_mem:.0f} MB")

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
print("  PRECISION GUIDE FOR AICR:")
print()
print("  ┌─────────┬────────────────────────────────────────────────┐")
print("  │ BF16    │ Default choice on B200 and RTX PRO 6000.       │")
print("  │         │ No GradScaler needed.  Same dynamic range as   │")
print("  │         │ FP32.  Activates Tensor Core throughput.       │")
print("  ├─────────┼────────────────────────────────────────────────┤")
print("  │ FP16    │ Avoid on Blackwell GPUs.  Use BF16 instead.    │")
print("  │         │ Requires GradScaler; offers no advantage.      │")
print("  ├─────────┼────────────────────────────────────────────────┤")
print("  │ FP8     │ Available on B200 via torchao or               │")
print("  │         │ transformer_engine.  Meaningful gain for       │")
print("  │         │ LLM-scale workloads (7B+ params).  More setup  │")
print("  │         │ required.  Ask RC for guidance.                │")
print("  └─────────┴────────────────────────────────────────────────┘")
print()
print("  USE BF16 today.  Evaluate FP8 once your BF16 run is stable.")
print(SEP)
