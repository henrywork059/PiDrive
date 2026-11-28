(() => {
  'use strict';

  const $ = id => document.getElementById(id);
  const api = window.PiSDPanelPresentation;
  const form = $('ppForm');
  const output = $('ppOutput');
  const savedState = $('ppSavedState');
  const outputCode = $('ppOutputCode');
  const importInput = $('ppImport');
  const feedback = $('ppFeedback');

  function updateRangeReadouts() {
    for (const field of form.querySelectorAll('input[type="range"]')) {
      const readout = form.querySelector(`[data-range-value-for="${field.id}"]`);
      if (readout) readout.textContent = field.value;
      const unit = field.dataset.valueUnit;
      field.setAttribute('aria-valuetext', unit ? field.value + ' ' + unit : field.value);
    }
  }

  function log(settings, message = 'Panel presentation settings ready.', code = 'PISD-OK-000') {
    if (feedback && feedback.textContent !== message) feedback.textContent = message;
    if (output) output.textContent = `${message}\n\n${JSON.stringify(settings, null, 2)}`;
    if (outputCode) { outputCode.textContent = code; outputCode.dataset.state = String(code).startsWith('PISD-OK') ? 'ok' : 'error'; }
  }

  // Native range controls can round a saved value to their step grid.
  // Keep the loaded settings intact unless the user actually edits a field.
  let filledSettings = {};
  const filledValues = new Map();
  const editedFields = new Set();

  function fieldValue(element) {
    return element.type === 'checkbox' ? String(element.checked) : String(element.value);
  }

  function collect() {
    const data = { ...filledSettings };
    for (const element of form.elements) {
      if (!element.name) continue;
      const value = fieldValue(element);
      if (editedFields.has(element.name) || filledValues.get(element.name) !== value) {
        data[element.name] = value;
      }
    }
    return api.normalize(data);
  }

  function fill(settings) {
    const normalized = api.normalize(settings);
    filledSettings = { ...normalized };
    filledValues.clear();
    editedFields.clear();
    for (const [key, value] of Object.entries(normalized)) {
      const field = form.elements[key];
      if (!field) continue;
      if (field.type === 'checkbox') field.checked = String(value) === 'true';
      else field.value = value;
      filledValues.set(key, fieldValue(field));
    }
    updateRangeReadouts();
    return normalized;
  }

  function autoSaveEnabled() { const field = form?.elements?.autoSave; return !field || field.checked; }

  async function saveBackend(settings, message) {
    const normalized = api.save(settings);
    api.apply(normalized);
    if (savedState) savedState.textContent = 'saving';
    try {
      const response = await fetch('/api/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ panel_presentation: normalized }) });
      const payload = await response.json();
      if (payload.settings?.panel_presentation) api.save(payload.settings.panel_presentation);
      const confirmed = response.ok && payload.ok === true;
      const code = confirmed ? (payload.code || 'PISD-OK-000') : (payload.code && !String(payload.code).startsWith('PISD-OK') ? payload.code : 'PISD-API-002');
      log(payload.settings?.panel_presentation || normalized, confirmed ? message : 'Backend save failed; settings are not confirmed saved.', code);
      if (savedState) savedState.textContent = confirmed ? 'saved backend' : 'save failed';
      return payload.settings?.panel_presentation || normalized;
    } catch (err) {
      log(normalized, `Backend save unavailable; kept browser fallback. ${err}`, 'PISD-API-002');
      if (savedState) savedState.textContent = 'browser fallback';
      return normalized;
    }
  }

  function applyFromForm(message = 'Applied preview settings.') { const settings = collect(); api.apply(settings); log(settings, message); if (savedState) savedState.textContent = 'preview applied'; return settings; }
  function saveFromForm(message = 'Saved and applied to all pages.') { return saveBackend(collect(), message); }
  function applyOrAutosave() { if (autoSaveEnabled()) return saveFromForm('Auto-saved and applied globally.'); return applyFromForm('Live preview applied only.'); }
  async function reset() { const settings = fill(api.DEFAULTS); await saveBackend(settings, 'Reset to compact defaults and saved.'); api.apply(settings); }
  function exportPreset() { const settings = collect(); const blob = new Blob([JSON.stringify(settings, null, 2)], { type: 'application/json' }); const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = 'pisd_panel_presentation_preset.json'; link.click(); URL.revokeObjectURL(link.href); log(settings, 'Exported preset JSON.'); }
  function importPreset(file) { if (!file) return; const reader = new FileReader(); reader.onload = async () => { try { const settings = fill(JSON.parse(String(reader.result || '{}'))); await saveBackend(settings, 'Imported, saved, and applied preset.'); } catch (err) { log({}, `Import failed: ${err}`, 'PISD-TEST-018'); } }; reader.readAsText(file); }

  document.addEventListener('DOMContentLoaded', async () => {
    let settings = api.read();
    try { const response = await fetch('/api/settings', { cache: 'no-store' }); const payload = await response.json(); if (payload.settings?.panel_presentation) settings = payload.settings.panel_presentation; } catch (_err) {}
    settings = fill(settings); api.apply(settings); log(settings);
    form.addEventListener('input', event => {
      if (event.target.name) editedFields.add(event.target.name);
      updateRangeReadouts();
      applyOrAutosave();
    });
    $('ppApply')?.addEventListener('click', event => { event.preventDefault(); applyFromForm(); });
    $('ppSave')?.addEventListener('click', event => { event.preventDefault(); saveFromForm(); });
    $('ppReset')?.addEventListener('click', event => { event.preventDefault(); reset(); });
    $('ppExport')?.addEventListener('click', event => { event.preventDefault(); exportPreset(); });
    $('ppImportButton')?.addEventListener('click', event => { event.preventDefault(); importInput?.click(); });
    importInput?.addEventListener('change', () => importPreset(importInput.files && importInput.files[0]));
  });
})();
