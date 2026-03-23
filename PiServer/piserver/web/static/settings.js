(() => {
  const api = window.PiServerStyle;
  if (!api) return;

  const defaults = api.getDefaultSettings();
  const current = Object.assign({}, defaults, api.loadCustomSettings() || {});

  const controls = {
    fontScale: { type: 'range', unit: '%', valueId: 'fontScaleValue' },
    gridGap: { type: 'range', unit: 'px', valueId: 'gridGapValue' },
    workspacePad: { type: 'range', unit: 'px', valueId: 'workspacePadValue' },
    panelPad: { type: 'range', unit: 'px', valueId: 'panelPadValue' },
    panelHeadPad: { type: 'range', unit: 'px', valueId: 'panelHeadPadValue' },
    controlGap: { type: 'range', unit: 'px', valueId: 'controlGapValue' },
    sectionGap: { type: 'range', unit: 'px', valueId: 'sectionGapValue' },
    cardGap: { type: 'range', unit: 'px', valueId: 'cardGapValue' },
    fieldGap: { type: 'range', unit: 'px', valueId: 'fieldGapValue' },
    radius: { type: 'range', unit: 'px', valueId: 'radiusValue' },
    bg: { type: 'color', valueId: 'bgText' },
    panel: { type: 'color', valueId: 'panelText' },
    panelAlt: { type: 'color', valueId: 'panelAltText' },
    text: { type: 'color', valueId: 'textText' },
    muted: { type: 'color', valueId: 'mutedText' },
    accent: { type: 'color', valueId: 'accentText' },
    danger: { type: 'color', valueId: 'dangerText' },
    ok: { type: 'color', valueId: 'okText' },
    line: { type: 'color', valueId: 'lineText' },
    lineStrong: { type: 'color', valueId: 'lineStrongText' },
  };

  function setMessage(message) {
    const el = document.getElementById('styleSettingsMessage');
    if (el) el.textContent = message;
  }

  function renderValues() {
    Object.entries(controls).forEach(([key, meta]) => {
      const el = document.getElementById(key);
      const valueEl = document.getElementById(meta.valueId);
      if (!el) return;
      el.value = current[key];
      if (valueEl) valueEl.textContent = meta.type === 'range' ? `${current[key]}${meta.unit}` : String(current[key]).toLowerCase();
    });
  }

  function applyPreview() {
    api.applyCustomSettings(current);
    renderValues();
  }

  function resetAll() {
    Object.assign(current, defaults);
    applyPreview();
    setMessage('Preview reset to the default PiServer style.');
  }

  function saveAll() {
    api.saveCustomSettings(current);
    api.applySavedSettings();
    setMessage('Style saved. The main PiServer page will use these settings.');
  }

  Object.entries(controls).forEach(([key, meta]) => {
    const el = document.getElementById(key);
    if (!el) return;
    el.addEventListener('input', (event) => {
      current[key] = meta.type === 'range' ? Number(event.target.value) : String(event.target.value).toLowerCase();
      applyPreview();
    });
  });

  document.getElementById('saveStyleBtn')?.addEventListener('click', saveAll);
  document.getElementById('resetStyleBtn')?.addEventListener('click', () => {
    api.clearCustomSettings();
    resetAll();
  });

  applyPreview();
})();
