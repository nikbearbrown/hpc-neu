
<img src="NU_logo_small.png" alt="Northeastern University" width="900"/>

<br>
<br>

# Research Computing Training

## Presenter

Arsalan Akhter

Research Computing Specialist

[Research Computing](https://rc.northeastern.edu/research-computing-team/)

## GPU Profiling and Performance Optimization on Explorer

Welcome to another session in the [Research Computing Summer 2026 Training Series](https://rc.northeastern.edu/research-computing-summer-training/)!

This session is for anyone who runs GPU jobs on the Explorer cluster and wants to understand whether those jobs are actually running efficiently — and what to do when they are not.

By the end of this training you will be able to:

1. [Confirm that your GPU job got the hardware you requested](#section-1-do-you-even-have-the-gpu)
2. [Read GPU metrics and know what healthy looks like](#section-2-seeing-your-gpu-live-nvidia-smi-and-nvitop)
3. [Choose the right profiling tool for your question](#section-3-the-profiling-toolchain)
4. [Diagnose and fix the most common bottleneck: data starvation](#section-4-the-1-bottleneck-data-starvation)
5. [Understand GPU memory vs utilization and tune both](#section-5-memory-vs-utilization-two-different-problems)
6. [Decide when (and when not) to scale to multiple GPUs](#section-6-when-and-when-not-to-scale-to-multiple-gpus)
7. [Apply a repeatable optimization workflow to any GPU job](#section-7-the-repeatable-optimization-workflow)
8. [Review your efficiency after a run with `gpu-logs`](#section-7-the-repeatable-optimization-workflow)

All materials are available at [GPU Profiling Training GitHub Repo](https://github.com/northeastern-rc-training/gpu-profiling-2026).

You are welcome to follow along. You can also just watch and try it later at your own pace. Recordings will be posted on the [Research Computing website](https://rc.northeastern.edu/research-computing-summer-training/).

---

## Opening: The Question Nobody Asks

You submitted a GPU job. It ran. It finished.

But **was the GPU actually working?**

Many GPU jobs on HPC clusters run at a fraction of what the hardware can actually do. That means a lot of time being wasted — the GPU is sitting idle, waiting, and the researcher's time getting wasted too. The good news: almost all of these inefficiencies have the same small set of causes, and once you learn to **measure** your job rather than guess at it, fixes are usually small changes that take minutes to apply.

> **The one thing to remember from this whole session:**
> **Measure before you change anything. Profile first, optimize second.**

That is the main principle! The training is built around this principle. 


<!---

> 💡 **Presenter note:** Open a second terminal pane now.
> Run `watch -n 1 nvidia-smi` in it (if on a GPU node) and keep it visible during the whole training.
> This turns the training into a live show — the audience can see GPU metrics updating in real time as demos run.

-->

## Prerequisites

Let's get the training materials ready before we start the demos.

1. SSH to Explorer: `ssh username@login.explorer.northeastern.edu`
2. Request an interactive GPU session for the live demos:
   ```bash
   srun --partition=gpu-short \
        --gres=gpu:v100-sxm2:1 \
        --cpus-per-task=4 \
        --mem=16G \
        --time=01:00:00 \
        --pty bash
   ```
3. Navigate to your scratch directory: `cd /scratch/$USER`
4. Clone the training repo:
   ```bash
   git clone https://github.com/northeastern-rc-training/Optimizing-GPU-Usage-on-Explorer
   cd Optimizing-GPU-Usage-on-Explorer/
   ```
5. Set up the Python environment:
   ```bash
   chmod +x setup_env.sh
   ./setup_env.sh
   source gpu_training_env/bin/activate
   which python   # should point to gpu_training_env
   ```

> 💡 **Question for Audience:** Why are we using `srun` here instead of `sbatch`?

The answer: `srun` gives us a live terminal on a compute node. We can run commands, see output immediately, kill and restart without re-queuing. This is the right environment for profiling and development. We use `sbatch` later, once the code is already optimized.

---

## Section 1: Do You Even Have the GPU?

*Build confidence in your setup before measuring anything.*

---

Before any optimization work can happen, you need to be sure your job is actually running on the hardware you requested. This sounds obvious — but it is a surprisingly common source of wasted time.

Here is what can go wrong:

- You request one GPU type but land on another (different memory, different capability)
- CUDA is not available because you are not on a GPU node, or the environment is not activated
- Your code runs on CPU silently, never raising an error

### 1.1 How SLURM Gives You a GPU

The two key directives in any GPU SLURM script are `--gres` and `--partition`.

```bash
#!/bin/bash
#SBATCH --job-name=my_gpu_job
#SBATCH --partition=gpu             # must be a GPU-enabled partition
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8           # CPU cores for data loading workers
#SBATCH --gres=gpu:v100-sxm2:1           # request 1 × V100 specifically
#SBATCH --mem=32G                   # this is CPU RAM, not GPU VRAM
#SBATCH --time=04:00:00
#SBATCH --output=logs/%x_%j.out     # %x = job name, %j = job id
#SBATCH --error=logs/%x_%j.err

mkdir -p logs                       # create the log dir before SLURM writes to it

python train.py
```

A few points worth pausing on:

- `--gres=gpu:v100-sxm2:1` is more specific than `--gres=gpu:1`. The second form may land you on a different GPU type than you expect. Be explicit about the type you want.
- `--mem=32G` is **CPU RAM**, not GPU memory. GPU VRAM is allocated automatically when you get the GPU.
- `--cpus-per-task=8` matters more than most people think. We will see exactly why in Section 4.
- **No CUDA module is needed.** The PyTorch wheels installed by `setup_env.sh` bundle their own CUDA runtime. As long as you are on a GPU node (the NVIDIA driver is always present) with the environment activated, `torch.cuda.is_available()` returns `True`.
- Create the `logs/` directory before submitting (or `mkdir -p logs` inside the script), or SLURM may fail to write its output files.

> 💡 **Tip:** Runnable SLURM templates live in `slurm/` — `v100_single_gpu.slurm` for single-GPU training and `ddp_multigpu.slurm` for multi-GPU DDP. Copy one and edit the values marked `← CHANGE`.

### 1.2 GPU Partitions on Explorer

| Partition | Max time | Best for |
|---|---|---|
| `gpu-short` | 2 hours | Quick tests, profiling, debugging |
| `gpu` | 8 hours | Standard training jobs |
| `multigpu` | 24 hours | Multi-GPU jobs (requires separate access request) |
| `gpu-interactive` | 2 hours | OOD-based development |
| `sharing` | 1 hour | Community-shared GPUs — great for quick tests |

```bash
# See which GPU types are available on a partition
sinfo -p gpu -o "%G"

# See which nodes on a partition are currently free
sinfo -p gpu -O "NodeList,Gres:30,GresUsed:30"
```

> 💡 **Question for Audience:** What GPU types are in the `sharing` partition?
> 
> **Hint:** `sinfo -p sharing -o "%G"`

### 1.3 Verifying at Runtime — Always

Never trust that SLURM gave you what you requested. Add this snippet at the top of every GPU script. It takes two seconds to run and has saved many hours.

```bash
# Demo:
python scripts/01_gpu_verify.py
```

What the script checks:
1. Is CUDA available at all? (If not, likely a module or node issue)
2. How many GPUs, and what are their names and VRAM sizes?
3. What is `CUDA_VISIBLE_DEVICES`? (SLURM sets this automatically)
4. Cross-verify with `nvidia-smi`
5. Quick tensor round-trip: CPU → GPU → CPU

> 💡 **Question for Audience:** If `torch.cuda.is_available()` returns `False` on a compute node, what is the most likely cause?

**Answer:** Most often the training environment is not activated (so Python is falling back to a CPU-only PyTorch), or you are not actually on a GPU node. Activate the venv with `source gpu_training_env/bin/activate` and re-run `scripts/01_gpu_verify.py`. No CUDA module is required — the PyTorch wheels bundle their own CUDA runtime.

### 1.4 The CUDA_VISIBLE_DEVICES Variable

SLURM sets this environment variable to tell your program exactly which GPU indices are allocated to your job. You should **never** override it in your script unless you are deliberately using a subset.

| What you see | What it means |
|---|---|
| `CUDA_VISIBLE_DEVICES=0` | You have GPU 0 (the first one allocated) |
| `CUDA_VISIBLE_DEVICES=0,1` | You have two GPUs |
| `CUDA_VISIBLE_DEVICES=NOT SET` | You are running without SLURM (e.g., interactive `srun`) — this is normal |

> **Section 1 takeaway:** Correct resource allocation is the prerequisite for everything else. Confirm your device, memory, and isolation before measuring anything.

---

## Section 2: Seeing Your GPU Live — nvidia-smi and nvitop

*The dashboard: what healthy looks like.*

---

The fastest profiling tool you have is already installed. It takes 30 seconds and tells you whether you even have a problem worth digging into.

### 2.1 nvidia-smi — The First Thing to Check

```bash
# Static snapshot
nvidia-smi

# Live refresh every 1 second (run in a second terminal pane)
watch -n 1 nvidia-smi
```

**nvidia-smi output explained:**

```
+-----------------------------------------------------------------------------+
| GPU  Name                    | Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage   |         Memory-Usage | GPU-Util  Compute M. |
|=============================================================================|
|   0  NVIDIA A100-SXM4-80GB   | 00000000:03:00.0 Off |                    0 |
| N/A   42C    P0   312W / 400W |  18432MiB / 81920MiB |     87%      Default |
+-----------------------------------------------------------------------------+
```

The two numbers that matter most:

- **GPU-Util 87%** — 87% of the last second had at least one GPU kernel running. This is good. Below 50% is a warning sign.
- **18432MiB / 81920MiB** — memory usage. 22% of total VRAM is in use. This means there is headroom for a larger batch size.

> 💡 **Question for Audience:** If you saw GPU-Util = 15% and Memory = 75%, what problem would you guess you have?

**Answer:** The GPU has memory allocated (model is loaded) but is barely computing. Something on the CPU side is not feeding it work fast enough. This is the data loading problem — and it is the most common problem we will fix in Section 4.

### 2.2 The Two Axes — A Mental Model

Think of GPU utilization and GPU memory as completely independent axes:

```
Memory usage
   High │  Memory-full, compute-idle   │  Healthy: big model, working hard  
        │  (model loaded, not running) │  (target zone: 80-100% util,       
        │                              │   75-90% memory)                   
        │                              │                                     
   Low  │  Empty: GPU doing nothing    │  Good throughput, VRAM headroom    
        │                              │  (increase batch size)              
        └──────────────────────────────┴──────────────────────────────────
                     Low utilization               High utilization
```

You want the upper right. Most inefficient jobs are in the upper left or lower left.

### 2.3 nvitop — A Better Dashboard

```bash
pip install nvitop
nvitop
```

nvitop shows a continuously updated TUI with process-level detail: which Python process is using which GPU, memory trend, power draw, and temperature. It is particularly useful for shared nodes where you want to confirm your job is the one using the GPU.

> **Section 2 takeaway:** Before running any profiling tool, open a second pane and run `watch -n 1 nvidia-smi`. If utilization is below 50%, you already know something is wrong. The rest of the session tells you how to find and fix it.

---

## Section 3: The Profiling Toolchain

*From "something is wrong" to "here is exactly what is wrong."*

---

nvidia-smi tells you *that* there is a problem. To find *where* the problem is, you need a profiler.

### 3.1 Three Layers of GPU Profiling

Different tools answer different questions:

| Layer | Tool | What it answers |
|---|---|---|
| **System / live** | `nvidia-smi`, `nvitop` | Is the GPU busy? How much VRAM? Temperature? |
| **Framework** | PyTorch Profiler, TF Profiler | Which layer or operator is using the most GPU time? |
| **Timeline** | Nsight Systems (`nsys`) | What is every CPU thread and GPU kernel doing, and in what order? |
| **Kernel deep-dive** | Nsight Compute (`ncu`) | Is this specific kernel memory-bound or compute-bound? |

You rarely need to go all the way to the kernel level. Most problems are visible at the system or framework layer.

**Example: how you escalate through the layers in practice**

You run a ResNet training job and `nvidia-smi` shows GPU utilization at 18%. That tells you *something is wrong* — but not what.

1. **System layer** (`nvidia-smi`): utilization 18%, memory 72%. The model is loaded but the GPU is barely working. Probably data starvation.
2. **Framework layer** (PyTorch Profiler): you run 20 steps and read the table. `DataLoader.__next__` is at the top with 1.8 seconds of CPU time and 0 CUDA time. Confirmed: the loader is the bottleneck.
3. **Timeline layer** (`nsys`): you open the `.nsys-rep` file and see the GPU kernel rows are nearly empty — long stretches of white between short orange bursts of compute. The CPU rows show file read system calls consuming the gaps. This tells you the bottleneck is I/O on the dataset, not CPU processing or the model itself.

You never needed to go to the kernel level. The fix — setting `num_workers=8` so data loading overlaps with compute — is visible at layer 2. The nsys timeline just confirms it.

### 3.2 Interactive Sessions: Profile Here, Not in Batch

> 💡 **This is one of the most important workflow habits to build.**

Most people profile by submitting a batch job, waiting in the queue, reading the log, and submitting again. That cycle is slow and discourages iteration.

The better workflow: get an `srun` interactive session, do all your profiling and tuning there, and only submit a `sbatch` job once your code is already well-optimized.

```bash
# Get an interactive GPU session
srun --partition=gpu-short --gres=gpu:v100-sxm2:1 --cpus-per-task=8 --mem=32G \
     --time=01:00:00 --pty bash

# In the session: activate the venv, run your script for 50 steps
source gpu_training_env/bin/activate
python train.py --max-steps 50

# Profile a short window — 20-30 steps is usually enough
nsys profile --output ~/profile_test python train.py --max-steps 30
```

Rule of thumb: if your job runs in under 30 minutes in an `srun` session, do not use `sbatch`. Only switch to batch once you have a tuned script that needs to run for hours.

### 3.3 PyTorch Profiler — The X-Ray

When you want to know which part of your model is the bottleneck, use the built-in PyTorch Profiler. It adds operator-level timing without requiring any external tools.

```bash
# Demo:
python scripts/04_pytorch_profiler_demo.py
```

The key pattern: profile a small window (10–20 steps), not the whole run.

```python
from torch.profiler import profile, record_function, ProfilerActivity

with profile(
    activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA],
    record_shapes=True,
    on_trace_ready=torch.profiler.tensorboard_trace_handler('./prof')
) as prof:
    for step, (x, y) in enumerate(dataloader):
        if step == 20: break          # ← small window only
        out  = model(x)
        loss = criterion(out, y)
        loss.backward()
        optimizer.step()
        prof.step()

# Print top operators by GPU time
print(prof.key_averages().table(sort_by='cuda_time_total', row_limit=15))
```

**Example — profiler output from a data-starved run:**

```
-----------------------------------------------  -----------  -----------  ------
Name                                             CPU total    CUDA total   Calls
-----------------------------------------------  -----------  -----------  ------
DataLoader.__next__                              1.843s       0.000s       20
aten::conv2d                                     0.041s       0.394s       160
aten::batch_norm                                 0.019s       0.087s       160
aten::relu_                                      0.007s       0.029s       160
aten::copy_ (host to device)                     0.017s       0.052s       20
aten::addmm                                      0.011s       0.038s       40
-----------------------------------------------  -----------  -----------  ------
```

`DataLoader.__next__` is at the top with **1.843 seconds of CPU time and zero CUDA time**. During every one of those 20 load calls, the GPU was completely idle. Total GPU compute time across all operators is under 0.6 seconds. The GPU is busy for roughly 25% of wall time — which matches the 25% utilization you saw in `nvidia-smi`.

**Example — profiler output from the same model after fixing the DataLoader:**

```
-----------------------------------------------  -----------  -----------  ------
Name                                             CPU total    CUDA total   Calls
-----------------------------------------------  -----------  -----------  ------
aten::conv2d                                     0.041s       0.394s       160
aten::batch_norm                                 0.019s       0.087s       160
aten::relu_                                      0.007s       0.029s       160
aten::addmm                                      0.011s       0.038s       40
aten::copy_ (host to device)                     0.017s       0.052s       20
DataLoader.__next__                              0.024s       0.000s       20
-----------------------------------------------  -----------  -----------  ------
```

Now `DataLoader.__next__` has dropped to 0.024 seconds — it prefetches the next batch in background workers while the GPU processes the current one. Compute operators dominate. `nvidia-smi` will now show 80%+ utilization.

**How to read the profiler table:**

- `Name` — the operator or function. Your custom `record_function("my_layer")` labels appear here.
- `CUDA total` — total GPU time spent in this operator across all profiled steps.
- `CPU total` — total CPU wall time. If this is much larger than CUDA total, the work is not properly on the GPU.
- `Self CPU` — time in this operator excluding its children. Helps isolate where time is spent.

**What to look for (in order of importance):**
1. Gaps between GPU kernels on the timeline → GPU is idle, CPU is not feeding it fast enough
2. Large `aten::copy_` entries → data being moved between CPU and GPU frequently
3. CPU time >> CUDA time → computation not offloaded to GPU
4. DataLoader or data-related functions appearing at the top → data pipeline bottleneck

### 3.4 Nsight Systems — The Full Timeline

For problems that require understanding the *order* of events — CPU threads, GPU kernels, memory copies, and NCCL communication all on one timeline — use Nsight Systems:

```bash
nsys profile \
  --trace=cuda,nvtx,osrt,cudnn,cublas \
  --output=/scratch/$USER/profile_%p \
  python train.py --epochs 2

# Transfer the .nsys-rep file to your laptop for GUI inspection
scp cluster:/scratch/$USER/profile_*.nsys-rep ./
```

> **Important:** Profile for only 1–2 epochs or use `--duration` to limit capture time. A full 100-epoch profile produces gigabyte-sized files and is difficult to analyze.

**What common problems look like in the nsys timeline:**

When you open the `.nsys-rep` file in the Nsight Systems GUI, you see horizontal rows — one per CPU thread and one per GPU stream. Here is what to look for:

| Pattern you see on the timeline | What it means | Fix |
|---|---|---|
| GPU row is mostly white with short orange bursts | GPU is idle between batches — data not arriving fast enough | Increase `num_workers` and `prefetch_factor` |
| CPU rows show `read()` system calls filling the gaps between GPU kernels | I/O bottleneck — data is being read from the network filesystem during training | Increase `num_workers`/`prefetch_factor` so reads overlap compute; store data as a few large files, not millions of tiny ones |
| `cudaMemcpy HtoD` calls appear scattered throughout the step, not at the beginning | Tensors are being moved to GPU inside the training loop, not in the DataLoader | Add `pin_memory=True`, do `.to(device)` in the DataLoader worker |
| GPU row is dense (orange), but a periodic gap appears every N steps | Gradient synchronization stall in multi-GPU training | Tune `--nproc_per_node`, overlap communication with `find_unused_parameters=False` |
| Two GPU streams alternate — one idle while the other runs | Forward and backward passes not overlapping | This is normal for single-GPU DDP; only a concern in pipeline parallelism |

**Concrete example:** You run `nsys profile` on a training job and open the report. The GPU kernel row (CUDA HW row) shows orange activity for about 15ms, then a 50ms white gap, then 15ms of orange again. That 50ms gap is the GPU waiting for the next batch. You hover over the CPU thread row and see `pthread` calls to `read()` filling that gap — confirming the data is being read from the network filesystem during training. Fix: raise `num_workers` and `prefetch_factor` so batches are loaded ahead of time and overlap with compute. After the fix, the white gaps shrink to under 5ms.

> **Section 3 takeaway:** Start with nvidia-smi. If utilization is low, run the PyTorch Profiler for 20 steps. Read the CUDA time column. The biggest entry there is where you should look first.

---

## Section 4: The #1 Bottleneck — Data Starvation

*Why your GPU sits idle most of the time, and what to do about it.*

---

The single most common cause of low GPU utilization in training jobs is not bad model code. It is a data pipeline that cannot keep up with the GPU.

Let's understand why this happens before we fix it.

### 4.1 The Factory Floor Analogy

Imagine a high-speed factory floor (the GPU). It can process a batch of products in 15 milliseconds. But the supply truck (the CPU data loader) takes 60 milliseconds to deliver the next batch.

The factory has to stop and wait. The workers are ready. The machines are ready. But there is nothing to process.

For 45 of every 60 milliseconds, the GPU is idle — not because of anything wrong with the model or the GPU itself. The bottleneck is the supply chain.

```python
# The simple diagnostic: time the loader vs. time the compute

import time, torch

# Step 1: Time just the data loading (no GPU work)
t0 = time.perf_counter()
for i, (x, y) in enumerate(loader):
    if i == 50: break
loader_ms = (time.perf_counter() - t0) / 50 * 1000
print(f'Mean batch load time: {loader_ms:.1f} ms')

# Step 2: Time just the compute (synthetic data, no loading)
dummy_x = torch.randn(256, 3, 224, 224, device='cuda')
t0 = time.perf_counter()
for _ in range(50):
    out = model(dummy_x)
    loss = out.sum()
    loss.backward()
    torch.cuda.synchronize()
compute_ms = (time.perf_counter() - t0) / 50 * 1000
print(f'Mean compute time:    {compute_ms:.1f} ms')

# If loader_ms > compute_ms, you are DATA BOUND
```

> If `compute_ms` is 25 ms and `loader_ms` is 60 ms, your GPU is idle for 35 of every 60 ms — that is 58% wasted GPU time. No amount of model optimization recovers that. Fix the loader first.

### 4.2 DataLoader Parameters — The Four Knobs

A **DataLoader** (PyTorch's `torch.utils.data.DataLoader`) is the component that feeds your model. It takes a `Dataset` and handles the plumbing between disk and GPU: reading samples, collating them into batches, shuffling, and — crucially — doing this work on **CPU worker processes in parallel** so the next batch is ready before the GPU finishes the current one.

Why it matters for utilization: a GPU can only train as fast as it is fed. If data loading is serial (the default, `num_workers=0`), the GPU sits idle waiting for each batch — the data starvation we just diagnosed. The four knobs below control how aggressively the DataLoader prefetches and parallelises that work, and tuning them is usually the highest-leverage, lowest-effort fix for low GPU utilization.

```python
from torch.utils.data import DataLoader

loader = DataLoader(
    dataset,
    batch_size=256,
    num_workers=8,            # ← CPU worker processes for parallel loading
    pin_memory=True,          # ← allocate in page-locked RAM for fast GPU transfer
    persistent_workers=True,  # ← keep workers alive between epochs
    prefetch_factor=4,        # ← batches each worker pre-loads ahead of time
)
```

What each parameter does:

- **`num_workers`** — spawns separate CPU processes that load data in parallel while the GPU runs the previous batch. Default is `0` (single-process, almost always wrong). Set to roughly `cpus-per-task - 1`.

- **`pin_memory=True`** — allocates CPU tensors in page-locked memory, allowing the GPU's DMA engine to transfer data directly without an intermediate copy. Reduces host-to-device transfer latency by 20–40%.

- **`persistent_workers=True`** — avoids the overhead of spawning and terminating worker processes between epochs. On HPC, process spawning through a job scheduler is expensive.

- **`prefetch_factor`** — each worker pre-loads this many batches into the pin-memory buffer. Trades CPU memory for reduced GPU idle time.

```bash
# Demo: compare DataLoader configurations
python scripts/03_dataloader_benchmark.py
```

### 4.3 Batching: Never Process One Sample at a Time

This is the complementary problem to data starvation: if your code sends individual samples to the GPU in a loop, you are wasting the hardware even when the data is available.

```bash
# Demo: one-by-one vs. batched processing
python scripts/02_naive_vs_batched.py
```

Every GPU call has a fixed overhead: kernel launch cost, PCIe transfer setup, synchronization. When you process 10,000 samples one at a time, you pay that overhead 10,000 times. When you batch them, you pay it once.

**Real-world impact on GPU utilization:**

| Configuration | GPU Utilization | Images/sec (ResNet-50, A100) |
|---|---|---|
| `num_workers=0`, no `pin_memory` | ~18% | ~420 |
| `num_workers=8`, `pin_memory=True` | ~55% | ~1,300 |
| `num_workers=8`, `pin_memory=True`, `prefetch_factor=4` | ~82% | ~1,950 |

> **For GROMACS / pre-built software users:** Your software already handles batching internally. If your job is I/O bound (reading topology files, writing trajectories), store your data as a few large files rather than millions of small ones — the network filesystem handles large sequential reads far better than many tiny ones.

> **Section 4 takeaway:** GPU utilization below 70% almost always points to the data pipeline, not the model. Fix the DataLoader parameters first — `num_workers`, `pin_memory`, `prefetch_factor`, `persistent_workers`. These require zero modifications to your model code.

---

## Section 5: Memory vs Utilization — Two Different Problems

*Two numbers on the nvidia-smi dashboard that look similar and mean completely different things.*

---

`nvidia-smi` reports two percentages: GPU utilization and memory usage. They are independent, and confusing them leads to applying the wrong fix.

### 5.1 What Each Number Means

| Metric | What it measures | Low is bad because | High is bad because |
|---|---|---|---|
| **GPU Utilization %** | Fraction of last second that a GPU kernel was running | GPU is idle — starved by CPU or data pipeline | Not inherently bad; 100% sustained means compute-bound |
| **Memory Usage %** | Fraction of VRAM currently allocated | Unused VRAM that could hold larger batches | OOM errors; forces small batches that reduce throughput |

The target zone: **utilization 80–100%, memory 75–90%.**

```
What you see in nvidia-smi → What it means → What to do
─────────────────────────────────────────────────────────
Low util  + Low  memory  →  GPU sitting empty       →  Check data pipeline (Section 4)
Low util  + High memory  →  Model loaded, not working →  Check data pipeline or sync issues
High util + Low  memory  →  Healthy, but underutilized VRAM  →  Increase batch size
High util + High memory  →  Healthy, working hard    →  You are in good shape
OOM error               →  Batch too large           →  Reduce batch, mixed precision, or checkpointing
```

### 5.2 Tuning Batch Size — The Simplest Lever

Batch size directly controls both memory usage and GPU utilization. Doubling the batch size roughly doubles throughput until you become compute-bound — as long as you have the VRAM.

A common mistake: using a very small batch size "to be safe" when there is plenty of VRAM available. If `nvidia-smi` shows memory at 20% and you are not OOM, double your batch size.

```python
# Quick binary search to find your maximum batch size
def test_batch_size(model, bs, input_shape=(3, 224, 224)):
    try:
        x = torch.randn(bs, *input_shape, device='cuda')
        y = model(x)
        y.sum().backward()
        torch.cuda.empty_cache()
        return True
    except torch.cuda.OutOfMemoryError:
        torch.cuda.empty_cache()
        return False

lo, hi = 1, 2048
while lo < hi:
    mid = (lo + hi + 1) // 2
    if test_batch_size(model, mid):
        lo = mid
    else:
        hi = mid - 1
print(f'Max batch size that fits: {lo}')
```

### 5.3 Mixed Precision — One Flag, Significant Speedup

By default, PyTorch uses 32-bit floats (FP32) for everything. Modern GPUs have dedicated hardware (Tensor Cores) that operates at much higher throughput in 16-bit formats.

Switching to BF16 (recommended on A100/H100):
- Roughly **halves activation memory** → fits a larger batch in the same VRAM
- Unlocks **Tensor Core throughput** → up to 8× faster matrix operations than FP32
- Requires **three lines of code change**

```python
from torch.amp import autocast

# Before (FP32)
out  = model(x)
loss = criterion(out, y)
loss.backward()

# After (BF16 — add just this wrapper)
with autocast(device_type='cuda', dtype=torch.bfloat16):
    out  = model(x)
    loss = criterion(out, y)
loss.backward()   # gradients automatically stay in FP32
```

**Which precision should you use on Explorer?**

| Precision | Bytes (exp/mantissa) | When to use on Explorer | Key tradeoff |
|---|---|---|---|
| FP32 | 4 (8 / 23) | Debugging / baseline only | Full precision + range, but slowest and 2× the memory of 16-bit; the baseline to compare against |
| BF16 | 2 (8 / 7) | **Default on A100 / H100** | Keeps FP32's range (no `GradScaler`) but coarser precision — safe because master weights and reductions stay FP32 |
| FP16 | 2 (5 / 10) | V100 / T4 (no BF16 hardware) | More mantissa than BF16, but a 5-bit exponent underflows → **requires `GradScaler`** |

> **Tradeoffs in one line:** every step down from FP32 trades **numerical quality for speed and memory** — but it is not a simple "lower is better" progression. A few things to keep in mind:
>
> - **Range vs. precision.** A 16-bit format must split its bits between exponent (range) and mantissa (precision). BF16 keeps FP32's 8 exponent bits (so gradients don't underflow → no `GradScaler`), at the cost of precision. FP16 makes the opposite bet: more precision, but a 5-bit exponent that underflows and *forces* loss scaling. On A100/H100, BF16's bet is the right one.
> - **"Mixed" precision is the safety net.** BF16 training is only stable because the risky parts stay in FP32 — master weights, the loss, softmax, and normalization reductions. `autocast` handles this automatically; casting *everything* to BF16 would often diverge.
> - **Memory savings are partial.** BF16 roughly halves *activation* memory, but FP32 master weights + Adam optimizer states are unchanged, so total VRAM does not drop by a full 2×.
> - **Speedup is op-dependent.** The Tensor Core speedup applies to matmuls and convolutions; memory-bound or elementwise ops see little benefit.

```bash
# Demo: FP32 vs BF16 memory and throughput
python scripts/05_mixed_precision_demo.py
```

### 5.4 When Memory Is Still Too Tight — Gradient Checkpointing

If you are training a very large model and even mixed precision is not enough to fit a reasonable batch, gradient checkpointing trades extra compute for reduced memory:

- During the forward pass, **activations are not stored** — they are recomputed on demand during backpropagation
- Typically reduces activation memory by **60–70%** at the cost of **~30% extra compute**

```python
# For Hugging Face Transformers models — one flag:
model.gradient_checkpointing_enable()

# For custom PyTorch modules:
from torch.utils.checkpoint import checkpoint

class MyBlock(torch.nn.Module):
    def forward(self, x):
        return checkpoint(self.expensive_layers, x, use_reentrant=False)
```

Use this when your batch size is forced below 8 due to VRAM, or when fine-tuning a 7B+ parameter model on a single GPU.

### 5.5 Monitoring Memory During a Run

```bash
# Demo: watch memory grow through a training run
python scripts/06_memory_monitor.py
```

```python
# Add to your training script to log peak memory per epoch
torch.cuda.reset_peak_memory_stats()
# ... epoch training loop ...
peak  = torch.cuda.max_memory_allocated() / 1024**3
total = torch.cuda.get_device_properties(0).total_memory / 1024**3
print(f'Peak VRAM: {peak:.1f} GB / {total:.1f} GB  ({100*peak/total:.0f}%)')
```

> **Section 5 takeaway:**
> - Low utilization + high memory → data pipeline or sync issue.
> - High utilization + low memory → increase batch size.
> - OOM → reduce batch size, enable mixed precision, or add gradient checkpointing.

---

## Section 6: When (and When Not) to Scale to Multiple GPUs

*Why 4 GPUs is not 4× faster, and when it actually helps.*

---

Multi-GPU training is often the first thing people reach for when a job is slow. It is frequently the wrong move — not because multi-GPU does not work, but because it multiplies whatever efficiency you already have. A job at 20% single-GPU efficiency becomes a 4-GPU job at 20% efficiency — except now it uses four times the allocation.

### 6.1 The Rule: 80% First

| Scenario | Multi-GPU useful? | Why |
|---|---|---|
| Single-GPU utilization already >80% | Yes | You are compute-bound; adding GPUs divides the work |
| Single-GPU utilization <60% | **No** | Fix the single-GPU bottleneck first |
| Model does not fit in one GPU's VRAM | Yes — required | Tensor or pipeline parallelism needed |
| Job is I/O bound (data loading) | **No** | N GPUs compete for the same filesystem — makes I/O worse |

> **Before you request multiple GPUs:** run your job with one GPU, check utilization with nvidia-smi. If it is below 70%, you have a bottleneck that multi-GPU will not fix. Work through Sections 4 and 5 first.

### 6.2 How Data-Parallel Training Works — The Core Idea

In data-parallel training, each GPU gets a copy of the full model. Each GPU processes a different mini-batch. After the forward and backward passes, all GPUs must agree on a single averaged gradient before the optimizer step. This synchronization step is called an **all-reduce**.

```
GPU 0: process batch A → gradients A
GPU 1: process batch B → gradients B    →  all-reduce  →  average gradient
GPU 2: process batch C → gradients C                      (every GPU gets this)
GPU 3: process batch D → gradients D

Each GPU then runs its optimizer step with the same averaged gradient.
Model copies stay in sync.
```

The cost of the all-reduce grows with model size and shrinks with interconnect bandwidth. NVLink-connected nodes within a single server are much faster than going between nodes over InfiniBand.

### 6.3 DDP in PyTorch

DistributedDataParallel (DDP) is the correct way to do data-parallel training in PyTorch. Do not use the older `DataParallel` — it has GIL contention and is slower.

**First, confirm your code is actually written for DDP.** If you run a plain PyTorch script with `--gres=gpu:v100-sxm2:4`, SLURM allocates 4 GPUs but your code will only use the first one — `model.cuda()` moves the model to device 0 and the other three sit idle (and drag down your efficiency).

```python
# Quick check: does this process participate in a DDP group?
import torch, torch.distributed as dist
print(dist.is_available())          # must be True
print(dist.is_initialized())        # must be True *after* dist.init_process_group()
print(torch.cuda.device_count())    # should match --gres=gpu:N
```

```python
# launch_ddp.py — called via torchrun, not python directly
import torch, torch.distributed as dist, os
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data.distributed import DistributedSampler

dist.init_process_group('nccl')
rank  = dist.get_rank()
local = int(os.environ['LOCAL_RANK'])
torch.cuda.set_device(local)

model   = MyModel().cuda(local)
model   = DDP(model, device_ids=[local])      # wrap AFTER moving to device

sampler = DistributedSampler(dataset)         # ensures no overlap between GPUs
loader  = DataLoader(dataset, sampler=sampler, batch_size=256)

for epoch in range(epochs):
    sampler.set_epoch(epoch)                  # re-shuffle each epoch
    for x, y in loader:
        ...                                   # same as single-GPU from here
```

```bash
# SLURM script for a 4-GPU single-node job
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4
#SBATCH --gres=gpu:v100-sxm2:4
#SBATCH --cpus-per-task=8

torchrun --nproc_per_node=4 launch_ddp.py
```

### 6.4 Measuring Scaling Efficiency

You should always measure whether adding GPUs gave you proportional speedup.

```python
# At the end of one epoch (rank 0 only):
if dist.get_rank() == 0:
    throughput = len(dataset) / elapsed_seconds
    efficiency = throughput / (world_size * single_gpu_throughput) * 100
    print(f'N={world_size}  {throughput:.0f} samples/sec  '
          f'scaling efficiency: {efficiency:.0f}%')
```

Good: >80% scaling efficiency. Below 70% means communication or I/O is the bottleneck, not compute.

> **Section 6 takeaway:** Multi-GPU amplifies efficiency — it does not create it. Reach 80%+ single-GPU utilization first. Then scale, request NVLink nodes when available, and measure scaling efficiency explicitly.

---

## Section 7: The Repeatable Optimization Workflow

*A checklist that applies to any GPU job, any framework, any domain.*

---

Every section in this training addressed a different bottleneck. In practice, these bottlenecks appear in roughly the same order of frequency and ease of fix. The workflow below gives you a repeatable process to work through them.

### 7.1 The Optimization Loop

Fix one thing at a time, and measure before and after each change. Fixing two things simultaneously makes it impossible to know what helped.

| Step | Action | Tool |
|---|---|---|
| 1. **Baseline** | Run your job, record throughput (samples/sec) and GPU utilization | `nvidia-smi`, `time` |
| 2. **Profile** | Capture a short profile to find the dominant bottleneck | PyTorch Profiler, `nsys` |
| 3. **Diagnose** | Classify: data loading? Memory? Compute? Communication? | Sections 4–6 |
| 4. **Fix one thing** | Apply the highest-impact change | Code or SLURM change |
| 5. **Re-profile** | Run the profiler again — did the bottleneck move? | Same tools |
| 6. **Record the gain** | Compare to baseline | Log or spreadsheet |
| 7. **Repeat** | Continue until diminishing returns | — |

### 7.2 Decision Guide: Which Section Applies?

```
GPU utilization < 50% ?
  ├─ Yes → Check data pipeline first (Section 4)
  │         Are you using num_workers=0? Fix that first.
  │         Then raise pin_memory / prefetch_factor / persistent_workers.
  │
  └─ No (util 50–80%) → Check memory usage
        ├─ Memory < 50% → Increase batch size (Section 5.2)
        ├─ Memory 50–85% → Try mixed precision (Section 5.3)
        ├─ Memory > 90% → Reduce batch / checkpointing (Section 5.4)
        └─ Memory looks fine → Profile with PyTorch Profiler (Section 3.3)

Util > 80% and memory looks healthy?
  └─ You are in good shape. Consider multi-GPU only if single GPU is truly saturated.

OOM error?
  └─ Reduce batch size → enable mixed precision → gradient checkpointing (in this order)
```

### 7.3 gpu-logs — Your Post-Job Efficiency Report

Explorer provides **`gpu-logs`**, a post-job tool that reports the time-series of GPU utilization over your entire run. It is the post-job equivalent of watching `watch -n 1 nvidia-smi` live during the job.

```bash
gpu-logs <jobid>

# Example
gpu-logs 2374457
```

What to look for:
- **Average GPU utilization** over the whole job — target > 70%.
- **The shape of the curve.** A flat, high line is healthy. A line that bounces between low values is data starvation. A flat, low line means the workload is too small for the GPU.
- **Average VRAM** — low usage means you have headroom for a larger batch.

**Make reviewing `gpu-logs` a habit:**

> After every batch job → run `gpu-logs <jobid>` → if average GPU utilization < 60%, fix it before submitting the next run.

### 7.4 Pre-Submission Checklist

Before submitting any GPU batch job, verify these items — ideally in an `srun` session first:

- [ ] `scripts/01_gpu_verify.py` passes — you confirmed device name and VRAM
- [ ] `nvidia-smi` during a short run shows utilization > 70%
- [ ] `num_workers` in DataLoader is set (not 0) and equals `cpus-per-task - 1`
- [ ] `pin_memory=True` is set in DataLoader
- [ ] `prefetch_factor` / `persistent_workers` set so loading overlaps compute
- [ ] Batch size uses at least 50% of VRAM (not leaving large amounts unused)
- [ ] Mixed precision enabled if on A100/H100 (just three lines of code)
- [ ] SLURM script requests the right GPU type (`gpu:v100-sxm2:1`, not just `gpu:1`)
- [ ] `--cpus-per-task` is at least 4 (preferably matching `num_workers + 1`)
- [ ] `logs/` directory exists (or `mkdir -p logs` in the script)
- [ ] You have profiled for 20–50 steps and read the output

### 7.5 HPC Hygiene Tips

**Use `srun` for profiling and development.** Only use `sbatch` once your code is tuned and needs to run for hours.

**Profile a short window.** 20–50 training steps gives you a representative profile. A full-run profile produces enormous files and is harder to read.

**One change at a time.** The most common mistake in optimization is changing three things at once and not knowing which one helped.

**Record your baselines.** Before any optimization, write down: GPU utilization, throughput in samples/sec, wall time. Without a baseline, you cannot measure improvement.

**Review `gpu-logs <jobid>` after every batch job** to confirm the run actually used the GPU (see Section 7.3).

**The profiling mindset.** Spending 10 minutes profiling saves hours of wasted compute and queue time. Frame it as an investment, not overhead.

---

## Section 8: Connecting to Your Work

*Bringing it back to your specific domain.*

---

The concepts in this training apply regardless of what software you run on the GPU. Here is how they map to common research domains on Explorer:

### Machine Learning / Deep Learning (PyTorch, TensorFlow)

Every section of this training applies directly. The scripts in `scripts/` demonstrate these patterns in runnable form. Start with `01_gpu_verify.py` and `04_pytorch_profiler_demo.py`.

### Pre-built ML software (Hugging Face, FastAI, scikit-learn with GPU backends)

- Sections 1, 2, and 4 apply directly — verify your device, watch utilization, check data storage.
- For Hugging Face Transformers, mixed precision and gradient checkpointing are one flag each:
  ```python
  training_args = TrainingArguments(
      bf16=True,                        # Section 5.3
      gradient_checkpointing=True,      # Section 5.4
      dataloader_num_workers=8,         # Section 4.2
      ...
  )
  ```

### Molecular Dynamics (GROMACS, NAMD, AMBER)

- Section 1 applies: verify the right GPU is allocated.
- Section 4 applies: MD codes are often I/O bound on trajectory writes. Write fewer, larger output files and reduce write frequency where you can — the network filesystem handles large sequential I/O far better than frequent small writes.
- Section 6 applies: multi-GPU MD scales well within a node using NVLink but degrades quickly across nodes over InfiniBand for small systems. Measure scaling efficiency.
- `nvidia-smi` and `nvitop` are your primary monitoring tools — the profilers in Section 3 are not applicable to GPU-accelerated MD in the same way.

### Custom CUDA / GPU code

All sections apply. The kernel-level tool (Nsight Compute) becomes relevant — it shows roofline analysis, warp occupancy, and memory bandwidth utilization per kernel.

---

## How to Get Help

Email the Research Computing team at [rchelp@northeastern.edu](mailto:rchelp@northeastern.edu).

Come to [office hours](https://rc.northeastern.edu/getting-help/) hosted on Zoom.

Or [book a consultation](https://rc.northeastern.edu/getting-help/) with an RC team member.

Review our [Documentation](https://rc-docs.northeastern.edu/en/latest/index.html).

---

## Quick Reference Card

| Problem | First thing to try | Script |
|---|---|---|
| Not sure if GPU is allocated | Run the verify script | `scripts/01_gpu_verify.py` |
| Utilization < 50% | Check `num_workers`, check storage tier | `scripts/03_dataloader_benchmark.py` |
| Slow inference / one-by-one loop | Batch your inputs | `scripts/02_naive_vs_batched.py` |
| Want to know which layer costs the most | PyTorch Profiler | `scripts/04_pytorch_profiler_demo.py` |
| OOM / want to fit larger batch | Enable mixed precision | `scripts/05_mixed_precision_demo.py` |
| Want to watch memory during training | Memory monitor | `scripts/06_memory_monitor.py` |
| Reviewing a finished batch job | gpu-logs guide | `scripts/07_gpu_logs_guide.py` |

---

## Explorer at a Glance (Reference)

| Item | Value |
|---|---|
| Login | `ssh <username>@login.explorer.northeastern.edu` |
| GPU partitions | `gpu-short` (2 h), `gpu` (8 h), `multigpu` (24 h), `gpu-interactive` (2 h), `sharing` (1 h) |
| GPU types | NVIDIA V100 (32 GB), A100 (80 GB) |
| GPU runtime | Bundled with the PyTorch CUDA wheels — no CUDA module needed |
| Python | system `python3` on PATH (no python module) |
| Environment | `venv` (`gpu_training_env`) |
| Storage | `/home`, `/scratch`, `/projects` (all network filesystems / NFS) |
| Post-job efficiency | `gpu-logs <jobid>` |
| Preferred precision | BF16 on A100/H100; FP16 on V100/T4 |

---

Thank you!

*For questions or support, contact the Research Computing team at [rchelp@northeastern.edu](mailto:rchelp@northeastern.edu)*
