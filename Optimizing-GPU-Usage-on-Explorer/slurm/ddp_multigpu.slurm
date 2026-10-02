#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
#  Explorer — Multi-GPU DistributedDataParallel (DDP) Job (template)
#
#  ONLY scale to multiple GPUs once a single GPU is > 80% utilised.  Multi-GPU
#  multiplies whatever efficiency you already have — it does not create it.
#  See Section 6 of the training.
#
#  The multigpu partition allows up to 24 h but requires a separate access
#  request.  Your code must be written for DDP (torchrun + DistributedSampler);
#  a plain single-GPU script will only ever use the first GPU.
#
#  Submit with:  sbatch ddp_multigpu.slurm
# ─────────────────────────────────────────────────────────────────────────────

#SBATCH --job-name=my_ddp_job            # ← CHANGE: descriptive name
#SBATCH --partition=multigpu              # 24 h; requires separate access request
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4               # one task per GPU
#SBATCH --gres=gpu:v100-sxm2:4                 # ← CHANGE: number of GPUs
#SBATCH --cpus-per-task=8                 # CPU workers per GPU process
#SBATCH --mem=128G                        # CPU RAM (NOT GPU VRAM)
#SBATCH --time=12:00:00                   # ← CHANGE: expected runtime + 20%
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

mkdir -p logs

# ── Environment ───────────────────────────────────────────────────────────────
# No modules needed — this cluster has no python module, and PyTorch's CUDA
# runtime ships in the wheels.  Just activate the venv.
source /scratch/$USER/Optimizing-GPU-Usage-on-Explorer/gpu_training_env/bin/activate  # ← CHANGE

echo "========================================"
echo "Job ID        : $SLURM_JOB_ID"
echo "Node          : $SLURMD_NODENAME"
echo "GPUs          : $CUDA_VISIBLE_DEVICES"
echo "Start time    : $(date)"
echo "========================================"

python scripts/01_gpu_verify.py

# ── Dataset location ─────────────────────────────────────────────────────────
# All filesystems here (/home, /scratch, /projects) are network filesystems (NFS).
# Keep your data as a few large files rather than millions of small ones, and let
# the DataLoader (num_workers / pin_memory / prefetch_factor) hide read latency.
DATA_DIR=/scratch/$USER/mydata                        # ← CHANGE: your data path
echo "Using DATA_DIR=$DATA_DIR"

# ── Launch DDP with torchrun ──────────────────────────────────────────────────
# --nproc_per_node must match the number of GPUs requested above.
# train_ddp.py should call dist.init_process_group('nccl') and wrap the model
# in DistributedDataParallel (see Section 6.3 of the training).
torchrun --standalone --nproc_per_node=4 train_ddp.py \   # ← CHANGE: your script
    --data-dir $DATA_DIR \
    --epochs 50 \
    --batch-size 256 \
    --fp16                                # FP16 on V100 (use --bf16 on A100/H100)

echo "========================================"
echo "End time : $(date)"
echo "========================================"

# ── Review efficiency after the job finishes ─────────────────────────────────
#   gpu-logs $SLURM_JOB_ID
# Also measure scaling efficiency (Section 6.4) — expect > 80%.  Below 70%
# means communication or I/O is the bottleneck, not compute.
