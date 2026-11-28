const el = id => document.getElementById(id);
let busy = false;
function render(data) {
  const input = data.camera_input || {};
  el("status").textContent = JSON.stringify({running: data.running, camera_input: input, hardware_enabled: data.hardware_enabled, motor_disconnected: data.motor_disconnected}, null, 2);
  el("replay").disabled = el("generated").disabled = data.running;
  el("fault").disabled = !data.running || input.capture_fault;
  el("clear").disabled = !input.capture_fault;
  el("motorDisconnect").disabled = !data.running || data.motor_disconnected;
}
async function action(path, body) {
  if (busy) return;
  busy = true;
  try {
    const response = await fetch(path, body === undefined ? {} : {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Request failed");
    render(data);
    el("feedback").textContent = "Status confirmed.";
  } catch (error) { el("feedback").textContent = error.message; }
  finally { busy = false; }
}
el("replay").onclick = () => action("/api/scenarios/replay", {source: el("source").value, loop: el("loop").checked});
el("generated").onclick = () => action("/api/scenarios/replay", {source: null});
el("fault").onclick = () => action("/api/scenarios/camera-fault", {active: true});
el("clear").onclick = () => action("/api/scenarios/camera-fault", {active: false});
el("motorDisconnect").onclick = () => { if (window.confirm("Disconnect virtual motors until PiSD stops?")) action("/api/scenarios/motor-disconnect", {confirm: true}); };
el("refresh").onclick = () => action("/api/status");
action("/api/status");
