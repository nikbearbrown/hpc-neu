import torch
import time

device = "cuda" if torch.cuda.is_available() else "cpu"
model = torch.nn.Linear(2048, 2048).to(device)
torch.cuda.reset_peak_memory_stats()
torch.cuda.synchronize()

data_size=50000

start = time.time()
# The "Straw" approach: A lot of separate commands to the GPU
for _ in range(data_size):
    data = torch.randn(1, 2048).to(device)
    _ = model(data)

torch.cuda.synchronize()
print(f"--- NAIVE RESULTS ---")
print(f"Naive Time: {time.time() - start:.4f}s")
print(f"Memory Used: {torch.cuda.max_memory_allocated() / 1e6:.2f}MB")