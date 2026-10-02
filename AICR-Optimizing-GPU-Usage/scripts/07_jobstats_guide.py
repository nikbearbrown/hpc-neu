"""
Script 07 — Jobstats Interpretation Guide
------------------------------------------
Jobstats is a post-job efficiency reporting tool deployed on AICR (developed
by Princeton Research Computing).  After a job finishes it provides a summary
of how efficiently the job used its allocated resources — CPU, GPU, and memory.

Jobstats is AICR-specific.  It is not available on Explorer.

How to access Jobstats after your job finishes:
    jobstats <jobid>

Or view it in the AICR Open OnDemand portal:
    https://ood.aicr.ai/ → Jobs → Job Composer or Active Jobs → select job

This script does NOT call Jobstats directly (it is a cluster command).
Instead it simulates a Jobstats-style output and explains what each metric
means and what corrective actions to take.

Usage:
    python 07_jobstats_guide.py            # shows simulated output and guide
"""

import random

SEP     = "=" * 66
SUBSEP  = "-" * 66

# Simulated Jobstats-style output fields
SIMULATED_REPORT = {
    "Job ID"                : "4827641",
    "Partition"             : "b200-batch",
    "Nodes"                 : 1,
    "GPUs requested"        : 2,
    "CPUs per task"         : 8,
    "Requested walltime"    : "08:00:00",
    "Actual walltime"       : "06:12:33",
    "GPU utilisation (avg)" : 43.0,   # percent
    "GPU memory used (avg)" : 18.2,   # GB
    "GPU memory total"      : 192.0,  # GB per GPU
    "CPU efficiency"        : 62.0,   # percent
    "Memory efficiency"     : 34.0,   # percent (CPU RAM)
}


def bar(pct: float, width: int = 30, warn_below: float = 70) -> str:
    filled = int(width * pct / 100)
    symbol = "█" if pct >= warn_below else "▒"
    return symbol * filled + "░" * (width - filled)


def fmt_pct(pct: float, warn_below: float = 70, good_above: float = 80) -> str:
    if pct >= good_above:
        return f"{pct:.1f}%  ✓ GOOD"
    elif pct >= warn_below:
        return f"{pct:.1f}%  ⚑ OK, but room to improve"
    else:
        return f"{pct:.1f}%  ✗ LOW"


print(SEP)
print("  JOBSTATS — POST-JOB EFFICIENCY REPORT (SIMULATED)")
print("  Real usage:  jobstats <jobid>  after your sbatch job finishes")
print(SEP)
print()

r = SIMULATED_REPORT

print(f"  Job ID        : {r['Job ID']}")
print(f"  Partition     : {r['Partition']}")
print(f"  Nodes         : {r['Nodes']}")
print(f"  GPUs          : {r['GPUs requested']}")
print(f"  CPUs/task     : {r['CPUs per task']}")
print(f"  Requested     : {r['Requested walltime']}")
print(f"  Actual        : {r['Actual walltime']}")
print()

# GPU utilisation
gpu_pct = r["GPU utilisation (avg)"]
print(f"  GPU Utilisation (avg across all GPUs and all time):")
print(f"    {fmt_pct(gpu_pct)}")
print(f"    [{bar(gpu_pct)}]")
print()

# GPU memory
vram_pct = r["GPU memory used (avg)"] / r["GPU memory total"] * 100
print(f"  GPU Memory Utilisation:")
print(f"    {r['GPU memory used (avg)']:.1f} GB / {r['GPU memory total']:.1f} GB per GPU  "
      f"= {fmt_pct(vram_pct)}")
print(f"    [{bar(vram_pct)}]")
print()

# CPU efficiency
cpu_pct = r["CPU efficiency"]
print(f"  CPU Efficiency:")
print(f"    {fmt_pct(cpu_pct, warn_below=50, good_above=70)}")
print(f"    [{bar(cpu_pct)}]")
print()

# Memory efficiency
mem_pct = r["Memory efficiency"]
print(f"  CPU-RAM Efficiency:")
print(f"    {fmt_pct(mem_pct, warn_below=30, good_above=60)}")
print(f"    [{bar(mem_pct)}]")
print()

# ── Interpretation guide ──────────────────────────────────────────────────────
print(SEP)
print("  HOW TO INTERPRET EACH METRIC")
print(SEP)

print("""
  GPU UTILISATION (most important metric)
  ────────────────────────────────────────
  What it measures:
    The fraction of time that GPU kernels were actually running, averaged
    across all allocated GPUs and the entire job duration.

  Target: > 70%

  If low (< 50%):
    • Check your data pipeline first (Section 4 of the training).
      num_workers=0 is the single most common cause.
    • Is your data on /home?  Move it to /scratch or $TMPDIR.
    • Are you using multiple GPUs when one would do?  Each idle GPU
      halves your effective efficiency score.

  GPU MEMORY UTILISATION
  ───────────────────────
  What it measures:
    Average VRAM used across GPUs.  The B200 has 192 GB — a low
    percentage here usually means unused capacity.

  Target: 60–90%

  If low (< 40%):
    • Increase batch size.  More VRAM usage almost always means better
      GPU utilisation.
    • BF16 reduces memory so you can fit a larger batch — counterintuitively
      this often *improves* efficiency even though memory % drops.

  If high (> 90%) and job crashed:
    • Enable BF16 autocast to halve activation memory.
    • Add gradient checkpointing.
    • Reduce batch size as a last resort.

  CPU EFFICIENCY
  ───────────────
  What it measures:
    (CPU-time used) / (CPUs allocated × walltime).
    Low values mean you requested more CPUs than your job could use.

  Target: > 60%

  If low:
    • If you set --cpus-per-task=16 but num_workers=2 in your DataLoader,
      most CPUs sit idle.  Set num_workers ≈ cpus-per-task - 1.
    • Alternatively, reduce --cpus-per-task to free those cores for
      other users on the shared cluster.

  CPU RAM EFFICIENCY
  ───────────────────
  What it measures:
    (Peak CPU RAM used) / (RAM requested with --mem).
    Wasted CPU RAM is wasted allocation.

  If low (< 40%):
    • Reduce the --mem value in your SLURM script.
    • Typical deep learning training needs 8–32 GB CPU RAM; 100 GB is
      rarely required.
""")

print(SEP)
print("  ACTION PLAN FOR THIS SIMULATED JOB")
print(SEP)
print(f"  GPU util = {gpu_pct:.0f}% (target: > 70%)")
print()
print("  1. IMMEDIATE: Check if the DataLoader uses num_workers > 0.")
print("     Script 03 benchmarks your configuration.")
print()
print("  2. VRAM only at 9% — increase batch size significantly.")
print("     Run Script 06 to find the safe maximum before OOM.")
print()
print("  3. CPU efficiency is 62% — slightly reduce --cpus-per-task or")
print("     increase num_workers to match what you requested.")
print()
print("  4. This job requested 2 GPUs.  At 43% utilisation on each, a")
print("     single GPU might have been sufficient.  Test with 1 GPU first.")
print()
print("  RULE: Review Jobstats after EVERY batch job.  If utilisation stays")
print("  below 60%, fix it before submitting the next run.  AICR compute is")
print("  shared across six universities — efficient use keeps wait times low")
print("  for everyone.")
print(SEP)
