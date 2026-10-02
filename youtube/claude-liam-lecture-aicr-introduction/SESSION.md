# SESSION — what was really run for this film

**What this is.** The record behind every terminal and browser beat. **Result.** One read-only command on the real cluster and two public page captures. No job was submitted.

## Cluster (read-only), login.aicr.ai, Fri Oct 2 12:58:46 EDT 2026

```
$ sinfo -o "%14P %11l %6D"
PARTITION      TIMELIMIT   NODES
cpu*           1-00:00:00  5
rtx-batch      1-00:00:00  17
b200-batch     1-00:00:00  25
b200-fullnode  1-00:00:00  4
rtx-devel      4:00:00     2
b200-devel     4:00:00     2
preemptable    1-00:00:00  46
```
Shown verbatim in B44 (trailing spaces trimmed).

Also checked, not shown: `module load cuda/13.1` resolves to `cuda/13.1.1`; `miniforge3/25.3.0-3` exists; `sinfo` reports 128 CPUs per node and 1,159,937 MB (cpu) / 2,321,639 MB (GPU) memory; Slurm 25.11.8.

## Not run

`sbatch`, `squeue`, `scancel`, `sacct`, `srun` (B53, B54) are shown as commands only, from the source. Submitting a test job was attempted and blocked by the session's safety rules (shared-cluster change), so no output for them is shown anywhere in the film.

## Browser captures (headless, public pages, no sign-in), 2026-10-02

- `https://ood.aicr.ai/` → redirects to the CILogon "Select an Identity Provider" page → `captures/ood.png` (B21)
- `https://rc-docs.northeastern.edu/en/latest/datamanagement/globus.html` → `captures/globus.png` (B60)
- The proposal Google Form redirects to a Google sign-in; not captured, not shown.
