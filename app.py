"""Real-Time Colour Detection System - Flask + OpenCV + NumPy."""

import base64
from datetime import datetime

import cv2
import numpy as np
from flask import Flask, Response, jsonify, render_template, request

app = Flask(__name__)

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

BOX_BGR = {
    "red": (0, 0, 255), "orange": (0, 140, 255),
    "yellow": (0, 230, 255), "green": (0, 200, 0),
    "blue": (255, 100, 0), "purple": (200, 60, 150),
    "black": (60, 60, 60), "white": (230, 230, 230),
}

MIN_AREA = 2000
MAX_BOXES_PER_COLOUR = 10
KERNEL = np.ones((5, 5), np.uint8)

# Browser camera state. Flask does not open a physical webcam.
camera_running = False
selected_colour = "all"
latest_jpeg = None
captured_jpeg = None
camera_results = []


def build_mask(hsv, name):
    mask = None
    for lo, hi in COLOUR_RANGES[name]:
        m = cv2.inRange(hsv, np.array(lo), np.array(hi))
        mask = m if mask is None else cv2.bitwise_or(mask, m)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, KERNEL)
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, KERNEL)


def describe(bgr):
    """Return HEX, RGB and HSV values for a mean BGR colour."""
    b, g, r = [int(round(v)) for v in bgr]
    h, s, v = cv2.cvtColor(
        np.uint8([[[b, g, r]]]), cv2.COLOR_BGR2HSV
    )[0][0]
    return {
        "hex": "#{:02X}{:02X}{:02X}".format(r, g, b),
        "rgb": [r, g, b],
        "hsv": [
            int(h) * 2,
            int(round(s / 255 * 100)),
            int(round(v / 255 * 100)),
        ],
    }


def detect(frame, selected="all"):
    """Annotate frame in place and return detections, largest first."""
    blurred = cv2.GaussianBlur(frame, (7, 7), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    names = list(COLOUR_RANGES) if selected == "all" else [selected]
    frame_area = frame.shape[0] * frame.shape[1]
    found = []

    for name in names:
        mask = build_mask(hsv, name)
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        best = None
        count = 0
        total_area = 0.0

        for c in contours[:MAX_BOXES_PER_COLOUR]:
            area = cv2.contourArea(c)
            if area < MIN_AREA:
                break

            count += 1
            roi = np.zeros(mask.shape, np.uint8)
            cv2.drawContours(roi, [c], -1, 255, -1)
            total_area += cv2.countNonZero(
                cv2.bitwise_and(roi, mask)
            )

            x, y, w, h = cv2.boundingRect(c)
            colour = BOX_BGR[name]
            cv2.rectangle(frame, (x, y), (x + w, y + h), colour, 3)
            cv2.rectangle(
                frame, (x, max(0, y - 24)),
                (x + 8 * len(name) + 14, y), colour, -1
            )
            txt = (0, 0, 0) if name in (
                "yellow", "white", "orange"
            ) else (255, 255, 255)

            cv2.putText(
                frame, name.upper(), (x + 6, max(16, y - 7)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, txt, 1, cv2.LINE_AA
            )

            if best is None:
                best = {
                    "name": name,
                    "area": area,
                    **describe(cv2.mean(blurred, roi)[:3]),
                }

        if best:
            best["count"] = count
            best["percent"] = round(total_area / frame_area * 100, 1)
            best["area"] = total_area
            found.append(best)

    found.sort(key=lambda d: d["area"], reverse=True)
    return found


def public_results(results):
    return [{k: v for k, v in d.items() if k != "area"} for d in results]


def make_stats(results):
    res = public_results(results)
    dominant = (
        {"name": res[0]["name"], "percent": res[0]["percent"]}
        if res else None
    )
    mode_colours = (
        list(COLOUR_RANGES)
        if selected_colour == "all"
        else [selected_colour]
    )
    counts = {d["name"]: d["count"] for d in res}
    stats = [
        {"name": name, "count": counts.get(name, 0)}
        for name in mode_colours
    ]
    return res, dominant, stats


@app.route("/")
def index():
    return render_template("index.html", colours=list(COLOUR_RANGES))


@app.route("/api/start", methods=["POST"])
def api_start():
    global camera_running, latest_jpeg, camera_results
    camera_running = True
    latest_jpeg = None
    camera_results = []
    return jsonify(ok=True)


@app.route("/api/stop", methods=["POST"])
def api_stop():
    global camera_running, latest_jpeg, camera_results
    camera_running = False
    latest_jpeg = None
    camera_results = []
    return jsonify(ok=True)


@app.route("/api/select", methods=["POST"])
def api_select():
    global selected_colour
    value = (request.get_json(silent=True) or {}).get("colour", "all")
    if value != "all" and value not in COLOUR_RANGES:
        return jsonify(ok=False, error="Unknown colour"), 400
    selected_colour = value
    return jsonify(ok=True, selected=value)


@app.route("/api/frame", methods=["POST"])
def api_frame():
    global latest_jpeg, camera_results

    if not camera_running:
        return jsonify(ok=False, error="Camera is not running."), 400

    data = (request.get_json(silent=True) or {}).get("image", "")
    if "," not in data:
        return jsonify(ok=False, error="Invalid image frame."), 400

    try:
        raw = base64.b64decode(data.split(",", 1)[1])
        array = np.frombuffer(raw, dtype=np.uint8)
        frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Could not decode frame.")
    except Exception:
        return jsonify(ok=False, error="Could not process camera frame."), 400

    # Mirror the image to match a normal front-facing webcam preview.
    frame = cv2.flip(frame, 1)
    results = detect(frame, selected_colour)

    ok, buffer = cv2.imencode(
        ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75]
    )
    if not ok:
        return jsonify(ok=False, error="Could not encode processed frame."), 500

    latest_jpeg = buffer.tobytes()
    camera_results = results
    detections, dominant, stats = make_stats(results)

    return jsonify(
        ok=True,
        image=base64.b64encode(latest_jpeg).decode("ascii"),
        detections=detections,
        dominant=dominant,
        stats=stats,
    )


@app.route("/api/status")
def api_status():
    detections, dominant, stats = make_stats(camera_results)
    return jsonify(
        running=camera_running,
        selected=selected_colour,
        detections=detections,
        dominant=dominant,
        stats=stats,
    )


@app.route("/api/capture", methods=["POST"])
def api_capture():
    global captured_jpeg

    if not camera_running or latest_jpeg is None:
        return jsonify(
            ok=False, error="Start the camera and wait for a frame before capturing."
        ), 400

    captured_jpeg = latest_jpeg
    return jsonify(ok=True)


@app.route("/captured.jpg")
def captured_image():
    if captured_jpeg is None:
        return jsonify(ok=False, error="Nothing captured yet."), 404

    headers = {"Cache-Control": "no-store"}
    if request.args.get("download"):
        name = datetime.now().strftime("colour-capture-%Y%m%d-%H%M%S.jpg")
        headers["Content-Disposition"] = (
            f'attachment; filename="{name}"'
        )
    return Response(captured_jpeg, mimetype="image/jpeg", headers=headers)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
