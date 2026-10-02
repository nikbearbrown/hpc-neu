# SHOTLIST — AICR Introduction (lecture)

**What this is.** One row per body beat: what the sentence is about, the lane picked, the runner-up, and why the pick wins (BEST-BEAT LAW).
**Result.** 24 body beats: 10 isometric drawings, 6 Manim charts/diagrams, 2 real web captures, 3 real-terminal beats, 2 real code listings, 1 large-icon row. No text-only cards in the body.

| Beat | About | Lane picked | Runner-up | Why this one wins |
|---|---|---|---|---|
| B10 | six universities share one cluster | isometric: six campus blocks, lines converge, AICR rack rises | map of Massachusetts | the claim is "many build one"; converging lines ARE that. A map adds geography the source never uses |
| B11 | 248 + 152 = 400 GPUs | Manim counting grids + hero number | ShowTellCard `dashboard` | two quantities compared and summed; unit squares show the 248:152 ratio, a single counter would not |
| B12 | what surrounds the GPUs | isometric: storage, software pages, CPU block arrive round the rack | icon row | these are parts of one machine; arranging them round the rack keeps the cast and shows "around" |
| B13 | develop on Explorer, run on AICR | isometric: job box checked at the small rack, rides a belt to the big rack | two-column card | the claim is a movement in one direction; the belt is the claim |
| B20 | PI's proposal opens access | isometric: page meets a gate, gate opens, project appears | capture of the request form | the form is behind a Google sign-in and could not be captured; nothing about its fields is asserted, so a drawing of the act is honest |
| B21 | sign in at ood.aicr.ai | **the real page**, captured (BrowserCapture) | drawn browser window | SHOW-THE-THING rung 1: the viewer will see exactly this page |
| B22 | j.smith → j_smith_neu | Manim text transform in mono | static two-line card | the change itself (dot to underscore, suffix added) is the fact; a transform shows what changed |
| B30 | three places for files | isometric: box, bin, cabinet with real paths | table | three containers of different size and purpose; shape carries purpose, the paths are the real artifact text |
| B31 | 100 GB, 7-day recovery | isometric: file leaves, dial sweeps, file returns | stat card | "recover within seven days" is a reversal; the returning page shows it |
| B32 | 10 TB, 30-day purge, no recovery | isometric: bin fills, sweep, one block rescued | calendar card | the consequence (everything else vanishes) only reads as motion |
| B40 | five partitions | Manim drawn table, rows on cue | real `sinfo` output (used next, in B44) | the source's own table is the figure to animate (WHOLE-SOURCE LAW 5) |
| B41 | batch 24 h vs devel 4 h, four jobs | Manim bars + four slots | table highlight | a 6:1 length ratio is seen at once as bars |
| B42 | unused GPUs sit idle | isometric: four GPU blocks, one lit | meter chart | "the extra cards sit idle" is about objects doing nothing; dark blocks say it |
| B43 | idle jobs are cancelled | Manim utilization line + cancel | isometric | utilization over time is a curve; the flat line is the evidence for the cancel |
| B44 | see the live partitions | **real terminal output** (CCPlainShell), captured read-only from login.aicr.ai | re-use the drawn table | real output shows what the viewer will actually see, including partitions the document does not list |
| B50 | three ways to run | large 2-D library icons (LibraryIconRow) | FormBCard | three named tools, each recognisable by a mark; FormBCard's 44 px icons made it a text card |
| B51 | the request lines of the script | **the real script** (ClaudeCodeBeat) | drawn form | it is code; show the code |
| B52 | the work lines of the script | **the real script** (ClaudeCodeBeat) | merge into B51 | 17 lines on one card falls under the type floor; two cards keep it readable |
| B53 | submit and follow a job | **the real commands** in a plain terminal | flow diagram | these are things the viewer types; no output is shown because none was run |
| B54 | interactive shell with srun | **the real command** in a plain terminal | icon | same reason; the flags are the content |
| B55 | Open OnDemand submits to Slurm for you | Manim flow: browser → Slurm queue → devel slot | capture of the OnDemand dashboard | the dashboard is behind a sign-in (human-only); the flow drawing asserts only what the source says and invents no interface |
| B60 | Globus for large transfers | **the real docs page**, captured (BrowserCapture) | isometric pipe between racks | the source points the viewer to this exact page |
| B61 | yearly review | Manim year ring with a gate | calendar card | "once a year, then continue" is a loop; a ring with a gate is a loop |
| B62 | data must leave at the end | isometric: blocks ride back to the Northeastern rack | text card | mirrors B13's belt in reverse; the cast pays off |

## Tool beats and their SHOW-THE-THING rung

| Beat | Tool | Rung | Evidence |
|---|---|---|---|
| B21 | Open OnDemand sign-in | 1, real capture | `captures/ood.png`, headless browser, 2026-10-02 |
| B44 | Slurm `sinfo` | 1, real output | `SESSION.md` |
| B51 B52 | the sbatch script | real text of the source | source lines 64–86 |
| B53 B54 | Slurm commands | real commands, no output shown | source lines 89–105 |
| B60 | Globus docs page | 1, real capture | `captures/globus.png`, 2026-10-02 |
| B20 | proposal form | not shown (sign-in wall) | drawing of the act only |
| B55 | Open OnDemand app launcher | not shown (sign-in wall) | flow drawing only; **upgrade available** if Bear signs in and captures the launcher |

## Built for this film (now in the library)

- `BrowserCapture` (Remotion): a real captured page in a browser window, camera push-in, one ring.
- `LibraryIconRow` (Remotion): 2–4 large library icons landing on cue.
- `CCPlainShell` gained an optional `durationSeconds` so line cues can run past 10 s.
