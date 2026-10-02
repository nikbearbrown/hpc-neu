#!/usr/bin/env python3
"""make_sheet.py — beat_sheet.json for claude-liam-lecture-aicr-introduction.

LECTURE (Bear, 2026-10-02): the WHOLE source as one act-structured film, primarily visual,
best visual per beat from the full playset, a tool shown as itself. Skill doctrine:
brutalist.art/skills/make/lecture/SKILL.md.

Source: hpc/AICR-Introduction-2026/aicr-introduction.md (Northeastern Research Computing
training, github.com/northeastern-rc-training/AICR-Introduction-2026). Cross-checked against
the saved AICR documentation pages in aicr/ and the live cluster (read-only), 2026-10-02.

Spine: BIDEA hesitant writer -> BDEFS key terms -> six acts -> BVDT recap -> BHTF your turn
-> BOUT spoken @NikBearBrown outro.
"""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
SLUG = HERE.name
TITLE = "AICR Introduction"
CAP = "lecture-aicr-introduction"          # runtime/remotion/public/<CAP>/ holds the captures
FPS = 30


def manim(bid, act, narration, cls, image, show, sparse=True):
    b = {"beat_id": bid, "act": act, "lane": "manim", "proof_gate": "SHOW",
         "narration_text": narration, "estimated_duration_s": round(len(narration.split()) / 2.5, 1),
         "voice": "am_onyx", "engine": "kokoro",
         "shot": {"type": "GRAPHIC", "source": "own", "visual_intent": image, "show": show,
                  "manim": {"class": cls}, "motion_claim": image}}
    if sparse:
        b["qc"] = {"sparse_by_design": True, "sparse_reason": SPARSE}
    return b


def remotion(bid, act, narration, pattern, props, show, gate="SHOW", lane="remotion", **extra):
    b = {"beat_id": bid, "act": act, "lane": lane, "proof_gate": gate,
         "narration_text": narration, "estimated_duration_s": round(len(narration.split()) / 2.5, 1),
         "voice": "am_onyx", "engine": "kokoro",
         "shot": {"type": "REMOTION", "source": "own", "show": show,
                  "remotion": {"pattern": pattern, "props": props}}}
    b.update(extra)
    return b


SPARSE = ("lecture, isometric lane (show-tell drawing laws): one drawn scene on a cream stage with a few labels, "
          "the voice carries the explanation. Only underfill and clustered are waived; edge-bleed, empty-frame "
          "and contrast still apply.")

A1, A2, A3, A4, A5, A6 = ("I · What AICR Is", "II · Getting On", "III · Where Files Live",
                          "IV · Compute", "V · Running A Job", "VI · Data And Lifecycle")

