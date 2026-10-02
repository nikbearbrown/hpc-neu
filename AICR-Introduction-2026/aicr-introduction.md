
<img src="NU_logo_small.png" alt="drawing" width="900"/>

# AICR Training

## Introduction to AICR
The AI Compute Resource (AICR) High Performance Computer (HPC) cluster is a joint effort between the 6 universities at the Massachusetts Green High Performance Computing Center (MGHPCC) and Massachusetts AI Hub. It is providing advanced GPU compute for AI driven research in the form of GPUs, fast storage, and a modern software stack for AI/ML research workflows.

AICR is a SLURM based cluster similar to the Explorer HPC cluster. AICR will have 248 NVIDIA B200 GPUs and 152 NVIDIA RTX6000 Pros GPUs for your AI research needs along with dedicated storage for your research projects. There is also a dedicated CPU only partition for data analysis, cleaning, and routines that do not require GPUs for compute.

AICR should be viewed as an extension to Northeastern's own Explorer HPC cluster in terms of compute resources for the researchers. With this in mind, the research work on AICR should have been tested and developed on the Explorer HPC. After that, AICR is to be utilized as a means of running production runs since this is a shared compute resource among all universities at the MGHPCC data center and Massachusetts AI Hub.

## Getting Started on AICR
In order to get started on AICR, faculty and principal investigators (PI) are requested to [submit a brief proposal using this form](https://docs.google.com/forms/d/e/1FAIpQLSfg1Vj9NRbn2ViPNFsypAGaoQJoKkr-BCssXZhKtDcNTCVYRg/viewform?pli=1). 

## Signing into AICR
You can sign in to AICR Open OnDemand(OOD) using Northeastern Credentials.

### Open OnDemand Login
The Open OnDemand address for AICR is https://ood.aicr.ai/

You will use your Northeastern username and password to sign into AICR.

On AICR, your username on the cluster itself it slightly different to help distinguish the accounts from the partner universities. For example, if your username is `j.smith` on Explorer, it becomes `j_smith_neu` on AICR.

## Storage on AICR
Similar to the Explorer HPC cluster, everyone will have a `/home/$USER`, a `/scratch/$USER`, and a `/work/neu/$PROJECT` directory.

The usage and purpose of each directory is the same as the Explorer HPC. Home directories are for small scripts and items related to your research environment that you require, the scratch directory is for temporary research output for running jobs, and the project directory is for collaborative longer term research work.

The notable differences from Explorer cluster are as follows:

- A user's home directories have a quota of 100 GB and files can be recovered up to 7 days if you accidentally delete them.
- A user's scratch directory has a quota of 10 TB with a 15 million file count cap. There is no file recovery in a user's scratch directory and there is a 30 day scratch purge policy so please be mindful to move important files out of your scratch directory.
- The PI's project directory is longer term storage for research and files can be recovered up to 7 days if you accidentally delete them. 

## Compute Resources on AICR
AICR will have 4 GPU based partitions for your scientific workflows. Each partition has been setup with a given purpose that enables a variety of targeted jobs.

| Partition  | CPU                     | GPU            | Max walltime | Max jobs per user | Purpose                              |
|------------|-------------------------|----------------|--------------|-------------------|--------------------------------------|
| cpu        | AMD EPYC 9745 128 Cores | none           | 24 h         | 4 running         | Data transformation and analysis     |
| b200-batch | AMD EPYC 9575F 64 Cores | B200           | 24 h         | N/A               | Training and inference (batch)       |
| b200-devel | AMD EYPC 9575F 64 Cores | B200           | 4 h          | 4 running         | Interactive development and OOD      |
| rtx-batch  | AMD EYPC 9575F 64 Cores | RTX PRO 6000   | 24 h         | N/A               | Training and inference (batch)       |
| rtx-devel  | AMD EYPC 9575F 64 Cores | RTX PRO 6000   | 4 h          | 4 running         | Interactive development and OOD      |

*CPU nodes have total of 1.1 TB and GPU nodes have total or 2.3 TB of memory per node*

The `batch` partitions are for non-interactive `sbatch` submissions and support multi-GPU jobs. Confirm your code can actually use multiple GPUs (e.g. DDP, NCCL-backed allreduce, or proper MPI ranks per GPU) before requesting more than one.

The `devel` partitions are for interactive work through `srun` or Open OnDemand. They have shorter walltimes and a 4-running-job limit per user. Cancel your interactive session when you are done so resources free up for others.

A background process monitors GPU utilization and will cancel jobs that sit idle, so do not hold a GPU you are not actively using. For analytical purposes and to provide statistics about user jobs,  [jobstats](https://princetonuniversity.github.io/jobstats/) will also be deployed on AICR.

## Submitting Jobs on AICR
AICR is a SLURM based HPC like the Explorer HPC cluster which makes the job submission a familiar experience. The following will outline how to submit sbatch jobs, srun jobs, and to use Open OnDemand on AICR.
AICR uses Slurm, so the workflow will be similar to the Explorer cluster. The examples below cover `sbatch`, `srun`, and Open OnDemand.

### sbatch
Create a submission script, then submit with `sbatch myjob.slurm`. Make the log directory before submitting (`mkdir -p logs`) so Slurm does not fail to write the output files.

```bash
#!/bin/bash
#SBATCH --partition=b200-batch
#SBATCH --job-name=b200_test_job
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=b200_test_%j.out
#SBATCH --error=b200_test_%j.err

module purge
module load cuda/13.1
module load miniforge3/25.3.0-3
source activate myenv

# For single-process multi-GPU runs (e.g. PyTorch DDP within a node),
# use torchrun and request the appropriate number of GPUs with
# --gres=gpu:N. For multi-node, increase --nodes and use srun/torchrun
# with the right rendezvous setup.

python training.py
```

Submit with:
```bash
$ sbatch myjob.slurm
```

Useful follow-up commands:

- `squeue -u $USER` to see your queued and running jobs
- `scancel <jobid>` to cancel a job
- `sacct -j <jobid> --format=JobID,Elapsed,MaxRSS,State` to see post-run resource usage

### srun
For an interactive shell on a GPU compute node:

```bash
srun -p rtx-devel -N 1 -n 1 -c 8 --mem=16G --gres=gpu:1 --time=01:00:00 --pty bash
```

This drops you onto a compute node with the requested resources. Always set `--time` so the session ends if you forget to exit. Type `exit` (or close the terminal) to release the allocation.

### Open OnDemand
Open OnDemand (https://ood.aicr.ai/) will be the easiest way to launch interactive GUI sessions. Potential GUI apps may include JupyterLab, XFCE Desktop etc.

When launching an app, there'll be options to choose the partition, walltime, and resources. The job is submitted to Slurm under the hood, so OOD sessions count against the `devel` partition limits.

## Data Transfer to AICR
Currently, Globus is supposed to be the primary data transfer method for larger data transfers. Northeastern has a subscription to Globus, and Northeastern users can set up a Globus account with their Northeastern credentials, and then connect directories on the Explorer cluster (or local directories) to the directroies in  AICR for data transfer. See [Using Globus](https://rc-docs.northeastern.edu/en/latest/datamanagement/globus.html) for setting up a Globus account with Northeastern credentials.

## Project and Account Lifecycle on AICR
It is important to recognize that accounts and project directories on AICR are a temporary resource and project/account lifecycle is required for this resource.

There will be a yearly check in to ensure projects still require access to the AICR HPC resource. PIs can reup their request for the resources and continue on with their accounts and project directories; however, the annual review is required.

Once the project is complete, it is important to move data from AICR back to an appropriate resource at Northeastern University. The storage space at AICR is not considered to be a permanent storage location for PI projects. PI projects are treated as ephemeral.

## Questions

*For questions or support, contact the Research Computing team at [rchelp@northeastern.edu](mailto:rchelp@northeastern.edu)*
