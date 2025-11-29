#!/usr/bin/env python3
"""
newDetect.py (threaded + frame-skip + resize)

Improvements to reduce display lag:
 - inference runs in a background thread
 - frames are resized before inference (configurable)
 - skip-frames controls how many frames to drop between inferences
 - annotated frame updated asynchronously and shown by main thread
 - all prior logging/cooldown/file-write behavior preserved
"""
import argparse
import time
import os
from datetime import datetime
from pathlib import Path
import traceback
import threading

try:
    import cv2
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except Exception:
    ULTRALYTICS_AVAILABLE = False

# Hardcoded defaults
HARDCODE_LAT = 18.5204
HARDCODE_LON = 73.8567

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model", "-m", default="runs/detect/yolov8n_leopard_detection3/weights/best.pt")
    p.add_argument("--source", "-s", default="./video-samples/s31.mp4")
    p.add_argument("--out", "-o", default="./outputTxt/detections.txt")
    p.add_argument("--lat", type=float, default=HARDCODE_LAT)
    p.add_argument("--lon", type=float, default=HARDCODE_LON)
    p.add_argument("--cooldown-mins", type=float, default=10.0)
    p.add_argument("--last-file", default=".last_logged_ts")
    p.add_argument("--no-show", dest="show", action="store_false", help="disable GUI window")
    p.set_defaults(show=True)
    p.add_argument("--test-write", action="store_true")
    p.add_argument("--force-log", action="store_true")
    p.add_argument("--verbose", action="store_true")
    # performance options
    p.add_argument("--max-width", type=int, default=640, help="max width (px) to resize frames for inference/display")
    p.add_argument("--skip-frames", type=int, default=1, help="process every Nth frame (1 = every frame)")
    p.add_argument("--conf", type=float, default=0.25, help="confidence threshold for model (passed to model)")
    p.add_argument("--no-plot", action="store_true", help="do not draw annotated plot (faster)")
    return p.parse_args()

def load_last_ts(path):
    try:
        if path.exists():
            s = path.read_text(encoding="utf8").strip()
            if s:
                return float(s)
    except Exception:
        pass
    return 0.0

def save_last_ts(path, ts):
    try:
        with open(path, "w", encoding="utf8") as f:
            f.write(str(float(ts)))
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print("Warning: could not write last-ts file:", e)

def detections_count_from_result(res):
    try:
        boxes = res.boxes
        try:
            return len(boxes)
        except Exception:
            xy = getattr(boxes, "xyxy", None)
            if xy is not None:
                try:
                    return xy.shape[0]
                except Exception:
                    pass
    except Exception:
        pass
    try:
        return int(getattr(res, "n", 0))
    except Exception:
        return 0

def test_write(out_file: Path, lat: float, lon: float):
    ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts_str},{lat},{lon}\n"
    try:
        with open(out_file, "a", encoding="utf8") as f:
            f.write(line); f.flush(); os.fsync(f.fileno())
        print("SUCCESS: wrote test line to:", out_file.resolve())
        print("Line:", line.strip())
        return True
    except Exception as e:
        print("FAILED: could not write to", out_file.resolve())
        traceback.print_exc()
        return False

