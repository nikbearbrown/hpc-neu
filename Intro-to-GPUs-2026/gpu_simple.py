import os

print("CUDA_VISIBLE_DEVICES =", os.environ.get("CUDA_VISIBLE_DEVICES"))

if "CUDA_VISIBLE_DEVICES" in os.environ:
    print("GPU successfully allocated by scheduler")
else:
    print("No GPU visible")