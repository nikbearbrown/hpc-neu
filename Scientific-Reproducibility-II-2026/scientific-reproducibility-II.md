# Research Computing Training
---

<img src="images/logo.png" alt="drawing" width="900"/>


## Presenter
---
Khurshid Shaymardanov \
HPC Systems Engineer \
Research Computing (RC) \
https://rc.northeastern.edu/research-computing-team/

# Version Control in Research — Git Walkthrough
**HPC Training Series · Scientific Reproducibility II**

---

**Requirements: `bash`, `git`, `awk`, `grep`, `sort` — nothing else.**

Every command here runs on any Linux or Mac system, including your HPC login node,
with no modules to load and no packages to install.

---

## The Scenario

You have RNA-seq count data from an experiment with two conditions
(treatment vs control, 3 replicates each).
You write a bash pipeline to filter low-count genes and produce a summary table.
You submit the results as a paper.

Six months later, a reviewer asks:

> *"What threshold did you use for low-count filtering?"*

Without Git, you would open a folder that looks like this:

```
filter.sh
filter_v2.sh
filter_final.sh
filter_final_USE_THIS.sh
results_old/
results_new/
results_for_paper/
results_for_paper_FINAL/
```

With Git, you run `git log` and the answer is right there.

---
### Without vs With Version Control

| Without Git ❌ | With Git ✅ |
|---|---|
| Files named `script_final_v2_REAL.py` | Every change has timestamp, author, message |
| Can't answer "what code produced figure 3?" | Tag the exact commit that generated your results |
| Collaborators overwrite each other's work | Branches for each person / experiment |
| No audit trail for reviewers | Full diff history forever |
| No way to roll back a bad change | `git revert` to any prior state |

---

### Research Scenarios Where Git Saves You

| Scenario | Git Solution |
|---|---|
| Reviewer asks "did you try parameter X=0.5?" | Checkout the branch where you tested it |
| Your postdoc leaves; new hire must rerun job | Clone repo, read README, exact commands in history |
| HPC config changed, broke pipeline | `git diff HEAD~1 slurm.conf` — spot it immediately |
| Collaboration across 3 institutions | Fork → branch → pull request; no emailing scripts |
| Publishing code alongside paper | Tag release → projects → [github repo] → citable DOI |

### 💡 The Git Mental Model

Git takes **snapshots** of your project, not diffs. Every `commit` is a complete picture of your files at that moment, linked to its parent. You navigate history by moving between snapshots.

```
  a3f8c21 ──── b7d2e14 ──── d9c1f37  (main)
               ↑
           branch point
```
---


## What this notebook covers

| Step | Command |
|---|---|
| Start tracking | `git init` |
| Ignore junk files | `.gitignore` |
| Save a snapshot | `git add` + `git commit` |
| See what changed | `git diff` + `git log` |
| Explore safely | `git switch -c` (branch) |
| Bring it back | `git merge` |
| Mark for paper | `git tag` |
| Shelve work | `git stash` | Switch tasks without committing half-done work |
| Run on HPC | Slurm + git guard |

---
## 0. Setup Check

Run this first. Everything needed should already be on your system.


```python
# Prerequites:

## SSHing into the cluster
ssh username@login.explorer.northeastern.edu

ssh k.shaymardanov@login.explorer.northeastern.edu

## For CLI (which is encouraged way to do), pick a compute node from short partition 
[k.shaymardanov@explorer-02 ~]$ srun --partition=short --pty bash

## For OOD option, use following steps to get ready for this session:
https://ood.explorer.northeastern.edu/pun/sys/dashboard > 
Standard Apps > 
Jupyter Notebook > 
username, short partition, 1 hr, 2 cores, work dir: /home/username/git-training

## If the git-training is missing, you can create any dir that you would prefer and cd into it
cd /home/username/git-training

## Once the working directory is ready, clone the repo to start working on the training
git clone https://github.com/northeastern-rc-training/Scientific-Reproducibility-II-2026.git
```


