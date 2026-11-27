const $ = (id) => document.getElementById(id);

const videoDisplay = $("video");
const placeholder = $("placeholder");
const liveBadge = $("liveBadge");
const startBtn = $("startBtn");
const stopBtn = $("stopBtn");
const captureBtn = $("captureBtn");

let selected = "all";
let stream = null;
let cameraVideo = null;
let canvas = document.createElement("canvas");
let frameTimer = null;
let sendingFrame = false;
let running = false;

async function post(url, body) {
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    return await res.json();
  } catch (e) {
    return { ok: false, error: "Cannot reach the server." };
  }
}

function setRunning(on) {
  running = on;
  videoDisplay.hidden = !on;
  liveBadge.hidden = !on;
  placeholder.hidden = on;
  startBtn.disabled = on;
  stopBtn.disabled = !on;
  captureBtn.disabled = !on;

  if (!on) {
    videoDisplay.removeAttribute("src");
    resetPanel();
    $("stats").innerHTML =
      '<p class="empty">Start the camera to see counts.</p>';
    $("statMode").textContent = "(All colours)";
  }
}

function resetPanel() {
  $("preview").style.background = "";
  $("preview").classList.remove("filled");
  $("previewText").textContent = "No colour";
  $("previewText").style.color = "";
  ["vName", "vHex", "vRgb", "vHsv"].forEach(
    (id) => ($(id).textContent = "—")
  );
  $("detected").innerHTML =
    '<p class="empty">Nothing detected yet.</p>';
  renderDominant(null, []);
}

const capName = (n) => n.charAt(0).toUpperCase() + n.slice(1);

function renderDominant(dominant, detections) {
  const box = $("domBox");

  if (!dominant) {
    box.style.background = "";
    box.classList.remove("filled");
    $("domName").textContent = "—";
    $("domPercent").textContent = "Covers — of the frame";
    return;
  }

  const d = detections.find((x) => x.name === dominant.name);
  box.style.background = d ? d.hex : "";
  box.classList.add("filled");
  $("domName").textContent = capName(dominant.name);
  $("domPercent").textContent =
    `Covers ${dominant.percent}% of the frame`;
}

function renderStats(stats) {
  $("statMode").textContent =
    stats.length === 1
      ? `(${capName(stats[0].name)} only)`
      : "(All colours)";

  $("stats").innerHTML = stats
    .map(
      (s) =>
        `<div class="stat ${s.count ? "" : "zero"}">` +
        `<i class="dot dot-${s.name}"></i>${capName(s.name)}` +
        `<b>${s.count}</b></div>`
    )
    .join("");
}

function textOn([r, g, b]) {
  return 0.299 * r + 0.587 * g + 0.114 * b > 150
    ? "#222"
    : "#fff";
}

function render(detections) {
  if (!detections.length) {
    resetPanel();
    $("previewText").textContent = "Searching…";
    $("detected").innerHTML =
      '<p class="empty">No matching colour in view.</p>';
    return;
  }

  const top = detections[0];
  const p = $("preview");

  p.style.background = top.hex;
  p.classList.add("filled");
  $("previewText").textContent = top.hex;
  $("previewText").style.color = textOn(top.rgb);
  $("vName").textContent = capName(top.name);
  $("vHex").textContent = top.hex;
  $("vRgb").textContent = `${top.rgb[0]}, ${top.rgb[1]}, ${top.rgb[2]}`;
  $("vHsv").textContent =
    `${top.hsv[0]}°, ${top.hsv[1]}%, ${top.hsv[2]}%`;

  $("detected").innerHTML = detections
    .map(
      (d) =>
        `<div class="swatch" title="${d.hex}">` +
        `<div class="box" style="background:${d.hex}"></div>` +
        `${d.name}</div>`
    )
    .join("");
}

async function processFrame() {
  if (!running || !cameraVideo || sendingFrame) return;
  if (cameraVideo.readyState < 2) return;

  sendingFrame = true;

  try {
    const width = 640;
    const height = Math.round(
      cameraVideo.videoHeight * (width / cameraVideo.videoWidth)
    );

    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(cameraVideo, 0, 0, width, height);

    const image = canvas.toDataURL("image/jpeg", 0.75);
    const data = await post("/api/frame", { image });

    if (!data.ok) {
      console.error(data.error);
      return;
    }

    videoDisplay.src = `data:image/jpeg;base64,${data.image}`;
    render(data.detections);
    renderDominant(data.dominant, data.detections);
    renderStats(data.stats);
  } catch (error) {
    console.error("Frame processing error:", error);
  } finally {
    sendingFrame = false;
  }
}

function stopFrameProcessing() {
  clearInterval(frameTimer);
  frameTimer = null;
  sendingFrame = false;
}

async function stopCamera() {
  stopFrameProcessing();

  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
    stream = null;
  }

  cameraVideo = null;
  await post("/api/stop");
  setRunning(false);
}

startBtn.addEventListener("click", async () => {
  startBtn.disabled = true;
  $("placeholderText").textContent = "Requesting camera permission…";

  try {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error(
        "Camera access requires HTTPS or localhost and a supported browser."
      );
    }

    stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: "user",
        width: { ideal: 960 },
        height: { ideal: 540 },
      },
      audio: false,
    });

    cameraVideo = document.createElement("video");
    cameraVideo.autoplay = true;
    cameraVideo.muted = true;
    cameraVideo.playsInline = true;
    cameraVideo.srcObject = stream;

    await cameraVideo.play();

    const result = await post("/api/start");

    if (!result.ok) {
      throw new Error(result.error || "Could not start detection.");
    }

    await post("/api/select", { colour: selected });

    setRunning(true);
    $("placeholderText").textContent =
      "Camera is off. Press Start Camera to begin.";

    await processFrame();
    frameTimer = setInterval(processFrame, 200);
  } catch (error) {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      stream = null;
    }

    cameraVideo = null;
    startBtn.disabled = false;
    $("placeholderText").textContent =
      error.name === "NotAllowedError"
        ? "Camera permission was denied. Allow camera access and try again."
        : error.message || "Could not start the camera.";

    console.error(error);
  }
});

stopBtn.addEventListener("click", stopCamera);

captureBtn.addEventListener("click", async () => {
  const result = await post("/api/capture");

  if (!result.ok) {
    alert(result.error || "Capture failed.");
    return;
  }

  $("captureImg").src = "/captured.jpg?t=" + Date.now();
  $("downloadLink").href = "/captured.jpg?download=1&t=" + Date.now();
  $("captureCard").hidden = false;
  $("captureCard").scrollIntoView({
    behavior: "smooth",
    block: "nearest",
  });
});

$("chips").addEventListener("click", async (event) => {
  const chip = event.target.closest(".chip");
  if (!chip) return;

  document.querySelectorAll(".chip").forEach(
    (item) => item.classList.remove("active")
  );

  chip.classList.add("active");
  selected = chip.dataset.colour;

  await post("/api/select", { colour: selected });
});

window.addEventListener("beforeunload", () => {
  stopFrameProcessing();

  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
  }

  navigator.sendBeacon("/api/stop");
});
