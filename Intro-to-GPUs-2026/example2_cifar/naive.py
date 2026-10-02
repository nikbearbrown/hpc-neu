import torch
import torchvision
from torch.utils.data import DataLoader
import time

dataset = torchvision.datasets.CIFAR10(root='./data', train=True, download=True, transform=torchvision.transforms.ToTensor())


# num_workers=0 means the CPU works one-by-one (Bottleneck)
loader = DataLoader(dataset, batch_size=256, num_workers=0)
num_batches = 40

torch.cuda.synchronize()
start = time.time()

for i, (images, labels) in enumerate(loader):
    images = images.to("cuda")
    if i == 40: break 

torch.cuda.synchronize()
print(f"--- NAIVE I/O RESULTS ---")
print(f"Time to load {num_batches} batches: {time.time() - start:.4f}s")