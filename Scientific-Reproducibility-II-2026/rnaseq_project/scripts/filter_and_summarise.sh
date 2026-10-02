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