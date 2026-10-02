<img src="NU_logo_small.png" alt="Northeastern University" width="900"/>

<br>
<br>

# AI Compute Resource (AICR) Training - Optimizing GPU usage on AICR

## Presenter

Arsalan Akhter

Research Computing Specialist - Northeastern University

[Research Computing](https://rc.northeastern.edu/research-computing-team/)

---

## GPU Profiling and Optimization on AICR

Welcome to Workshop 2 of the AICR Training Series!

This session is for anyone who runs GPU jobs on AICR and wants to know whether those jobs are actually using the hardware efficiently — and what to do when they are not.

Workshop 1 covered logging in, storage, partitions, and submitting your first job.  This session picks up from there and focuses entirely on **GPU efficiency**.

By the end of this training you will be able to:

1. [Confirm that your GPU job got the hardware you requested](#section-1-do-you-even-have-the-gpu)
2. [Read live GPU metrics and recognize what healthy utilisation looks like](#section-2-seeing-your-gpu-live)
3. [Choose the right profiling tool for your question](#section-3-the-profiling-toolchain)
4. [Diagnose and fix the most common bottleneck: data starvation](#section-4-the-1-bottleneck-data-starvation)
5. [Understand GPU memory vs utilisation and tune both independently](#section-5-memory-vs-utilisation-two-different-problems)
6. [Decide when (and when not) to scale to multiple GPUs](#section-6-when-and-when-not-to-scale-to-multiple-gpus)
7. [Apply a repeatable optimization workflow to any GPU job](#section-7-the-repeatable-optimization-workflow)
8. [Use Jobstats to review your efficiency after a run](#section-7-the-repeatable-optimization-workflow)

All materials for this workshop are available at the GitHub repository linked in the session invitation.

You are welcome to follow along in real time.  You can also just watch and work through it at your own pace afterward.  Recordings will be posted on the [Research Computing website](https://rc.northeastern.edu).

---

## The Question Nobody Asks

You submitted a GPU job.  It ran.  It finished.

But **was the GPU actually working?**

Many GPU jobs on HPC clusters do not utilize the GPU to what the hardware is capable of.  A lot of time is wasted when the GPU is sitting idle, waiting.

On AICR this matters more.  AICR's B200 and RTX PRO 6000 GPUs are among the fastest hardware available to academic researchers anywhere.  An idle B200 is roughly 2.5× more expensive to waste than an idle A100.  AICR is also shared across six universities — every idle allocation is time another researcher couldn't use.

The good news: almost all inefficiencies share a small set of root causes.  Once you learn to **measure** your job rather than assume it is fine, fixes are usually one or two code changes.

> **The single most important thing to remember from this training:**
> **Measure before you change anything.  Profile first, optimize second.**

Every section adds one measuring instrument to your toolkit.

## Prerequisites — Getting the Training Materials

Before the demos begin, get your environment ready.

**Step 1 — Log into AICR Open OnDemand**

Open [https://ood.aicr.ai/](https://ood.aicr.ai/) and sign in with your Northeastern credentials.

> ⚠️ **AICR username note:** Your username on AICR is slightly different from
> Explorer.  If your Explorer username is `j.smith`, your AICR username is
> `j_smith_neu`.

**Step 2 — Request an interactive GPU session**

Use the **b200-devel** partition for interactive development and profiling.
All of today's demos run here.

```bash
srun -p b200-devel -N 1 -n 1 -c 8 --mem=32G --gres=gpu:1 \
     --time=01:00:00 --pty bash
```

<!---

> 💡 **Presenter note:** Open a second terminal pane now.
> SSH into an AICR devel session and run `watch -n 1 nvidia-smi`.
> Keep that pane visible as each demo runs.  The audience sees GPU metrics
> update live as scripts execute — this turns an abstract concept into a real
> number changing on screen.
-->
---

> 💡 **Question for the audience:** Why `srun` instead of `sbatch`?
>
> Answer: `srun` drops you into a live terminal on a compute node.  You can
> run commands, see output immediately, and kill and restart without re-queuing.
> This is the right environment for profiling.  `sbatch` is for production
> runs once the code is already optimized.

**Step 3 — Load modules and clone the training repo**

```bash
module load cuda/13.1.1
module load miniforge3/25.3.0-3

cd /scratch/$USER
git clone https://github.com/northeastern-rc-training/AICR-Optimizing-GPU-Usage.git
```

**Step 4 — Set up the Python environment**

```bash
cd AICR-Optimizing-GPU-Usage
chmod +x setup_env.sh
./setup_env.sh
source activate aicr_gpu_workshop
which python   # should point into the conda environment
```

---

## Section 1: Do You Even Have the GPU?

*Build confidence in your setup before measuring anything.*

---

Before any efficiency work can begin, you must confirm that your job is
actually running on the hardware you requested.  This sounds obvious, but it is
a more common source of wasted time than people expect.

Things that can silently go wrong:
- The CUDA module was not loaded → `torch.cuda.is_available()` returns `False`
  and PyTorch runs on CPU without raising an error
- A typo in `--gres` lands you on a different node type
- `CUDA_VISIBLE_DEVICES` is set by a previous job in your shell history

### 1.1 AICR GPU Partitions

AICR has two GPU families and four GPU partitions:

| Partition | GPU | VRAM | Max walltime | Purpose |
|---|---|---|---|---|
| `b200-devel` | NVIDIA B200 | 192 GB | 4 h | Interactive dev, profiling, OOD |
| `b200-batch` | NVIDIA B200 | 192 GB | 24 h | Batch training and inference |
| `rtx-devel`  | NVIDIA RTX PRO 6000 | 96 GB | 4 h | Interactive dev, lighter workloads |
| `rtx-batch`  | NVIDIA RTX PRO 6000 | 96 GB | 24 h | Batch training and inference |

**Which partition should you use?**

- Start with `b200-devel` for today's demos (interactive, B200 hardware)
- Use `b200-batch` for production training jobs submitted with `sbatch`
- Use `rtx-*` for workloads that fit within 96 GB VRAM or don't need full B200 throughput

<!-- Image prompt for slide:
"A clean two-column diagram comparing NVIDIA B200 (Blackwell, 192 GB HBM3e,
~1000W TDP) and NVIDIA RTX PRO 6000 (Blackwell, 96 GB GDDR7, ~300W) side by
side with a decision tree below: 'Model > 80 GB? → B200.  Inference or
lighter training? → RTX PRO 6000.  Both support FP32 / BF16 / FP8.'
Use Northeastern red (#C8102E) accents on a white background."
-->

### 1.2 A Minimal SLURM Script for AICR

```bash
#!/bin/bash
#SBATCH --job-name=my_training
#SBATCH --partition=b200-batch          # choose b200-batch or rtx-batch
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8              # set to your num_workers + 1
#SBATCH --gres=gpu:1                   # one GPU on the partition you chose
#SBATCH --mem=32G                      # CPU RAM — NOT GPU VRAM
#SBATCH --time=04:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

mkdir -p logs

module purge
module load cuda/13.1
module load miniforge3/25.3.0-3
source activate aicr_gpu_workshop

python train.py
```

A few things worth pausing on:

- **`--mem=32G` is CPU RAM**, not GPU VRAM.  GPU VRAM is allocated automatically when SLURM gives you the GPU.
- **`--cpus-per-task=8` matters more than it looks.**  DataLoader worker processes consume these CPU cores.  We revisit this in Section 4.
- Create the `logs/` directory before submitting, or SLURM will fail to write output files on some configurations.

### 1.3 Verifying GPU Allocation at Runtime

Never trust that SLURM gave you what you asked for.  Run the verification
script at the top of every job.  It takes less than five seconds.

```bash
python scripts/01_gpu_verify.py
```

The script checks:
1. Is CUDA reachable?  (If not: module issue or wrong node)
2. How many GPUs, which model, how much VRAM?
3. What is `CUDA_VISIBLE_DEVICES`?  (SLURM sets this to isolate your GPU)
4. Cross-verify with `nvidia-smi`
5. Quick tensor round-trip: CPU → GPU → CPU

> **Demo:** Run `python scripts/01_gpu_verify.py` and read the output together.

> 💡 **Question for the audience:** `torch.cuda.is_available()` already returned
> `True` — so why does the script still do a CPU → GPU → CPU tensor round-trip?
>
> Answer: `is_available()` only confirms PyTorch can *see* a GPU, not that it
> can actually *use* it. A round-trip catches real failures that surface only
> when you touch the device — a driver/runtime mismatch, an out-of-memory GPU
> already saturated by another process, or ECC/hardware errors — before your
> training job hits them 20 minutes in.

### 1.4 CUDA_VISIBLE_DEVICES

SLURM sets this environment variable to tell your program which GPU indices
belong to your job.  **Never override it in your script** unless you deliberately
want a subset.

| What you see | What it means |
|---|---|
| `CUDA_VISIBLE_DEVICES=0` | You have one GPU (index 0 as SLURM sees it) |
| `CUDA_VISIBLE_DEVICES=0,1` | Two GPUs allocated |
| `NOT SET` | Running outside SLURM (e.g., an `srun` interactive shell) — normal |

### 1.5 ⚠️ AICR-Specific: The Idle GPU Cancellation Policy

AICR runs a background process that monitors GPU utilisation.  **Jobs that hold
a GPU without running kernels will be cancelled automatically.**

This policy exists because AICR is a shared resource across six universities.
A job that holds a B200 for hours while doing nothing is blocking researchers at Northeastern and
at partner institutions.

**Practical implications:**

- Do not request a GPU allocation and then spend time writing code or debugging Python errors.  Use a CPU node or your local machine for that.
- Run the verification script early.  If there is a module or environment problem, you will find out in seconds rather than losing your slot.
- Profile in `b200-devel` (short interactive sessions) — not in `b200-batch`.

> **Section 1 takeaway:** Verify your device, VRAM, and that the GPU is
> actually usable before doing anything else.  Idle allocations on AICR get
> cancelled.

---

## Section 2: Seeing Your GPU Live

*The dashboard: what healthy utilisation looks like.*

---

The fastest profiling tool available is already installed on every AICR compute
node.  It takes thirty seconds to run and tells you whether you have a problem
worth investigating further.

### 2.1 nvidia-smi — The First Check

```bash
# One-time snapshot
nvidia-smi

# Continuous refresh every 1 second (open in a second terminal)
watch -n 1 nvidia-smi
```

**What to read in the output:**

```
+-------------------------------------------------------------------------+
| GPU  Name                      | Temp  Pwr:Usage/Cap  | GPU-Util  Mem |
|=======================================================================|
|   0  NVIDIA B200               |  52C    387W / 1000W |     84%       |
|                  Memory: 24576MiB / 196608MiB                         |
+-------------------------------------------------------------------------+
```

Two numbers matter most:

- **GPU-Util 84%** — 84% of the past second had at least one GPU kernel running.  This is healthy.  Below 50%? We need to check something!
- **24576 MiB / 196608 MiB** — memory allocated vs. total VRAM.  This is only 12% of the B200's 192 GB.  There is enormous headroom to increase batch size.

> 💡 **Question for the audience:** If you saw `GPU-Util: 12%` and
> `Memory: 91%`, what problem would you guess?
>
> Answer: The GPU has VRAM allocated (the model is loaded) but is barely
> computing.  Something on the CPU side is not feeding it work.  This is the
> data loading bottleneck — the most common problem we fix in Section 4.

### 2.2 The Two-Axes Mental Model

GPU utilisation and GPU memory are independent metrics that are often confused.

```
                        GPU Memory Usage
                              │
                         High │  Model loaded,       │  Target zone:
                              │  GPU barely running  │  big model,
                              │                      │  working hard
                              │  (data pipeline      │  80-100% util,
                              │   problem)           │  70-90% memory
                              │                      │
                         Low  │  GPU doing nothing   │  Good throughput,
                              │                      │  VRAM headroom
                              └──────────────────────┴──────────────────
                                    Low util               High util
                                                   GPU Utilisation %
```

The goal is the upper-right quadrant.  Most inefficient jobs are in the upper-left (model loaded, not computing — data pipeline problem) or lower-left (GPU doing nothing at all).

<!-- Image prompt for slide:
"A 2×2 matrix diagram. X-axis: 'GPU Utilisation (%)' from Low to High.
Y-axis: 'GPU Memory Usage (%)' from Low to High. Upper-left quadrant
(orange): 'Model loaded, GPU idle — fix data pipeline'. Upper-right
(green, highlighted): 'Target zone: 80–100% util, 70–90% memory'.
Lower-left (red): 'Nothing happening — check everything'. Lower-right
(yellow): 'Good throughput — increase batch size to use more VRAM'.
Clean flat-design style with Northeastern red (#C8102E) for the target zone border."
-->

### 2.3 nvitop — A Better Dashboard

```bash
nvitop
```

`nvitop` shows a continuously-updating TUI with per-process GPU usage, memory
trend, power draw, and temperature.  It is especially useful on shared nodes
where you want to confirm it is *your* Python process using the GPU, not a
leftover process from a previous session.

```bash
pip install nvitop   # if not in your environment
nvitop
```

> **Section 2 takeaway:** Open a second terminal and run `watch -n 1 nvidia-smi`
> before starting any optimization work.  If utilisation is below 50%, you
> already know something is wrong.  The rest of this training tells you how
> to find and fix it.

---

## Section 3: The Profiling Toolchain

*From "something is wrong" to "here is exactly what is wrong."*

---

`nvidia-smi` tells you *that* there is a problem.  To find *where* the time is
going, you need a profiler.

### 3.1 Three Layers of GPU Profiling

Different tools answer different questions:

| Layer | Tool | What it answers |
|---|---|---|
| **System / live** | `nvidia-smi`, `nvitop` | Is the GPU busy?  How much VRAM?  Temperature? |
| **Framework** | PyTorch Profiler | Which operator or layer uses the most GPU time? |
| **Timeline** | Nsight Systems (`nsys`) | Exact timing of every CPU thread, GPU kernel, and memory copy |
| **Kernel deep-dive** | Nsight Compute (`ncu`) | Is this kernel memory-bound or compute-bound? |

You rarely need to go all the way to the kernel level.  Most problems are
visible at the system or framework layer.

### 3.2 Workflow: Profile in Devel, Run Production in Batch

> 💡 **This workflow habit is especially important on AICR.**

The `b200-batch` and `rtx-batch` partitions are for polished, efficient jobs.
Using a batch allocation for debugging wastes shared resources across all MGHPCC
partner universities.

**The correct AICR workflow:**

```
b200-devel (srun, interactive)
    ↓  run scripts/01_gpu_verify.py
    ↓  run your code for 50–100 steps
    ↓  profile with PyTorch Profiler
    ↓  fix the bottleneck
    ↓  re-profile: confirm utilisation > 70%
b200-batch (sbatch, unattended)
    ↓  production run, already optimized
    ↓  review Jobstats after completion
```

<!-- Image prompt for slide:
"A vertical flowchart with two swim-lane columns. Left lane labeled
'b200-devel (srun)' shows boxes: Verify GPU → Short profile run →
Diagnose bottleneck → Fix → Re-profile → Confirm >70% util.
Right lane labeled 'b200-batch (sbatch)' shows: Submit job →
Monitor (squeue) → Review Jobstats. An arrow bridges the two lanes
after 'Confirm >70% util'. Use Northeastern red for the bridge arrow.
Clean minimal style."
-->

<!--Rule of thumb: if your entire job runs in under 30 minutes in an interactive
session, there is no reason to use `sbatch`.  Switch to batch only when you
have a tuned script that genuinely needs hours.-->

### 3.3 PyTorch Profiler

When you want to know which part of your model is the bottleneck, the PyTorch
Profiler gives operator-level timing without any external dependencies.

```bash
python scripts/04_pytorch_profiler_demo.py
```

The key pattern — **always profile a short window, not the full run:**

```python
from torch.profiler import profile, record_function, ProfilerActivity

with profile(
    activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA],
    record_shapes=True,
    on_trace_ready=torch.profiler.tensorboard_trace_handler('./prof')
) as prof:
    for step, (x, y) in enumerate(dataloader):
        if step == 20:
            break                  # ← short window only — 10-20 steps is enough
        out  = model(x)
        loss = criterion(out, y)
        loss.backward()
        optimizer.step()
        prof.step()

print(prof.key_averages().table(sort_by='cuda_time_total', row_limit=15))
```

**How to read the profiler output:**

| Column | What it means |
|---|---|
| `Name` | The operator or your `record_function("label")` markers |
| `CUDA total` | Total GPU time across all profiled steps — this is your primary target |
| `CPU total` | CPU wall time.  If much larger than CUDA total, work is not on the GPU |
| `Self CPU` | Time in this op excluding children — helps isolate the true bottleneck |

**What to look for, in order of priority:**

1. **Gaps between GPU kernels on the timeline** → GPU is idle, CPU is too slow
2. **Large `aten::copy_` entries** → data moving between CPU and GPU frequently
3. **CPU total >> CUDA total** → computation is not properly on the GPU
4. **DataLoader functions at the top of the CPU table** → data pipeline bottleneck

### 3.4 Nsight Systems — Full Timeline

For problems that require understanding the *ordering* of events — CPU threads,
GPU kernels, memory copies, and multi-GPU communication all on one timeline —
use Nsight Systems:

```bash
nsys profile \
  --trace=cuda,nvtx,osrt,cudnn,cublas \
  --output=/scratch/$USER/profile_$(date +%s) \
  python train.py --max-steps 50

# Copy the .nsys-rep file to your laptop to open in Nsight GUI
scp your_aicr_username@<aicr-login>:/scratch/$USER/profile_*.nsys-rep ./
```

> **Important:** Limit the capture to 50–100 steps or use `--duration`.
> Full-run profiles produce gigabyte files and are difficult to navigate.

> **Section 3 takeaway:** Start with `nvidia-smi`.  If utilisation is low, run
> the PyTorch Profiler for 20 steps and sort by `cuda_time_total`.  The top
> entry is where to look first.

---

## Section 4: The #1 Bottleneck — Data Starvation

*Why your GPU waits, and what to do about it.*

---

The most common cause of low GPU utilisation in training jobs is not necessarily a bad model
code.  It potentially can also be a data pipeline that cannot keep up with the GPU.

This is even more acute on AICR than on older clusters.  The B200 processes
each batch faster than for example an A100 by a large margin.  If your DataLoader barely
kept up on Explorer, it will definitely starve a B200.

### 4.1 The Factory Floor Analogy

Imagine a high-speed factory (the B200).  It can process a batch in 8
milliseconds.  But the supply truck (the CPU DataLoader) takes 50 milliseconds
to load and deliver the next batch.

The factory stops and waits.  Workers are ready.  Machines are idle.  Not
because anything is wrong with the factory — the supply chain cannot keep up.

```python
# The diagnostic: compare load time to compute time

import time, torch

# Time just the data loading (no GPU work)
t0 = time.perf_counter()
for i, (x, y) in enumerate(loader):
    if i >= 50:
        break
loader_ms = (time.perf_counter() - t0) / 50 * 1000

# Time just the compute (synthetic data, bypass the loader)
dummy_x = torch.randn(256, 3, 224, 224, device='cuda')
torch.cuda.synchronize()
t0 = time.perf_counter()
for _ in range(50):
    out = model(dummy_x)
    out.sum().backward()
    torch.cuda.synchronize()
compute_ms = (time.perf_counter() - t0) / 50 * 1000

print(f'Load time per batch    : {loader_ms:.1f} ms')
print(f'Compute time per batch : {compute_ms:.1f} ms')

# If loader_ms > compute_ms, you are DATA BOUND.
# No amount of model optimization will help until you fix this first.
```

> 💡 **Question for the audience:** If `loader_ms = 45` ms and
> `compute_ms = 9` ms, what fraction of the GPU's time is wasted waiting?
>
> Answer: The GPU works for 9 ms and waits for 36 ms.  That is 80% wasted.

**Demo:**

```bash
python scripts/03_dataloader_benchmark.py
```

<!-- Section 4.2 (AICR Storage) commented out — kept for reference

### 4.2 AICR Storage: Where Your Data Lives Matters

On AICR, `/home`, `/scratch`, and `/work` are all **NFS exports on the same
server** (`storage0001.nfs`) — so choose your tier primarily by **quota, purge
policy, and contention**, not by an assumed raw-speed ranking.  The exports may
sit on different backends, but don't assume one NFS tier is dramatically faster
than another without measuring (see *Measuring tier speed* below).

The real speed lever is **getting off NFS entirely**: copy your dataset to
node-local `$TMPDIR` at job start.  That, plus using sequential-read file
formats, matters far more than which NFS tier you pick.

| Storage | Quota | Purge | Best for |
|---|---|---|---|
| `/home/$USER` | ~100 GB, shared | None | Code, configs, small files.  **Don't train from here** — shared, high metadata contention. |
| `/scratch/$USER` | ~10 TB | **30-day purge** | Active training datasets and large sequential reads.  Move results out before purge. |
| `/work/neu/$PROJECT` | Project allocation | None | Longer-term project data and results.  Purge-safe. |
| `$TMPDIR` | Node-local (varies) | End of job | **Fastest — not NFS.**  `rsync` your dataset here at job start.  **Check availability on your compute node.** |

> ℹ️ Quotas above are *per-user allocations*, separate from the raw filesystem
> capacity you see in `df -h` (which shows the whole export, e.g. `/scratch` at
> 2.7 PB).  Confirm your current quotas with the cluster's quota command.

> ⚠️ **The 30-day scratch purge is automatic and irreversible.**  Set a calendar
> reminder after every long job to move important outputs from `/scratch/$USER`
> to `/work/neu/$PROJECT` before they are deleted.

```bash
# In your SLURM script — copy data to fast local storage before training
if [ -n "$TMPDIR" ] && [ -d "$TMPDIR" ]; then
    echo "Copying dataset to $TMPDIR ..."
    rsync -a /scratch/$USER/mydata/ $TMPDIR/mydata/
    DATA_DIR=$TMPDIR/mydata
else
    DATA_DIR=/scratch/$USER/mydata
fi

python train.py --data-dir $DATA_DIR
```

Image prompt for slide:
"A vertical storage tier diagram for AICR. Four tiers stacked vertically:
at the top '$TMPDIR (node-local)' labeled 'Fastest — copy data here at job
start'; next '/scratch/$USER' labeled 'Good — 10 TB, 30-day purge, sequential
reads'; next '/work/neu/$PROJECT' labeled 'Moderate — long-term, purge-safe';
at the bottom '/home/$USER' labeled 'Slowest — never train here, 100 GB
quota'. Arrows on the right show data flow direction. Use a warm-to-cool
color gradient from top (green) to bottom (red). Clean flat design."

**Avoid tiny-file datasets on `/scratch`.**  If your dataset consists of
millions of small image files (e.g., ImageNet in JPEG format), the filesystem
metadata overhead alone can become the bottleneck.  Convert to a format that
enables large sequential reads:
- **HDF5** (`h5py`) — pack many images into one file
- **WebDataset** — tar-based streaming format, excellent for large vision datasets
- **LMDB** — fast key-value store, common in older vision pipelines

-->

### 4.2 DataLoader Configuration — The Four Knobs

A **DataLoader** (PyTorch's `torch.utils.data.DataLoader`) is the component that
feeds your model.  It takes a `Dataset` and handles the plumbing between disk and
GPU: reading samples, collating them into batches, shuffling, and — crucially —
doing this work on **CPU worker processes in parallel** so the next batch is
ready before the GPU finishes the current one.

Why it matters for utilization: a GPU can only train as fast as it is fed.  If
data loading is serial (the default), the GPU sits idle waiting for each batch —
this is the "data starvation" from Section 4.  

The four knobs below control how
aggressively the DataLoader prefetches and parallelises that work, and tuning
them is usually the highest-leverage, lowest-effort fix for low GPU utilization.

```python
from torch.utils.data import DataLoader

loader = DataLoader(
    dataset,
    batch_size=256,
    num_workers=7,             # ← num_workers = cpus-per-task minus 1
    pin_memory=True,           # ← always True on GPU training
    persistent_workers=True,   # ← avoid re-spawning workers each epoch
    prefetch_factor=2,         # ← each worker pre-loads this many batches
)
```

**What each setting does:**

| Parameter | Effect | Typical starting value |
|---|---|---|
| `num_workers` | Spawns CPU processes that load data in parallel while the GPU runs | `cpus-per-task - 1` (never 0) |
| `pin_memory=True` | Allocates CPU tensors in page-locked RAM for fast GPU DMA transfer | Always `True` on GPU nodes |
| `persistent_workers=True` | Keeps worker processes alive between epochs (avoids spawn overhead) | Always `True` when `num_workers > 0` |
| `prefetch_factor` | Each worker pre-loads this many batches ahead | Start at 2; increase if loader is still slow |

> **The single biggest win:** Changing `num_workers=0` (the PyTorch default) to
> `num_workers=4` or higher.  This is a one-line change that often takes a job
> from 20% GPU utilisation to 60–80% with no other code changes.

> **Section 4 takeaway:** GPU utilization below 60% almost always points to the
> data pipeline.  Fix DataLoader parameters (`num_workers`, `pin_memory`).
> This does not require changing your model code.

<!-- Storage-tier advice removed from takeaway (see commented Section 4.2):
Fix storage locality first (`$TMPDIR` or `/scratch`, never `/home`). -->

---

## Section 5: Memory vs Utilization — Two Different Problems

*Two numbers on the nvidia-smi display that look similar and mean completely different things.*

---

`nvidia-smi` shows two percentages that are easy to confuse: GPU utilisation
and memory usage.  They are independent axes.  Applying the fix for one to
the other makes things worse.

### 5.1 What Each Number Measures

| Metric | What it measures | Low is a problem because | High is bad if |
|---|---|---|---|
| **GPU Util %** | Fraction of the past second when GPU kernels were running | GPU is idle (data or sync issue) | Rarely — 100% sustained is fine |
| **Memory %** | Fraction of VRAM currently allocated | Unused VRAM could hold a bigger batch | Approaching OOM |

**Quick decision table:**

```
What you see              → Most likely cause         → First thing to try
─────────────────────────────────────────────────────────────────────────
Low util  + Low  memory   → GPU doing nothing         → Verify CUDA, check data
Low util  + High memory   → Model loaded, not running → Fix data pipeline (§4)
High util + Low  memory   → Healthy, VRAM unused      → Increase batch size
High util + High memory   → Healthy, working hard     → You're in good shape
OOM crash                 → Batch too large            → Mixed precision first (§5.3)
```

### 5.2 Batch Size Tuning

Batch size directly controls both axes.  Doubling the batch size roughly
doubles throughput as long as the GPU is not already compute-saturated — and
you have the VRAM.

On the B200 (192 GB VRAM), most researchers can use much larger batches than
they did on A100 (80 GB) or V100 (32 GB).  If `nvidia-smi` shows memory at
15–20%, there is likely room to increase batch size 4–8×.

```python
# Binary search for the maximum batch size your model fits in VRAM
def fits_in_vram(model, batch_size, input_shape=(3, 224, 224)):
    try:
        x = torch.randn(batch_size, *input_shape, device='cuda')
        out = model(x)
        out.sum().backward()
        torch.cuda.empty_cache()
        return True
    except torch.cuda.OutOfMemoryError:
        torch.cuda.empty_cache()
        return False

lo, hi = 1, 4096
while lo < hi:
    mid = (lo + hi + 1) // 2
    if fits_in_vram(model, mid):
        lo = mid
    else:
        hi = mid - 1
print(f'Maximum batch size: {lo}')
```

Use 70–85% of the maximum as your production batch size to leave headroom for
activation memory growth during the backward pass.

### 5.3 Mixed Precision — BF16 First, FP8 Later

By default PyTorch uses 32-bit floats (FP32).  Both the B200 and RTX PRO 6000
are Blackwell architecture with 5th-generation Tensor Cores that dramatically
accelerate lower-precision computations.

**BF16 — the default choice for AICR:**

```python
from torch.amp import autocast

# Before (FP32)
out  = model(x)
loss = criterion(out, y)
loss.backward()

# After (BF16) — add exactly this wrapper
with autocast(device_type='cuda', dtype=torch.bfloat16):
    out  = model(x)
    loss = criterion(out, y)
loss.backward()   # gradients automatically stay in FP32
```

Benefits of BF16 on AICR hardware:
- Roughly **halves activation memory** → fits a much larger batch in the same VRAM
- **2–4× faster** matrix operations on Blackwell Tensor Cores
- **No GradScaler needed** — BF16 has the same numeric range as FP32, avoiding the underflow problem that affects FP16

```bash
python scripts/05_mixed_precision_demo.py
```

**FP8 — for large-scale workloads on B200:**

The B200 natively supports FP8 computation, which offers further speedups for
large model training (7B+ parameter language models, large vision transformers).
FP8 requires additional setup via `torchao` or `transformer_engine`:

```python
# FP8 via torchao (requires: pip install torchao)
from torchao.float8 import convert_to_float8_training
model = convert_to_float8_training(model)
```

FP8 is not covered in depth today.  Start with BF16 and contact the RC team if
your workload is large enough to benefit from FP8.

| Precision | Bytes (exp/mantissa) | When to use on AICR | Key tradeoff |
|---|---|---|---|
| FP32 | 4 (8 / 23) | Debugging only | Full precision + range, but slowest and 2× the memory; baseline to compare against |
| BF16 | 2 (8 / 7) | **Default for all GPU training on AICR** | Keeps FP32's range (no scaler) but coarse precision (~2–3 digits) — safe because master weights + reductions stay FP32 |
| FP16 | 2 (5 / 10) | Avoid on Blackwell | More mantissa than BF16, but tiny exponent range → gradient underflow, needs GradScaler; no upside over BF16 here |
| FP8 | 1 (4 / 3) | Large LLMs on B200 | Biggest speed/memory win, but coarse enough to hurt accuracy — needs per-tensor scaling, calibration, and higher-precision master weights |

> **Tradeoffs in one line:** every step down the ladder trades **numerical
> quality for speed and memory** — and it is not a simple "lower is better"
> progression.  A few things worth keeping in mind:
>
> - **Range vs. precision.**  A 16-bit format must split its bits between
>   exponent (range) and mantissa (precision).  BF16 keeps FP32's 8 exponent
>   bits (so gradients don't underflow → no GradScaler), at the cost of
>   precision.  FP16 makes the opposite bet: more precision, but a 5-bit
>   exponent that underflows and *forces* loss scaling.  On Blackwell, BF16's
>   bet is the right one.
> - **"Mixed" precision is the safety net.**  BF16 training is only stable
>   because the risky parts stay in FP32 — master weights, the loss, softmax,
>   and layer/batch-norm reductions.  `autocast` handles this automatically;
>   casting *everything* to BF16 would often diverge.
> - **Memory savings are partial.**  BF16 roughly halves *activation* memory,
>   but FP32 master weights + Adam optimizer states are unchanged, so total
>   VRAM does not drop by a full 2×.
> - **Speedup is op-dependent.**  The 2–4× applies to Tensor-Core matmuls and
>   convolutions; memory-bound or elementwise ops see little benefit, and tiny
>   models may be bottlenecked elsewhere entirely.
> - **FP8 costs more than setup.**  Beyond `torchao`/`transformer_engine`
>   plumbing, FP8 needs scaling/calibration and can measurably degrade accuracy
>   on smaller models — which is why it only pays off when the model is large
>   enough to amortize the loss in quality against the speed gain.

### 5.4 When Memory Is Still Too Tight — Gradient Checkpointing

If you are training a very large model and even BF16 does not give you enough
headroom, gradient checkpointing trades compute for memory.

During the forward pass, activations are **not stored** — they are recomputed
on demand during backpropagation.  This typically reduces activation memory by
60–70% at the cost of ~30% extra compute.

```python
# For Hugging Face Transformers — one flag:
model.gradient_checkpointing_enable()

# For custom PyTorch modules:
from torch.utils.checkpoint import checkpoint

class MyBlock(torch.nn.Module):
    def forward(self, x):
        return checkpoint(self.expensive_layers, x, use_reentrant=False)
```

Apply gradient checkpointing when:
- Your batch size is forced below 8 due to VRAM
- You are fine-tuning a 70B+ model on a single B200
- You want to double your batch size and can afford 30% more compute time

**Demo:**

```bash
python scripts/06_memory_monitor.py
```

Watch memory grow through the training loop and see the diagnostic hints.

> **Section 5 takeaway:**
> - Low util + high memory → fix data pipeline (Section 4).
> - High util + low memory → increase batch size.
> - OOM → enable BF16 first, then gradient checkpointing, then reduce batch.
> - Do not trade memory for compute (checkpointing) until you've tried BF16.

---

## Section 6: When (and When Not) to Scale to Multiple GPUs

*Why four GPUs is not four times faster, and when multi-GPU actually helps.*

---

Multi-GPU training is often the first thing people reach for when a job is slow.


It can also be the wrong move. 

 Multi-GPU amplifies the efficiency you already
have — it does not create it.

On AICR this matters doubly.  Batch partitions are shared across **six
universities**.  Requesting four B200 GPUs when one would do takes four
allocations away from other institutions.

### 6.1 The 80% Rule

Fix single-GPU efficiency first.  Then scale.

| Scenario | Multi-GPU useful? | Reason |
|---|---|---|
| Single-GPU util already > 80% | Yes | You are compute-bound; add GPUs to divide the work |
| Single-GPU util < 60% | **No** | Fix the bottleneck first — adding GPUs multiplies waste |
| Model does not fit in one GPU's VRAM | Yes — required | Even with B200's 192 GB, 70B+ models may need 2 GPUs |
| Job is I/O bound (data loading bottleneck) | **No** | Multiple GPUs compete for the same filesystem — makes I/O worse |

> 💡 **AICR context:** Because the B200 has 192 GB VRAM, many workloads that
> needed 4 A100s (4 × 80 GB = 320 GB) now fit on **two B200s** (2 × 192 GB =
> 384 GB), or even **one B200** after enabling BF16.  Check single-GPU
> utilisation before requesting more.

### 6.2 How Data-Parallel Training Works

In data-parallel training (DDP), each GPU holds a full copy of the model.
Each GPU processes a different mini-batch.  After the backward pass, all GPUs
**all-reduce** their gradients — they communicate to compute a single averaged
gradient, then each runs the optimizer step with the same result.

```
GPU 0: batch A → gradients A ─┐
GPU 1: batch B → gradients B ─┤→ all-reduce → averaged gradient → each GPU updates
GPU 2: batch C → gradients C ─┘
```

The cost of the all-reduce grows with model size.  Within a single node
(NVLink), this is fast.  Across nodes (InfiniBand), it is slower.  For most
workloads, single-node multi-GPU is substantially faster per-GPU than multi-node.

### 6.3 Checking Whether Your Code Actually Uses Multiple GPUs

Before requesting `--gres=gpu:4`, confirm your code is written for DDP.  If
you run a plain PyTorch script with `--gres=gpu:4`, SLURM allocates 4 GPUs but
your code will only use the first one (`CUDA_VISIBLE_DEVICES` will list all
four, but `model.cuda()` only moves to device 0).

```python
# Check: does your code use DDP?
import torch.distributed as dist
print(dist.is_available())   # must be True
print(dist.is_initialized()) # must be True after dist.init_process_group()

# Check: how many GPUs does PyTorch see?
import torch
print(torch.cuda.device_count())   # should match --gres=gpu:N
```

For DDP on AICR:

```bash
#SBATCH --partition=b200-batch
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4       # one task per GPU
#SBATCH --gres=gpu:4
#SBATCH --cpus-per-task=8         # CPU workers per GPU process

torchrun --nproc_per_node=4 train_ddp.py
```

### 6.4 Measuring Scaling Efficiency

Always measure whether the extra GPUs gave you proportional speedup.

```python
# At the end of the first epoch (on rank 0 only):
if dist.get_rank() == 0:
    throughput = total_samples / elapsed_seconds
    efficiency = throughput / (world_size * single_gpu_baseline) * 100
    print(f'World size: {world_size}  |  {throughput:.0f} samples/sec  |  '
          f'Scaling efficiency: {efficiency:.0f}%')
```

- **> 80% efficiency** — good; multi-GPU is paying off
- **70–80%** — acceptable; some communication overhead
- **< 70%** — communication or I/O is the real bottleneck, not compute

If scaling efficiency is below 70%, go back and fix the single-GPU bottleneck
before adding more GPUs.

> **Section 6 takeaway:** Confirm > 80% utilisation on a single GPU first.
> Verify your code is actually DDP-enabled.  Start with the fewest GPUs that
> meet your requirement.  Measure scaling efficiency — if below 70%, more GPUs
> will not help.

---

## Section 7: The Repeatable Optimization Workflow

*A process that applies to any GPU job, any framework, any domain.*

---

Every section addressed a different bottleneck.  In practice they appear in the
same order of frequency.  The workflow below gives you a repeatable process.

### 7.1 The Optimization Loop

Fix one thing at a time.  Measure before and after each change.  Fixing two
things simultaneously makes it impossible to know what helped.

| Step | Action | Tool |
|---|---|---|
| 1. **Baseline** | Run for 50 steps; record throughput (samples/sec) and GPU util | `nvidia-smi`, `time` |
| 2. **Profile** | Capture a 20-step profiler trace | PyTorch Profiler |
| 3. **Diagnose** | Classify: data loading? Memory? Compute? Communication? | Sections 4–6 |
| 4. **Fix one thing** | Apply the highest-impact change | Code or SLURM script |
| 5. **Re-profile** | Did the bottleneck move? | Same tools |
| 6. **Record the gain** | Compare throughput to baseline | Log or notebook |
| 7. **Repeat** | Continue until util > 80% or diminishing returns | — |

### 7.2 Decision Guide

<!-- Storage-tier steps removed from decision guide (see commented Section 4.2):
     Data on /home or /scratch? Copy to $TMPDIR.
     Millions of tiny files? Convert to HDF5 or WebDataset. -->

```
GPU utilisation < 50%?
  ├─ Yes → Data pipeline (Section 4)
  │         num_workers=0? Fix that first.
  │
  └─ No (50–80%) → Check memory usage
        ├─ Memory < 40%  → Increase batch size (Section 5.2)
        ├─ Memory 40–85% → Try BF16 autocast (Section 5.3)
        ├─ Memory > 90%  → Reduce batch / gradient checkpointing (5.4)
        └─ Memory OK     → Profile with PyTorch Profiler (Section 3.3)

Util > 80% and memory looks healthy?
  └─ Consider multi-GPU only if single GPU is genuinely saturated.
     Measure scaling efficiency (Section 6.4) — expect > 80%.

OOM error?
  └─ Enable BF16 → gradient checkpointing → reduce batch (in this order)
```

### 7.3 Jobstats — Your Post-Job Efficiency Report

AICR deploys **Jobstats**, a post-job reporting tool developed by Princeton
Research Computing.  After a batch job finishes, run:

```bash
jobstats <jobid>
```

Jobstats shows:
- Average GPU utilisation over the entire job duration
- Peak and average VRAM usage
- CPU efficiency (how much of what you requested was actually used)
- Memory efficiency

It is the post-job equivalent of `watch -n 1 nvidia-smi`.

**Demo:**

```bash
python scripts/07_jobstats_guide.py
```

This script simulates a Jobstats report and walks through how to interpret
each metric and what to do when numbers are low.

**Make reviewing Jobstats a habit:**

> After every batch job → run `jobstats <jobid>` → if GPU utilisation < 60%,
> fix it before submitting the next run.

### 7.4 The AICR Pre-Submission Checklist

Before submitting any GPU batch job, verify these items — ideally in a
`b200-devel` or `rtx-devel` session first:

- [ ] `scripts/01_gpu_verify.py` passes — confirmed device name and VRAM
- [ ] `nvidia-smi` during a 50-step test shows utilisation > 70%
- [ ] `num_workers` in DataLoader is NOT 0 — set to `cpus-per-task - 1`
- [ ] `pin_memory=True` is set in DataLoader
<!-- - [ ] Training data is NOT on `/home`
- [ ] Scratch data has at least 2 weeks until the 30-day purge -->

- [ ] Batch size uses at least 60% of available VRAM
- [ ] BF16 autocast is enabled (`autocast(device_type='cuda', dtype=torch.bfloat16)`)
- [ ] SLURM script requests the correct partition (`b200-batch` or `rtx-batch`)
- [ ] `--cpus-per-task` is at least 4 and matches `num_workers + 1`
- [ ] `logs/` directory exists before submitting
- [ ] You have profiled for 20 steps and read the CUDA time column

### 7.5 HPC Hygiene on AICR

**Use devel partitions for profiling and iteration.**  Reserve batch partitions
for jobs that are already tuned and need to run for hours.

**Profile a short window, always.**  20–50 training steps gives a representative
profile.  A full-run trace produces large files and is harder to analyze.

**One change at a time.**  The most common optimization mistake is changing
three things at once.  You lose the ability to know what helped.

**Record your baselines.**  Before any change, write down: GPU utilisation,
throughput in samples/sec, wall time for N steps.  Without a baseline you
cannot measure improvement.

**Cancel interactive sessions when done.**  `b200-devel` has a limit of 4
concurrent running jobs per user.  An idle devel session blocks your own
future requests and takes resources from other users.

**The profiling mindset:** ten minutes of profiling saves hours of wasted queue
time and compute.  It is an investment, not overhead.

---

## Section 8: Connecting to Your Research Domain

*These principles apply beyond PyTorch training scripts.*

---

Everything covered today generalizes across research domains.  Here is how each
section maps to common workflows on AICR.

### Machine Learning and Deep Learning (PyTorch, TensorFlow)

Every section of this training applies directly.  Start with
`scripts/01_gpu_verify.py`, then `scripts/04_pytorch_profiler_demo.py`.  The
optimization loop in Section 7 is your permanent workflow.

For Hugging Face Transformers, most optimizations are one flag:

```python
from transformers import TrainingArguments

args = TrainingArguments(
    bf16=True,                           # Section 5.3
    gradient_checkpointing=True,         # Section 5.4 (if needed)
    dataloader_num_workers=8,            # Section 4.2
    dataloader_pin_memory=True,          # Section 4.2
    ...
)
```

### Molecular Dynamics (GROMACS, NAMD, AMBER)

- Section 1 applies: verify the GPU type before a long run
- Section 4 applies: copy input files and trajectory output paths to fast
  storage (`$TMPDIR` if available, otherwise `/scratch`)
- Section 6 applies: multi-node MD scales well within a node using NVLink
  but degrades for small systems across nodes over InfiniBand
- `nvidia-smi` and `nvitop` are your primary monitoring tools

### LLM Inference (serving, batch generation)

- Use the RTX PRO 6000 partition for smaller models; B200 for 70B+ models
- Consider vLLM for high-throughput batch inference (covered in Workshop 3)
<!-- - The storage tier advice (Section 4) applies to model weight loading:
  load weights from `/scratch`, not `/home` -->

### Custom CUDA or Triton Kernels

All sections apply.  At Section 3, also use **Nsight Compute (`ncu`)** which
shows per-kernel roofline analysis, warp occupancy, and memory bandwidth
utilisation — the level of detail needed to tune hand-written kernels.

---

## How to Get Help

Email the Research Computing team: [rchelp@northeastern.edu](mailto:rchelp@northeastern.edu)

[Office hours and Zoom help sessions](https://rc.northeastern.edu/getting-help/) are available throughout the semester.

[Book a one-on-one consultation](https://rc.northeastern.edu/getting-help/) with an RC specialist.

[Research Computing documentation](https://rc-docs.northeastern.edu/en/latest/index.html)

---

## Quick Reference Card

| Problem | First action | Script |
|---|---|---|
| Not sure the GPU is allocated | Run the verify script | `scripts/01_gpu_verify.py` |
| Util < 50% | Check `num_workers`; check storage tier | `scripts/03_dataloader_benchmark.py` |
| Processing inputs one at a time | Batch your inputs | `scripts/02_naive_vs_batched.py` |
| Want to know which layer costs most | PyTorch Profiler | `scripts/04_pytorch_profiler_demo.py` |
| OOM or want to fit a larger batch | Enable BF16 | `scripts/05_mixed_precision_demo.py` |
| Want to watch VRAM during training | Memory monitor | `scripts/06_memory_monitor.py` |
| Reviewing a finished batch job | Jobstats guide | `scripts/07_jobstats_guide.py` |

---

## AICR at a Glance (Reference)

| Item | Value |
|---|---|
| OOD login | [https://ood.aicr.ai/](https://ood.aicr.ai/) |
| Username format | `j_smith_neu` (not `j.smith`) |
| B200 VRAM | 192 GB per GPU |
| RTX PRO 6000 VRAM | 96 GB per GPU |
| CUDA module | `cuda/13.1` |
| Conda module | `miniforge3/25.3.0-3` |
| Post-job efficiency | `jobstats <jobid>` |
| Preferred precision | BF16 (`torch.bfloat16`) |

<!-- Storage rows removed from reference table (see commented Section 4.2):
| Home quota | 100 GB |
| Scratch quota | 10 TB |
| Scratch purge | 30 days (automatic, irreversible) |
| Recommended data storage | `/scratch/$USER` or `$TMPDIR` (not `/home`) |
-->

---

<!--*Workshop 2 of the AICR Training Series*-->

*For questions or support: [rchelp@northeastern.edu](mailto:rchelp@northeastern.edu)*