# ───────────────────────────── the opening pair ─────────────────────────────
OPEN = [
 remotion("BIDEA", "the idea",
    "Hallo. This is Liam, in for Bear. First, a correction. AICR is not the cluster where you build and test "
    "your AI work. It's the cluster where you run the big jobs. It's a shared GPU cluster for AI research in "
    "Massachusetts, and this lecture covers what it is, how you get on, where your files live, and how you run a job.",
    "BrutalistHesitantWriter",
    {"text": "AICR is the cluster where I\nbuild and test my AI work", "triggerWords": "build and test",
     "replacementWords": "run the big jobs for", "fontSize": 70, "charMs": 62, "hesitateBetween": 6,
     "hesitateWithin": 1, "mistakeRate": 2, "jitter": 20, "seed": SLUG, "banner": ""},
    [{"at": 0.0, "event": "types 'AICR is the cluster where I build and test my AI work'"},
     {"at": 0.35, "event": "backspaces 'build and test' -> 'run the big jobs for'"}],
    lane="bookend", lead_silence_s=0.8,
    motion_claim="The writer types the newcomer's framing (build and test) and corrects it to the real one (run the big jobs).",
    qc={"sparse_by_design": True, "sparse_reason": "Hesitant-writer bookend: the correction is the motion."}),
 remotion("BDEFS", "terms",
    "Six terms. An HPC cluster: many computers wired together and shared by many people. A GPU: a chip that does "
    "AI math far faster than a normal processor. Slurm: the scheduler. You ask for resources, and it decides when "
    "you run. A partition: a named group of machines with its own rules. A PI: the principal investigator, the "
    "faculty member who leads a project. And Open OnDemand: a website that gives you the cluster in a browser.",
    "ClaudeDefinitions",
    {"title": "Terms In This Lecture",
     "terms": [{"term": "HPC cluster", "meaning": "many computers wired together and shared by many people"},
               {"term": "GPU", "meaning": "a chip that does AI math far faster than a normal processor"},
               {"term": "Slurm", "meaning": "the scheduler: you ask for resources, it decides when you run"},
               {"term": "partition", "meaning": "a named group of machines with its own rules"},
               {"term": "PI", "meaning": "principal investigator: the faculty member who leads a project"},
               {"term": "Open OnDemand", "meaning": "a website that gives you the cluster in a browser"}],
     "folderLabel": "@NikBearBrown"},
    [{"at": 0.08, "event": "'HPC cluster' lands"}, {"at": 0.25, "event": "'GPU'"}, {"at": 0.4, "event": "'Slurm'"},
     {"at": 0.58, "event": "'partition'"}, {"at": 0.72, "event": "'PI'"}, {"at": 0.87, "event": "'Open OnDemand'"}],
    gate="CARD", lane="bookend",
    qc={"sparse_by_design": True, "sparse_reason": "TERMS card: six prerequisites, one line each."}),
]

# ───────────────────────────── the acts ─────────────────────────────
SBATCH_HEAD = """#!/bin/bash
#SBATCH --partition=b200-batch
#SBATCH --job-name=b200_test_job
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=b200_test_%j.out
#SBATCH --error=b200_test_%j.err"""
SBATCH_BODY = """module purge
module load cuda/13.1
module load miniforge3/25.3.0-3
source activate myenv

python training.py"""

