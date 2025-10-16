import cv2
from ultralytics import YOLO

# Load the trained YOLOv8 model
# IMPORTANT: Replace this path with the actual path to your trained model's weights.
# The path will look something like: 'runs/detect/yolov8n_leopard_detection/weights/best.pt'
model_path = 'runs/detect/yolov8n_leopard_detection3/weights/best.pt'
model = YOLO(model_path)

# Open a connection to the webcam (0 is usually the default camera)
# Or, you can provide a path to a video file like: 'path/to/your/video.mp4'
video_source = "./videoplayback.mp4" 
cap = cv2.VideoCapture(video_source)

if not cap.isOpened():
    print(f"Error: Could not open video source: {video_source}")
    exit()

while True:
    # Read a frame from the video
    success, frame = cap.read()

    if success:
        # Run YOLOv8 inference on the frame
        results = model(frame)

        # Visualize the results on the frame
        annotated_frame = results[0].plot()

        # Display the annotated frame
        cv2.imshow("YOLOv8 Leopard Detection", annotated_frame)

        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    else:
        # Break the loop if the end of the video is reached
        break

# Release the video capture object and close the display window
cap.release()
cv2.destroyAllWindows()
