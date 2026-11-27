const $ = (id) => document.getElementById(id);
const runtimeError = $("runtimeError");
let state = null;
let paused = false;
let cameraRefreshBusy = false;
let frameIdentity = null;
let pollBusy = false;
let actionEpoch = 0;

async function api(path, body = undefined) {
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || data.message || `HTTP ${response.status}`);
  return data;
}

function showError(message = "") {
  runtimeError.textContent = message;
  runtimeError.hidden = !message;
}

function drawTopView(engine) {
  const canvas = $("topView");
  const ctx = canvas.getContext("2d");
  const { width, height } = canvas;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#151d18";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "#27352c";
  ctx.lineWidth = 1;
  for (let x = 0; x < width; x += 26) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke(); }
  for (let y = 0; y < height; y += 26) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke(); }
  const points = engine.track_points || [];
  const vehicle = engine.vehicle || {};
  const scale = 10;
  const centerX = width / 2;
  const centerY = height * 0.68;
  const local = points.map(([x, y]) => {
    const dx = x - vehicle.x_m;
    const dy = y - vehicle.y_m;
    const h = vehicle.heading_rad || 0;
    return [centerX + (dx * Math.cos(h) - dy * Math.sin(h)) * scale,
      centerY - (dx * Math.sin(h) + dy * Math.cos(h)) * scale];
  });
  if (local.length > 1) {
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = "#66716a";
    ctx.lineWidth = Math.max(15, engine.road_width_m * scale);
    ctx.beginPath(); local.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)); ctx.stroke();
    ctx.strokeStyle = "#d5bd67";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([7, 8]);
    ctx.beginPath(); local.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)); ctx.stroke();
    ctx.setLineDash([]);
  }
  for (const obstacle of engine.obstacles || []) {
    const dx = Number(obstacle.x_m) - Number(vehicle.x_m || 0);
    const dy = Number(obstacle.y_m) - Number(vehicle.y_m || 0);
    const h = vehicle.heading_rad || 0;
    const x = centerX + (dx * Math.cos(h) - dy * Math.sin(h)) * scale;
    const y = centerY - (dx * Math.sin(h) + dy * Math.cos(h)) * scale;
    if (x >= 0 && x <= width && y >= 0 && y <= height) {
      ctx.fillStyle = "#ff7b31"; ctx.beginPath(); ctx.arc(x, y, 4, 0, Math.PI * 2); ctx.fill();
    }
  }
  ctx.save();
  ctx.translate(centerX, centerY);
  ctx.rotate(-(vehicle.heading_rad || 0));
  ctx.fillStyle = vehicle.collision || vehicle.off_track ? "#ff6d5e" : "#ff5a0f";
  ctx.beginPath(); ctx.moveTo(0, -11); ctx.lineTo(7, 8); ctx.lineTo(0, 5); ctx.lineTo(-7, 8); ctx.closePath(); ctx.fill();
  ctx.restore();
}

function updateGPIO(rows) {
  const body = $("gpioRows");
  body.replaceChildren();
  for (const row of rows || []) {
    const tr = document.createElement("tr");
    for (const value of [row.pin, row.function, row.state, `${Number(row.duty_cycle_percent || 0).toFixed(1)}%`]) {
      const td = document.createElement("td"); td.textContent = value; tr.append(td);
    }
    body.append(tr);
  }
}

function render(data) {
  state = data;
  const online = Boolean(data.running);
  $("runtimeDot").classList.toggle("online", online);
  $("runtimeLabel").textContent = online ? "EMULATOR ONLINE" : "OFFLINE";
  $("modeBadge").textContent = online ? "Advanced emulator" : "Basic simulation";
  $("versionLabel").textContent = `PiSD ${data.version || "0.11.0"}`;
  $("runtimeUrl").textContent = online ? data.url : "Not running";
  $("openPisd").href = online ? data.url : "#";
  $("openManual").href = online ? data.manual_drive_url : "#";
  $("workspacePath").textContent = data.workspace || "—";
  $("startButton").disabled = online;
  $("restartButton").disabled = !online;
  $("stopButton").disabled = !online;
  const engine = data.engine || {};
  const vehicle = engine.vehicle || {};
  const motor = engine.motor || {};
  $("trackName").textContent = engine.track_name || "Straight road";
  $("vehicleState").textContent = vehicle.collision ? "Collision" : vehicle.off_track ? "Off track" : Math.abs(vehicle.speed_mps || 0) > 0.02 ? "Moving" : "Stopped";
  $("leftOutput").textContent = Number(motor.left_intended || 0).toFixed(2);
  $("rightOutput").textContent = Number(motor.right_intended || 0).toFixed(2);
  $("leftMeter").style.width = `${Math.min(100, Math.abs(Number(motor.left_hardware || 0)) * 100)}%`;
  $("rightMeter").style.width = `${Math.min(100, Math.abs(Number(motor.right_hardware || 0)) * 100)}%`;
  $("leftWheel").textContent = `Wheel ${Number(vehicle.left_wheel_mps || 0).toFixed(2)} m/s`;
  $("rightWheel").textContent = `Wheel ${Number(vehicle.right_wheel_mps || 0).toFixed(2)} m/s`;
  const command = motor.last_command || {};
  $("steeringOutput").textContent = Number(command.steering || 0).toFixed(2);
  $("throttleOutput").textContent = Number(command.throttle || 0).toFixed(2);
  $("vehicleSpeed").textContent = `${Number(vehicle.speed_mps || 0).toFixed(2)} m/s`;
  $("heading").textContent = `${Number(vehicle.heading_deg || 0).toFixed(1)}°`;
  $("position").textContent = `${Number(vehicle.x_m || 0).toFixed(2)}, ${Number(vehicle.y_m || 0).toFixed(2)} m`;
  $("physicsFps").textContent = `${engine.physics?.actual_fps || 0} Hz`;
  $("pwmFrequency").textContent = `PWM ${motor.pwm_frequency_hz || 1000} Hz`;
  updateGPIO(motor.virtual_gpio);
  drawTopView(engine);
  const camera = data._pisd_camera || {};
  if (camera.backend === "emulator") {
    $("cameraState").textContent = "Live";
    $("cameraSource").textContent = `Frame source: ${camera.last_capture_source || "emulator"}`;
    $("cameraSeq").textContent = `Sequence: ${camera.frame_seq || 0}`;
    $("cameraFps").textContent = `FPS: ${camera.measured_capture_fps || 0}`;
  } else {
    $("cameraState").textContent = online ? "Starting" : "Waiting";
  }
  const events = data.events || [];
  const eventList = $("eventList"); eventList.replaceChildren();
  for (const item of events.slice(-8).reverse()) {
    const row = document.createElement("div"); row.className = `event ${item.level || ""}`;
    const time = document.createElement("time"); time.textContent = item.timestamp || "";
    const text = document.createElement("span"); text.textContent = item.message || "";
    row.append(time, text); eventList.append(row);
  }
  if (online) {
    $("frameEmpty").hidden = true;
    const identity = `${data.generation}:${data.manual_drive_url}`;
    if (frameIdentity !== identity) {
      frameIdentity = identity;
      $("pisdFrame").src = data.manual_drive_url;
    }
    $("pisdFrame").style.display = "block";
  } else {
    $("frameEmpty").hidden = false;
    $("pisdFrame").style.display = "none";
    frameIdentity = null;
    $("pisdFrame").src = "about:blank";
  }
}