B = [
 # ACT I
 manim("B10", A1,
    "Start with what it is. AICR stands for AI Compute Resource. Six universities at the Massachusetts Green High "
    "Performance Computing Center, together with the Massachusetts AI Hub, built one cluster, and they share it.",
    "B10_SixIntoOne",
    "Six small campus blocks stand around the stage; a line draws from each to the centre, where one large data-centre block rises; label 'AICR'.",
    [{"at": 0.2, "event": "six campus blocks"}, {"at": 0.6, "event": "lines draw to the centre"}, {"at": 0.8, "event": "the shared cluster rises"}]),
 manim("B11", A1,
    "Inside are two kinds of GPU. Two hundred forty-eight NVIDIA B200s, and one hundred fifty-two RTX PRO 6000s. "
    "That's four hundred GPUs in all.",
    "B11_GpuCount",
    "Two grids of small squares fill in, counting up: 248 on the left (B200), 152 on the right (RTX PRO 6000); the two counters merge into a hero '400'.",
    [{"at": 0.25, "event": "248 B200 squares fill"}, {"at": 0.6, "event": "152 RTX squares fill"}, {"at": 0.88, "event": "400"}], sparse=False),
 manim("B12", A1,
    "Around the GPUs: fast storage, a modern software stack for machine learning, and a CPU-only section for the "
    "work that needs no GPU, like cleaning and analysing data.",
    "B12_Around",
    "The GPU rack from B10 sits centre; a storage block slides in beside it, a stack of software pages lands on top, and a lighter CPU block arrives on the other side.",
    [{"at": 0.15, "event": "storage"}, {"at": 0.4, "event": "software stack"}, {"at": 0.65, "event": "CPU-only block"}]),
 manim("B13", A1,
    "Northeastern already has its own cluster, called Explorer. Treat AICR as an extension of it. You develop and "
    "test on Explorer. When the code works, you bring it to AICR for the production run. AICR is shared by every "
    "partner university, so it isn't the place to debug.",
    "B13_ExplorerToAicr",
    "A small rack labelled 'Explorer' on the left with a job box beside it; the box is worked on (a check lands); it then rides a belt to the large 'AICR' rack on the right, whose lights come on.",
    [{"at": 0.1, "event": "Explorer rack"}, {"at": 0.4, "event": "develop and test: check"}, {"at": 0.6, "event": "box rides to AICR"}, {"at": 0.75, "event": "production run: lights"}]),
 # ACT II
 manim("B20", A2,
    "Getting on starts with a faculty member. The principal investigator submits a brief proposal through a "
    "request form. Access comes through that project.",
    "B20_Proposal",
    "A proposal page slides toward a closed gate; the gate opens; a project folder appears behind it and two small user tokens step through.",
    [{"at": 0.3, "event": "proposal page"}, {"at": 0.6, "event": "gate opens"}, {"at": 0.85, "event": "project and its users"}]),
 remotion("B21", A2,
    "Once you're on a project, the easiest door is Open OnDemand, at o o d dot A I C R dot A I. It sends you to a "
    "sign-in page. You choose your identity provider, then sign in with your Northeastern username and password.",
    "BrowserCapture",
    {"url": "ood.aicr.ai", "image": f"{CAP}/ood.png", "caption": "The real sign-in page, captured 2 October 2026",
     "moves": [{"at": 0.0, "x": 0.5, "y": 0.42, "scale": 1.3},
               {"at": 0.57, "x": 0.5, "y": 0.55, "scale": 1.7, "ring": [0.255, 0.405, 0.49, 0.295]}]},
    [{"at": 0.0, "event": "browser window opens on ood.aicr.ai"}, {"at": 0.57, "event": "zoom to 'Select an Identity Provider'; terracotta ring"}],
    motion_claim="The real sign-in page; the camera pushes in to the identity-provider choice as it is named."),
 manim("B22", A2,
    "One thing changes: your username. On the cluster it's slightly different, so accounts from the partner schools "
    "stay distinct. If you're j dot smith on Explorer, you're j underscore smith underscore n e u on AICR.",
    "B22_Username",
    "'j.smith' in mono under the label Explorer; a copy slides right under the label AICR, its dot turns into an underscore and '_neu' slides on.",
    [{"at": 0.55, "event": "j.smith on Explorer"}, {"at": 0.75, "event": "dot becomes underscore, _neu arrives"}], sparse=False),
 # ACT III
 manim("B30", A3,
    "Your files live in three places, the same three as on Explorer. Home, for small scripts and your environment. "
    "Scratch, for temporary output from running jobs. And the project directory, for shared, longer-term work.",
    "B30_ThreePlaces",
    "Three containers land in a row: a small box (home), a wide open bin (scratch), a cabinet (project); each gets its real path as a label.",
    [{"at": 0.3, "event": "home"}, {"at": 0.55, "event": "scratch"}, {"at": 0.8, "event": "project"}]),
 manim("B31", A3,
    "Home holds a hundred gigabytes. Delete a file there by accident, and you have seven days to recover it. "
    "The project directory has the same seven-day safety net.",
    "B31_SevenDays",
    "The home box with '100 GB'; a file page lifts out and vanishes, a seven-day dial sweeps, and the page comes back; the cabinet gets the same dial.",
    [{"at": 0.1, "event": "100 GB"}, {"at": 0.35, "event": "file deleted"}, {"at": 0.55, "event": "7 days: it comes back"}, {"at": 0.85, "event": "project has it too"}]),
 manim("B32", A3,
    "Scratch is huge. Ten terabytes, and up to fifteen million files. But nothing in scratch can be recovered, and "
    "there's a thirty-day purge. So move anything important out before it's gone.",
    "B32_ScratchPurge",
    "The scratch bin fills with blocks, one marked with a terracotta dot; '10 TB' lands; a thirty-day sweep line crosses the bin; the marked block is lifted out to the cabinet just before the rest vanish.",
    [{"at": 0.1, "event": "bin fills, 10 TB"}, {"at": 0.5, "event": "30-day sweep"}, {"at": 0.8, "event": "the important block is moved out; the rest are purged"}]),
 # ACT IV
 manim("B40", A4,
    "Compute is split into partitions. One is CPU only. Four have GPUs: a batch and a devel partition for the "
    "B200s, and a batch and a devel partition for the RTX cards. Every GPU node carries about two point three "
    "terabytes of memory.",
    "B40_PartitionTable",
    "A drawn table builds row by row from the source: cpu, b200-batch, b200-devel, rtx-batch, rtx-devel, with GPU and max walltime columns.",
    [{"at": 0.15, "event": "cpu row"}, {"at": 0.35, "event": "B200 rows"}, {"at": 0.6, "event": "RTX rows"}, {"at": 0.85, "event": "2.3 TB per GPU node"}], sparse=False),
 manim("B41", A4,
    "Batch partitions are for jobs you submit and walk away from. They run up to twenty-four hours, and they "
    "support more than one GPU. Devel partitions are for interactive work: four hours at most, and four running "
    "jobs per user.",
    "B41_BatchVsDevel",
    "Two bars grow side by side: a long one to 24 h (batch) and a short one to 4 h (devel); under devel four job slots fill and a fifth bounces off.",
    [{"at": 0.3, "event": "batch bar grows to 24 h"}, {"at": 0.65, "event": "devel bar stops at 4 h"}, {"at": 0.85, "event": "four slots, the fifth waits"}], sparse=False),
 manim("B42", A4,
    "Before you ask for more than one GPU, confirm your code can actually use them. If it can't, the extra cards "
    "sit idle.",
    "B42_IdleCards",
    "Four GPU blocks in a row; a job box plugs into all four; only the first lights up and its meter fills, the other three stay dark with empty meters.",
    [{"at": 0.2, "event": "four GPUs requested"}, {"at": 0.6, "event": "one works"}, {"at": 0.85, "event": "three sit idle"}]),
 manim("B43", A4,
    "And idle is watched. A background process tracks GPU utilization and cancels jobs that sit idle. So end your "
    "interactive session when you're done. A tool called jobstats will also report how each job used what it "
    "asked for.",
    "B43_IdleCancel",
    "A utilization line runs along a time axis, drops to zero and stays flat; a watcher marker reaches it and the job block is struck out and removed; the freed GPU lights for the next job in the queue.",
    [{"at": 0.2, "event": "utilization falls to zero"}, {"at": 0.4, "event": "idle job cancelled"}, {"at": 0.6, "event": "GPU goes to the next job"}], sparse=False),
 remotion("B44", A4,
    "You can see the live list yourself. The command s info prints every partition, its time limit, and its node "
    "count. Run it and you may see more partitions than the five here, because the cluster keeps changing.",
    "CCPlainShell",
    {"title": "ssh — login.aicr.ai",
     "lines": ['$ sinfo -o "%14P %11l %6D"',
               "PARTITION      TIMELIMIT   NODES",
               "cpu*           1-00:00:00  5",
               "rtx-batch      1-00:00:00  17",
               "b200-batch     1-00:00:00  25",
               "b200-fullnode  1-00:00:00  4",
               "rtx-devel      4:00:00     2",
               "b200-devel     4:00:00     2",
               "preemptable    1-00:00:00  46"],
     "startCue": 60, "lineGap": 26},
    [{"at": 0.15, "event": "the sinfo command lands"}, {"at": 0.3, "event": "real partition rows print (captured read-only, 2 October 2026)"}],
    motion_claim="The real command and its real output print line by line."),
 # ACT V
 remotion("B50", A5,
    "AICR runs Slurm, so there are three ways to work. s batch, for jobs that run without you. s run, for an "
    "interactive shell. And Open OnDemand, in the browser.",
    "LibraryIconRow",
    {"title": "V · Running A Job",
     "items": [{"label": "sbatch", "sub": "runs without you", "icon": "file-code", "mono": True, "cue_phrase": "s batch"},
               {"label": "srun", "sub": "an interactive shell", "icon": "terminal", "mono": True, "cue_phrase": "s run"},
               {"label": "Open OnDemand", "sub": "in the browser", "icon": "browser", "cue_phrase": "And Open OnDemand"}]},
    [{"at": 0.35, "event": "sbatch"}, {"at": 0.6, "event": "srun"}, {"at": 0.8, "event": "Open OnDemand"}],
    motion_claim="Three named routes, each landing as one large library icon as it is spoken."),
 remotion("B51", A5,
    "A batch job is a script. The lines that start with S BATCH are your request: which partition, how many CPUs, "
    "one GPU, sixteen gigabytes of memory, and a time limit of thirty minutes.",
    "ClaudeCodeBeat",
    {"title": "myjob.slurm — the request", "code": SBATCH_HEAD, "language": "bash", "largeText": True,
     "sparkLine": "Every #SBATCH line is part of the request."},
    [{"at": 0.1, "event": "the script header prints line by line"}],
    motion_claim="The real script header from the training material prints line by line."),
 remotion("B52", A5,
    "Below the request is the work. Clear the loaded modules. Load CUDA and miniforge. Activate your environment. "
    "Then run your training script.",
    "ClaudeCodeBeat",
    {"title": "myjob.slurm — the work", "code": SBATCH_BODY, "language": "bash", "largeText": True,
     "sparkLine": "Modules first, then your code."},
    [{"at": 0.1, "event": "the script body prints line by line"}],
    motion_claim="The real script body prints line by line."),
 remotion("B53", A5,
    "Submit it with s batch and the file name. If your script writes logs into a folder, create that folder first. "
    "Then three commands follow the job around. s queue shows your queued and running jobs. s cancel stops one. "
    "And s acct shows what a finished job actually used.",
    "CCPlainShell",
    {"title": "ssh — login.aicr.ai",
     "lines": ["$ mkdir -p logs",
               "$ sbatch myjob.slurm",
               "# your queued and running jobs",
               "$ squeue -u $USER",
               "# cancel a job",
               "$ scancel <jobid>",
               "# what a finished job used",
               "$ sacct -j <jobid> \\",
               "    --format=JobID,Elapsed,MaxRSS,State"],
     "startCue": 20, "lineGap": 31},
    [{"at": 0.05, "event": "mkdir, sbatch"}, {"at": 0.5, "event": "squeue"}, {"at": 0.7, "event": "scancel"}, {"at": 0.85, "event": "sacct"}],
    motion_claim="The commands from the training material land in order; no output is shown because none was run."),
 remotion("B54", A5,
    "For an interactive shell on a GPU node, use s run. This one asks the RTX devel partition for eight CPUs, "
    "sixteen gigabytes, and one GPU, for one hour. Always set the time, so the session ends even if you forget. "
    "And type exit to give the GPU back.",
    "CCPlainShell",
    {"title": "ssh — login.aicr.ai",
     "lines": ["$ srun -p rtx-devel -N 1 -n 1 -c 8 \\",
               "    --mem=16G --gres=gpu:1 \\",
               "    --time=01:00:00 --pty bash",
               "# always set --time",
               "$ exit"],
     "startCue": 30, "lineGap": 75},
    [{"at": 0.1, "event": "the srun command"}, {"at": 0.6, "event": "--time"}, {"at": 0.9, "event": "exit"}],
    motion_claim="The real srun command from the training material; exit releases the allocation."),
 manim("B55", A5,
    "Or skip the terminal. Open OnDemand launches graphical sessions, such as JupyterLab or a desktop. You choose "
    "the partition, the time, and the resources, and it submits the job to Slurm for you. Those sessions count "
    "against the devel limits.",
    "B55_OodToSlurm",
    "A browser window with three choice chips (partition, time, resources); a job box leaves the window, enters a Slurm queue, and takes one of the four devel slots from B41.",
    [{"at": 0.2, "event": "browser window"}, {"at": 0.45, "event": "partition, time, resources"}, {"at": 0.65, "event": "job goes to Slurm"}, {"at": 0.85, "event": "it takes a devel slot"}], sparse=False),
 # ACT VI
 remotion("B60", A6,
    "To move large data, the primary method is Globus. Northeastern has a subscription. You set up a Globus account "
    "with your Northeastern credentials, then connect a folder on Explorer, or on your own machine, to a folder on "
    "AICR.",
    "BrowserCapture",
    {"url": "rc-docs.northeastern.edu/en/latest/datamanagement/globus.html", "image": f"{CAP}/globus.png",
     "caption": "Northeastern Research Computing docs, captured 2 October 2026",
     "moves": [{"at": 0.0, "x": 0.5, "y": 0.3, "scale": 1.35, "ring": [0.245, 0.035, 0.18, 0.07]},
               {"at": 0.3, "x": 0.5, "y": 0.75, "scale": 1.5, "ring": [0.245, 0.64, 0.5, 0.33]}]},
    [{"at": 0.0, "event": "the real 'Using Globus' docs page"}, {"at": 0.3, "event": "camera moves down to the account set-up steps; ring"}],
    motion_claim="The real documentation page; the camera moves from the title to the set-up steps as they are described."),
 manim("B61", A6,
    "Last, the part people forget. Accounts and project directories on AICR are temporary. Once a year there's a "
    "check-in. The PI renews the request, and the project continues.",
    "B61_YearlyReview",
    "A ring of twelve month ticks; a marker travels round it and reaches a gate at the top labelled 'annual review'; a check lands, the gate opens, and the marker starts another lap.",
    [{"at": 0.3, "event": "a year goes round"}, {"at": 0.6, "event": "annual review gate"}, {"at": 0.85, "event": "renewed: another lap"}], sparse=False),
 manim("B62", A6,
    "And when the project ends, the data has to leave. AICR is not permanent storage. Move your results back to a "
    "Northeastern resource. Questions go to the Research Computing team, at r c help at northeastern dot e d u.",
    "B62_DataGoesHome",
    "The AICR rack on the right with the project cabinet; its blocks ride the belt back to the Northeastern rack on the left; the cabinet empties and pales; the email address lands underneath.",
    [{"at": 0.15, "event": "project ends"}, {"at": 0.45, "event": "data rides back to Northeastern"}, {"at": 0.75, "event": "rchelp@northeastern.edu"}]),
]

