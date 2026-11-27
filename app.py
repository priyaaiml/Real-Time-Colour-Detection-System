"""Real-Time Colour Detection System - Flask + OpenCV + NumPy."""
import platform
import threading
import time
from datetime import datetime

import cv2
import numpy as np
from flask import Flask, Response, jsonify, render_template, request

app = Flask(__name__)

# ---------------------------------------------------------------- detection
# HSV ranges (OpenCV: H 0-179, S 0-255, V 0-255)
COLOUR_RANGES = {
    "red":    [((0, 120, 70), (10, 255, 255)), ((170, 120, 70), (179, 255, 255))],
    "orange": [((11, 120, 80), (22, 255, 255))],
    "yellow": [((23, 100, 80), (35, 255, 255))],
    "green":  [((36, 80, 50), (85, 255, 255))],
    "blue":   [((86, 100, 50), (130, 255, 255))],
    "purple": [((131, 70, 40), (160, 255, 255))],
    "black":  [((0, 0, 0), (179, 255, 50))],
    "white":  [((0, 0, 200), (179, 40, 255))],
}
# Box colour (BGR) used when drawing each label
BOX_BGR = {
    "red": (0, 0, 255), "orange": (0, 140, 255), "yellow": (0, 230, 255),
    "green": (0, 200, 0), "blue": (255, 100, 0), "purple": (200, 60, 150),
    "black": (60, 60, 60), "white": (230, 230, 230),
}
MIN_AREA = 2000
MAX_BOXES_PER_COLOUR = 10  # every counted region gets a box
KERNEL = np.ones((5, 5), np.uint8)


def build_mask(hsv, name):
    mask = None
    for lo, hi in COLOUR_RANGES[name]:
        m = cv2.inRange(hsv, np.array(lo), np.array(hi))
        mask = m if mask is None else cv2.bitwise_or(mask, m)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, KERNEL)
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, KERNEL)


def describe(bgr):
    """Return hex / rgb / hsv for a mean BGR colour."""
    b, g, r = [int(round(v)) for v in bgr]
    h, s, v = cv2.cvtColor(np.uint8([[[b, g, r]]]), cv2.COLOR_BGR2HSV)[0][0]
    return {
        "hex": "#{:02X}{:02X}{:02X}".format(r, g, b),
        "rgb": [r, g, b],
        "hsv": [int(h) * 2, int(round(s / 255 * 100)), int(round(v / 255 * 100))],
    }


