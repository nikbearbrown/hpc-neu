"""
Script 06 — GPU Memory & Utilisation Monitor  (Before vs After)
--------------------------------------------------------------
nvidia-smi shows a snapshot of memory at one point in time.  During a real
training run, both VRAM usage AND GPU utilisation evolve:
  1. Baseline (Python + CUDA runtime loaded)
  2. Model parameters loaded
  3. Optimizer state allocated (Adam doubles memory per parameter)
  4. Forward pass: activations fill memory
  5. Backward pass: peak usage
  6. After optimizer.step() and zero_grad(): partial release

The trap on Explorer: even a V100 (32 GB) is fast enough that a small-batch,
FP32 workload leaves it mostly idle.  Each step's kernels finish almost
instantly, so per-step launch/sync overhead dominates and utilisation stays
low even though "the code runs fine".

This script demonstrates the fix directly.  It runs the SAME TASK twice —
identical input size and model, so throughput (img/s) is a fair, apples-to-
apples comparison.  Only the *execution* changes:

  1. BASELINE  — tiny batch, FP32, contiguous memory.  Small batches leave the
                 GPU's SMs mostly idle; launch/sync overhead dominates.
  2. TUNED     — large batch, 16-bit autocast (BF16 on A100/H100, FP16 on
                 V100/T4), and channels_last memory format → higher utilisation
                 AND higher throughput on the very same workload.

For each phase it measures peak VRAM, mean/max GPU utilisation (sampled live
from NVML), and throughput, then prints exactly WHAT changed and WHY
utilisation went up.

Note we do NOT scale the image resolution or model width between phases — that
would change how much work each image costs, making img/s meaningless to
compare.  Resolution and width are properties of your task; batch size,
precision, and memory format are execution knobs you tune for free.

Explorer hardware context:
  V100  — 32 GB VRAM  (demo default; no BF16 hardware, so the script uses FP16)
  A100  — 80 GB VRAM  (larger; supports BF16 Tensor Cores)

A fast GPU does NOT help if you feed it tiny batches — low utilisation is
wasted hardware.  Goal: keep utilisation at 80-100% with a batch large enough
to saturate the SMs, and mixed precision to feed the Tensor Cores.  (This demo
uses a small model, so its VRAM footprint stays low; on a real model you would
also aim to fill 75-90% of VRAM.)

Usage:
    python 06_memory_monitor.py                 (GPU strongly recommended)
    python 06_memory_monitor.py --baseline-only (just show the problem)

Utilisation sampling needs NVML bindings (usually preinstalled with the driver):
    pip install nvidia-ml-py
Without it, the script still runs and reports memory + throughput.
"""

# Postpone annotation evaluation so modern syntax like `float | None` works on
# the cluster's system Python (which predates 3.10).
from __future__ import annotations

import argparse
import threading
import time

import torch
import torch.nn as nn

# ── NVML (GPU utilisation) — optional, degrade gracefully ───────────────────────
try:
    import pynvml

    pynvml.nvmlInit()
    _NVML_HANDLE = pynvml.nvmlDeviceGetHandleByIndex(
        torch.cuda.current_device() if torch.cuda.is_available() else 0
    )
    NVML_OK = True
except Exception:
    _NVML_HANDLE = None
    NVML_OK = False

DEVICE          = "cuda" if torch.cuda.is_available() else "cpu"
EPOCHS          = 3
STEPS_PER_EPOCH = 40
WARMUP_STEPS    = 8

# The task is held FIXED across both phases (identical input size and model),
# so throughput in img/s is a valid apples-to-apples comparison.  Only the
# *execution* changes between phases: batch size, precision, and memory format.
FIXED_RES   = 64
FIXED_WIDTH = 96

SEP = "=" * 72


