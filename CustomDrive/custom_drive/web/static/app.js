async function postJSON(path, body = {}) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return res.json();
}

function renderStatus(status) {
  const s = document.getElementById('status');
  s.innerHTML = `
    <div><b>Running:</b> ${status.running}</div>
    <div><b>State:</b> ${status.state}</div>
    <div><b>Detail:</b> ${status.detail}</div>
    <div><b>Retries:</b> ${status.retries}</div>
    <div><b>Completed cycles:</b> ${status.completed_cycles}/${status.max_cycles}</div>
    <div><b>Active leg:</b> ${status.active_route_leg || '-'}</div>
    <div><b>Cmd:</b> steer=${status.last_command.steering.toFixed(2)}, throttle=${status.last_command.throttle.toFixed(2)}, note=${status.last_command.note}</div>
  `;

  const logs = document.getElementById('logs');
  logs.textContent = (status.logs || []).map((entry) =>
    `[${entry.timestamp.toFixed(2)}] ${entry.action}: ${entry.detail}`
  ).join('\n');

  const frame = document.getElementById('frame');
  frame.innerHTML = '<rect x="0" y="0" width="640" height="360" fill="#0b1220"/>';
  for (const det of status.detections || []) {
    const b = det.box;
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('x', b.x1);
    rect.setAttribute('y', b.y1);
    rect.setAttribute('width', b.x2 - b.x1);
    rect.setAttribute('height', b.y2 - b.y1);
    rect.setAttribute('fill', 'none');
    rect.setAttribute('stroke', '#22c55e');
    rect.setAttribute('stroke-width', '2');
    frame.appendChild(rect);

    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', b.x1);
    text.setAttribute('y', Math.max(14, b.y1 - 4));
    text.setAttribute('fill', '#86efac');
    text.setAttribute('font-size', '12');
    text.textContent = `${det.label} ${(det.confidence * 100).toFixed(0)}%`;
    frame.appendChild(text);
  }
}

async function refresh() {
  const res = await fetch('/api/status');
  const status = await res.json();
  renderStatus(status);
}

document.getElementById('startBtn').onclick = async () => {
  await postJSON('/api/start', { tick_s: 0.2 });
  await refresh();
};
document.getElementById('stopBtn').onclick = async () => {
  await postJSON('/api/stop');
  await refresh();
};
document.getElementById('stepBtn').onclick = async () => {
  await postJSON('/api/step');
  await refresh();
};
document.getElementById('resetBtn').onclick = async () => {
  const max_cycles = Number(document.getElementById('maxCycles').value || 2);
  await postJSON('/api/reset', { max_cycles });
  await refresh();
};

setInterval(refresh, 500);
refresh();