class InferenceWorker(threading.Thread):
    def __init__(self, model, conf, out_file, lat, lon, cooldown_secs, last_file_path,
                 force_log=False, no_plot=False, verbose=False):
        super().__init__(daemon=True)
        self.model = model
        self.conf = conf
        self.out_file = Path(out_file)
        self.lat = lat
        self.lon = lon
        self.cooldown_secs = cooldown_secs
        self.last_file_path = Path(last_file_path)
        self.force_log = force_log
        self.no_plot = no_plot
        self.verbose = verbose

        self._frame = None          # latest frame to run inference on (resized BGR numpy)
        self._frame_lock = threading.Lock()
        self._annotated = None      # latest annotated frame to display
        self._annot_lock = threading.Lock()
        self._stop = threading.Event()
        self.last_logged = load_last_ts(self.last_file_path)

    def update_frame(self, frame):
        with self._frame_lock:
            self._frame = frame

    def get_annotated(self):
        with self._annot_lock:
            return None if self._annotated is None else self._annotated.copy()

    def stop(self):
        self._stop.set()

    def _maybe_write_log(self, ts_str, nboxes):
        now = time.time()
        if self.force_log or (now - self.last_logged >= self.cooldown_secs):
            line = f"{ts_str},{self.lat},{self.lon}\n"
            try:
                with open(self.out_file, "a", encoding="utf8") as f:
                    f.write(line); f.flush(); os.fsync(f.fileno())
                self.last_logged = now
                save_last_ts(self.last_file_path, self.last_logged)
                print(f"[{ts_str}] Detected {nboxes} — logged to {self.out_file.resolve()}")
            except Exception as e:
                print("Error writing detection line:", e)
                traceback.print_exc()
        else:
            if self.verbose:
                remaining = int(self.cooldown_secs - (now - self.last_logged))
                print(f"Within cooldown ({remaining}s remaining), skipping write.")

    def run(self):
        while not self._stop.is_set():
            frame = None
            with self._frame_lock:
                if self._frame is None:
                    # nothing to do right now
                    pass
                else:
                    # take the latest frame and clear it (drop older)
                    frame = self._frame.copy()
                    self._frame = None
            if frame is None:
                time.sleep(0.01)
                continue

            try:
                # YOLO inference: pass conf param
                results = self.model(frame, conf=self.conf)
                res = results[0]
            except Exception as e:
                print("Inference error (worker):", e)
                traceback.print_exc()
                time.sleep(0.2)
                continue

            nboxes = detections_count_from_result(res)
            ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if nboxes > 0:
                # handle writing with cooldown
                self._maybe_write_log(ts_str, nboxes)

            # Prepare annotated image (or raw) for display
            if self.no_plot:
                # If no plot, we will just return the original frame
                annotated = frame
            else:
                try:
                    annotated = res.plot()
                except Exception:
                    annotated = frame

            with self._annot_lock:
                self._annotated = annotated

def scale_frame_to_max_width(frame, max_w):
    h, w = frame.shape[:2]
    if w <= max_w:
        return frame
    scale = max_w / float(w)
    new_w = int(w * scale)
    new_h = int(h * scale)
    return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

def main():
    args = parse_args()
    if args.test_write:
        # ensure parent exists
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        test_write(Path(args.out), args.lat, args.lon)
        return

    if not ULTRALYTICS_AVAILABLE:
        print("ultralytics/cv2 not available. Install dependencies to run inference.")
        return

    out_file = Path(args.out)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    print("Output file:", out_file.resolve())
    print("Using model:", args.model)
    print("Source:", args.source)
    print("Max width:", args.max_width, "Skip frames:", args.skip_frames,
          "Conf:", args.conf, "No-plot:", args.no_plot)

    # load model
    try:
        model = YOLO(args.model)
    except Exception as e:
        print("Could not load model:", e)
        traceback.print_exc()
        return

    # open capture
    try:
        src = int(args.source)
    except Exception:
        src = args.source
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        print("Error: could not open source:", args.source)
        return

    # start worker thread
    worker = InferenceWorker(model=model, conf=args.conf,
                             out_file=args.out, lat=args.lat, lon=args.lon,
                             cooldown_secs=args.cooldown_mins * 60.0,
                             last_file_path=args.last_file,
                             force_log=args.force_log,
                             no_plot=args.no_plot, verbose=args.verbose)
    worker.start()

    frame_count = 0
    last_show_time = time.time()
    displayed_frames = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                if args.verbose:
                    print("No frame read; end of source or camera disconnected.")
                break

            # resize for display & inference to max width to reduce cost
            scaled = scale_frame_to_max_width(frame, args.max_width)

            # feed worker every Nth frame (skip frames)
            frame_count += 1
            if (frame_count % args.skip_frames) == 0:
                # worker expects BGR numpy frame at reduced size
                worker.update_frame(scaled)

            # show latest annotated frame if available, otherwise show current scaled frame
            annotated = worker.get_annotated()
            to_show = annotated if annotated is not None else scaled

            if args.show:
                cv2.imshow("YOLOv8 Leopard Detection", to_show)
                displayed_frames += 1
                # keep GUI responsive. Use small waitKey (1). If no-show, we still want to be non-blocking
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    if args.verbose: print("Quit requested.")
                    break

            # verbose: print approximate display FPS every 2s
            if args.verbose and (time.time() - last_show_time) > 2.0:
                now = time.time()
                fps = displayed_frames / (now - last_show_time)
                print(f"[verbose] approx display FPS: {fps:.1f}, frame_count: {frame_count}")
                displayed_frames = 0
                last_show_time = now

    finally:
        if args.verbose: print("Stopping worker and releasing capture...")
        worker.stop()
        # give worker a moment to finish
        worker.join(timeout=1.0)
        cap.release()
        if args.show:
            cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
