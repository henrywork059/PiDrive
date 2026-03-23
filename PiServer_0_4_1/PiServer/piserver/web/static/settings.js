(() => {
  const api = window.PiServerStyle;
  if (!api) return;

  const defaults = api.getDefaultSettings();
  const current = { ...defaults, ...(api.loadCustomSettings() || {}) };

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
    controlRadius: { type: 'range', unit: 'px', valueId: 'controlRadiusValue' },
    cardRadius: { type: 'range', unit: 'px', valueId: 'cardRadiusValue' },
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
      const input = document.getElementById(key);
      const valueEl = document.getElementById(meta.valueId);
      if (!input) return;
      input.value = current[key];
      if (!valueEl) return;
      valueEl.textContent = meta.type === 'range'
        ? `${current[key]}${meta.unit}`
        : String(current[key]).toLowerCase();
    });
  }

  function applyPreview() {
    api.applyCustomSettings(current);
    renderValues();
  }

  Object.entries(controls).forEach(([key, meta]) => {
    const input = document.getElementById(key);
    if (!input) return;
    input.addEventListener('input', (event) => {
      current[key] = meta.type === 'range'
        ? Number(event.target.value)
        : String(event.target.value).toLowerCase();
      applyPreview();
    });
  });

  document.getElementById('saveStyleBtn')?.addEventListener('click', () => {
    api.saveCustomSettings(current);
    setMessage('Style saved. The main PiServer page will use these settings.');
  });

  document.getElementById('resetStyleBtn')?.addEventListener('click', () => {
    api.clearCustomSettings();
    Object.assign(current, defaults);
    api.applyCustomSettings(current);
    renderValues();
    setMessage('Style reset to the default PiServer style.');
  });

  applyPreview();
})();