```python
# Check all required tools
for tool in git bash awk grep sort uniq wc cut; do
    if command -v $tool &>/dev/null; then
        echo "  OK  $tool  ($($tool --version 2>&1 | head -1))"
    else
        echo "  MISSING  $tool"
    fi
done

# Check if GitHub credentials are in place
echo "  name:  $(git config --global user.name  || echo 'NOT SET — run: git config --global user.name "Your Name"')"
echo "  email: $(git config --global user.email || echo 'NOT SET — run: git config --global user.email "you@uni.edu"')"
```

---
## 1. The Research Data

We generate synthetic RNA-seq count data entirely in bash using `awk`.
Each row is a gene. Each column is a sample (3 controls, 3 treated).

In a real project this file would be the output of a read-counting tool
(HTSeq, featureCounts, Salmon) — but the Git workflow is identical.


```python
cd /projects/username
mkdir -p rnaseq_project/{data,results,scripts,slurm}
cd rnaseq_project

awk 'BEGIN {
    srand(42)
    print "gene_id\tctrl_1\tctrl_2\tctrl_3\ttreat_1\ttreat_2\ttreat_3"
    for (i = 1; i <= 200; i++) {
        base = int(rand() * 2000)
        fold = (rand() > 0.8) ? 3 : 1
        printf "GENE%04d", i
        for (j = 1; j <= 3; j++)
            printf "\t%d", int(base * (0.8 + rand()*0.4))
        for (j = 1; j <= 3; j++)
            printf "\t%d", int(base * fold * (0.8 + rand()*0.4))
        printf "\n"
    }
}' /dev/null > data/counts.tsv

# Check on "Dimensions"
echo "  Rows (genes + header): $(wc -l < data/counts.tsv)"
echo "  Columns:               $(head -1 data/counts.tsv | awk '{print NF}')"

# First 5 rows of the file we have just created
head -5 data/counts.tsv | column -t
```

---
## 2. The Analysis Pipeline

A single bash script that:
1. Filters out low-count genes (below a threshold)
2. Computes per-gene mean counts for each condition
3. Produces a summary table

This is the file we will version-control through the session.


```python
cd rnaseq_project

cat > scripts/filter_and_summarise.sh << 'SCRIPT'
#!/usr/bin/env bash
# =============================================================
# filter_and_summarise.sh
# Filter low-count genes and compute condition means.
#
# Usage: bash scripts/filter_and_summarise.sh
# Output: results/summary.tsv
# =============================================================
set -euo pipefail   # exit on error, unset var, pipe failure

INPUT="data/counts.tsv"
OUTPUT="results/summary.tsv"

# ── PARAMETERS ── change these, then commit before re-running
MIN_COUNT=10        # filter: remove genes with mean count below this
LOG_FILE="results/run.log"

echo "[$(date --iso-8601=seconds)] Starting analysis" | tee "$LOG_FILE"
echo "  Input:      $INPUT"     | tee -a "$LOG_FILE"
echo "  Threshold:  $MIN_COUNT" | tee -a "$LOG_FILE"
echo "  Git commit: $(git rev-parse HEAD 2>/dev/null || echo 'not tracked')" | tee -a "$LOG_FILE"

# ── Step 1: Filter and compute means ──
awk -v threshold="$MIN_COUNT" '
BEGIN { OFS="\t" }
NR == 1 {
    print "gene_id", "mean_ctrl", "mean_treat", "fold_change", "status"
    next
}
{
    # Columns: gene ctrl1 ctrl2 ctrl3 treat1 treat2 treat3
    mean_ctrl  = ($2 + $3 + $4) / 3
    mean_treat = ($5 + $6 + $7) / 3
    overall    = (mean_ctrl + mean_treat) / 2

    # Filter: skip genes below threshold in both conditions
    if (overall < threshold) next

    # Fold change (treat / ctrl), guard against division by zero
    fc = (mean_ctrl > 0) ? mean_treat / mean_ctrl : 0

    # Call direction
    if      (fc >= 2.0) status = "UP"
    else if (fc <= 0.5) status = "DOWN"
    else                status = "NS"

    printf "%s\t%.1f\t%.1f\t%.2f\t%s\n", $1, mean_ctrl, mean_treat, fc, status
}
' "$INPUT" > "$OUTPUT"

# ── Step 2: Report ──
TOTAL=$(awk 'NR>1' "$INPUT" | wc -l)
KEPT=$(awk 'NR>1' "$OUTPUT" | wc -l)
UP=$(awk 'NR>1 && $5=="UP"'   "$OUTPUT" | wc -l)
DOWN=$(awk 'NR>1 && $5=="DOWN"' "$OUTPUT" | wc -l)
NS=$(awk 'NR>1 && $5=="NS"'   "$OUTPUT" | wc -l)

echo "" | tee -a "$LOG_FILE"
echo "── Results ──────────────────"   | tee -a "$LOG_FILE"
echo "  Total genes:   $TOTAL"         | tee -a "$LOG_FILE"
echo "  After filter:  $KEPT"          | tee -a "$LOG_FILE"
echo "  Upregulated:   $UP"            | tee -a "$LOG_FILE"
echo "  Downregulated: $DOWN"          | tee -a "$LOG_FILE"
echo "  Not significant: $NS"          | tee -a "$LOG_FILE"
echo "  Output: $OUTPUT"               | tee -a "$LOG_FILE"
echo "[$(date --iso-8601=seconds)] Done" | tee -a "$LOG_FILE"
SCRIPT

chmod +x scripts/filter_and_summarise.sh
echo 'Script written: scripts/filter_and_summarise.sh'
wc -l scripts/filter_and_summarise.sh
```