# ───────────────────────────── the closing three ─────────────────────────────
RECAP = ["AICR is a shared GPU cluster: 248 B200s and 152 RTX PRO 6000s.",
         "Develop on Explorer; bring the production run to AICR.",
         "A PI's proposal gets you on; sign in at ood.aicr.ai.",
         "Home holds 100 GB; scratch holds 10 TB with a 30-day purge.",
         "Batch runs 24 hours, devel runs 4, and idle GPU jobs get cancelled.",
         "Projects are reviewed yearly; move your data home at the end."]
VERDICT = remotion("BVDT", "recap",
    "Let's recap with Claude. AICR is a shared GPU cluster, with two hundred forty-eight B200s and one hundred "
    "fifty-two RTX PRO 6000s. You develop on Explorer, and bring the production run to AICR. A PI's proposal gets "
    "you on, and you sign in through Open OnDemand. Home holds a hundred gigabytes. Scratch holds ten terabytes, "
    "with a thirty-day purge. Batch partitions run twenty-four hours, devel partitions run four, and idle GPU jobs "
    "get cancelled. Projects are reviewed every year, and your data goes home at the end.",
    "ClaudeVerdictArtifact",
    {"artifactTitle": "Recap", "artifactHeading": TITLE, "artifactLines": RECAP},
    [{"at": 0.0, "event": "artifact page opens"}, {"at": 0.1, "event": "six recap lines land in narration order"}],
    lane="bookend", lead_silence_s=0.5,
    qc={"sparse_by_design": True, "sparse_reason": "Mandated ClaudeVerdictArtifact bookend."})

