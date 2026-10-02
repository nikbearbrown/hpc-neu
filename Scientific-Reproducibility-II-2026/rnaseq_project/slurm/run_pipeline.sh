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