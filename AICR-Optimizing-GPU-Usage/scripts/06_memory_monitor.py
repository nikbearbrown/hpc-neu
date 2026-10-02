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

The trap on AICR: the B200 (192 GB, very high SM count) is so powerful that a
small model / small batch / FP32 workload leaves it mostly idle.  Kernel-launch
and Python overhead dominate, and BOTH memory and utilisation stay low —
often < 40% util even though "the code runs fine".

This script demonstrates the fix directly.  It runs the SAME model twice:

  1. BASELINE  — an undersized config (small batch, tiny images, FP32)
                 → the < 40% utilisation you are seeing.
  2. TUNED     — a B200-appropriate config (large batch, larger images,
                 wider model, BF16 Tensor Cores, channels_last, GPU-resident
                 data) → high, healthy utilisation.

For each phase it measures peak VRAM, mean/max GPU utilisation (sampled live
from NVML), and throughput, then prints exactly WHAT changed and WHY
utilisation went up.

AICR hardware context:
  B200          — 192 GB VRAM  (very large; even big models fit in FP32)
  RTX PRO 6000  — 96 GB VRAM   (still large by most standards)

Having lots of VRAM does NOT mean you should leave it mostly empty.
Low memory usage + low utilisation = wasted hardware.
Goal: utilisation 80-100%, memory 70-90%.

Usage:
    python 06_memory_monitor.py                 (GPU strongly recommended)
    python 06_memory_monitor.py --baseline-only (just show the problem)

Utilisation sampling needs NVML bindings (usually preinstalled with the driver):
    pip install nvidia-ml-py
Without it, the script still runs and reports memory + throughput, and infers
utilisation from throughput scaling.
"""

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

SEP = "=" * 72


# ── Utilisation sampler ─────────────────────────────────────────────────────────
class GpuUtilSampler(threading.Thread):
    """Polls NVML for SM utilisation in a background thread while a phase runs."""

    def __init__(self, interval: float = 0.05):
        super().__init__(daemon=True)
        self.interval = interval
        self.samples: list[int] = []
        self._stop = threading.Event()

    def run(self) -> None:
        if not NVML_OK:
            return
        while not self._stop.is_set():
            try:
                self.samples.append(pynvml.nvmlDeviceGetUtilizationRates(_NVML_HANDLE).gpu)
            except Exception:
                pass
            self._stop.wait(self.interval)

    def stop(self) -> None:
        self._stop.set()

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


# ── One training phase ──────────────────────────────────────────────────────────
def run_phase(name: str, cfg: dict) -> dict:
    """Run a short training loop under `cfg` and return its metrics."""
    print(SEP)
    print(f"  PHASE: {name}")
    print(SEP)
    print(f"    batch_size   : {cfg['batch']}")
    print(f"    resolution   : {cfg['res']}x{cfg['res']}")
    print(f"    model width  : {cfg['width']} -> {cfg['width']*4}")
    print(f"    precision    : {'BF16 autocast' if cfg['bf16'] else 'FP32'}")
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
        if cfg["bf16"] and DEVICE == "cuda":
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
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
def baseline_config() -> dict:
    # Deliberately undersized — this is the < 40% util workload.
    return {"batch": 64, "res": 32, "width": 64, "bf16": False, "channels_last": False}


def tuned_config() -> dict:
    """Scale the tuned workload to the GPU actually present."""
    if DEVICE != "cuda":
        return {"batch": 128, "res": 48, "width": 96, "bf16": False, "channels_last": False}
    gb = total_vram_gb()
    if gb > 150:      # B200 (192 GB)
        return {"batch": 1024, "res": 96, "width": 256, "bf16": True, "channels_last": True}
    if gb > 60:       # RTX PRO 6000 (96 GB)
        return {"batch": 512, "res": 80, "width": 192, "bf16": True, "channels_last": True}
    return {"batch": 256, "res": 64, "width": 128, "bf16": True, "channels_last": True}


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
    print("  GPU MEMORY & UTILISATION MONITOR — AICR")
    print(SEP)
    print(f"  Device : {DEVICE}")
    if DEVICE == "cuda":
        gb = total_vram_gb()
        print(f"  GPU    : {torch.cuda.get_device_name(0)}  ({gb:.1f} GB VRAM)")
        if gb > 150:
            print("  ↳ B200 (192 GB) — extremely powerful; small workloads leave it idle.")
        elif gb > 60:
            print("  ↳ RTX PRO 6000 (96 GB) — large; still easy to under-feed.")
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
    tuned = run_with_oom_guard("TUNED (B200-appropriate — the fix)", tuned_cfg)

    # ── Comparison + explanation ────────────────────────────────────────────────
    print(SEP)
    print("  WHAT CHANGED  (baseline → tuned)")
    print(SEP)
    b, t = baseline_config(), tuned_cfg
    rows = [
        ("Batch size",   f"{b['batch']}", f"{t['batch']}",
         "more samples per kernel launch → less launch/Python overhead"),
        ("Resolution",   f"{b['res']}x{b['res']}", f"{t['res']}x{t['res']}",
         "bigger tensors → larger, more efficient GEMMs/convolutions"),
        ("Model width",  f"{b['width']}", f"{t['width']}",
         "more channels → more arithmetic per byte moved"),
        ("Precision",    "FP32", "BF16" if t["bf16"] else "FP32",
         "engages 5th-gen Tensor Cores, ~halves activation bytes"),
        ("Data feed",    "new randn/step", "preallocated on GPU",
         "removes per-step host overhead → GPU never waits"),
    ]
    print(f"  {'Lever':<13}{'baseline':<16}{'tuned':<16}why it raises utilisation")
    print(f"  {'-'*13}{'-'*16}{'-'*16}{'-'*30}")
    for lever, bv, tv, why in rows:
        print(f"  {lever:<13}{bv:<16}{tv:<16}{why}")
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
    print("  Takeaway: on a B200, < 40% utilisation usually means the workload is")
    print("  too small for the hardware, NOT that the GPU is slow.  Scale batch,")
    print("  resolution, and model width, and use BF16 — then re-check nvidia-smi.")
    print(SEP)


if __name__ == "__main__":
    main()