YT_PROMPT = ("I'm about to run my first production job on a shared GPU cluster that uses Slurm. Here is my training setup: "
             "[describe it in two sentences]. Write an sbatch script that asks for one GPU and a 30-minute time limit. "
             "Then tell me which of my files belong in home, which in scratch, and which in the project directory.")
YOURTURN = remotion("BHTF", "your turn",
    "Your turn. Paste this into Claude: " + YT_PROMPT + " Then check two things yourself. Does every S BATCH line ask "
    "only for what your code can use? And is anything you can't afford to lose sitting in scratch?",
    "ClaudeComposerAsk",
    {"greeting": "Your turn.", "topic": "CLAUDE · YOUR TURN", "segment": "Plan Your First AICR Job", "command": YT_PROMPT,
     "runningText": "paste this into Claude…",
     "output": ["Check: does every #SBATCH line ask only for what your code can use?",
                "Check: is anything you can't afford to lose sitting in scratch?"],
     "folderLabel": "@NikBearBrown", "modelLabel": "Opus 5.5", "effortLabel": "High"},
    [{"at": 0.0, "event": "Composer opens — 'Your turn.'"}, {"at": 0.1, "event": "the prompt types in full"}, {"at": 0.8, "event": "two check lines land"}],
    lane="bookend")

