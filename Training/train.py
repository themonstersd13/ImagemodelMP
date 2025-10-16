from ultralytics import YOLO

# Load a pretrained YOLOv8 model
model = YOLO('yolov8n.pt')

# Train the model on the custom dataset
results = model.train(
    data='e:/PROGRAMING/MINiProject/dataset/data.yaml',
    epochs=20,
    imgsz=640,
    batch=8,
    name='yolov8n_leopard_detection',
    # device=0,
    # Augmentation parameters
    augment=True,
    hsv_h=0.015,  # hue
    hsv_s=0.7,  # saturation
    hsv_v=0.4,  # value
    degrees=0.0,
    translate=0.1,
    scale=0.5,
    shear=0.0,
    perspective=0.0,
    flipud=0.0,
    fliplr=0.5,
    mosaic=1.0,
    mixup=0.0,
)

print("Training finished.")
print("Model saved to:", results.save_dir)
