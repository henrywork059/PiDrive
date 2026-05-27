const stGlobalCode = document.getElementById('stGlobalCode');
const stActionLog = document.getElementById('stActionLog');
const SETTINGS_STORAGE_KEY = 'pisd.runtimeSettings.v2';

function setSettingsCode(name, code) {
  const value = code || 'PISD-OK-000';
  const target = document.querySelector(`[data-code-for="${name}"]`);
  if (target) { target.textContent = value; target.dataset.state = String(value).startsWith('PISD-OK') ? 'ok' : 'error'; }
  if (stGlobalCode) { stGlobalCode.textContent = value; stGlobalCode.dataset.state = String(value).startsWith('PISD-OK') ? 'ok' : 'error'; }
}
function logResponse(action, payload, status='') { if (stActionLog) stActionLog.textContent = JSON.stringify({ action, http_status: status, response: payload }, null, 2); setSettingsCode('action', payload?.code); }
function numberMaybe(value) { return /^-?\d+(\.\d+)?$/.test(String(value)) ? Number(value) : value; }
function clampNumber(value, min, max, fallback) { const n = Number(value); return Number.isFinite(n) ? Math.max(min, Math.min(max, n)) : fallback; }
function formPayload(form) { const payload = {}; for (const el of form.elements) { if (!el.name) continue; if (el.dataset.type === 'boolean') payload[el.name] = el.value === 'true'; else if (el.type === 'number' || el.type === 'range' || el.tagName === 'SELECT') payload[el.name] = numberMaybe(el.value); else payload[el.name] = el.value; } return payload; }
function normaliseSettingsForUi(settings = {}) {
  const next = JSON.parse(JSON.stringify(settings || {}));
  next.motor = next.motor || {};
  next.manual_drive = next.manual_drive || {};
  next.motor.left_max_speed = clampNumber(next.motor.left_max_speed ?? 1.0, 0, 1.0, 1.0);
  next.motor.right_max_speed = clampNumber(next.motor.right_max_speed ?? 1.0, 0, 1.0, 1.0);
  next.motor.steer_mix = clampNumber(next.motor.steer_mix ?? 1.0, 0, 1.0, 1.0);
  next.motor.steering_mode = ['turn_rate', 'arcade_mix'].includes(String(next.motor.steering_mode || '').trim()) ? String(next.motor.steering_mode).trim() : 'turn_rate';
  delete next.motor.turn_gain;
  delete next.motor.turn_curve;
  next.motor.min_inside_speed = clampNumber(next.motor.min_inside_speed ?? 0.0, 0, 0.95, 0.0);
  next.motor.allow_pivot_turn = String(next.motor.allow_pivot_turn ?? false).toLowerCase() === 'true' || next.motor.allow_pivot_turn === true;
  next.motor.left_bias = clampNumber(next.motor.left_bias ?? 0.0, -0.35, 0.35, 0.0);
  next.motor.right_bias = clampNumber(next.motor.right_bias ?? 0.0, -0.35, 0.35, 0.0);
  next.motor.start_deadzone = clampNumber(next.motor.start_deadzone ?? 0.0, 0, 0.95, 0.0);
  next.motor.start_kick_seconds = clampNumber(next.motor.start_kick_seconds ?? 0.12, 0, 0.75, 0.12);
  next.manual_drive.max_speed_limit = clampNumber(next.manual_drive.max_speed_limit ?? 1.0, 0.1, 1.0, 1.0);
  next.manual_drive.speed = clampNumber(next.manual_drive.speed ?? 0.18, 0, next.manual_drive.max_speed_limit, 0.18);
  delete next.manual_drive.steer_strength;
  next.manual_drive.recording_fps = clampNumber(next.manual_drive.recording_fps ?? 6, 0.2, 30, 6);
  return next;
}
function fillForm(form, values = {}) { if (!form || !values) return; for (const el of form.elements) { if (!el.name || values[el.name] === undefined) continue; el.value = String(values[el.name]); } updateOutputs(form); }
function updateOutputs(root=document) { root.querySelectorAll('input[type="range"]').forEach(input => { const out = input.parentElement?.querySelector('output'); if (out) out.textContent = input.value; }); }
function gatherSettings() { return normaliseSettingsForUi({ camera: formPayload(document.getElementById('stCameraForm')), motor: formPayload(document.getElementById('stMotorForm')), manual_drive: formPayload(document.getElementById('stManualDriveForm')), panel_presentation: formPayload(document.getElementById('stPresentationForm')) }); }
function fillAll(settings={}) { settings = normaliseSettingsForUi(settings); fillForm(document.getElementById('stCameraForm'), settings.camera); fillForm(document.getElementById('stMotorForm'), settings.motor); fillForm(document.getElementById('stManualDriveForm'), settings.manual_drive); fillForm(document.getElementById('stPresentationForm'), settings.panel_presentation); if (settings.panel_presentation && window.PiSDPanelPresentation) window.PiSDPanelPresentation.apply(settings.panel_presentation); }
function storeLocal(settings) { settings = normaliseSettingsForUi(settings); localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify({ ...settings, saved_at: new Date().toISOString() })); if (settings.panel_presentation && window.PiSDPanelPresentation) window.PiSDPanelPresentation.save(settings.panel_presentation); }
async function settingsApi(method, path, body) { const options={method,headers:{}}; if(body!==undefined&&method!=='GET'){options.headers['Content-Type']='application/json';options.body=JSON.stringify(body);} const res=await fetch(path,options); const payload=await res.json(); logResponse(`${method} ${path}`, payload, res.status); return payload; }
async function loadSettings() { const payload = await settingsApi('GET','/api/settings'); if (payload.settings) { fillAll(payload.settings); storeLocal(payload.settings); } setSettingsCode('settings', payload.code); }
async function saveSettings(apply=false) { const settings = gatherSettings(); storeLocal(settings); if (settings.panel_presentation && window.PiSDPanelPresentation) window.PiSDPanelPresentation.apply(settings.panel_presentation); const payload = await settingsApi('POST', apply ? '/api/settings/apply' : '/api/settings', settings); if (payload.settings) { fillAll(payload.settings); storeLocal(payload.settings); } setSettingsCode('settings', payload.code); }
async function resetSettings() { const payload = await settingsApi('POST','/api/settings/reset',{}); if (payload.settings) { fillAll(payload.settings); storeLocal(payload.settings); } setSettingsCode('settings', payload.code); }
function exportSettings() { const blob = new Blob([JSON.stringify(gatherSettings(), null, 2)], {type:'application/json'}); const url = URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='pisd_runtime_settings.json'; a.click(); setTimeout(()=>URL.revokeObjectURL(url),500); }
function importSettings(file) { const reader = new FileReader(); reader.onload = () => { try { const settings = JSON.parse(reader.result); fillAll(settings); storeLocal(settings); logResponse('import settings file', {ok:true, code:'PISD-OK-000', message:'Settings imported into form. Click Save and apply.'}); } catch(err) { logResponse('import settings file', {ok:false, code:'PISD-SET-003', message:String(err)}); } }; reader.readAsText(file); }
document.getElementById('stLoadSettings')?.addEventListener('click', loadSettings);
document.getElementById('stSaveSettings')?.addEventListener('click', () => saveSettings(false));
document.getElementById('stApplySettings')?.addEventListener('click', () => saveSettings(true));
document.getElementById('stResetSettings')?.addEventListener('click', resetSettings);
document.getElementById('stExportSettings')?.addEventListener('click', exportSettings);
document.getElementById('stImportSettings')?.addEventListener('change', e => { if(e.target.files?.[0]) importSettings(e.target.files[0]); });
document.getElementById('stStopAll')?.addEventListener('click', () => settingsApi('POST','/api/control/stop',{}));
document.querySelectorAll('input, select').forEach(el => el.addEventListener('input', () => { updateOutputs(document); const s=gatherSettings(); storeLocal(s); if (s.panel_presentation && window.PiSDPanelPresentation) window.PiSDPanelPresentation.apply(s.panel_presentation); }));
updateOutputs(document);
loadSettings().catch(err => logResponse('load settings failed', {ok:false, code:'PISD-API-002', message:String(err)}));
