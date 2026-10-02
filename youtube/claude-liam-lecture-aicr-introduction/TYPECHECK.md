# TYPECHECK.md — GATE T

Reel: `claude-liam-lecture-aicr-introduction`  |  Checked: 2026-10-02T13:54  |  Overall: **FAIL**  |  Beats checked: 29  |  FAILs: 0

Spec: `skills/make/kerning/reference/type-spec.md` §8.  Floor: 1.9% frame-height.  Contrast: 4.5:1 WCAG.  Kern threshold: 3.5× expected advance.  Wordy budget: 2 elements.

> **§8.7–§8.9 PLACEHOLDER / TRUNCATION — GATE BLOCKED:**
> Every item below must be fixed before `./art run` or `./art final`.
> Labels must be authored short phrases (2–5 words). Subs must add something real
> (≤8 words) or be omitted. 'see narration' and truncated strings must not reach
> a rendered surface.

> - §8.12 [B51/code] prose-in-code-card: every line is a comment or contains no code tokens — use FormACard/ClaudeVerdictArtifact for enumerable prose (DESIGN-PRINCIPLES §1), or show real code
> - §8.12 [B52/code] prose-in-code-card: every line is a comment or contains no code tokens — use FormACard/ClaudeVerdictArtifact for enumerable prose (DESIGN-PRINCIPLES §1), or show real code

| beat | lane | polarity | worst finding | status | fix |
|------|------|----------|---------------|--------|-----|
| BIDEA | bookend | light | min-size §8.1: min text-run height 61px >= floor 41px | PASS | — |
| BDEFS | bookend | light | no-wordy-card §8.5: no prose payload found | PASS | — |
| B10 | manim | light | min-size §8.1: min text-run height 63px >= floor 41px (individual-char fallback at 2×) | PASS | — |
| B11 | manim | light | min-size §8.1: min text-run height 108px >= floor 41px (individual-char fallback at 2×) | PASS | — |
| B12 | manim | light | min-size §8.1: min text-run height 66px >= floor 41px | PASS | — |
| B13 | manim | light | min-size §8.1: min text-run height 66px >= floor 41px (individual-char fallback at 2×) | PASS | — |
| B20 | manim | light | min-size §8.1: min text-run height 219px >= floor 41px | PASS | — |
| B21 | remotion | light | no-wordy-card §8.5: no prose payload found | PASS | — |
| B22 | manim | light | min-size §8.1: min text-run height 92px >= floor 41px | PASS | — |
| B30 | manim | light | min-size §8.1: min text-run height 64px >= floor 41px | PASS | — |
| B31 | manim | light | min-size §8.1: min text-run height 64px >= floor 41px | PASS | — |
| B32 | manim | light | min-size §8.1: min text-run height 64px >= floor 41px | PASS | — |
| B40 | manim | light | min-size §8.1: min text-run height 62px >= floor 41px | PASS | — |
| B41 | manim | light | min-size §8.1: min text-run height 66px >= floor 41px (individual-char fallback at 2×) | PASS | — |
| B42 | manim | light | min-size §8.1: min text-run height 63px >= floor 41px (individual-char fallback at 2×) | PASS | — |
| B43 | manim | light | min-size §8.1: min text-run height 607px >= floor 41px | PASS | — |
| B44 | remotion | dark | no-wordy-card §8.5: no prose payload found | PASS | — |
| B50 | remotion | light | no-wordy-card §8.5: no prose payload found | PASS | — |
| B51 | remotion | light | no-wordy-card §8.5: no prose payload found | PASS | — |
| B52 | remotion | light | no-wordy-card §8.5: no prose payload found | PASS | — |
| B53 | remotion | dark | no-wordy-card §8.5: no prose payload found | PASS | — |
| B54 | remotion | dark | no-wordy-card §8.5: no prose payload found | PASS | — |
| B55 | manim | light | min-size §8.1: min text-run height 70px >= floor 41px | PASS | — |
| B60 | remotion | light | no-wordy-card §8.5: no prose payload found | PASS | — |
| B61 | manim | light | min-size §8.1: min text-run height 42px >= floor 41px | PASS | — |
| B62 | manim | light | min-size §8.1: min text-run height 63px >= floor 41px (individual-char fallback at 2×) | PASS | — |
| BVDT | bookend | light | min-size §8.1: hand-drawn pattern (ClaudeVerdictArtifact) — §8.1 hachure/crossbar fragment… | PASS | — |
| BHTF | bookend | light | min-size §8.1: hand-drawn pattern (ClaudeComposerAsk) — §8.1 hachure/crossbar fragments ar… | PASS | — |
| BOUT | bookend | light | min-size §8.1: min text-run height 97px >= floor 41px | PASS | — |

---

## Failures requiring action before cut

### SWEEP GATES §8.7–§8.12b (placeholder / truncation / code-card)

- **§8.12 [B51/code] prose-in-code-card: every line is a comment or contains no code tokens — use FormACard/ClaudeVerdictArtifact for enumerable prose (DESIGN-PRINCIPLES §1), or show real code**
- **§8.12 [B52/code] prose-in-code-card: every line is a comment or contains no code tokens — use FormACard/ClaudeVerdictArtifact for enumerable prose (DESIGN-PRINCIPLES §1), or show real code**

**Fix:** §8.7–§8.9: rewrite flagged labels/subs to authored words. §8.12: replace prose-comment code beat with FormACard or ClaudeVerdictArtifact. §8.12b: give ClaudeCodeBeat a real filename title (e.g. 'analysis.py').

---

## Check summary

| Check | Beats checked | FAILs |
|-------|---------------|-------|
| no-wordy-card §8.5 | 9 | 0 |
| min-size §8.1 | 29 | 0 |
| overflow §8.2 | 29 | 0 |
| contrast §8.3 | 29 | 0 |
| contrast-local §8.3b | 29 | 0 |
| bbox-overlap §8.6b | 29 | 0 |
| card-clip §8.13 | 29 | 0 |
| kerning §8.4 | 16 | 0 |
| redundancy §8.10 (advisory) | 5 | 0 (advisory — no exit effect) |

---

*GATE T: any FAIL blocks `./art run` and `./art final`. Fix the flagged beats and re-run `scripts/type_check.py` until green.*