def detect(frame, selected="all"):
    """Annotate frame in place. Returns list of detections (largest first)."""
    blurred = cv2.GaussianBlur(frame, (7, 7), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    names = list(COLOUR_RANGES) if selected == "all" else [selected]
    frame_area = frame.shape[0] * frame.shape[1]
    found = []
    for name in names:
        mask = build_mask(hsv, name)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        best = None
        count = 0         # number of detected regions of this colour
        total_area = 0.0  # pixels covered by this colour (for dominant colour %)
        for c in contours[:MAX_BOXES_PER_COLOUR]:
            area = cv2.contourArea(c)
            if area < MIN_AREA:
                break
            count += 1
            # Fill this region, keep only real colour pixels (ignores holes inside it)
            roi = np.zeros(mask.shape, np.uint8)
            cv2.drawContours(roi, [c], -1, 255, -1)
            total_area += cv2.countNonZero(cv2.bitwise_and(roi, mask))
            x, y, w, h = cv2.boundingRect(c)
            colour = BOX_BGR[name]
            cv2.rectangle(frame, (x, y), (x + w, y + h), colour, 3)
            cv2.rectangle(frame, (x, max(0, y - 24)), (x + 8 * len(name) + 14, y), colour, -1)
            txt = (0, 0, 0) if name in ("yellow", "white", "orange") else (255, 255, 255)
            cv2.putText(frame, name.upper(), (x + 6, max(16, y - 7)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, txt, 1, cv2.LINE_AA)
            if best is None:
                best = {"name": name, "area": area, **describe(cv2.mean(blurred, roi)[:3])}
        if best:
            best["count"] = count
            best["percent"] = round(total_area / frame_area * 100, 1)
            best["area"] = total_area  # used to sort: biggest coverage first
            found.append(best)
    found.sort(key=lambda d: d["area"], reverse=True)
    return found



# ------------------------------------------------------------------- camera
class Camera:
    def __init__(self):
        self.cap = None
        self.running = False
        self.session = 0
        self.selected = "all"
        self.results = []
        self.latest_jpeg = None   # newest annotated frame (for Capture)
        self.captured = None      # frame saved by the Capture button
        self.lock = threading.Lock()

    def start(self):
        with self.lock:
            if self.running:
                return True
            if platform.system() == "Windows":
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            else:
                cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                cap.release()
                return False
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
            self.cap, self.running = cap, True
            self.session += 1
            self.results = []
            return True

    def stop(self):
        with self.lock:
            self.running = False
            self.session += 1
            self.results = []
            self.latest_jpeg = None
            if self.cap is not None:
                self.cap.release()
                self.cap = None

    def frames(self):
        my_session = self.session
        while self.running and self.session == my_session:
            with self.lock:
                if not self.running or self.cap is None:
                    break
                ok, frame = self.cap.read()
                selected = self.selected
            if not ok:
                time.sleep(0.05)
                continue
            frame = cv2.flip(frame, 1)  # mirror view
            found = detect(frame, selected)
            self.results = found
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok:
                self.latest_jpeg = buf.tobytes()
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")


camera = Camera()


# ------------------------------------------------------------------- routes
@app.route("/")
def index():
    return render_template("index.html", colours=list(COLOUR_RANGES))


@app.route("/video_feed")
def video_feed():
    return Response(camera.frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/start", methods=["POST"])
def api_start():
    ok = camera.start()
    if not ok:
        return jsonify(ok=False, error="Could not access the webcam. Close other apps using it and try again."), 500
    return jsonify(ok=True)


@app.route("/api/stop", methods=["POST"])
def api_stop():
    camera.stop()
    return jsonify(ok=True)


@app.route("/api/select", methods=["POST"])
def api_select():
    value = (request.get_json(silent=True) or {}).get("colour", "all")
    if value != "all" and value not in COLOUR_RANGES:
        return jsonify(ok=False, error="Unknown colour"), 400
    camera.selected = value
    return jsonify(ok=True, selected=value)


@app.route("/api/status")
def api_status():
    results = list(camera.results)  # already sorted: largest coverage first
    res = [{k: v for k, v in d.items() if k != "area"} for d in results]
    # Dominant colour = colour covering the largest area of the frame
    dominant = {"name": res[0]["name"], "percent": res[0]["percent"]} if res else None
    # Region counts only for the colours in the current detection mode
    mode_colours = list(COLOUR_RANGES) if camera.selected == "all" else [camera.selected]
    counts = {d["name"]: d["count"] for d in res}
    stats = [{"name": n, "count": counts.get(n, 0)} for n in mode_colours]
    return jsonify(running=camera.running, selected=camera.selected,
                   detections=res, dominant=dominant, stats=stats)


@app.route("/api/capture", methods=["POST"])
def api_capture():
    if not camera.running or camera.latest_jpeg is None:
        return jsonify(ok=False, error="Start the camera before capturing."), 400
    camera.captured = camera.latest_jpeg
    return jsonify(ok=True)


@app.route("/captured.jpg")
def captured_image():
    if camera.captured is None:
        return jsonify(ok=False, error="Nothing captured yet."), 404
    headers = {"Cache-Control": "no-store"}
    if request.args.get("download"):
        name = datetime.now().strftime("colour-capture-%Y%m%d-%H%M%S.jpg")
        headers["Content-Disposition"] = f'attachment; filename="{name}"'
    return Response(camera.captured, mimetype="image/jpeg", headers=headers)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
