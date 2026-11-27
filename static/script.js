const $ = (id) => document.getElementById(id);
const video = $("video"), placeholder = $("placeholder"), liveBadge = $("liveBadge");
const startBtn = $("startBtn"), stopBtn = $("stopBtn"), captureBtn = $("captureBtn");
let timer = null;
let selected = "all";

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
  video.hidden = !on;
  liveBadge.hidden = !on;
  placeholder.hidden = on;
  startBtn.disabled = on;
  stopBtn.disabled = !on;
  captureBtn.disabled = !on;
  if (!on) {
    video.removeAttribute("src");
    resetPanel();
    $("stats").innerHTML = '<p class="empty">Start the camera to see counts.</p>';
    $("statMode").textContent = "(All colours)";
  }
}

function resetPanel() {
  $("preview").style.background = "";
  $("preview").classList.remove("filled");
  $("previewText").textContent = "No colour";
  $("previewText").style.color = "";
  ["vName", "vHex", "vRgb", "vHsv"].forEach((id) => ($(id).textContent = "—"));
  $("detected").innerHTML = '<p class="empty">Nothing detected yet.</p>';
  renderDominant(null, []);
}

const capName = (n) => n.charAt(0).toUpperCase() + n.slice(1);

// Dominant colour card: name + percentage of the frame it covers
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
  $("domPercent").textContent = `Covers ${dominant.percent}% of the frame`;
}

// Statistics card: number of regions per colour in the current mode
function renderStats(stats) {
  $("statMode").textContent = stats.length === 1 ? `(${capName(stats[0].name)} only)` : "(All colours)";
  $("stats").innerHTML = stats
    .map((s) => `<div class="stat ${s.count ? "" : "zero"}"><i class="dot dot-${s.name}"></i>${capName(s.name)}<b>${s.count}</b></div>`)
    .join("");
}

function textOn([r, g, b]) {
  return 0.299 * r + 0.587 * g + 0.114 * b > 150 ? "#222" : "#fff";
}

function render(detections) {
  if (!detections.length) {
    resetPanel();
    $("previewText").textContent = "Searching…";
    $("detected").innerHTML = '<p class="empty">No matching colour in view.</p>';
    return;
  }
  const top = detections[0];
  const p = $("preview");
  p.style.background = top.hex;
  p.classList.add("filled");
  $("previewText").textContent = top.hex;
  $("previewText").style.color = textOn(top.rgb);
  $("vName").textContent = top.name.charAt(0).toUpperCase() + top.name.slice(1);
  $("vHex").textContent = top.hex;
  $("vRgb").textContent = `${top.rgb[0]}, ${top.rgb[1]}, ${top.rgb[2]}`;
  $("vHsv").textContent = `${top.hsv[0]}°, ${top.hsv[1]}%, ${top.hsv[2]}%`;

  $("detected").innerHTML = detections
    .map((d) => `<div class="swatch" title="${d.hex}"><div class="box" style="background:${d.hex}"></div>${d.name}</div>`)
    .join("");
}

async function poll() {
  try {
    const data = await (await fetch("/api/status")).json();
    if (!data.running) { stopPolling(); setRunning(false); return; }
    render(data.detections);
    renderDominant(data.dominant, data.detections);
    renderStats(data.stats);
  } catch (e) { /* server briefly unavailable */ }
}
function startPolling() { stopPolling(); timer = setInterval(poll, 400); }
function stopPolling() { clearInterval(timer); timer = null; }

startBtn.addEventListener("click", async () => {
  startBtn.disabled = true;
  const res = await post("/api/start");
  if (!res.ok) {
    startBtn.disabled = false;
    $("placeholderText").textContent = res.error || "Could not start the camera.";
    return;
  }
  await post("/api/select", { colour: selected });
  video.src = "/video_feed?t=" + Date.now();
  setRunning(true);
  startPolling();
});

stopBtn.addEventListener("click", async () => {
  stopPolling();
  await post("/api/stop");
  $("placeholderText").innerHTML = "Camera is off. Press <strong>Start Camera</strong> to begin.";
  setRunning(false);
});

captureBtn.addEventListener("click", async () => {
  const res = await post("/api/capture");
  if (!res.ok) { alert(res.error || "Capture failed."); return; }
  $("captureImg").src = "/captured.jpg?t=" + Date.now();
  $("captureCard").hidden = false;
  $("captureCard").scrollIntoView({ behavior: "smooth", block: "nearest" });
});

$("chips").addEventListener("click", async (e) => {
  const chip = e.target.closest(".chip");
  if (!chip) return;
  document.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
  chip.classList.add("active");
  selected = chip.dataset.colour;
  await post("/api/select", { colour: selected });
});

// Release the camera if the page is closed
window.addEventListener("beforeunload", () => navigator.sendBeacon("/api/stop"));
