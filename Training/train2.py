# train_max_accuracy_cpu.py
import os
from ultralytics import YOLO
import torch

DATA_YAML = r"e:/PROGRAMING/MINiProject/dataset/data.yaml"
OUTPUT_NAME = "yolov8m_leopard_detection"
# pick a medium model for CPU feasibility
MODEL_CHECKPOINT = "yolov8m.pt"   # medium model: better than 'n' but still manageable on CPU
IMG_SIZE = 640
EPOCHS = 180
WORKERS = 2
AMP = False    # AMP not helpful on CPU
EMA = False    # can enable but may be slower

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Using device:", device)

model = YOLO(MODEL_CHECKPOINT)

# Use full dataset (all 10k images)
# Use progressive resizing: start with 480 then fine-tune at 640
print("Stage 1: coarse")
model.train(
    data=DATA_YAML,
    epochs=int(EPOCHS * 0.6),
    imgsz=480,
    batch=8,
    name=OUTPUT_NAME + "_stage1",
    device='cpu',
    augment=True,
    hsv_h=0.015, hsv_s=0.7, hsv_v=0.4,
    translate=0.1, scale=0.4, fliplr=0.5,
    mosaic=1.0, mixup=0.25,
    workers=WORKERS,
    patience=30,
)

print("Stage 2: fine-tune")
model.train(
    data=DATA_YAML,
    epochs=int(EPOCHS * 0.4),
    imgsz=IMG_SIZE,
    batch=6,
    name=OUTPUT_NAME + "_stage2",
    device='cpu',
    resume=True,
    augment=True,
    hsv_h=0.01, hsv_s=0.6, hsv_v=0.3,
    translate=0.05, scale=0.25, fliplr=0.5,
    mosaic=0.8, mixup=0.15,
    workers=WORKERS,
    patience=30,
)

print("CPU training finished. Check runs/train/* for results.")
