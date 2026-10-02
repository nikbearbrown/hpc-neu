"""
Script 04 — PyTorch Profiler Demo
-----------------------------------
nvidia-smi tells you THAT the GPU is idle.  The PyTorch Profiler tells you
WHERE time is going — which operators, which layers, how much was CPU vs GPU.

This script trains a small CNN for a few steps with the profiler active and
prints the results in two tables: top operators by CPU time and by CUDA time.
A TensorBoard trace is also saved so you can explore the full timeline.

Explorer workflow note:
  Run profiling sessions in an interactive slot on a short partition
  (gpu-short / gpu-interactive), NOT in a long batch job.  Get an srun shell,
  profile a short window, fix the bottleneck, and only then submit the tuned
  job to the `gpu` or `multigpu` partition with sbatch.

Usage:
    srun --partition=gpu-short --gres=gpu:v100-sxm2:1 --cpus-per-task=4 --mem=16G \
         --time=01:00:00 --pty bash
    source gpu_training_env/bin/activate
    python scripts/04_pytorch_profiler_demo.py

Works on CPU too (CUDA tables will be absent; useful for testing the script).
TensorBoard trace → ./prof_output/
"""

import os
import torch
import torch.nn as nn
from torch.profiler import ProfilerActivity, profile, record_function
from torch.utils.data import DataLoader, TensorDataset

DEVICE        = "cuda" if torch.cuda.is_available() else "cpu"
BATCH_SIZE    = 32
PROFILE_STEPS = 10    # short window — 10–20 steps is always enough

SEP = "=" * 62

print(SEP)
print("  PYTORCH PROFILER DEMO — EXPLORER")
print(SEP)
print(f"  Device        : {DEVICE}")

if DEVICE == "cuda":
    p = torch.cuda.get_device_properties(0)
    print(f"  GPU           : {p.name}  ({p.total_memory / 1024**3:.1f} GB)")

print(f"  Profile steps : {PROFILE_STEPS}")
print()


# ── A small CNN with labelled sections ────────────────────────────────────────
class TinyCNN(nn.Module):
    """Small CNN representative of typical image-classification workloads."""

    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.pool  = nn.AdaptiveAvgPool2d((4, 4))
        self.fc    = nn.Linear(64 * 4 * 4, 10)
        self.relu  = nn.ReLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        with record_function("conv_block_1"):
            x = self.relu(self.conv1(x))
        with record_function("conv_block_2"):
            x = self.relu(self.conv2(x))
        with record_function("pool_and_classify"):
            x = self.pool(x)
            x = x.view(x.size(0), -1)
            x = self.fc(x)
        return x


model     = TinyCNN().to(DEVICE)
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
criterion = nn.CrossEntropyLoss()

images = torch.randn(200, 3, 32, 32)
labels = torch.randint(0, 10, (200,))
loader = DataLoader(TensorDataset(images, labels), batch_size=BATCH_SIZE)

# ── Profiler setup ────────────────────────────────────────────────────────────
activities = [ProfilerActivity.CPU]
if DEVICE == "cuda":
    activities.append(ProfilerActivity.CUDA)

os.makedirs("prof_output", exist_ok=True)

# ── Warm up CUDA BEFORE profiling ─────────────────────────────────────────────
# The first CUDA calls trigger one-time kernel/module loading (you'd see it as a
# huge "Runtime Triggered Module Loading" row that dwarfs the real compute).  A
# few untimed steps burn that cost off so the tables below reflect the model's
# actual work, not startup overhead.
if DEVICE == "cuda":
    print("Warming up CUDA (loading kernels) ...")
    for _ in range(3):
        wx = torch.randn(BATCH_SIZE, 3, 32, 32, device=DEVICE)
        model(wx).sum().backward()
    optimizer.zero_grad(set_to_none=True)
    torch.cuda.synchronize()

# Schedule: skip 1 step (wait), warm up for 1 step, then profile PROFILE_STEPS
schedule = torch.profiler.schedule(wait=1, warmup=1, active=PROFILE_STEPS)

print(f"Running {PROFILE_STEPS + 2} training steps with profiler active ...")
print()

with profile(
    activities=activities,
    schedule=schedule,
    record_shapes=True,
    profile_memory=True,
    with_stack=False,
    on_trace_ready=torch.profiler.tensorboard_trace_handler("./prof_output"),
) as prof:
    for step, (x, y) in enumerate(loader):
        if step >= PROFILE_STEPS + 2:
            break
        x, y = x.to(DEVICE), y.to(DEVICE)
        optimizer.zero_grad(set_to_none=True)

        with record_function("forward"):
            out  = model(x)
            loss = criterion(out, y)
        with record_function("backward"):
            loss.backward()
        with record_function("optimizer_step"):
            optimizer.step()

        prof.step()

# ── Print results ─────────────────────────────────────────────────────────────
print(SEP)
print("  TOP OPERATORS — CPU TIME")
print(SEP)
print(prof.key_averages().table(sort_by="cpu_time_total", row_limit=12))

if DEVICE == "cuda":
    print(SEP)
    print("  TOP OPERATORS — CUDA (GPU) TIME")
    print(SEP)
    print(prof.key_averages().table(sort_by="cuda_time_total", row_limit=12))

print()
print(SEP)
print("  HOW TO READ THE TABLE")
print(SEP)
print("  Name        : the PyTorch operator or your record_function() label")
print("  CPU total   : total CPU wall time across all profiled steps")
print("  CUDA total  : total GPU kernel time for this operator")
print("  Self CPU    : time in this op excluding time in its children")
print()
print("  WHAT TO LOOK FOR (in order of priority):")
print("  1. Gaps on the CUDA timeline → GPU is idle between batches")
print("     This points to the data pipeline (Section 4 of the training).")
print("  2. Large `aten::copy_` entries → data shuffled between CPU and GPU")
print("     frequently.  Pin your tensors or pre-load to GPU memory.")
print("  3. CPU total >> CUDA total → computation not offloaded to the GPU.")
print("     Check that tensors are on the right device (.to(DEVICE)).")
print("  4. DataLoader-related functions at the top of the CPU table →")
print("     data pipeline bottleneck — tune num_workers and pin_memory.")
print()
print("  NOTE: this is a teaching demo, not a before/after benchmark.  It runs a")
print("  tiny CNN on synthetic in-memory data, so it has NO bottleneck to fix —")
print("  the point is to learn what the tables look like and how to read them.")
print("  On a real job, the top rows will point you at the actual problem.")
print()
print(f"  TensorBoard trace saved → ./prof_output/")
print("  To view the interactive timeline:")
print("    tensorboard --logdir ./prof_output")
print("  Then open http://localhost:6006 in your browser")
print("  (or set up an SSH tunnel from your laptop to the login node).")
print(SEP)
