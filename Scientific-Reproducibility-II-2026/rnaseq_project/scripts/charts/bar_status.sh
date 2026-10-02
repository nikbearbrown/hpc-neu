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