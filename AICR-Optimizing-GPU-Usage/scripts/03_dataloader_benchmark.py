"""
Script 03 — DataLoader Configuration Benchmark
------------------------------------------------
The NVIDIA B200 on AICR can finish a training batch in a few milliseconds.
If your data pipeline takes longer than that to deliver the next batch, the
GPU stalls — it holds its VRAM allocation (and your queue time) while doing
absolutely nothing.

This script benchmarks four DataLoader configurations and shows how much of
the GPU's time would be spent waiting under each one.

AICR storage note:
  • /home/$USER      — never train from here (slow, shared, 100 GB quota)
  • /scratch/$USER   — good for large sequential reads; 30-day purge; no
                       tiny-file workloads
  • /work/neu/$PROJECT — for longer-term data; slower throughput than scratch
  • $TMPDIR          — node-local fast storage IF available on your compute
                       node; copy data here at job start (see snippet below)

Usage:
    python 03_dataloader_benchmark.py

No GPU required — this measures CPU-side loading speed only.
"""

import time
import os
import torch
from torch.utils.data import DataLoader, TensorDataset

N_SAMPLES   = 8_000
IMAGE_SHAPE = (3, 64, 64)
BATCH_SIZE  = 64
N_BATCHES   = 60

# Simulated GPU compute time per batch (milliseconds).
# On a B200, a typical ResNet-50 forward+backward on a 64-image batch
# completes in roughly 5–15 ms at BF16.  Adjust this to match your workload.
SIMULATED_GPU_MS = 12.0

SEP = "=" * 62

print(SEP)
print("  DATALOADER CONFIGURATION BENCHMARK — AICR")
print(SEP)
print(f"  Dataset     : {N_SAMPLES:,} synthetic images {IMAGE_SHAPE}")
print(f"  Batches     : {N_BATCHES} × batch_size={BATCH_SIZE}")
print(f"  Simulated GPU compute/batch : {SIMULATED_GPU_MS:.0f} ms  (B200 BF16 estimate)")
print()

images  = torch.randn(N_SAMPLES, *IMAGE_SHAPE)
labels  = torch.randint(0, 10, (N_SAMPLES,))
dataset = TensorDataset(images, labels)

cpu_count = os.cpu_count() or 4


def benchmark_loader(loader: DataLoader, n_batches: int) -> float:
    """Return the mean per-batch load time in milliseconds."""
    # Warm up: let worker processes start
    for i, _ in enumerate(loader):
        if i >= 3:
            break

    t0 = time.perf_counter()
    count = 0
    for x, _ in loader:
        count += 1
        if count >= n_batches:
            break
    elapsed = time.perf_counter() - t0
    return elapsed / count * 1_000  # ms


configs = [
    {
        "label": "Config A  num_workers=0  (PyTorch default)",
        "kwargs": dict(batch_size=BATCH_SIZE, num_workers=0, pin_memory=False),
    },
    {
        "label": "Config B  num_workers=2",
        "kwargs": dict(batch_size=BATCH_SIZE, num_workers=2, pin_memory=False),
    },
    {
        "label": "Config C  num_workers=4",
        "kwargs": dict(batch_size=BATCH_SIZE, num_workers=4, pin_memory=False),
    },
    {
        "label": f"Config D  num_workers=4  pin_memory  persistent_workers",
        "kwargs": dict(
            batch_size=BATCH_SIZE,
            num_workers=4,
            pin_memory=True,
            persistent_workers=True,
            prefetch_factor=2,
        ),
    },
]

results = []
for cfg in configs:
    loader  = DataLoader(dataset, **cfg["kwargs"])
    mean_ms = benchmark_loader(loader, N_BATCHES)
    results.append((cfg["label"], mean_ms))

    print(f"  {cfg['label']}")
    print(f"    Mean load time per batch : {mean_ms:.1f} ms")
    if mean_ms > SIMULATED_GPU_MS:
        idle_pct = (mean_ms - SIMULATED_GPU_MS) / mean_ms * 100
        print(f"    GPU would wait           : {idle_pct:.0f}% of the time  ← DATA BOUND")
    else:
        print(f"    Loader faster than GPU ({SIMULATED_GPU_MS:.0f} ms)    ← GPU BOUND ✓")
    print()

# ── Summary table ─────────────────────────────────────────────────────────────
print(SEP)
print(f"  SUMMARY  (GPU compute baseline = {SIMULATED_GPU_MS:.0f} ms / batch)")
print(SEP)
print(f"  {'Configuration':<46} {'ms':>6}  Status")
print(f"  {'-'*46}  {'-'*6}  {'-'*18}")
for label, ms in results:
    tag   = label.split()[0] + " " + label.split()[1]
    state = "GPU idle ←" if ms > SIMULATED_GPU_MS else "GPU bound ✓"
    print(f"  {tag:<46} {ms:>6.1f}  {state}")

print()
print(SEP)
print("  AICR STORAGE QUICK GUIDE")
print(SEP)
print("  /home/$USER")
print("    Quota: 100 GB.  NEVER train from here.")
print("    Slow and shared — impacts other users and your own jobs.")
print()
print("  /scratch/$USER")
print("    Quota: 10 TB.  Good for large sequential reads.")
print("    30-DAY PURGE — move important outputs to /work before the deadline.")
print("    Avoid datasets made of millions of tiny files (use HDF5 or WebDataset).")
print()
print("  /work/neu/$PROJECT")
print("    Longer-term, collaborative storage.  Slower than scratch for I/O.")
print("    Safe from the purge — use this for final model checkpoints.")
print()
print("  $TMPDIR  (node-local storage — check if available on your node)")
print("    Fastest option when available.  Copy your dataset at job start:")
print()
print("      # In your SLURM script, before `python train.py`:")
print("      if [ -d \"$TMPDIR\" ]; then")
print("          echo 'Copying dataset to node-local storage ...'")
print("          rsync -a /scratch/$USER/mydata/ $TMPDIR/mydata/")
print("          DATA_DIR=$TMPDIR/mydata")
print("      else")
print("          DATA_DIR=/scratch/$USER/mydata")
print("      fi")
print("      python train.py --data-dir $DATA_DIR")
print()
print("  DataLoader settings for AICR (starting point):")
print()
print("    from torch.utils.data import DataLoader")
print("    loader = DataLoader(")
print("        dataset,")
print("        batch_size=256,")
print("        num_workers=max(1, cpus_per_task - 1),  # match --cpus-per-task")
print("        pin_memory=True,")
print("        persistent_workers=True,")
print("        prefetch_factor=2,")
print("    )")
print(SEP)
