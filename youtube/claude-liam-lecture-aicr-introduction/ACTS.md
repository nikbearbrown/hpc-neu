# ACTS — AICR Introduction (lecture)

**What this is.** The coverage map for the lecture film of `hpc/AICR-Introduction-2026/aicr-introduction.md`.
**Why.** A lecture covers the WHOLE source; every section must land in an act or be listed as left out.
**Result.** All ten sections of the source are covered in six acts, 24 body beats. Nothing was left out. Runtime 6 min 19 s.

| Source section | Act | Beats |
|---|---|---|
| Introduction to AICR (what it is, GPU counts, CPU partition, extension of Explorer) | I · What AICR Is | B10 B11 B12 B13 |
| Getting Started on AICR (PI proposal form) | II · Getting On | B20 |
| Signing into AICR / Open OnDemand Login (address, credentials, username mapping) | II · Getting On | B21 B22 |
| Storage on AICR (three directories, quotas, recovery, purge) | III · Where Files Live | B30 B31 B32 |
| Compute Resources on AICR (partition table, memory, batch vs devel, idle monitor, jobstats) | IV · Compute | B40 B41 B42 B43 B44 |
| Submitting Jobs: sbatch (script, submit, follow-up commands) | V · Running A Job | B50 B51 B52 B53 |
| Submitting Jobs: srun | V · Running A Job | B54 |
| Submitting Jobs: Open OnDemand | V · Running A Job | B55 |
| Data Transfer to AICR (Globus) | VI · Data And Lifecycle | B60 |
| Project and Account Lifecycle; Questions | VI · Data And Lifecycle | B61 B62 |

## LEFT OUT

Nothing. Two details were compressed rather than dropped:
- CPU model names and per-node core counts in the partition table are not spoken or drawn. The source's table says 64 cores for GPU nodes; the AICR docs and the live cluster report 128. The film avoids the number (see FACTCHECK row 14).
- The multi-node comment inside the sbatch script (torchrun, rendezvous setup) is not shown; the script listing is the runnable part only.

## Order

The source's order is kept. No swaps.

## Cast (one cast, whole film)

| Object | Picture | Beats |
|---|---|---|
| AICR | large dark rack, four slabs | B10 B12 B13 B62 |
| Explorer / Northeastern | small dark rack, two slabs | B13 B62 |
| a job | small kraft box, one terracotta tape | B13 B41 B42 B43 B55 |
| home | small closed kraft box | B30 B31 |
| scratch | wide open kraft bin | B30 B32 |
| project directory | tall white cabinet | B20 B30 B31 B32 B62 |
| a GPU | dark block, light turns terracotta when busy | B42 B43 |

## Self-contained check

The source leans on one outside thing: Explorer. B13 says what it is ("Northeastern already has its own cluster, called Explorer") before using it. Six prerequisite terms are defined in BDEFS. The film never says "this training", "this document" or names a chapter.
