import torch

print("Torch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
print("GPU name:", torch.cuda.get_device_name(0))

x = torch.tensor([1.0, 2.0, 3.0], device="cuda")
print("Tensor device:", x.device)