---
## 3. `git init` — Start Tracking

Do this **before** your first run, not after.
The `.git/` folder is Git's database — one per project.


```python
cd rnaseq_project

git init

# Set identity if not already configured globally if not done yet
git config user.name  'Research User'
git config user.email 'user@university.edu'

echo ''
ls -la | grep git
```

---
## 4. `.gitignore` — Keep Results Out of Git

Results, logs, and large data files should **not** go in Git.
Track the code that makes them, not the files themselves.

Large data lives in your institutional storage or /projects — not in a git repo.


```python
cd rnaseq_project

cat > .gitignore << 'EOF'
# ── Results and outputs ──
results/

# ── Raw data (large — store in institutional repository)
data/*.fastq
data/*.fastq.gz
data/*.bam
data/*.bai

# ── Log files ──
*.log
slurm-*.out

# ── Editor / OS noise ──
.DS_Store
*.swp
*~

# ── Allow small reference files through ──
!results/summary.tsv     # the table itself is small enough to track
!results/run.log         # the run log is the audit trail
EOF

cat .gitignore
```

---
## 5. `README.md` — Reproduction Instructions

Write this before your first commit.
It is a contract with anyone who clones your repo — including future you.


```python
cd rnaseq_project

cat > README.md << 'EOF'
# RNA-seq Count Filtering Pipeline

Companion code for [Paper Title], [Journal], [Year].  
Contact: your@university.edu

## Requirements

bash, awk, grep, sort — no additional installs needed.

## Reproduce the paper results

```bash
git clone https://github.com/you/rnaseq_project
cd rnaseq_project
git checkout v1.0-submission      # exact code used in paper
bash scripts/filter_and_summarise.sh
# Output: results/summary.tsv
```

## The structure of the project

rnaseq_project
├── data
│   └── counts.tsv
├── README.md
├── results
│   ├── run.log
│   ├── slurm_job_id.err
│   ├── slurm_job_id.out
│   └── summary.tsv
├── scripts
│   ├── charts
│   │   ├── bar_status.sh
│   │   └── hist_foldchange.sh
│   └── filter_and_summarise.sh
└── slurm
    └── run_pipeline.sh

## Parameters

All parameters are defined at the top of `scripts/filter_and_summarise.sh`.  
The exact values used in each run are recorded in `results/run.log`.

| Parameter | Default | Description |
|---|---|---|
| `MIN_COUNT` | 10 | Minimum mean count to keep a gene |

## Data availability

Raw counts: [/projects]
EOF
```

---
## 6. First Commit

Three commands you will use dozens of times:

| Command | What it does |
|---|---|
| `git status` | What has changed since last commit? |
| `git add <file>` | Choose what goes into the next snapshot |
| `git commit -m '...'` | Save the snapshot permanently |


```python
cd rnaseq_project

git status

git add .

git commit -m 'Initial pipeline: filter script, README, .gitignore'

git log --oneline
```

---
## 7. Run → Inspect → Commit

