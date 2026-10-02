"""
7.1 Single GPU: basic PyTorch on one GPU

PyTorch picks up CUDA automatically if a GPU is available. Tensors placed
on the GPU device dispatch to optimized CUDA kernels (cuBLAS, cuDNN, etc.)
without any explicit kernel code from the user.

Run:
    python single_gpu.py
"""

import torch
import time


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    if device.type == "cuda":
        print(f"GPU name:     {torch.cuda.get_device_name(0)}")

    N = 4096

    # Allocate tensors ONCE, outside the timed region.
    a = torch.randn(N, N, device=device)
    b = torch.randn(N, N, device=device)

    # Warm-up: first kernel launch includes JIT / cuBLAS init overhead.
    for _ in range(3):
        _ = torch.matmul(a, b)
    if device.type == "cuda":
        torch.cuda.synchronize()

    # Timed run. Average over multiple iterations for a more stable number.
    n_iter = 100
    t0 = time.perf_counter()
    for _ in range(n_iter):
        c = torch.matmul(a, b)
    if device.type == "cuda":
        torch.cuda.synchronize()
    elapsed = (time.perf_counter() - t0) / n_iter

    gflops = 2.0 * N ** 3 / elapsed / 1e9
    print(f"matmul {N}x{N} (avg over {n_iter} iters): "
          f"{elapsed*1000:.2f} ms/iter  |  {gflops:.1f} GFLOPS")
    print(f"Result shape: {tuple(c.shape)}, dtype: {c.dtype}")
    print(f"Sum of C (for sanity): {c.sum().item():.4f}")


if __name__ == "__main__":
    main()
