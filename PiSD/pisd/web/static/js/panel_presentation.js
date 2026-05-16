(() => {
  'use strict';

  const $ = id => document.getElementById(id);
  // Persistence is handled by PiSDPanelPresentation through browser localStorage.
  const api = window.PiSDPanelPresentation;
  const form = $('ppForm');
  const output = $('ppOutput');
  const savedState = $('ppSavedState');
  const outputCode = $('ppOutputCode');
  const importInput = $('ppImport');

  function log(settings, message = 'Panel presentation settings ready.') {
    if (output) output.textContent = `${message}\n\n${JSON.stringify(settings, null, 2)}`;
    if (outputCode) outputCode.textContent = 'PISD-OK-000';
  }

  function collect() {
    const data = {};
    for (const element of form.elements) {
      if (!element.name) continue;
      if (element.type === 'checkbox') data[element.name] = element.checked ? 'true' : 'false';
      else data[element.name] = String(element.value);
    }
    return api.normalize(data);
  }

  function fill(settings) {
    const normalized = api.normalize(settings);
    for (const [key, value] of Object.entries(normalized)) {
      const field = form.elements[key];
      if (!field) continue;
      if (field.type === 'checkbox') field.checked = String(value) === 'true';
      else field.value = value;
    }
    return normalized;
  }

  function autoSaveEnabled() {
    const field = form?.elements?.autoSave;
    return !field || field.checked;
  }

  function applyFromForm(message = 'Applied preview settings.') {
    const settings = collect();
    api.apply(settings);
    log(settings, message);
    if (savedState) savedState.textContent = 'preview applied';
    return settings;
  }

  function saveFromForm(message = 'Saved and applied to all pages in this browser.') {
    const settings = api.save(collect());
    api.apply(settings);
    log(settings, message);
    if (savedState) savedState.textContent = 'saved globally';
    return settings;
  }

  function applyOrAutosave() {
    if (autoSaveEnabled()) return saveFromForm('Auto-saved and applied globally.');
    return applyFromForm('Live preview applied only.');
  }

  function reset() {
    const settings = api.save(api.DEFAULTS);
    fill(settings);
    api.apply(settings);
    log(settings, 'Reset to compact defaults and saved.');
    if (savedState) savedState.textContent = 'saved default';
  }

  function exportPreset() {
    const settings = collect();
    const blob = new Blob([JSON.stringify(settings, null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'pisd_panel_presentation_preset.json';
    link.click();
    URL.revokeObjectURL(link.href);
    log(settings, 'Exported preset JSON.');
  }

  function importPreset(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const settings = api.save(JSON.parse(String(reader.result || '{}')));
        fill(settings);
        api.apply(settings);
        log(settings, 'Imported, saved, and applied preset.');
        if (savedState) savedState.textContent = 'saved imported';
      } catch (err) {
        if (outputCode) outputCode.textContent = 'PISD-TEST-018';
        if (output) output.textContent = `Import failed: ${err}`;
      }
    };
    reader.readAsText(file);
  }

  document.addEventListener('DOMContentLoaded', () => {
    const settings = fill(api.read());
    api.apply(settings);
    log(settings);
    form.addEventListener('input', () => applyOrAutosave());
    $('ppApply')?.addEventListener('click', event => { event.preventDefault(); applyFromForm(); });
    $('ppSave')?.addEventListener('click', event => { event.preventDefault(); saveFromForm(); });
    $('ppReset')?.addEventListener('click', event => { event.preventDefault(); reset(); });
    $('ppExport')?.addEventListener('click', event => { event.preventDefault(); exportPreset(); });
    $('ppImportButton')?.addEventListener('click', event => { event.preventDefault(); importInput?.click(); });
    importInput?.addEventListener('change', () => importPreset(importInput.files && importInput.files[0]));
  });
})();