OUTRO = {"beat_id": "BOUT", "act": "outro", "lane": "bookend", "proof_gate": "SHOW",
         "narration_text": f"{TITLE}. At Nik Bear Brown.", "estimated_duration_s": 4.0, "voice": "am_onyx", "engine": "kokoro",
         "shot": {"type": "REMOTION", "source": "own", "show": [{"at": 0.0, "event": "title restates; handle; mascot"}],
                  "remotion": {"pattern": "ClaudeTitleOutro", "props": {"title": TITLE, "slug": SLUG, "handle": "@NikBearBrown", "subline": ""}}},
         "kind": "outro_voice", "tail_silence_s": 1.0}

BEATS = OPEN + B + [VERDICT, YOURTURN, OUTRO]

sheet = {"metadata": {
    "slug": SLUG, "title": TITLE, "topic": "RESEARCH COMPUTING · AICR", "skill": "lecture", "style_preset": "lecture",
    "channel": "claude-liam", "persona": "Liam (in for Bear)", "voice": "am_onyx", "voice_kokoro": "am_onyx", "engine": "kokoro",
    "clock": "narration", "palette": "claude", "register": "Teardown", "fps": 24, "aspect_ratio": "16:9", "width": 3840, "height": 2160,
    "caption_policy": "none", "greeting_language": "German (Hallo)",
    "audience": "Northeastern researchers and students about to use the AICR GPU cluster for the first time; assumes no other film or book",
    "source_doc": "hpc/AICR-Introduction-2026/aicr-introduction.md (Northeastern Research Computing training, "
                  "github.com/northeastern-rc-training/AICR-Introduction-2026), read 2026-10-02",
    "playlist": "AICR", "chapter_number": 0,
    "tags": ["AICR", "AI Compute Resource", "MGHPCC", "Massachusetts AI Hub", "Northeastern University", "Research Computing",
             "HPC", "GPU cluster", "Slurm", "sbatch", "srun", "Open OnDemand", "Globus", "Explorer cluster", "Nik Bear Brown"]},
    "beats": BEATS}