# ── Utilisation sampler ─────────────────────────────────────────────────────────
class GpuUtilSampler(threading.Thread):
    """Polls NVML for SM utilisation in a background thread while a phase runs."""

    def __init__(self, interval: float = 0.05):
        super().__init__(daemon=True)
        self.interval = interval
        self.samples: list[int] = []
        # NOTE: do NOT name this `_stop` — threading.Thread already has an
        # internal `_stop()` method, and shadowing it with an Event breaks
        # Thread.join() ('Event' object is not callable).
        self._stop_event = threading.Event()

    def run(self) -> None:
        if not NVML_OK:
            return
        while not self._stop_event.is_set():
            try:
                self.samples.append(pynvml.nvmlDeviceGetUtilizationRates(_NVML_HANDLE).gpu)
            except Exception:
                pass
            self._stop_event.wait(self.interval)

    def stop(self) -> None:
        self._stop_event.set()

    @property
    def mean(self) -> float | None:
        return sum(self.samples) / len(self.samples) if self.samples else None

    @property
    def peak(self) -> int | None:
        return max(self.samples) if self.samples else None


# ── Model (width/depth scale with the chosen config) ────────────────────────────
def conv_block(c_in: int, c_out: int) -> nn.Sequential:
    # Two convs then a downsample — compute-dense, keeps activation memory sane.
    return nn.Sequential(
        nn.Conv2d(c_in, c_out, 3, padding=1), nn.ReLU(inplace=True),
        nn.Conv2d(c_out, c_out, 3, padding=1), nn.ReLU(inplace=True),
        nn.MaxPool2d(2),
    )


class ConvNet(nn.Module):
    def __init__(self, width: int):
        super().__init__()
        self.features = nn.Sequential(
            conv_block(3, width),
            conv_block(width, width * 2),
            conv_block(width * 2, width * 4),
            nn.AdaptiveAvgPool2d((4, 4)),
        )
        self.classifier = nn.Linear(width * 4 * 4 * 4, 10)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(x).flatten(1))


# ── Memory helpers ──────────────────────────────────────────────────────────────
def total_vram_gb() -> float:
    return torch.cuda.get_device_properties(0).total_memory / 1024 ** 3


def peak_vram_pct() -> float:
    peak = torch.cuda.max_memory_allocated()
    total = torch.cuda.get_device_properties(0).total_memory
    return peak / total * 100.0


def precision_label(amp_dtype) -> str:
    if amp_dtype is None:
        return "FP32"
    return "BF16 autocast" if amp_dtype == torch.bfloat16 else "FP16 autocast"


# ── One training phase ──────────────────────────────────────────────────────────
def run_phase(name: str, cfg: dict) -> dict:
    """Run a short training loop under `cfg` and return its metrics."""
    print(SEP)
    print(f"  PHASE: {name}")
    print(SEP)
    print(f"    batch_size   : {cfg['batch']}")
    print(f"    resolution   : {cfg['res']}x{cfg['res']}")
    print(f"    model width  : {cfg['width']} -> {cfg['width']*4}")
    print(f"    precision    : {precision_label(cfg['amp'])}")
    print(f"    memory format: {'channels_last' if cfg['channels_last'] else 'contiguous'}")
    print()

    model = ConvNet(cfg["width"]).to(DEVICE)
    if cfg["channels_last"] and DEVICE == "cuda":
        model = model.to(memory_format=torch.channels_last)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    criterion = nn.CrossEntropyLoss()

    # GPU-resident, preallocated batch: removes per-step host/data overhead so
    # the GPU is fed continuously (a real utilisation lever, not a cheat).
    x = torch.randn(cfg["batch"], 3, cfg["res"], cfg["res"], device=DEVICE)
    y = torch.randint(0, 10, (cfg["batch"],), device=DEVICE)
    if cfg["channels_last"] and DEVICE == "cuda":
        x = x.to(memory_format=torch.channels_last)

    def step() -> None:
        optimizer.zero_grad(set_to_none=True)
        # This synthetic loop measures memory/throughput only, so FP16 runs
        # without a GradScaler; a real FP16 training run needs one.
        if cfg["amp"] is not None and DEVICE == "cuda":
            with torch.autocast(device_type="cuda", dtype=cfg["amp"]):
                loss = criterion(model(x), y)
        else:
            loss = criterion(model(x), y)
        loss.backward()
        optimizer.step()

    # Warmup (cuDNN autotune, allocator warmup) — excluded from timing.
    for _ in range(WARMUP_STEPS):
        step()
    if DEVICE == "cuda":
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()

    sampler = GpuUtilSampler()
    sampler.start()
    t0 = time.perf_counter()
    n_steps = EPOCHS * STEPS_PER_EPOCH
    for _ in range(n_steps):
        step()
    if DEVICE == "cuda":
        torch.cuda.synchronize()
    elapsed = time.perf_counter() - t0
    sampler.stop()
    sampler.join()

    samples = n_steps * cfg["batch"]
    metrics = {
        "throughput": samples / elapsed,
        "util_mean": sampler.mean,
        "util_peak": sampler.peak,
        "vram_pct": peak_vram_pct() if DEVICE == "cuda" else None,
    }

    if metrics["vram_pct"] is not None:
        bar_fill = int(32 * metrics["vram_pct"] / 100)
        bar = "█" * bar_fill + "░" * (32 - bar_fill)
        print(f"    Peak VRAM       : {metrics['vram_pct']:5.1f}%  [{bar}]")
    if metrics["util_mean"] is not None:
        print(f"    GPU utilisation : {metrics['util_mean']:5.1f}% mean, "
              f"{metrics['util_peak']}% peak")
    else:
        print("    GPU utilisation : (NVML unavailable — install nvidia-ml-py)")
    print(f"    Throughput      : {metrics['throughput']:8.0f} img/s")
    print()

    # Free before the next phase.
    del model, optimizer, x, y
    if DEVICE == "cuda":
        torch.cuda.empty_cache()
    return metrics


