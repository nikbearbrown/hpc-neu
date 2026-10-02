"""
Script 02 — Naive (one-by-one) vs Batched GPU Processing
----------------------------------------------------------
GPUs are built for massive parallelism.  The NVIDIA V100 on Explorer contains
thousands of CUDA cores that sit idle when you send work one item at a time.

This script measures the same total computation done two ways:
  • Naive   : 10,000 individual forward passes (one sample each)
  • Batched : One forward pass over all 10,000 samples simultaneously

The ratio between the two reveals how much of the GPU's capacity was wasted
in the naive approach.

Explorer note: the faster the GPU, the larger the relative penalty of
one-by-one processing.  Each kernel launch has a fixed overhead, and on a
data-center GPU like the V100 that fixed cost is a big fraction of total time
when call sizes are tiny — so batching is essential.

Usage:
    python 02_naive_vs_batched.py

Works on CPU for code testing, but the speedup ratio is most meaningful on
a GPU node.
"""

import time
import torch

FEATURE_SIZE = 1024
DATA_SIZE    = 10_000
DEVICE       = "cuda" if torch.cuda.is_available() else "cpu"
WARMUP_STEPS = 5

SEP = "=" * 58

print(SEP)
print("  NAIVE vs BATCHED GPU PROCESSING")
print(SEP)
print(f"  Device      : {DEVICE}")

if DEVICE == "cuda":
    p = torch.cuda.get_device_properties(0)
    print(f"  GPU         : {p.name}  ({p.total_memory / 1024**3:.1f} GB VRAM)")

print(f"  Samples     : {DATA_SIZE:,}")
print(f"  Feature dim : {FEATURE_SIZE}")
print()

model = torch.nn.Linear(FEATURE_SIZE, FEATURE_SIZE).to(DEVICE)
model.eval()


def sync():
    if DEVICE == "cuda":
        torch.cuda.synchronize()


# ── Warm up the GPU so first-call JIT overhead doesn't skew results ───────────
print("Warming up ...")
with torch.no_grad():
    dummy = torch.randn(32, FEATURE_SIZE, device=DEVICE)
    for _ in range(WARMUP_STEPS):
        _ = model(dummy)
sync()
print("Done.\n")

# ── Approach 1: one sample at a time ─────────────────────────────────────────
print("[1] Naive approach — one sample per GPU call ...")
sync()
t0 = time.perf_counter()
with torch.no_grad():
    for _ in range(DATA_SIZE):
        sample = torch.randn(1, FEATURE_SIZE, device=DEVICE)
        _ = model(sample)
sync()
naive_s = time.perf_counter() - t0

print(f"    Total wall time : {naive_s:.3f} s")
print(f"    Per-sample      : {naive_s / DATA_SIZE * 1_000:.4f} ms")

# ── Approach 2: all samples in one call ──────────────────────────────────────
print()
print("[2] Batched approach — all samples in a single GPU call ...")
all_data = torch.randn(DATA_SIZE, FEATURE_SIZE, device=DEVICE)
sync()
t0 = time.perf_counter()
with torch.no_grad():
    _ = model(all_data)
sync()
batched_s = time.perf_counter() - t0

print(f"    Total wall time : {batched_s:.3f} s")
print(f"    Per-sample      : {batched_s / DATA_SIZE * 1_000:.4f} ms")

# ── Summary ───────────────────────────────────────────────────────────────────
speedup = naive_s / batched_s if batched_s > 0 else float("inf")

print()
print(SEP)
print("  SUMMARY")
print(SEP)
print(f"  Naive   : {naive_s:.3f} s")
print(f"  Batched : {batched_s:.3f} s")
print(f"  Speedup : {speedup:.1f}×")
print()
print("  WHY THE DIFFERENCE?")
print("  Every call to the GPU has a fixed overhead regardless of how much")
print("  work you send: kernel launch latency, synchronisation, and PCIe")
print("  transfer setup.  In the naive loop you pay that overhead 10,000")
print("  times.  In the batched call you pay it once.")
print()
print("  ON EXPLORER (V100):")
print("  The V100 computes each batch quickly.  That means the fixed")
print("  kernel-launch overhead is a LARGER fraction of total time if you use")
print("  tiny call sizes — making batching even more critical.")
print()
print("  TAKEAWAY: Never iterate over individual samples and send them to the")
print("  GPU one at a time.  Always batch your inputs.")
print(SEP)
