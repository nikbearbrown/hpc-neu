# Manim scene brief — claude-liam-lecture-aicr-introduction

You are writing Manim scenes for ONE film, a `lecture` (the whole AICR Introduction training
document as one film, narrated by Liam, Kokoro audio already generated and measured). Three
authors are working in parallel, each on a different set of beats. You own only your beats.

Reel folder (all paths below are relative to it):
`/Users/bear/Documents/CoWork/bear-textbooks/books/hpc/youtube/claude-liam-lecture-aicr-introduction/`
Toolkit: `/Users/bear/Documents/CoWork/bear-textbooks/books/brutalist.art/`

## Read first, in full

1. `beat_sheet.json` in the reel: for each of your beats read `narration_text`,
   `actual_duration_s`, `shot.visual_intent`, `shot.show`. The narration is the clock.
2. `_kit.py` in the reel: the shared drawing kit AND the film's cast. READ-ONLY. Do not edit it.
3. `brutalist.art/skills/make/show-tell/SKILL.md`, the whole "Drawing kit and laws" section
   (DRAWING LAWS). Every bullet there is a real gate failure someone already hit. Obey them.
4. `brutalist.art/skills/make/lecture/SKILL.md`: BEST-BEAT LAW and "PRIMARILY VISUAL".
5. Worked example of the style and helpers:
   `/Users/bear/Documents/CoWork/bear-textbooks/books/anthropics/youtube/show-tell-context-is-a-budget/scenes.py`

## What to deliver

One file in the reel folder, named as your assignment says (`_scenes_partA.py`, `_scenes_partB.py`
or `_scenes_partC.py`). It contains ONLY your scene classes and any helper functions/constants
they need. No imports, no kit code: the final `scenes.py` is `_kit.py` + part A + part B + part C
concatenated, so everything in `_kit.py` is already in scope.

- Every scene class is written literally as `class B10_SixIntoOne(Scene):` with the exact class
  name given in `beat_sheet.json` (`shot.manim.class`). The build finds scenes by that text.
- Prefix every helper and constant with your beat id or part letter (`b30_bin_state`, `PA_SHADOW`)
  so the three parts never collide.
- Do NOT attach the midpoint guard yourself; the assembler does
  (`for _cls in (...): _cls.play = ST.play`). When you test, add that loop at the bottom of your
  scratch file so you test what will ship.
- End every `construct` with `done(self)`.
- Pace with `until(self, "exact phrase from the narration")` so each motion lands on its words.

## The picture rules (short version; the skill files are the long version)

- Primarily visual. On screen: labels of 1–3 words, a hero number, or a real path/username/command
  in mono via `M()`. Never a sentence. The voice explains.
- Motion carries the claim: every spoken point has a motion. A beat that reads the same as a still
  fails. Every scene must ADD at least one new non-text shape after its first frame
  (Create/FadeIn/GrowFromCenter of a new object); moves alone fail Gate A.
- One cast, whole film: use the cast helpers in `_kit.py` (`explorer_rack`, `aicr_rack`, `job_box`,
  `home_box`, `scratch_bin`, `project_cabinet`, `gpu_block`). The same object must look the same in
  every beat. If the act's first beat is yours, put the act title (the beat's `act` field, e.g.
  "I · What AICR Is") as a small `T(..., 40)` title at top-left for the whole beat.
- Claude palette only (constants in `_kit.py`). Terracotta is the ONE accent, never text, never a
  thin bar; ink for numerals and labels. Text size ≥ 32. Everything inside ±6.2 × ±3.3.
- Labels sit beside objects, never inside an outline and never on a terracotta fill.
- Nothing may be mid-animation at the clip midpoint (the guard handles `play`; do not defeat it
  with long `Succession`/`LaggedStart` blocks that straddle the middle; split them).
- Keep each scene's total run time ≤ its `actual_duration_s` (`done()` prints `[pace]`; "OVER" is
  a bug: shorten run_times, do not drop content).
- Facts: use only numbers and names that are in the narration or `shot.visual_intent`. Do not add
  any fact, figure, product name or label that is not there.

## How to test (do all of it before you report)

Work in your OWN scratch folder so parallel authors never collide:
`/private/tmp/claude-501/-Users-bear-Documents-CoWork/20cbc7ee-e6a5-4110-97e2-edffd518db1c/scratchpad/part<A|B|C>/`

1. Build a scratch `scenes.py` there: `cat <reel>/_kit.py <reel>/_scenes_part<X>.py > scenes.py`,
   then append the guard-attach loop. Copy `<reel>/beat_sheet.json` beside it (the kit reads it for pacing).
2. Stills: `manim -ql -s --media_dir ./media scenes.py <Class>` and LOOK at the PNG (Read tool).
   Then render the low-res video `manim -ql --media_dir ./media scenes.py <Class>`, pull frames at
   25%, 50% and 90% with ffmpeg, and LOOK at them. Check `[pace]` is not OVER and that the clip
   length is within 0.1 s under the beat's `actual_duration_s`.
3. Gate A, exactly as the build runs it, from a folder holding ONLY scenes.py (no beat sheet):
   `PYTHONPATH=<toolkit>/runtime/manim python3 <toolkit>/runtime/qc/static_scene_check.py <dir>/scenes.py --class <Class>`
4. Gate W: `python3 <toolkit>/runtime/qc/wcag_margin_check.py scenes.py --class <Class>`
5. Layout audit: `python3 <toolkit>/runtime/qc/manim_layout_audit.py scenes.py --class <Class> --curve-strict`
   (run in the folder that has beat_sheet.json).
   Exit code 0 is a pass for all three; fix anything else.
Never run `art run`, never render at 4K, never touch `beat_sheet.json`, `make_sheet.py`,
`_kit.py`, another author's part file, or anything outside the reel folder and your scratch folder.

## Report back

For each scene: class name, one line on what moves, the `[pace]` line, and the three gate results.
List anything you could not get to pass, with the exact failure text. Do not claim a pass you did
not see.
