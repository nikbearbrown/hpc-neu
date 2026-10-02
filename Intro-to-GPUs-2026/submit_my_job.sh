#!/bin/bash
#SBATCH --job-name=gpu_job
#SBATCH --partition=gpu
#SBATCH --gres=gpu:v100-sxm2:1
#SBATCH --time=00:05:00  # HH:MM:SS
#SBATCH --output=gpu_job_%j.out

source "$(pwd)/gpu_env/bin/activate"
python example1/gpu_test_torch.py