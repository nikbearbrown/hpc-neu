import torch
import torchvision
from torch.utils.data import DataLoader
import time

dataset = torchvision.datasets.CIFAR10(root='./data', train=True, download=True, transform=torchvision.transforms.ToTensor())

# CHANGE: num_workers=4 uses 4 CPU cores to prepare data
# CHANGE: pin_memory=True speeds up the transfer from RAM to GPU
loader = DataLoader(dataset, batch_size=256, num_workers=2, pin_memory=True)
num_batches = 40

torch.cuda.synchronize()
start = time.time()

for i, (images, labels) in enumerate(loader):
    # non_blocking=True allows the transfer to happen while the CPU prepares the next batch
    images = images.to("cuda", non_blocking=True)
    if i == num_batches: break 

torch.cuda.synchronize()
print(f"--- OPTIMIZED I/O RESULTS ---")
print(f"Time to load {num_batches} batches: {time.time() - start:.4f}s")