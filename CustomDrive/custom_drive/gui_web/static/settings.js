(() => {
  const api = window.PiServerStyle;
  if (!api) return;

  const fieldMap = {
    fontScale: { cssVar: '--font-scale', unit: '%', fallback: 80 },
    gridGap: { cssVar: '--gap', unit: 'px', fallback: 4 },
    workspacePad: { cssVar: '--workspace-pad', unit: 'px', fallback: 10 },
    panelPad: { cssVar: '--panel-pad', unit: 'px', fallback: 12 },
    panelHeadPadY: { cssVar: '--panel-head-pad-y', unit: 'px', fallback: 10 },
    panelHeadPadX: { cssVar: '--panel-head-pad-x', unit: 'px', fallback: 12 },
    radius: { cssVar: '--radius', unit: 'px', fallback: 10 },
    cardGap: { cssVar: '--card-gap', unit: 'px', fallback: 10 },
    fieldGap: { cssVar: '--field-gap', unit: 'px', fallback: 10 },
    bg: { cssVar: '--bg', color: true },
    panel: { cssVar: '--panel', color: true },
    panelAlt: { cssVar: '--panel-alt', color: true },
    text: { cssVar: '--text', color: true },
    muted: { cssVar: '--muted', color: true },
    accent: { cssVar: '--accent', color: true },
    danger: { cssVar: '--danger', color: true },
    ok: { cssVar: '--ok', color: true },
    line: { cssVar: '--line', color: true },
    lineStrong: { cssVar: '--line-strong', color: true },
  };

  function normalizeHex(value, fallback = '#000000') {
    const raw = String(value || '').trim();
    const short = raw.match(/^#([0-9a-f]{3})$/i);
    if (short) {
      return `#${short[1].split('').map((part) => part + part).join('')}`.toLowerCase();
    }
    const full = raw.match(/^#([0-9a-f]{6})$/i);
    if (full) return `#${full[1]}`.toLowerCase();
    return fallback;
  }

  function parseNumeric(raw, fallback) {
    const match = String(raw || '').match(/-?\d+(?:\.\d+)?/);
    return match ? Number(match[0]) : fallback;
  }

  function syncFieldsFromResolvedVars() {
    const resolved = api.getResolvedVars();
    Object.entries(fieldMap).forEach(([id, meta]) => {
      const el = document.getElementById(id);
      if (!el) return;
      const raw = resolved[meta.cssVar];
      if (meta.color) {
        const color = normalizeHex(raw, '#000000');
        el.value = color;
        document.getElementById(`${id}Text`)?.replaceChildren(document.createTextNode(color));
      } else {
        const numeric = parseNumeric(raw, meta.fallback);
        el.value = `${numeric}`;
        document.getElementById(`${id}Value`)?.replaceChildren(document.createTextNode(`${numeric}${meta.unit}`));
      }
    });
  }

  function buildOverridesFromFields() {
    const overrides = {};
    Object.entries(fieldMap).forEach(([id, meta]) => {
      const el = document.getElementById(id);
      if (!el) return;
      if (meta.color) {
        const color = normalizeHex(el.value, '#000000');
        overrides[meta.cssVar] = color;
        if (meta.cssVar === '--accent') {
          const value = color.slice(1);
          overrides['--accent-rgb'] = [0, 2, 4].map((start) => parseInt(value.slice(start, start + 2), 16)).join(', ');
        }
        document.getElementById(`${id}Text`)?.replaceChildren(document.createTextNode(color));
      } else {
        const value = `${el.value}${meta.unit}`;
        overrides[meta.cssVar] = value;
        if (meta.cssVar === '--font-scale') overrides['--font-scale-factor'] = String(Number(el.value) / 100);
        document.getElementById(`${id}Value`)?.replaceChildren(document.createTextNode(value));
      }
    });
    return overrides;
  }

  function setMessage(message) {
    const el = document.getElementById('styleSettingsMessage');
    if (el) el.textContent = message;
  }

  function previewChanges() {
    api.saveCustomOverrides(buildOverridesFromFields());
    setMessage('Style preview updated. Save when you are ready.');
  }

  document.getElementById('saveStyleBtn')?.addEventListener('click', () => {
    api.saveCustomOverrides(buildOverridesFromFields());
    setMessage('Style saved. The CustomDrive GUI will use these settings.');
  });

  document.getElementById('resetStyleBtn')?.addEventListener('click', () => {
    api.resetCustomOverrides();
    syncFieldsFromResolvedVars();
    setMessage('Style reset to the default PiServer-style theme.');
  });

  Object.keys(fieldMap).forEach((id) => {
    document.getElementById(id)?.addEventListener('input', previewChanges);
  });

  syncFieldsFromResolvedVars();
})();