# keep measured audio fields across re-runs (audio-first: never lose the clock)
old = {}
p = HERE / "beat_sheet.json"
if p.exists():
    for ob in json.load(open(p))["beats"]:
        old[ob["beat_id"]] = ob
for b in BEATS:
    ob = old.get(b["beat_id"])
    if ob and ob.get("narration_text") == b["narration_text"]:
        for k in ("actual_duration_s", "audio_file"):
            if k in ob:
                b[k] = ob[k]
    # measured audio drives every Remotion clock
    dur = b.get("actual_duration_s")
    props = (b["shot"].get("remotion") or {}).get("props")
    if dur and props is not None:
        pat = b["shot"]["remotion"]["pattern"]
        if pat in ("ClaudeDefinitions", "BrowserCapture", "LibraryIconRow", "CCPlainShell", "ClaudeCodeBeat"):
            props["durationSeconds"] = dur
        if pat == "LibraryIconRow":
            n = b["narration_text"]
            for it in props["items"]:
                at = round(n.index(it["cue_phrase"]) / len(n), 3)
                it["at"] = at if not 0.43 <= at <= 0.57 else 0.58      # never land on the sampled midpoint
p.write_text(json.dumps(sheet, indent=2, ensure_ascii=False) + "\n")
print(len(BEATS), "beats; est", round(sum(b.get("actual_duration_s") or b["estimated_duration_s"] for b in BEATS)), "s")