Run the analysis. Look at the results. Commit the state that produced them.
This links every result permanently to the code and parameters that made it.


```python
cd rnaseq_project

bash scripts/filter_and_summarise.sh
```


```python
cd rnaseq_project

# first 10 lines of the output from the previous script execution
head -10 results/summary.tsv | column -t

# Status breakdown
awk 'NR>1 {print $5}' results/summary.tsv | sort | uniq -c | sort -rn

# Top 5 upregulated genes
awk 'NR>1 && $5=="UP" {print}' results/summary.tsv \
    | sort -t$'\t' -k4 -rn \
    | head -5 \
    | column -t
```


```python
cd rnaseq_project

# Commit the run outputs (summary + log are allowed through .gitignore)
git add results/summary.tsv results/run.log
git commit -m 'analysis: baseline run, MIN_COUNT=10, 200 genes, threshold=10'

git log --oneline
```

### ⚛️ 7.1. Atomic Commits — One Logical Change Per Commit

```
❌  "fixed stuff and added new feature and changed config"
✅  "Fix off-by-one in loop bounds for particle indexing"
```

- Each commit should do **one thing** — reviewers and your future self will thank you  
- If you're writing "and" in a commit message, split the commit  
- Use `git add -p` to stage only specific hunks within a file

---

### 📝 7.2. Conventional Commit Messages

Format: `<type>(<scope>): <short summary>`

Types for research: `feat`, `fix`, `data`, `analysis`, `refactor`, `docs`, `config`, `perf`

```
feat(preprocessing): add outlier detection via IQR filter
fix(slurm): correct memory allocation for GPU nodes  
data: update training set to v2.3 (1.2M samples)
analysis(fig3): reproduce with corrected normalization
docs: add reproduction instructions to README
```

Git log then reads like a **changelog**. Bonus: `git log --grep="fix"` to find all bug fixes instantly.

---
## 8. `git diff` — See Exactly What Changed

Before you commit anything, always check what you are about to commit.
`git diff` shows you line-by-line changes — red removed, green added.


```python
cd rnaseq_project

# Make a small change: raise the threshold
sed -i 's/MIN_COUNT=10/MIN_COUNT=20/' scripts/filter_and_summarise.sh

# What changed? 
git diff scripts/filter_and_summarise.sh
```


```python
cd rnaseq_project

bash scripts/filter_and_summarise.sh

# Status breakdown with MIN_COUNT=20 
awk 'NR>1 {print $5}' results/summary.tsv | sort | uniq -c

git add scripts/filter_and_summarise.sh results/summary.tsv results/run.log
git commit -m 'analysis: raise MIN_COUNT 10->20, stricter low-count filter'

git log --oneline
```

---
## 9. `git log` — Your Audit Trail

`git log` shows who changed what and when.
Every line of your history is a documented decision.


```python
cd rnaseq_project

# Compact log 
git log --oneline

# Detailed log 
git log --stat

# Search for a specific change 
git log --oneline --grep='MIN_COUNT'
```

---
## 10. Branches — Safe Exploration

A reviewer asks you to try a fold-change cutoff of 1.5 instead of 2.0.
You don't know yet if this will go in the paper.
**Never modify your working script directly for speculative changes.**

Create a branch: a parallel version of the project that leaves `main` untouched.


```python
cd rnaseq_project

# Create and switch to a branch
git switch -c explore/fc-cutoff-1.5

# Listing the branches
git branch --list
```


```python
cd rnaseq_project

# Modify the fold-change cutoffs in the script
sed -i 's/fc >= 2.0/fc >= 1.5/' scripts/filter_and_summarise.sh
sed -i 's/fc <= 0.5/fc <= 0.67/' scripts/filter_and_summarise.sh

# Check the change before committing
git diff scripts/filter_and_summarise.sh
```


```python
cd rnaseq_project

bash scripts/filter_and_summarise.sh

# Results with FC cutoff 1.5 from above change
awk 'NR>1 {print $5}' results/summary.tsv | sort | uniq -c

git add scripts/filter_and_summarise.sh results/summary.tsv results/run.log
git commit -m 'explore: relax FC cutoff to 1.5/0.67 (reviewer suggestion)'
```


