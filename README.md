# Leopard Detection Alarm — Monorepo README

This repository combines model training/inference (Python + Ultralytics YOLOv8), database ingestion (Node.js), a backend API for ESP32, and the ESP32 firmware (Arduino/PlatformIO). This guide explains each part and how to run them on Windows PowerShell.

## Overview
- Python scripts run YOLOv8 to detect leopards from camera/video. On detection, they log timestamp + GPS coords to a text file.
- A Node.js ingestor tails the text file and writes rows to MySQL (`LogDetections`).
- A Node.js server exposes `/check-alarm` for ESP32 to query recent detections and decide whether to trigger the siren.
- ESP32 firmware polls the server and activates LED + buzzer if an alarm is signaled.

## Repositories
- Backend/Detection (this repo): `https://github.com/themonstersd13/ImagemodelMP`
- Mobile Application (alerts UI): `https://github.com/SrushtiGarad7/Leopard-Detection-Alert-System`

## Git Clone Instructions
Clone the backend/detection repo:
```powershell
# Choose a workspace folder, then:
git clone https://github.com/themonstersd13/ImagemodelMP.git
cd ImagemodelMP
```

Optionally, clone the mobile application (Android) in a separate folder:
```powershell
git clone https://github.com/SrushtiGarad7/Leopard-Detection-Alert-System.git
```
Refer to that repo’s README for building and running the mobile app.

## Folder Map
- `dataset/` — YOLO dataset and `data.yaml`.
- `Training/` — training scripts (`train.py`, `train2.py`).
- `runs/detect/` — Ultralytics output folders with trained weights (e.g., `yolov8n_leopard_detection3/weights/best.pt`).
- `video-samples/` — sample videos for local testing.
- `detect.py` — simple YOLOv8 inference + display.
- `newDetect.py` — improved YOLOv8 inference (threaded, frame-skip, resize, logging).
- `outputTxt/` — file-tail ingestor to MySQL (`insertLog.js`, `db.js`, `.env`, `README.md`).
- `ESP/` — Express server (`server.js`, `db.cjs`, `.env`) for ESP32.
- `leopardDetectionAlarm/` — ESP32 Arduino project (PlatformIO) — firmware (`src/main.cpp`).

## File Structure (key paths)
```
MINiProject/
  detect.py
  newDetect.py
  yolov8n.pt
  yolov8m.pt
  dataset/
    data.yaml
    train/
      images/
      labels/
  Training/
    train.py
    train2.py
  runs/
    detect/
      yolov8n_leopard_detection3/
        weights/best.pt
  video-samples/
  outputTxt/
    package.json
    db.js
    insertLog.js
    detections.txt
    .env
    README.md
  ESP/
    package.json
    server.js
    db.cjs
    .env
  leopardDetectionAlarm/
    platformio.ini
    src/main.cpp
```

## Prerequisites
- Python 3.11+ with `ultralytics`, `opencv-python`.
- Node.js 18+.
- MySQL database (local or hosted).
- PlatformIO extension for VS Code and ESP32 toolchain.

## Python — Detection Scripts

### `detect.py` (quick demo)
- **Purpose:** Run YOLOv8 on a video/webcam and display annotated frames.
- **Key config:** edit `model_path` and `video_source` in the file.
- **Run:**
```powershell
# activate venv if you have one
# .\venv\Scripts\Activate.ps1
pip install ultralytics opencv-python
python .\detect.py
```
- **Quit:** press `q` in the window.

### `newDetect.py` (production-friendly)
- **Purpose:** Threaded inference with resize + frame-skipping; writes detections to `outputTxt/detections.txt` with cooldown to avoid spam.
- **Defaults:**
  - `--model` `runs/detect/yolov8n_leopard_detection3/weights/best.pt`
  - `--source` `./video-samples/s31.mp4` (set to `0` for webcam)
  - `--out` `./outputTxt/detections.txt`
  - `--cooldown-mins` `10`
  - Performance options: `--max-width 640`, `--skip-frames 1`, `--conf 0.25`, `--no-plot`
- **Dry-run file write test:**
```powershell
python .\newDetect.py --test-write --out .\outputTxt\detections.txt --lat 18.5204 --lon 73.8567
```
- **Run inference:**
```powershell
# Ensure dependencies
pip install ultralytics opencv-python
# Run with webcam (index 0)
python .\newDetect.py --source 0 --model .\runs\detect\yolov8n_leopard_detection3\weights\best.pt --out .\outputTxt\detections.txt --verbose
# Or run on a video file
python .\newDetect.py --source .\video-samples\s31.mp4 --verbose
```
- **Notes:** Writes a line `YYYY-MM-DD HH:MM:SS,lat,lon` on detection; enforces cooldown via `.last_logged_ts`.

## Node.js — Output Ingestor (`outputTxt/`)
- **Purpose:** Tail `detections.txt` and insert new lines into MySQL table `LogDetections`.
- **Docs:** See `outputTxt/README.md`.
- **Setup:** create `outputTxt/.env` with either `DATABASE_URL` or individual vars `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT`.
- **Table:**
```sql
CREATE TABLE IF NOT EXISTS `LogDetections` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `time` DATETIME NOT NULL,
  `latitude` DOUBLE NOT NULL,
  `longitude` DOUBLE NOT NULL
);
```
- **Run:**
```powershell
cd .\outputTxt
npm install
npm start
```
- **Default file:** `outputTxt/detections.txt`.

