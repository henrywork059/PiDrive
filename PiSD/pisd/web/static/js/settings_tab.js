const stGlobalCode = document.getElementById('stGlobalCode');
const stStatusJson = document.getElementById('stStatusJson');
const stActionLog = document.getElementById('stActionLog');
const SETTINGS_STORAGE_KEY = 'pisd.runtimeSettings.v1';

function readStoredSettings() {
  try { return JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY) || '{}') || {}; }
  catch (_err) { return {}; }
}

function saveStoredSettings(partial) {
  const next = { ...readStoredSettings(), ...partial, saved_at: new Date().toISOString() };
  localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(next));
  return next;
}

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

function fillForm(form, values = {}) {
  if (!form || !values || typeof values !== 'object') return;
  for (const element of form.elements) {
    if (!element.name || values[element.name] === undefined) continue;
    element.value = String(values[element.name]);
  }
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

async function readCameraConfig() {
  const payload = await settingsApi('GET', '/api/camera/config', undefined, 'camera');
  if (payload.config) {
    fillForm(document.getElementById('stCameraForm'), payload.config);
    saveStoredSettings({ camera: payload.config });
  }
}

async function readMotorConfig() {
  const payload = await settingsApi('GET', '/api/motor/config', undefined, 'motor');
  if (payload.config) {
    fillForm(document.getElementById('stMotorForm'), payload.config);
    saveStoredSettings({ motor: payload.config });
  }
}

function restoreSavedForms() {
  const saved = readStoredSettings();
  fillForm(document.getElementById('stCameraForm'), saved.camera);
  fillForm(document.getElementById('stMotorForm'), saved.motor);
  if (stActionLog && (saved.camera || saved.motor)) {
    stActionLog.textContent = JSON.stringify({
      message: 'Saved settings restored into the form. Submit Apply to update the backend runtime for all tabs.',
      code: 'PISD-OK-000',
      saved_at: saved.saved_at || '',
      camera: saved.camera || {},
      motor: saved.motor || {},
    }, null, 2);
  }
}

document.getElementById('stRefreshStatus')?.addEventListener('click', refreshSettingsStatus);
document.getElementById('stStopAll')?.addEventListener('click', () => settingsApi('POST', '/api/control/stop', {}, 'motor').then(refreshSettingsStatus));
document.getElementById('stReadCamera')?.addEventListener('click', readCameraConfig);
document.getElementById('stReadMotor')?.addEventListener('click', readMotorConfig);
document.getElementById('stCameraForm')?.addEventListener('submit', (event) => {
  event.preventDefault();
  const payload = formPayload(event.currentTarget);
  saveStoredSettings({ camera: payload });
  settingsApi('POST', '/api/camera/apply', payload, 'camera').then(refreshSettingsStatus);
});
document.getElementById('stMotorForm')?.addEventListener('submit', (event) => {
  event.preventDefault();
  const payload = formPayload(event.currentTarget);
  saveStoredSettings({ motor: payload });
  settingsApi('POST', '/api/motor/apply', payload, 'motor').then(refreshSettingsStatus);
});

restoreSavedForms();