```python
cd rnaseq_project

# Switch back to main — original script is exactly as you left it
git switch main

# FC cutoffs in main script 
grep 'fc >=' scripts/filter_and_summarise.sh
```

---
## 11. Merge — Bringing Results Back

The relaxed cutoff looks good. You decide to include it in the revised (which normally can happen as PR or pull request in GitHub) submission.
If you are the only person doing the ressearch, then doing the following
Merge the branch into main.


```python
cd rnaseq_project

git merge explore/fc-cutoff-1.5 --no-ff \
  -m 'Merge explore/fc-cutoff-1.5: FC >= 1.5 for revised submission'

# Full history 
git log --oneline --graph --all

# once the project is merged, then we dont need the exploration branch anymore and thus we will delete it
git branch -d explore/fc-cutoff-1.5
```

---
## 12. `git tag` — Mark the Submission

Before you submit the paper: tag the exact commit that produced your figures.
This is permanent. `git checkout v1.0-submission` will give you
bit-identical code at any point in the future.


```python
cd rnaseq_project

git tag -a v1.0-submission \
  -m 'Code submitted to journal, 2025-09-01. MIN_COUNT=20, FC=1.5'

# Existing tags
git tag -l -n1

git log --oneline --graph

# Once things look good, we can then push (upload) the data into the remote repository which is a GitHub
git push origin main

# tags need explicit push'
git push origin v1.0-submission   
```

---
## 13. Time Travel — Reproducing an Earlier Result

A reviewer asks: *"What were your results with the original MIN_COUNT=10?"*

You don't need to remember. Git remembers.


```python
cd rnaseq_project

# Full history
git log --oneline

# Finding the commit with MIN_COUNT=10
git log --oneline --grep='MIN_COUNT=10'
```


```python
cd rnaseq_project

# Get the hash of the first analysis commit
HASH=$(git log --oneline --grep='MIN_COUNT=10' | awk '{print $1}')
echo "Restoring script from commit: $HASH"

# Restore just that one file — working tree only, not a full checkout
git checkout $HASH -- scripts/filter_and_summarise.sh

grep 'MIN_COUNT\|fc >=' scripts/filter_and_summarise.sh

bash scripts/filter_and_summarise.sh

# Status breakdown at MIN_COUNT=10 
awk 'NR>1 {print $5}' results/summary.tsv | sort | uniq -c

# Restore current version
git checkout HEAD -- scripts/filter_and_summarise.sh
```

---
## 14. Slurm — Running on HPC

Two rules for HPC + Git:

1. **Commit before you submit.** Every job must trace to a specific commit.
2. **Record the commit hash in the job log.** Then result files are always traceable.

The script below enforces both automatically.


```python
cd rnaseq_project

cat > slurm/run_pipeline.sh << 'EOF'
#!/bin/bash
#SBATCH --job-name=rnaseq_filter
#SBATCH --partition=compute
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=results/slurm_%j.out
#SBATCH --error=results/slurm_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=your@university.edu

# ── Reproducibility header — printed in every job log ────────
echo "Job ID:     $SLURM_JOB_ID"
echo "Node:       $SLURM_NODELIST"
echo "Date:       $(date --iso-8601=seconds)"
echo "Git commit: $(git rev-parse HEAD)"
echo "Git branch: $(git rev-parse --abbrev-ref HEAD)"
echo "----------------------------------------------"

# ── Guard: refuse to run with uncommitted changes ────────────
if ! git diff --quiet || ! git diff --staged --quiet; then
    echo 'ERROR: uncommitted changes detected.'
    echo 'Commit your changes before submitting a job.'
    echo '  git status'
    echo '  git add scripts/ && git commit -m "..."'
    exit 1
fi

# ── Run the pipeline ─────────────────────────────────────────
bash scripts/filter_and_summarise.sh

# ── Tag this exact run in git ─────────────────────────────────
git tag run-$SLURM_JOB_ID \
  -m "Slurm job $SLURM_JOB_ID on $SLURM_NODELIST $(date --iso-8601)"
echo "Tagged: run-$SLURM_JOB_ID"

echo 'Done.'
EOF

chmod +x slurm/run_pipeline.sh
echo 'Slurm script written: slurm/run_pipeline.sh'
echo ''
echo 'On HPC: sbatch slurm/run_pipeline.sh'
echo '        squeue -u $USER'
echo '        tail -f results/slurm_<jobid>.out'
```

