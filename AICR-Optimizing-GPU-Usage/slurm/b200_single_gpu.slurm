#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
#  AICR — Single B200 GPU Training Job (template)
#
#  Copy this file, adjust the values marked with ← CHANGE, and submit with:
#      sbatch b200_single_gpu.slurm
#
#  Before submitting, run this job in a devel session first:
#      srun -p b200-devel -N 1 -n 1 -c 8 --mem=32G --gres=gpu:1 \
#           --time=01:00:00 --pty bash
#  Confirm GPU utilisation > 70% with:  watch -n 1 nvidia-smi
# ─────────────────────────────────────────────────────────────────────────────

#SBATCH --job-name=my_training           # ← CHANGE: descriptive name
#SBATCH --partition=b200-batch           # B200 batch partition (24 h max)
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8               # ← CHANGE: set to num_workers + 1
#SBATCH --gres=gpu:1                    # one GPU
#SBATCH --mem=32G                       # CPU RAM (not GPU VRAM)
#SBATCH --time=04:00:00                 # ← CHANGE: expected runtime + 20%
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

# Create log directory before submitting (or add the mkdir here)
mkdir -p logs

# ── Environment ───────────────────────────────────────────────────────────────
module purge
module load cuda/13.1
module load miniforge3/25.3.0-3
source activate myenv                   # ← CHANGE: your conda environment

echo "========================================"
echo "Job ID        : $SLURM_JOB_ID"
echo "Node          : $SLURMD_NODENAME"
echo "GPUs          : $CUDA_VISIBLE_DEVICES"
echo "Start time    : $(date)"
echo "========================================"

# ── Verify GPU allocation (always) ───────────────────────────────────────────
python scripts/01_gpu_verify.py

# ── Copy dataset to node-local storage if available ──────────────────────────
# Check for $TMPDIR (node-local fast storage) and copy your data there.
# Fall back to /scratch if $TMPDIR is not set on this node.
if [ -n "$TMPDIR" ] && [ -d "$TMPDIR" ]; then
    echo "Copying dataset to node-local storage ($TMPDIR) ..."
    rsync -a /scratch/$USER/mydata/ $TMPDIR/mydata/   # ← CHANGE: your data path
    DATA_DIR=$TMPDIR/mydata
    echo "Done. Using DATA_DIR=$DATA_DIR"
else
    DATA_DIR=/scratch/$USER/mydata                    # ← CHANGE: your data path
    echo "TMPDIR not available, using DATA_DIR=$DATA_DIR"
fi

# ── Training ──────────────────────────────────────────────────────────────────
python train.py \                                     # ← CHANGE: your script
    --data-dir $DATA_DIR \
    --epochs 50 \
    --batch-size 256 \
    --bf16                               # always use BF16 on B200

echo "========================================"
echo "End time : $(date)"
echo "========================================"

# ── Review Jobstats after the job finishes ────────────────────────────────────
# Run this command after the job completes:
#   jobstats $SLURM_JOB_ID
# Look for GPU utilisation > 70%.  If lower, consult Section 7 of the training.
