#!/bin/bash
#SBATCH --job-name=gpu_job
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err       # %x is for job name, %j is for SLURM job ID


# Load modules if needed
# module load anaconda3/2024.06
# module load cuda/12.8.0

# Activate virtual environment
source gpu_env/bin/activate

# Run your script
python gpu_test_torch.py