The guard block is the key habit:

```bash
if ! git diff --quiet || ! git diff --staged --quiet; then
    echo 'ERROR: uncommitted changes. Commit before submitting.'
    exit 1
fi
```

This makes it **structurally impossible** to produce a result you cannot trace.
Combined with `git tag run-$SLURM_JOB_ID`, every output file on your cluster
maps to an exact commit — even years later.


```python
cd rnaseq_project

git add slurm/
git commit -m 'ci: Slurm job script with uncommitted-change guard'

git log --oneline --graph --all
```

---
## ✏️ Exercises

Work in your own terminal. All you need is bash and git.

---

### Exercise 1 — Make a documented change

Change `MIN_COUNT` from `20` to `50` in `scripts/filter_and_summarise.sh`.
Pretend a collaborator measured the noise floor and determined 50 is safer.

1. Edit the file
2. `git diff` — verify the change
3. Run the script
4. `git add` + `git commit -m '...'` with a message that explains *why*, not just *what*
5. `git log --oneline` — confirm it's recorded


```python
# Exercise 1 — your workspace
cd rnaseq_project

# YOUR CODE HERE
# sed -i 's/MIN_COUNT=20/MIN_COUNT=50/' scripts/filter_and_summarise.sh
# git diff
# bash scripts/filter_and_summarise.sh
# git add scripts/filter_and_summarise.sh results/summary.tsv results/run.log
# git commit -m '...'

echo 'Exercise 1'
```

---
### Exercise 2 — A branch for a risky experiment

You want to try adding a third column of output: the log2 fold change.
You don't know if it will work. Put it on a branch.

```bash
git switch -c feature/log2fc
```

In `filter_and_summarise.sh`, modify the `printf` line to add log2fc:

```bash
# Change the header line:
print "gene_id", "mean_ctrl", "mean_treat", "fold_change", "log2fc", "status"

# Add log2fc calculation before the printf:
log2fc = (fc > 0) ? log(fc)/log(2) : -999

# Update printf to include it:
printf "%s\t%.1f\t%.1f\t%.2f\t%.2f\t%s\n", $1, mean_ctrl, mean_treat, fc, log2fc, status
```

Run it, commit, merge into main.


```python
# Exercise 2 — your workspace
cd rnaseq_project

# YOUR CODE HERE
# git switch -c feature/log2fc
# ... edit the script ...
# bash scripts/filter_and_summarise.sh
# git add scripts/filter_and_summarise.sh results/
# git commit -m 'feat: add log2fc column to summary output'
# git switch main
# git merge feature/log2fc --no-ff -m 'Merge feature/log2fc'

echo 'Exercise 2'
```

---
### Exercise 3 — The reviewer question

Reproduce the exact results from the very first run (MIN_COUNT=10, FC=2.0).

```bash
git log --oneline                            # find the right commit hash
git checkout <hash> -- scripts/filter_and_summarise.sh
bash scripts/filter_and_summarise.sh         # original result
git checkout HEAD -- scripts/filter_and_summarise.sh  # restore
```

Compare the summary.tsv gene counts with what you have now.
How many fewer genes passed the stricter filter?


```python
# Exercise 3 — your workspace
cd rnaseq_project

echo '=== History ==='
git log --oneline

# YOUR CODE HERE
# HASH=$(git log --oneline | grep 'MIN_COUNT=10' | awk '{print $1}')
# git checkout $HASH -- scripts/filter_and_summarise.sh
# bash scripts/filter_and_summarise.sh
# awk 'NR>1' results/summary.tsv | wc -l
# git checkout HEAD -- scripts/filter_and_summarise.sh

echo 'Exercise 3'
```

---
## 15. Seeing Branch State in the Terminal

Two things that should be in every researcher's git setup:
a short alias for the branch graph, and a shell function that
puts the branch name permanently in your prompt.

### `git log --graph` — the branch map


```python
cd rnaseq_project

# The most useful orientation command in git
# --oneline  compact one line per commit
# --graph    ASCII art of the branch/merge structure
# --all      show every branch and tag, not just current
# --decorate label each commit with its branch/tag names
git log --oneline --graph --all --decorate
```


