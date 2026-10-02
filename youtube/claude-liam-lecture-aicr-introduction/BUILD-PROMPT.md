# BUILD-PROMPT — AICR Introduction (lecture)

Paste into Claude Code, run from `books/`:

> lecture hpc/AICR-Introduction-2026/aicr-introduction.md — Liam persona, title "AICR Introduction" (no year). Reuse the existing AICR films in `aicr/youtube/` for facts and cast. Build into `hpc/youtube/claude-liam-lecture-aicr-introduction/`.

To rebuild this exact film from what is in the folder:

```bash
R=hpc/youtube/claude-liam-lecture-aicr-introduction
python3 $R/make_sheet.py                                            # the sheet (keeps measured audio)
python3 brutalist.art/runtime/scripts/generate_audio_kokoro.py $R   # only if narration changed; then re-pad BOUT (1.0 s) and re-run make_sheet.py
cat $R/_kit.py $R/_scenes_partA.py $R/_scenes_partB.py $R/_scenes_partC.py $R/_scenes_tail.py > $R/scenes.py
./brutalist.art/art run   $R --height 2160
./brutalist.art/art final $R --height 2160 --out $R/exports/landscape
python3 brutalist.art/runtime/scripts/bookend_check.py $R
```

Captures live in `captures/` and are mirrored to `brutalist.art/runtime/remotion/public/lecture-aicr-introduction/`.
Skill doctrine: `brutalist.art/skills/make/lecture/SKILL.md`.