# ── Config selection ────────────────────────────────────────────────────────────
def best_amp_dtype():
    """BF16 on A100/H100 (sm_80+); FP16 on V100/T4.  V100/T4 have FP16 Tensor
    Cores but NO BF16 hardware.  We check compute capability rather than
    torch.cuda.is_bf16_supported(), which returns True even on a V100 (it
    reports software support) and would pick a format the Tensor Cores can't
    accelerate."""
    if DEVICE != "cuda":
        return None
    major = torch.cuda.get_device_capability()[0]
    return torch.bfloat16 if major >= 8 else torch.float16


def baseline_config() -> dict:
    # Same task as the tuned phase — only the batch is deliberately tiny.
    # Small batches leave the SMs idle; launch/sync overhead dominates.
    return {"batch": 8, "res": FIXED_RES, "width": FIXED_WIDTH,
            "amp": None, "channels_last": False}


def tuned_config() -> dict:
    """SAME task as the baseline (same res + width).  Only the execution knobs
    change: a large batch (scaled to the GPU present), mixed precision, and
    channels_last memory format."""
    if DEVICE != "cuda":
        return {"batch": 64, "res": FIXED_RES, "width": FIXED_WIDTH,
                "amp": None, "channels_last": False}
    gb  = total_vram_gb()
    amp = best_amp_dtype()
    if gb > 70:       # A100 (80 GB)
        batch = 512
    elif gb > 24:     # V100 (32 GB)
        batch = 256
    else:
        batch = 128
    return {"batch": batch, "res": FIXED_RES, "width": FIXED_WIDTH,
            "amp": amp, "channels_last": True}