```python
# That command is 40 characters to type every time.
# Set it as a two-letter alias once, use it forever.

git config --global alias.lg 'log --oneline --graph --all --decorate'

# git lg (your new alias) 
cd rnaseq_project && git lg

# Two more useful aliases:
git config --global alias.st   'status --short --branch'
git config --global alias.last 'log -1 --stat'

#git st 
cd rnaseq_project && git st

# git last 
cd rnaseq_project && git last
```

These three aliases cover 90% of daily orientation needs:

| Alias | Expands to | Use when |
|---|---|---|
| `git lg` | `log --oneline --graph --all --decorate` | Where am I in history? What branches exist? |
| `git st` | `status --short --branch` | What files have I changed? |
| `git last` | `log -1 --stat` | What did my last commit actually contain? |


```python
# Apply the prompt function for this session only (no ~/.bashrc edit needed)
git_branch() {
    git rev-parse --abbrev-ref HEAD 2>/dev/null | awk '{printf " (" $0 ")"}'
}

cd rnaseq_project

# Let's make sure we are on main branch
echo "rnaseq_project$(git_branch)"

# creating and switching to demo/promt-test branch
git switch -c demo/prompt-test 2>/dev/null

# switching back to main and deleting the test branch
git switch main
git branch -d demo/prompt-test
```

---
## 16. CLI Charts — Exploratory Branch

Pure ASCII charts using only `awk` and `printf`.
No Python, no R, no display server — runs on any login node.

We do this on its own branch: the charts are exploratory
and we may not want them in main permanently.


```python
cd rnaseq_project
git switch -c explore/cli-charts
mkdir -p scripts/charts
echo "On branch: $(git rev-parse --abbrev-ref HEAD)"
```

### Chart 1 — Bar chart: UP / DOWN / NS counts


```python
cd rnaseq_project

cat > scripts/charts/bar_status.sh << 'SCRIPT'
#!/usr/bin/env bash
# Horizontal bar chart of gene regulation status
# Usage: bash scripts/charts/bar_status.sh [summary.tsv]
INPUT="${1:-results/summary.tsv}"
BAR_CHAR='█'
MAX_WIDTH=40

echo ''
echo 'Gene regulation status'
echo '────────────────────────────────────────────────'

awk -v w=$MAX_WIDTH -v c="$BAR_CHAR" '
NR==1 { next }
{ counts[$5]++ }
END {
    max = 0
    for (k in counts) if (counts[k] > max) max = counts[k]
    for (k in counts) {
        bar_len = int(w * counts[k] / max)
        bar = ""
        for (i = 0; i < bar_len; i++) bar = bar c
        printf "  %-6s %5d  %s\n", k, counts[k], bar
    }
}
' "$INPUT" | sort -k1

echo ''
TOTAL=$(awk 'NR>1' "$INPUT" | wc -l)
echo "  Total genes passing filter: $TOTAL"
echo ''
SCRIPT

chmod +x scripts/charts/bar_status.sh
bash scripts/charts/bar_status.sh
```

### Chart 2 — Histogram: fold change distribution


```python
cd rnaseq_project

cat > scripts/charts/hist_foldchange.sh << 'SCRIPT'
#!/usr/bin/env bash
# Histogram of log2 fold changes (column 4 of summary.tsv)
# Usage: bash scripts/charts/hist_foldchange.sh [summary.tsv]
INPUT="${1:-results/summary.tsv}"
BINS=12
BAR_CHAR='▒'
MAX_WIDTH=36

echo ''
echo 'log2(Fold Change) Distribution'
echo '────────────────────────────────────────────────'

awk -v bins=$BINS -v w=$MAX_WIDTH -v c="$BAR_CHAR" '
NR==1 { next }
$4 > 0 {
    l2 = log($4) / log(2)
    vals[++n] = l2
    if (n==1 || l2 < mn) mn = l2
    if (n==1 || l2 > mx) mx = l2
}
END {
    width = (mx - mn) / bins
    for (i = 1; i <= n; i++) {
        b = int((vals[i] - mn) / width)
        if (b >= bins) b = bins - 1
        counts[b]++
    }
    max_c = 0
    for (b = 0; b < bins; b++)
        if (counts[b]+0 > max_c) max_c = counts[b]

    for (b = 0; b < bins; b++) {
        lo  = mn + b * width
        hi  = lo + width
        cnt = counts[b]+0
        bar_len = (max_c > 0) ? int(w * cnt / max_c) : 0
        bar = ""
        for (i = 0; i < bar_len; i++) bar = bar c
        printf "  [%+5.2f to %+5.2f]  %4d  %s\n", lo, hi, cnt, bar
    }
    printf "\n  x-axis: log2(fold change)   n = %d genes\n", n
}
' "$INPUT"
echo ''
SCRIPT

chmod +x scripts/charts/hist_foldchange.sh
bash scripts/charts/hist_foldchange.sh
```


