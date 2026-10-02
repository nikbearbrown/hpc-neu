#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
#  AICR — Single RTX PRO 6000 GPU Job (template)
#
#  Use the rtx-* partitions for workloads that:
#    • fit within 96 GB VRAM
#    • benefit from a Blackwell GPU without needing B200 scale
#    • are development / lighter inference workloads
#
#  The RTX PRO 6000 also supports BF16 and FP8 (Blackwell architecture).
#
#  Submit with:  sbatch rtx_single_gpu.slurm
# ─────────────────────────────────────────────────────────────────────────────

#SBATCH --job-name=my_rtx_job           # ← CHANGE: descriptive name
#SBATCH --partition=rtx-batch           # RTX PRO 6000 batch partition
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8               # ← CHANGE: num_workers + 1
#SBATCH --gres=gpu:1
#SBATCH --mem=32G
#SBATCH --time=04:00:00                 # ← CHANGE: expected runtime + 20%
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

mkdir -p logs

# ── Environment ───────────────────────────────────────────────────────────────
module purge
module load cuda/13.1
module load miniforge3/25.3.0-3
source activate myenv                   # ← CHANGE: your conda environment

echo "========================================"
echo "Job ID   : $SLURM_JOB_ID"
echo "Node     : $SLURMD_NODENAME"
echo "GPU      : $CUDA_VISIBLE_DEVICES"
echo "Start    : $(date)"
echo "========================================"

python scripts/01_gpu_verify.py

# Copy data to local storage if available
if [ -n "$TMPDIR" ] && [ -d "$TMPDIR" ]; then
    rsync -a /scratch/$USER/mydata/ $TMPDIR/mydata/
    DATA_DIR=$TMPDIR/mydata
else
    DATA_DIR=/scratch/$USER/mydata
fi

python train.py \
    --data-dir $DATA_DIR \
    --epochs 50 \
    --batch-size 128 \
    --bf16

echo "End : $(date)"

# After job: run `jobstats $SLURM_JOB_ID` to review efficiency.
