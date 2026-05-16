const stGlobalCode = document.getElementById('stGlobalCode');
const stStatusJson = document.getElementById('stStatusJson');
const stActionLog = document.getElementById('stActionLog');

function setSettingsCode(name, code) {
  const value = code || 'PISD-OK-000';
  const target = document.querySelector(`[data-code-for="${name}"]`);
  if (target) target.textContent = value;
  if (stGlobalCode) stGlobalCode.textContent = value;
}

function formPayload(form) {
  const payload = {};
  for (const element of form.elements) {
    if (!element.name) continue;
    if (element.dataset.type === 'boolean') payload[element.name] = element.value === 'true';
    else if (element.type === 'number' || element.tagName === 'SELECT' && /^-?\d+(\.\d+)?$/.test(element.value)) payload[element.name] = Number(element.value);
    else payload[element.name] = element.value;
  }
  return payload;
}

async function settingsApi(method, path, body, codeTarget = 'action') {
  const options = { method, headers: {} };
  if (body !== undefined && method !== 'GET') {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  const payload = await response.json();
  setSettingsCode(codeTarget, payload.code);
  setSettingsCode('action', payload.code);
  if (stActionLog) stActionLog.textContent = JSON.stringify({ method, path, http_status: response.status, response: payload }, null, 2);
  return payload;
}

async function refreshSettingsStatus() {
  const payload = await settingsApi('GET', '/api/status', undefined, 'system');
  if (stStatusJson) stStatusJson.textContent = JSON.stringify(payload, null, 2);
}

document.getElementById('stRefreshStatus')?.addEventListener('click', refreshSettingsStatus);
document.getElementById('stStopAll')?.addEventListener('click', () => settingsApi('POST', '/api/control/stop', {}, 'motor').then(refreshSettingsStatus));
document.getElementById('stReadCamera')?.addEventListener('click', () => settingsApi('GET', '/api/camera/config', undefined, 'camera'));
document.getElementById('stReadMotor')?.addEventListener('click', () => settingsApi('GET', '/api/motor/config', undefined, 'motor'));
document.getElementById('stCameraForm')?.addEventListener('submit', (event) => {
  event.preventDefault();
  settingsApi('POST', '/api/camera/apply', formPayload(event.currentTarget), 'camera').then(refreshSettingsStatus);
});
document.getElementById('stMotorForm')?.addEventListener('submit', (event) => {
  event.preventDefault();
  settingsApi('POST', '/api/motor/apply', formPayload(event.currentTarget), 'motor').then(refreshSettingsStatus);
});
