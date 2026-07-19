import torch
try:
    checkpoint = torch.load(r"C:\Users\acer\Desktop\BAandOD_Model\models\fasterrcnn_device_best.pth")
    print("✓ File loaded successfully")
    print("Keys in checkpoint:", checkpoint.keys() if isinstance(checkpoint, dict) else type(checkpoint))
except Exception as e:
    print(f"✗ Error loading: {type(e).__name__}: {e}")