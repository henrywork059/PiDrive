(() => {
  function byId(id) { return document.getElementById(id); }

  const defaults = window.PiServerStyle?.themes?.opsFlat?.vars || {};
  const saved = window.PiServerStyle?.getSavedStyle?.() || {};

  const fields = {
    bg: '--bg',
    panel: '--panel',
    panelAlt: '--panel-alt',
    line: '--line',
    text: '--text',
    muted: '--muted',
    accent: '--accent',
    danger: '--danger',
    ok: '--ok',
    gap: '--gap',
    radius: '--radius',
    pageMargin: '--page-margin',
    panelPadding: '--panel-padding',
    controlFontSize: '--control-font-size',
    baseFontSize: '--base-font-size',
  };

  function styleValue(cssVar) {
    return saved[cssVar] || defaults[cssVar] || getComputedStyle(document.documentElement).getPropertyValue(cssVar).trim();
  }

  function fillForm() {
    Object.entries(fields).forEach(([id, cssVar]) => {
      const el = byId(id);
      if (el) el.value = normalizeForInput(cssVar, styleValue(cssVar));
    });
    syncLabels();
  }

  function normalizeForInput(cssVar, value) {
    const v = String(value || '').trim();
    if (v.startsWith('#')) return v;
    if (cssVar === '--base-font-size') return v.replace('%', '');
    if (cssVar === '--control-font-size') return v.replace('rem', '');
    return v.replace('px', '');
  }

  function readForm() {
    return {
      '--bg': byId('bg').value,
      '--panel': byId('panel').value,
      '--panel-alt': byId('panelAlt').value,
      '--line': byId('line').value,
      '--text': byId('text').value,
      '--muted': byId('muted').value,
      '--accent': byId('accent').value,
      '--danger': byId('danger').value,
      '--ok': byId('ok').value,
      '--gap': byId('gap').value,
      '--radius': byId('radius').value,
      '--page-margin': byId('pageMargin').value,
      '--panel-padding': byId('panelPadding').value,
      '--control-font-size': byId('controlFontSize').value,
      '--base-font-size': byId('baseFontSize').value,
    };
  }

  function applyPreview() {
    const clean = window.PiServerStyle.sanitizeStyle(readForm());
    Object.entries(clean).forEach(([key, value]) => document.documentElement.style.setProperty(key, value));
    syncLabels(clean);
  }

  function syncLabels(clean = window.PiServerStyle.sanitizeStyle(readForm())) {
    const mappings = {
      gapValue: clean['--gap'],
      radiusValue: clean['--radius'],
      pageMarginValue: clean['--page-margin'],
      panelPaddingValue: clean['--panel-padding'],
      controlFontSizeValue: clean['--control-font-size'],
      baseFontSizeValue: clean['--base-font-size'],
    };
    Object.entries(mappings).forEach(([id, value]) => { const el = byId(id); if (el) el.textContent = value; });
  }

  function setMessage(text, tone = 'muted') {
    const el = byId('settingsMessage');
    if (!el) return;
    el.className = `banner ${tone}`;
    el.textContent = text;
  }

  fillForm();
  applyPreview();

  document.querySelectorAll('.settings-form input').forEach((input) => {
    input.addEventListener('input', applyPreview);
  });

  byId('saveStyleBtn')?.addEventListener('click', () => {
    const clean = window.PiServerStyle.saveCustomStyle(readForm());
    Object.entries(clean).forEach(([key, value]) => document.documentElement.style.setProperty(key, value));
    setMessage('Style saved for this browser.', 'ok');
  });

  byId('resetStyleBtn')?.addEventListener('click', () => {
    window.PiServerStyle.clearCustomStyle();
    window.PiServerStyle.applyTheme('opsFlat');
    fillForm();
    applyPreview();
    setMessage('Style reset to default theme.', 'muted');
  });
})();
