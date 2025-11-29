from ultralytics import YOLO

model = YOLO('yolov8n.pt')  # small, fast model (good baseline for CPU)

# Stage 1: fast coarse training at smaller imgsz
model.train(
    data='e:/PROGRAMING/MINiProject/dataset/data.yaml',
    epochs=15,
    imgsz=320,
    batch=8,
    name='yolov8n_leopard_stage1',
    device='cpu',
    augment=True,
    hsv_h=0.015, hsv_s=0.7, hsv_v=0.4,
    translate=0.1, scale=0.5, fliplr=0.5, mosaic=1.0,
    patience=10,  # early stop if val metric doesn't improve
    workers=2,
)

# Stage 2: fine-tune at larger imgsz for better precision (resume training)
model.train(
    data='e:/PROGRAMING/MINiProject/dataset/data.yaml',
    epochs=7,                    # 15 + 7 ~= 22 total
    imgsz=480,
    batch=8,
    name='yolov8n_leopard_stage2',
    device='cpu',
    resume=True,
    augment=True,
    patience=10,
    workers=2,
)
