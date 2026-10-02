#!/usr/bin/env bash
# Histogram of log2 fold changes (column 4 of summary.tsv)
# Usage: bash scripts/charts/hist_foldchange.sh [summary.tsv]
INPUT="${1:-results/summary.tsv}"
BINS=12
BAR_CHAR='▒'
MAX_WIDTH=36

echo ''
echo 'log2(Fold Change) Distribution'
echo '────────────────────────────────────────────────'

awk -v bins=$BINS -v w=$MAX_WIDTH -v c="$BAR_CHAR" '
NR==1 { next }
$4 > 0 {
    l2 = log($4) / log(2)
    vals[++n] = l2
    if (n==1 || l2 < mn) mn = l2
    if (n==1 || l2 > mx) mx = l2
}
END {
    width = (mx - mn) / bins
    for (i = 1; i <= n; i++) {
        b = int((vals[i] - mn) / width)
        if (b >= bins) b = bins - 1
        counts[b]++
    }
    max_c = 0
    for (b = 0; b < bins; b++)
        if (counts[b]+0 > max_c) max_c = counts[b]

    for (b = 0; b < bins; b++) {
        lo  = mn + b * width
        hi  = lo + width
        cnt = counts[b]+0
        bar_len = (max_c > 0) ? int(w * cnt / max_c) : 0
        bar = ""
        for (i = 0; i < bar_len; i++) bar = bar c
        printf "  [%+5.2f to %+5.2f]  %4d  %s\n", lo, hi, cnt, bar
    }
    printf "\n  x-axis: log2(fold change)   n = %d genes\n", n
}
' "$INPUT"
echo ''