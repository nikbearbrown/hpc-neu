"""
Script 03 — DataLoader Configuration Benchmark
------------------------------------------------
The NVIDIA V100 on Explorer can finish a training batch in a few milliseconds.
If your data pipeline takes longer than that to deliver the next batch, the
GPU stalls — it holds its VRAM allocation (and your queue time) while doing
absolutely nothing.

This script benchmarks four DataLoader configurations and shows how much of
the GPU's time would be spent waiting under each one.

Explorer storage note:
  All filesystems (/home, /scratch, /projects) are network filesystems (NFS).
  Keep your dataset under /projects/foo or /scratch/$USER, pack it into a few large files
  (HDF5 / WebDataset) rather than millions of tiny ones, and rely on the
  DataLoader (num_workers / pin_memory / prefetch_factor) to hide read latency.

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
# On a V100, a typical ResNet-50 forward+backward on a 64-image batch
# completes in roughly 25–40 ms at FP16.  Adjust this to match your workload.
SIMULATED_GPU_MS = 25.0

SEP = "=" * 62

print(SEP)
print("  DATALOADER CONFIGURATION BENCHMARK — EXPLORER")
print(SEP)
print(f"  Dataset     : {N_SAMPLES:,} synthetic images {IMAGE_SHAPE}")
print(f"  Batches     : {N_BATCHES} × batch_size={BATCH_SIZE}")
print(f"  Simulated GPU compute/batch : {SIMULATED_GPU_MS:.0f} ms  (V100 FP16 estimate)")
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
print("  EXPLORER STORAGE QUICK GUIDE")
print(SEP)
print("  All filesystems here — /home, /scratch, /projects — are network")
print("  filesystems (NFS).  There is no faster local tier to copy into, so")
print("  how you structure the data and the DataLoader is what matters.")
print()
print("  /projects/foo or /scratch/$USER")
print("    Keep your dataset here.  Pack it into a few large files (HDF5 or")
print("    WebDataset) rather than millions of tiny ones — per-file metadata")
print("    overhead over NFS is what kills small-file read throughput.")
print()
print("  /home/$USER")
print("    Small and shared.  Fine for code and configs, not for datasets.")
print()
print("  Let the DataLoader hide read latency:")
print("    raise num_workers, keep pin_memory=True, and set prefetch_factor")
print("    so batches are read ahead while the GPU is busy.")
print()
print("  DataLoader settings for Explorer (starting point):")
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