async function poll() {
  if (pollBusy) return;
  pollBusy = true;
  const epoch = actionEpoch;
  try {
    const data = await api("/api/status");
    if (data.running && data.url) {
      try {
        const pisd = await api("/api/pisd/status");
        data._pisd_camera = pisd.camera || {};
        data._pisd_status = pisd;
      } catch (_) {}
    }
    if (epoch !== actionEpoch) return;
    render(data);
    $("pollStatus").textContent = `Updated ${new Date().toLocaleTimeString()}`;
  } catch (error) {
    $("pollStatus").textContent = error.message;
  } finally { pollBusy = false; }
}

async function refreshCamera() {
  if (cameraRefreshBusy || !state?.running) return;
  cameraRefreshBusy = true;
  const image = $("cameraImage");
  const empty = $("cameraEmpty");
  try {
    const response = await fetch(`/api/camera.jpg?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error("Waiting for a camera frame");
    const blob = await response.blob();
    image.onload = () => URL.revokeObjectURL(image.dataset.objectUrl || "");
    const url = URL.createObjectURL(blob);
    image.dataset.objectUrl = url;
    image.src = url;
    image.style.display = "block";
    empty.hidden = true;
  } catch (_) {
    image.style.display = "none";
    empty.hidden = false;
    empty.textContent = "Waiting for PiSD camera frames…";
  } finally {
    cameraRefreshBusy = false;
  }
}

async function runAction(action) {
  showError("");
  actionEpoch++;
  try {
    const data = await api(action, { port: Number($("pisdPort").value) });
    actionEpoch++;
    render(data);
  }
  catch (error) { showError(error.message); await poll(); }
}

$("startButton").addEventListener("click", () => runAction("/api/runtime/start"));
$("restartButton").addEventListener("click", () => runAction("/api/runtime/restart"));
$("stopButton").addEventListener("click", () => runAction("/api/runtime/stop"));
$("resetButton").addEventListener("click", async () => { await api("/api/vehicle/reset", {}); poll(); });
$("trackSelect").addEventListener("change", async (event) => { await api("/api/track", { track_id: event.target.value }); poll(); });
$("pauseButton").addEventListener("click", async () => {
  paused = !paused;
  await api("/api/simulation/pause", { paused });
  $("pauseButton").textContent = paused ? "Resume" : "Pause";
  $("stepButton").disabled = !paused;
  poll();
});
$("stepButton").addEventListener("click", async () => { await api("/api/simulation/step", { steps: 1 }); poll(); });
$("speedRange").addEventListener("input", async (event) => {
  $("speedValue").textContent = `${Number(event.target.value).toFixed(1)}×`;
  await api("/api/simulation/speed", { scale: Number(event.target.value) });
});
document.querySelectorAll(".viewport").forEach((button) => button.addEventListener("click", () => {
  document.querySelectorAll(".viewport").forEach((item) => item.classList.remove("active"));
  button.classList.add("active");
  const width = button.dataset.width;
  $("frameShell").style.width = width;
}));

async function initialize() {
  try {
    const data = await api("/api/status");
    $("trackSelect").replaceChildren(...(data.tracks || []).map((track) => {
      const option = document.createElement("option"); option.value = track.id; option.textContent = track.name; return option;
    }));
    render(data);
  } catch (error) { showError(error.message); }
  setInterval(poll, 500);
  setInterval(refreshCamera, 180);
}
initialize();