def run_with_oom_guard(name: str, cfg: dict) -> dict:
    """Retry with a halved batch if we hit an OOM on smaller GPUs."""
    while True:
        try:
            return run_phase(name, cfg)
        except RuntimeError as e:
            if "out of memory" in str(e).lower() and cfg["batch"] > 32:
                torch.cuda.empty_cache()
                cfg = {**cfg, "batch": cfg["batch"] // 2}
                print(f"    ⚑  OOM — retrying with batch_size={cfg['batch']}\n")
            else:
                raise


# ── Main ────────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-only", action="store_true",
                        help="Only run the undersized baseline (show the problem).")
    args = parser.parse_args()

    print(SEP)
    print("  GPU MEMORY & UTILISATION MONITOR — EXPLORER")
    print(SEP)
    print(f"  Device : {DEVICE}")
    if DEVICE == "cuda":
        gb = total_vram_gb()
        print(f"  GPU    : {torch.cuda.get_device_name(0)}  ({gb:.1f} GB VRAM)")
        amp_name = precision_label(best_amp_dtype()).split()[0]  # "BF16" / "FP16"
        print(f"  ↳ tuned phase will use {amp_name} autocast on this GPU.")
    if not NVML_OK:
        print("  NVML   : not available — install `nvidia-ml-py` for live utilisation.")
    else:
        print("  NVML   : live GPU-utilisation sampling enabled.")
    print()

    base = run_with_oom_guard("BASELINE (undersized — the problem)", baseline_config())

    if args.baseline_only or DEVICE != "cuda":
        print(SEP)
        print("  Baseline only.  Re-run without --baseline-only (on a GPU) to see")
        print("  the tuned config and the improvement it produces.")
        print(SEP)
        return

    tuned_cfg = tuned_config()
    tuned = run_with_oom_guard("TUNED (GPU-appropriate — the fix)", tuned_cfg)

    # ── Comparison + explanation ────────────────────────────────────────────────
    print(SEP)
    print("  WHAT CHANGED  (baseline → tuned)")
    print(SEP)
    b, t = baseline_config(), tuned_cfg
    print(f"  Task held FIXED : {FIXED_RES}x{FIXED_RES} input, model width "
          f"{FIXED_WIDTH} → {FIXED_WIDTH*4}")
    print(f"  (same work per image, so img/s is a fair comparison)")
    print()
    rows = [
        ("Batch size",    f"{b['batch']}", f"{t['batch']}",
         "more samples per kernel launch → amortises launch/sync overhead"),
        ("Precision",     precision_label(b["amp"]), precision_label(t["amp"]),
         "engages Tensor Cores, ~halves activation bytes"),
        ("Memory format", "contiguous" if not b["channels_last"] else "channels_last",
         "channels_last" if t["channels_last"] else "contiguous",
         "channels_last matches the Tensor Core layout for convolutions"),
    ]
    print(f"  {'Lever':<15}{'baseline':<16}{'tuned':<16}why it raises utilisation")
    print(f"  {'-'*15}{'-'*16}{'-'*16}{'-'*30}")
    for lever, bv, tv, why in rows:
        print(f"  {lever:<15}{bv:<16}{tv:<16}{why}")
    print()

    print(SEP)
    print("  RESULT")
    print(SEP)
    def fmt_util(m):
        return f"{m['util_mean']:.0f}%" if m["util_mean"] is not None else "n/a"
    print(f"  {'':<20}{'baseline':<14}{'tuned':<14}")
    print(f"  {'GPU utilisation':<20}{fmt_util(base):<14}{fmt_util(tuned):<14}")
    if base["vram_pct"] is not None:
        print(f"  {'Peak VRAM':<20}{base['vram_pct']:.0f}%{'':<11}{tuned['vram_pct']:.0f}%")
    print(f"  {'Throughput (img/s)':<20}{base['throughput']:<14.0f}{tuned['throughput']:<14.0f}")
    speedup = tuned["throughput"] / base["throughput"] if base["throughput"] else float("nan")
    print(f"\n  → {speedup:.1f}x more images/second on the same GPU.")
    if base["util_mean"] is not None and tuned["util_mean"] is not None:
        print(f"  → GPU utilisation rose from {base['util_mean']:.0f}% "
              f"to {tuned['util_mean']:.0f}%.")
    print()
    print("  Takeaway: on a fast GPU like the V100, low utilisation usually")
    print("  means you are feeding it too little per step, NOT that the GPU is")
    print("  slow.  For the SAME task, increase the batch size, enable mixed")
    print("  precision, and use channels_last — then re-check nvidia-smi.")
    print("  (Resolution and model width are part of your task, not tuning")
    print("  knobs — changing them changes the work, so don't compare img/s")
    print("  across different values.)")
    print(SEP)


if __name__ == "__main__":
    main()
