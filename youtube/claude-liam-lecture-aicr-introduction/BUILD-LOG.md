# BUILD-LOG — AICR Introduction (lecture)

**What this is.** The decisions and gate results for the first film made with the `lecture` skill. **Source.** `hpc/AICR-Introduction-2026/aicr-introduction.md`. **Channel.** claude-liam (@NikBearBrown), Liam in for Bear, Kokoro `am_onyx`.

## 2026-10-02

- Bear: "let's try a lecture, Liam persona, on the first folder there, AICR introduction; remove the dates, it should just say AICR introduction rather than AICR introduction 2026 … the AICR folder already has a bunch of films made, which you should use for these as well."
  - Title is "AICR Introduction", slug `claude-liam-lecture-aicr-introduction`. The source folder `hpc/AICR-Introduction-2026/` is a clone of the public repo and was NOT renamed (my reading: the date comes off the film, not off the upstream repo folder).
  - The eleven `aicr/youtube/aicr-*` films were used for their fact-checks against the AICR docs and for the cast ideas (storage ladder, partition table). Their bodies are mostly text cards, so no clip was re-used; this film redraws those ideas as pictures.
- Plan: six acts, 24 body beats, estimated 6 min 20 s. Lane histogram: isometric 10, Manim chart/diagram 6, real capture 2, real terminal 3, real code 2, icon row 1.
- Audio: 29 beats, 379 s measured. BOUT padded with a 1.0 s tail.
- Kokoro says "AICR" as "acre" (as in the earlier films). Kept; flagged in FACTCHECK.
- SHOW-THE-THING: real `sinfo` output from login.aicr.ai (read-only); real captures of the sign-in page and the Globus docs page. Submitting a test job to show real `sbatch`/`squeue` output was blocked by the session's safety rules, so B53/B54 show commands only.
- Not captured (sign-in walls): the proposal Google Form (B20) and the Open OnDemand app launcher (B55). Both beats are drawings that assert only what the source says. Upgrade available if Bear captures them signed in.
- MISS → built: no browser-capture scene and no large-icon scene in the library. Built `BrowserCapture` and `LibraryIconRow`, registered, re-indexed. `CCPlainShell` gained optional `durationSeconds`.
- Manim scenes authored in three parallel parts (`_scenes_partA/B/C.py`) on one shared kit (`_kit.py`), assembled into `scenes.py`.
