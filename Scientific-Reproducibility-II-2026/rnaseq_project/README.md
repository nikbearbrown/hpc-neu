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

rnaseq_project \
├── data \
│   └── counts.tsv \
├── README.md \
├── results \
├── scripts \
│   ├── charts \
│   │   ├── bar_status.sh \
│   │   └── hist_foldchange.sh \
│   └── filter_and_summarise.sh \
└── slurm \
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