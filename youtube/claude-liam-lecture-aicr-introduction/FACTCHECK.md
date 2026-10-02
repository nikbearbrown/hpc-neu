# FACTCHECK — AICR Introduction (lecture)

**What this is.** Every factual claim in the narration and on screen, checked. **Sources.** S = the source document `hpc/AICR-Introduction-2026/aicr-introduction.md`; D = the saved AICR documentation pages in `aicr/` (dated June 1, 2026); C = the live cluster, read-only, 2026-10-02 (`SESSION.md`). **Result.** 27 claims: 24 PASS, 3 CORRECTED. Checked 2026-10-02.

| # | Beat | Claim | Verdict | Source | Fix |
|---|---|---|---|---|---|
| 1 | BIDEA, B13 | AICR is for production runs; develop and test on Explorer first | PASS | S §Introduction | |
| 2 | B10 | AICR = AI Compute Resource | PASS | S | |
| 3 | B10 | Six universities at MGHPCC, with the Massachusetts AI Hub | PASS | S; D lists BU, Harvard, MIT, Northeastern, UMass, Yale | |
| 4 | B11 | 248 NVIDIA B200 GPUs | PASS | S; D (31 nodes × 8); C (31 B200 nodes) | |
| 5 | B11 | 152 RTX PRO 6000 GPUs | PASS | S; D (19 nodes × 8); C (19 RTX nodes) | source prose says "RTX6000 Pros"; the film uses the product name from its table and D |
| 6 | B11 | 400 GPUs in all | PASS | 248 + 152 | |
| 7 | B12 | fast storage, modern AI/ML software stack, CPU-only partition for analysis and cleaning | PASS | S | |
| 8 | B13 | Explorer is Northeastern's own HPC cluster; AICR is shared among the partner universities | PASS | S | |
| 9 | B20 | PIs submit a brief proposal through a form | PASS | S §Getting Started | |
| 10 | B21 | Open OnDemand address ood.aicr.ai; Northeastern username and password | PASS | S; D | |
| 11 | B21 | the sign-in page asks you to choose an identity provider | PASS | capture `captures/ood.png`; D "Select your institution from the login page" | |
| 12 | B22 | j.smith on Explorer becomes j_smith_neu on AICR | PASS | S; C (the account used is `ni_brown_neu`) | |
| 13 | B30 | /home/$USER, /scratch/$USER, /work/neu/$PROJECT and their purposes | PASS | S; C (paths exist) | |
| 14 | B40 | per-node CPU core counts | CORRECTED | S table says 64 cores for GPU nodes; D and C say 128 | not stated in the film |
| 15 | B31 | home quota 100 GB, 7-day recovery | PASS | S; D (100 GiB, 7-day snapshots) | |
| 16 | B31 | project directory: 7-day recovery | PASS | S; D | |
| 17 | B32 | scratch 10 TB, 15 million file cap, no recovery, 30-day purge | PASS | S; D (10 TiB, no snapshots, files older than 30 days purged). File cap is in S only | |
| 18 | B40 | five partitions: cpu, b200-batch, b200-devel, rtx-batch, rtx-devel; walltimes 24 h / 4 h | PASS | S table; D; C | source prose says "4 GPU based partitions", table lists 5 rows incl. cpu: film says "one CPU only, four with GPUs" |
| 19 | B40 | about 2.3 TB memory per GPU node | PASS | S; C (2,321,639 MB); D says 2.25 TB | "about" kept |
| 20 | B41 | batch: up to 24 h, multi-GPU; devel: 4 h, 4 running jobs per user | PASS | S; D | |
| 21 | B42, B43 | confirm multi-GPU use; a background process cancels idle GPU jobs; jobstats will be deployed | PASS | S | "will" kept: the source says it will be deployed |
| 22 | B44 | sinfo output; more partitions than five | PASS | C, verbatim | the live list has 7 (adds b200-fullnode, preemptable) |
| 23 | B51, B52 | the sbatch script | PASS | S lines 64–86, verbatim (multi-node comment omitted) | `cuda/13.1` checked on C: resolves to 13.1.1 |
| 24 | B53 | sbatch / squeue / scancel / sacct usage; mkdir -p logs | CORRECTED | S | the source's script does not write to `logs/`, so the film says "if your script writes logs into a folder, create it first" |
| 25 | B54 | srun command and "always set --time", exit releases | PASS | S, verbatim | |
| 26 | B55, B60 | OOD sessions submit to Slurm and count against devel limits; Globus is the primary method for large transfers; Northeastern has a subscription | PASS | S; capture `captures/globus.png` | source says Globus "is supposed to be" primary; film says "the primary method" |
| 27 | B61, B62 | yearly review; storage not permanent; move data back; rchelp@northeastern.edu | CORRECTED | S | source typo "reup" not used; meaning kept ("renews the request") |

## Stripped as datable

None needed: the film quotes no version numbers aloud. The capture captions carry their own date.

## Pronunciation note (for Bear)

Kokoro reads "AICR" as one word, "acre", as it did in the eleven earlier AICR films. Kept for consistency. If it should be spelled out, every beat that says it re-voices for free.
