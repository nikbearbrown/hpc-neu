import torch
import time

device = "cuda" if torch.cuda.is_available() else "cpu"
model = torch.nn.Linear(2048, 2048).to(device)
torch.cuda.reset_peak_memory_stats()
torch.cuda.synchronize()

data_size=50000

start = time.time()
# CHANGE: We send all the data rows at once instead of a loop of 1 (Efficient)
data = torch.randn(data_size, 2048).to(device)
_ = model(data)

torch.cuda.synchronize()
print(f"--- OPTIMIZED RESULTS ---")
print(f"Time Taken: {time.time() - start:.4f}s")
print(f"Peak VRAM:  {torch.cuda.max_memory_allocated() / 1e6:.2f} MB")