```python
cd rnaseq_project

git add scripts/charts/
git commit -m 'feat: add bar chart and fold-change histogram (ASCII, awk-only)'

# Branch graph 
git lg

# Switching to main branch
git switch main

# Merging the exploratory brnach into main and removing the left over
git merge explore/cli-charts --no-ff -m 'Merge explore/cli-charts: bar + histogram charts'
git branch -d explore/cli-charts

# Final graph
git lg
```

---
## Quick Commands Reference

```bash
# ── Daily workflow ───────────────────────────────────────────
git status                    # what has changed?
git diff <file>               # show line-by-line changes
git add <file>                # stage a file
git add .                     # stage everything
git commit -m 'clear message' # save the snapshot
git log --oneline             # view history

# ── Branches ────────────────────────────────────────────────
git switch -c explore/idea    # new branch
git switch main               # back to main
git merge explore/idea --no-ff -m 'Merge ...'  # bring it back
git branch -d explore/idea    # clean up

# ── Time travel ──────────────────────────────────────────────
git log --oneline             # find the hash
git checkout <hash> -- file   # restore one file from history
git checkout HEAD -- file     # undo the restore
git diff HEAD~1 file          # what changed in the last commit?

# ── Marking submissions ──────────────────────────────────────
git tag -a v1.0 -m 'Paper submission 2025-09-01'
git push origin main
git push origin v1.0          # tags need explicit push

# ── Searching history ────────────────────────────────────────
git log --grep='MIN_COUNT'    # find commits mentioning a term
git log -p -- script.sh       # full diff history of one file
git blame script.sh           # who wrote each line, and when
```

---
*Next in the series: Containers & Singularity — reproducible environments on HPC.*

---

### ❓ Common Questions

**Q: Can I use Git for large datasets?**  
Not directly. Use **Git LFS** for files up to ~2GB, or better yet **DVC** (Data Version Control) which layers on Git and stores data in S3/GCS/HPC scratch. Track the data manifest in Git, data elsewhere.

**Q: How do I fix a bad commit?**  
`git commit --amend` for the last commit (before pushing). `git revert <hash>` to undo a pushed commit safely. Never use `git reset --hard` on shared branches.

**Q: What about Jupyter notebooks in Git?**  
Notebooks contain output metadata that creates noisy diffs. Use **nbstripout** (`pip install nbstripout`) to clear outputs before committing, or **Jupytext** to sync notebooks as clean `.py` scripts. Both install with pip.

**Q: How do I handle merge conflicts?**  
Git marks conflicts with `<<<<<<<` markers in files. Open the file, choose which version (or combine both), remove the markers, then `git add` and `git commit`. Use `git mergetool` for a visual interface.

---

### 📚 Resources

- 📖 **Pro Git book** (free) — [git-scm.com/book](https://git-scm.com/book) — the definitive reference
- 🔬 **The Turing Way** — [book.the-turing-way.org](https://book.the-turing-way.org) — research software engineering & reproducibility
- 🗃️ **DVC** — [dvc.org](https://dvc.org) — version control for data & ML experiments
- 🎮 **Learn Git Branching** — [learngitbranching.js.org](https://learngitbranching.js.org) — interactive visual tutorial
- 🚫 **gitignore.io** — [toptal.com/developers/gitignore](https://www.toptal.com/developers/gitignore) — auto-generate .gitignore for any stack

---

### 🔜 Next in the Series