## Node.js — ESP Backend (`ESP/`)
- **Purpose:** Serve `/check-alarm` for ESP32. Returns `alarm: true` if a detection exists within last 10 minutes.
- **Dependencies:** `express`, `mysql2`, `dotenv`, `cors`, `body-parser`.
- **Setup:** create `ESP/.env` with DB credentials (same variables as above). Optional `PORT`.
- **Run:**
```powershell
cd .\ESP
npm install
npm start
# Server on http://localhost:3000 (unless PORT set)
```
- **Endpoints:**
  - `POST /check-alarm` — responds `{ alarm: boolean, detection?: {...} }`.
  - `GET /set-alarm?status=true|false` — manual override toggle.
  - `GET /status` — health + manual flag.

## ESP32 Firmware — `leopardDetectionAlarm/`
- **Purpose:** Poll the backend and drive LED + buzzer when alarm.
- **Edit:** `src/main.cpp` — set `ssid`, `password`, and `serverURL` to your server IP, e.g. `http://<PC-IP>:3000/check-alarm`.
- **Build/Upload:**
```powershell
# With PlatformIO extension in VS Code
# Or from terminal in project folder
cd .\leopardDetectionAlarm
# Build
pio run
# Upload (ensure correct COM port in platformio.ini)
pio run --target upload
# Monitor
pio device monitor --baud 115200
```
- **Pins:** `LED_PIN=5`, `BUZZER_PIN=18`. Alarm duration 15s; queries every 5s; suppresses requests for 5 min after an alarm.

## Training — `Training/`
- **Purpose:** Train YOLOv8 models using `dataset/data.yaml`.
- **Typical run (example):**
```powershell

## Mobile App — RakshaSetu (React Native)
- Repo: `https://github.com/SrushtiGarad7/Leopard-Detection-Alert-System`
- Purpose: Real-time wildlife detection alerts and mapping (focused on Leopard detection). Designed to consume a public SQL-backed API.

### Key Features
- Real-time Map Tracking: Shows current user location; plots leopard detection markers.
- Detection List: Sortable list with location, confidence, and time.
- API Polling: Manual "Refresh Detections" fetch from your SQL API endpoint.
- Instant Audio Alert: Plays a tone on new data to simulate critical alerts.
- Responsive UI: React Native components for mobile/web.

### API Integration Setup
Update the API link in the app to your public endpoint. In `App.js`, set:
```javascript
pip install ultralytics
python .\Training\train.py --data .\dataset\data.yaml --model yolov8n.pt --epochs 50
```
- **Outputs:** saved under `runs/detect/.../weights/best.pt`.

### Required API Response Format
The endpoint should return a JSON array of objects with:
- `id`: number/string (e.g., `101`) — unique key.
- `species`: string (e.g., "Leopard (Panthera pardus)").
- `location`: object `{ latitude: number, longitude: number }`.
- `confidence`: number (0.0–1.0) — detection confidence.
- `timestamp`: string (e.g., "10/25/2025, 10:30:00 PM").
- `detector_id`: string (e.g., "SQL-Sensor-05").
- `status`: string (e.g., "New").

If your current backend doesn't yet provide an `/api/logs` endpoint, you can implement a simple read-only API that queries `LogDetections` and maps rows to the above schema.

### Connection Troubleshooting
- Local IPs (e.g., `http://10.39.22.186:3500/api/logs`) only work on your LAN.
- Use a public URL via tunneling or deploy to cloud:
  - ngrok: `ngrok http 3000` to expose your local ESP server/API.
  - Cloud options: Render, Railway, Fly.io, AWS, Heroku.

### Technical Stack (App)
- Frontend: React Native
- State: React Hooks (`useState`, `useEffect`, `useCallback`)
- Styles: `StyleSheet`
- Mapping: `react-native-maps` (`MapView`, `Marker`)
- Data: External SQL API (HTTP GET)

## End-to-End Flow
1. Start ESP backend server:
```powershell
cd .\ESP; npm install; npm start
```
2. Start ingestor:
```powershell
cd .\outputTxt; npm install; npm start
```
3. Run detection script to feed detections:
```powershell
python .\newDetect.py --source 0 --model .\runs\detect\yolov8n_leopard_detection3\weights\best.pt --out .\outputTxt\detections.txt
```
4. Flash ESP32 firmware and set `serverURL` to your PC IP.
5. Confirm `/status` and `/check-alarm` respond; ESP should trigger alarm on fresh detections.

## Tips
- If the ESP can’t reach your PC, ensure both are on same network and use the PC’s LAN IP in `serverURL`.
- For webcam, use `--source 0`. For RTSP/IP cams, pass the RTSP URL.
- Adjust `--conf`, `--max-width`, and `--skip-frames` to balance speed vs accuracy.

## Known Paths
- Weights: `runs/detect/yolov8n_leopard_detection3/weights/best.pt`.
- Sample videos: `video-samples/`.
- Text log: `outputTxt/detections.txt` (auto-created).
- Cooldown marker: `.last_logged_ts`.

## License
Internal project materials; usage within the team.
