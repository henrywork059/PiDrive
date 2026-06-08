(() => {
  'use strict';

  const OK = 'PISD-OK-000';
  const PANEL_GUI_ERROR = 'PISD-TEST-012';
  const PANEL_SKIP = 'PISD-TEST-013';
  const PANEL_API_ERROR = 'PISD-TEST-014';
  const STORAGE_KEY = 'pisd.panelTestingPreset.v1';

  const PANEL_ID_CONTRACT_MARKERS = [
    'system-status-panel',
    'camera-preview-panel',
    'camera-settings-panel',
    'motor-settings-panel',
    'motor-channel-panel',
    'manual-drive-panel',
    'safety-stop-panel',
    'error-monitor-panel',
    'api-inspector-panel',
    'validation-panel',
    'recording-panel',
    'model-runtime-panel',
  ];

  const dom = {
    shell: document.getElementById('ptShell'),
    panelGrid: document.getElementById('ptPanelGrid'),
    panelCount: document.getElementById('ptPanelCount'),
    viewportFrame: document.getElementById('ptViewportFrame'),
    report: document.getElementById('ptPanelReport'),
    globalCode: document.getElementById('ptGlobalCode'),
    environmentLabel: document.getElementById('ptEnvironmentLabel'),
    theme: document.getElementById('ptTheme'),
    layoutMode: document.getElementById('ptLayoutMode'),
    viewportPreset: document.getElementById('ptViewportPreset'),
    panelSizePreset: document.getElementById('ptPanelSizePreset'),
    density: document.getElementById('ptDensity'),
    fontScale: document.getElementById('ptFontScale'),
    panelGap: document.getElementById('ptPanelGap'),
    panelRadius: document.getElementById('ptPanelRadius'),
    borderStrength: document.getElementById('ptBorderStrength'),
    shadowStrength: document.getElementById('ptShadowStrength'),
    minPanelWidth: document.getElementById('ptMinPanelWidth'),
    previewAspect: document.getElementById('ptPreviewAspect'),
    importPreset: document.getElementById('ptImportPreset'),
  };

  let lastStatus = readJson('panelInitialStatusJson') || {};
  const manifest = readJson('panelManifestJson') || {};
  const PANEL_BLUEPRINTS = Array.isArray(manifest.panels) && manifest.panels.length ? manifest.panels : [];
  let sizeCycleIndex = 0;
  const lastPanelResponses = new Map();

  function readJson(id) {
    const node = document.getElementById(id);
    if (!node) return null;
    try { return JSON.parse(node.textContent || '{}'); }
    catch (_err) { return null; }
  }

  function escapeText(value) {
    return String(value ?? '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[ch]));
  }

  function writeReport(lines, append = false) {
    const text = Array.isArray(lines) ? lines.join('\n') : String(lines);
    dom.report.textContent = append ? `${dom.report.textContent}\n${text}` : text;
    dom.report.scrollTop = dom.report.scrollHeight;
  }

  function statusLine(state, code, label, message = '') {
    return `${state.padEnd(4)} ${String(code || OK).padEnd(13)} ${label} - ${message}`;
  }

  function okLine(label, message = 'ok', code = OK) { return statusLine('OK', code, label, message); }
  function failLine(label, message = 'failed', code = PANEL_API_ERROR) { return statusLine('FAIL', code, label, message); }
  function skipLine(label, message = 'future placeholder', code = PANEL_SKIP) { return statusLine('SKIP', code, label, message); }

  function endpointsHtml(panel) {
    const endpoints = Array.isArray(panel.endpoints) ? panel.endpoints : [];
    if (!endpoints.length) return '<span class="pt-muted">No live API yet. Reserved for final GUI stage.</span>';
    return endpoints.map(item => `<span class="pt-chip"><strong>${escapeText(item.method)}</strong> ${escapeText(item.path)}</span>`).join('');
  }

  function expectedCodesHtml(panel) {
    const test = panel.safe_test || {};
    const codes = Array.isArray(test.expected_codes) ? test.expected_codes : [];
    if (!codes.length) return '<span class="pt-muted">No expected code set.</span>';
    return codes.map(code => `<span class="pt-code-inline">${escapeText(code)}</span>`).join(' ');
  }

  function field(label, value) {
    return `<div class="pt-metric"><span>${escapeText(label)}</span><strong>${escapeText(value)}</strong></div>`;
  }

  function bodyHtml(panel) {
    switch (panel.body) {
      case 'status':
        return `<div class="pt-metric-grid">
          ${field('Version', lastStatus.version || manifest.version || 'unknown')}
          ${field('Hardware', lastStatus.hardware_requested ? 'requested' : 'simulation')}
          ${field('Camera', (lastStatus.camera || {}).backend || 'not started')}
          ${field('Motor', (lastStatus.motor || {}).adapter || 'unknown')}
        </div>`;
      case 'cameraPreview':
        return `<div class="pt-preview-surface"><span>Camera preview surface<br><small>aspect controlled by panel settings</small></span></div>
          <div class="pt-action-grid"><button class="pt-button" data-panel-api="POST /api/camera/start">Start camera API</button><button class="pt-button" data-panel-api="GET /api/camera/frame.jpg">Fetch frame</button></div>`;
      case 'cameraSettings':
        return `<div class="pt-field-grid">
          <label><span>Width</span><input value="426" inputmode="numeric"></label>
          <label><span>Height</span><input value="240" inputmode="numeric"></label>
          <label><span>FPS</span><input value="12" inputmode="numeric"></label>
          <label><span>Quality</span><input value="65" inputmode="numeric"></label>
          <label><span>Capture</span><select><option>request</option><option>array</option></select></label>
          <label><span>Array order</span><select><option>rgb</option><option>bgr</option><option>auto</option></select></label>
        </div>`;
      case 'motorSettings':
        return `<div class="pt-field-grid">
          <label><span>Left direction</span><select><option>1</option><option>-1</option></select></label>
          <label><span>Right direction</span><select><option>1</option><option>-1</option></select></label>
          <label><span>Steering direction</span><select><option>1</option><option>-1</option></select></label>
          <label><span>Steer mix</span><input value="1.0"></label>
        </div>`;
      case 'motorChannel':
        return `<div class="pt-field-grid">
          <label><span>Side</span><select><option>left</option><option>right</option></select></label>
          <label><span>Direction</span><select><option>1</option><option>-1</option></select></label>
          <label><span>Speed</span><input value="0.12"></label>
          <label><span>Duration</span><input value="0.25"></label>
        </div><p class="pt-muted">Safe panel API test does not arm real motor output.</p>`;
      case 'manualDrive':
        return `<div class="pt-joystick-pad">
          <button class="pt-button">↑</button><button class="pt-button">←</button><button class="pt-button pt-button-danger">STOP</button><button class="pt-button">→</button><button class="pt-button">↓</button>
        </div><p class="pt-muted">Panel API check sends zero throttle only.</p>`;
      case 'safetyStop':
        return `<div class="pt-action-tile"><strong class="pt-danger-text">Emergency stop must remain reachable in every layout.</strong><p>Panel should stay readable in compact, phone, and high-contrast modes.</p></div>`;
      case 'errors':
        return `<div class="pt-metric-grid">
          ${field('App errors', ((lastStatus.errors || {}).app || []).length)}
          ${field('Camera errors', ((lastStatus.errors || {}).camera || []).length)}
          ${field('Motor errors', ((lastStatus.errors || {}).motor || []).length)}
        </div>`;
      case 'apiInspector':
        return `<div class="pt-field-grid"><label><span>Method</span><select><option>GET</option><option>POST</option></select></label><label><span>Path</span><input value="/api/status"></label></div><div class="pt-console pt-console-mini">Response preview area</div>`;
      case 'validation':
        return `<div class="pt-action-grid"><button class="pt-button" data-panel-check="required-dom">Check DOM</button><button class="pt-button" data-panel-check="responsive">Check responsive</button><button class="pt-button" data-panel-check="api-map">Check API map</button></div>`;
      default:
        return `<div class="pt-placeholder"><strong>${escapeText(panel.title)}</strong><p>${escapeText(panel.purpose)}</p><p class="pt-muted">Placeholder is intentional. This panel space is reserved so the final GUI can be planned without locking the design too early.</p></div>`;
    }
  }

  function renderPanels() {
    dom.panelGrid.innerHTML = PANEL_BLUEPRINTS.map(panel => `
      <article class="pt-panel" id="${escapeText(panel.id)}" data-panel-id="${escapeText(panel.id)}" data-group="${escapeText(panel.group)}" data-size="${escapeText(panel.default_size || panel.defaultSize || 'standard')}">
        <header class="pt-panel-head">
          <div class="pt-panel-title-group">
            <h3>${escapeText(panel.title)}</h3>
            <p>${escapeText(panel.purpose)}</p>
          </div>
          <div class="pt-panel-tools">
            <span class="pt-panel-code">${OK}</span>
            <button class="pt-mini-button" data-panel-size="compact" title="compact size">C</button>
            <button class="pt-mini-button" data-panel-size="standard" title="standard size">S</button>
            <button class="pt-mini-button" data-panel-size="large" title="large size">L</button>
            <button class="pt-mini-button" data-panel-test="${escapeText(panel.id)}" title="test this panel">Test panel</button>
            <button class="pt-mini-button" data-panel-contract="${escapeText(panel.id)}" title="show API contract">Contract</button>
            <button class="pt-mini-button" data-panel-response="${escapeText(panel.id)}" title="show last response">Last</button>
            <button class="pt-mini-button" data-panel-expected="${escapeText(panel.id)}" title="show expected result">Expected</button>
          </div>
        </header>
        <div class="pt-panel-body">
          ${bodyHtml(panel)}
          <div class="pt-action-grid">${endpointsHtml(panel)}</div>
          <div class="pt-contract-strip"><span>Expected:</span> ${expectedCodesHtml(panel)}</div>
        </div>
        <footer class="pt-panel-foot">
          <span class="pt-muted">Group: ${escapeText(panel.group)}</span>
          <span class="pt-muted">Min width: ${escapeText(panel.minimum_width_px || 'n/a')}px</span>
          <span class="pt-muted">Danger: ${panel.dangerous_action ? 'yes' : 'no'}</span>
        </footer>
      </article>`).join('');
    dom.panelCount.textContent = `${PANEL_BLUEPRINTS.length} planned panels listed with API contracts.`;
  }

  function collectSettings() {
    return {
      theme: dom.theme.value,
      layoutMode: dom.layoutMode.value,
      viewportPreset: dom.viewportPreset.value,
      panelSizePreset: dom.panelSizePreset.value,
      density: dom.density.value,
      fontScale: dom.fontScale.value,
      panelGap: dom.panelGap.value,
      panelRadius: dom.panelRadius.value,
      borderStrength: dom.borderStrength.value,
      shadowStrength: dom.shadowStrength.value,
      minPanelWidth: dom.minPanelWidth.value,
      previewAspect: dom.previewAspect.value,
      panelSizes: Object.fromEntries([...document.querySelectorAll('.pt-panel')].map(panel => [panel.dataset.panelId, panel.dataset.size])),
    };
  }

  function applyPreset(settings) {
    if (!settings || typeof settings !== 'object') return;
    const pairs = [
      ['theme', dom.theme], ['layoutMode', dom.layoutMode], ['viewportPreset', dom.viewportPreset], ['panelSizePreset', dom.panelSizePreset], ['density', dom.density],
      ['fontScale', dom.fontScale], ['panelGap', dom.panelGap], ['panelRadius', dom.panelRadius], ['borderStrength', dom.borderStrength], ['shadowStrength', dom.shadowStrength], ['minPanelWidth', dom.minPanelWidth], ['previewAspect', dom.previewAspect],
    ];
    for (const [key, node] of pairs) if (node && settings[key] !== undefined) node.value = settings[key];
    applySettings();
    if (settings.panelSizes) {
      for (const [id, size] of Object.entries(settings.panelSizes)) {
        const panel = document.querySelector(`[data-panel-id="${CSS.escape(id)}"]`);
        if (panel && size) panel.dataset.size = size;
      }
    }
  }

  function savePreset() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(collectSettings()));
    writeReport(okLine('panel.preset_save', 'saved to browser localStorage'));
  }

  function loadPreset() {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      writeReport(skipLine('panel.preset_load', 'no saved preset found'));
      return;
    }
    try {
      applyPreset(JSON.parse(raw));
      writeReport(okLine('panel.preset_load', 'loaded from browser localStorage'));
    } catch (err) {
      writeReport(failLine('panel.preset_load', err.message, PANEL_GUI_ERROR));
    }
  }

  function exportPreset() {
    const preset = { code: OK, exported_at: new Date().toISOString(), settings: collectSettings() };
    const blob = new Blob([JSON.stringify(preset, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'pisd_panel_preset.json';
    link.click();
    URL.revokeObjectURL(url);
    writeReport(okLine('panel.preset_export', 'download started'));
  }

  async function importPresetFile(file) {
    if (!file) return;
    try {
      const data = JSON.parse(await file.text());
      applyPreset(data.settings || data);
      writeReport(okLine('panel.preset_import', file.name));
    } catch (err) {
      writeReport(failLine('panel.preset_import', err.message, PANEL_GUI_ERROR));
    } finally {
      if (dom.importPreset) dom.importPreset.value = '';
    }
  }

  function applySettings() {
    document.body.dataset.theme = dom.theme.value;
    dom.shell.dataset.layout = dom.layoutMode.value;
    dom.shell.dataset.density = dom.density.value;
    dom.viewportFrame.dataset.preset = dom.viewportPreset.value;
    document.documentElement.style.setProperty('--pt-font-scale', dom.fontScale.value);
    document.documentElement.style.setProperty('--pt-gap', `${dom.panelGap.value}px`);
    document.documentElement.style.setProperty('--pt-radius', `${dom.panelRadius.value}px`);
    document.documentElement.style.setProperty('--pt-border-alpha', dom.borderStrength.value);
    document.documentElement.style.setProperty('--pt-shadow-alpha', dom.shadowStrength.value);
    document.documentElement.style.setProperty('--pt-min-panel-width', `${dom.minPanelWidth.value}px`);
    document.documentElement.style.setProperty('--pt-preview-aspect', dom.previewAspect.value);
    applyPanelSizePreset(dom.panelSizePreset.value);
    dom.environmentLabel.textContent = `${dom.layoutMode.value} / ${dom.density.value} / ${dom.viewportPreset.value}`;
  }

  function applyPanelSizePreset(preset) {
    const sizes = ['compact', 'standard', 'large', 'wide', 'full'];
    document.querySelectorAll('.pt-panel').forEach((panel, index) => {
      if (preset === 'auto') {
        const blueprint = PANEL_BLUEPRINTS.find(item => item.id === panel.dataset.panelId);
        panel.dataset.size = blueprint?.default_size || blueprint?.defaultSize || 'standard';
      } else if (preset === 'stress') {
        panel.dataset.size = sizes[index % sizes.length];
      } else {
        panel.dataset.size = preset;
      }
    });
  }

  async function apiCall(method, path, body) {
    const options = { method, headers: {} };
    if (body !== undefined && body !== null) {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(body);
    }
    const response = await fetch(path, options);
    const type = response.headers.get('content-type') || '';
    if (type.includes('application/json')) return { status: response.status, payload: await response.json() };
    return { status: response.status, bytes: (await response.blob()).size };
  }

  async function refreshStatus() {
    try {
      const result = await apiCall('GET', '/api/status');
      lastStatus = result.payload || {};
      dom.globalCode.textContent = lastStatus.code || OK;
      renderPanels();
      applySettings();
      writeReport(okLine('api.status', `HTTP ${result.status}`));
    } catch (err) {
      writeReport(failLine('api.status', err.message));
    }
  }

  function panelSelfTest(panelId) {
    const panel = document.querySelector(`[data-panel-id="${CSS.escape(panelId)}"]`);
    const blueprint = PANEL_BLUEPRINTS.find(item => item.id === panelId);
    if (!panel || !blueprint) return failLine(`panel.${panelId}`, 'panel missing', PANEL_GUI_ERROR);
    const hasTitle = panel.querySelector('h3')?.textContent?.trim() === blueprint.title;
    const hasBody = !!panel.querySelector('.pt-panel-body');
    const hasCode = !!panel.querySelector('.pt-panel-code');
    const hasSizing = ['compact', 'standard', 'large'].every(size => !!panel.querySelector(`[data-panel-size="${size}"]`));
    const hasContract = Array.isArray(blueprint.endpoints) && blueprint.safe_test && blueprint.minimum_width_px;
    if (hasTitle && hasBody && hasCode && hasSizing && hasContract) return okLine(`panel.${panelId}`, 'structure, size controls, and API contract ok');
    return failLine(`panel.${panelId}`, 'missing title/body/code/size controls/contract', PANEL_GUI_ERROR);
  }

  async function runPanelApiTest(panelId) {
    const panel = PANEL_BLUEPRINTS.find(item => item.id === panelId);
    if (!panel) return failLine(`panel.${panelId}`, 'panel not registered', PANEL_API_ERROR);
    const test = panel.safe_test || {};
    if (!test.path || test.method === 'NONE' || panel.future_placeholder) {
      const line = skipLine(test.label || `panel.${panelId}.placeholder`, panel.purpose || 'future placeholder');
      lastPanelResponses.set(panelId, { state: 'SKIP', code: PANEL_SKIP, panel, test });
      return line;
    }
    try {
      const result = await apiCall(test.method || 'GET', test.path, test.payload);
      const code = result.payload?.code || (result.status >= 200 && result.status < 300 ? OK : PANEL_API_ERROR);
      const expected = Array.isArray(test.expected_codes) ? test.expected_codes : [OK];
      const passed = expected.includes(code);
      lastPanelResponses.set(panelId, { state: passed ? 'OK' : 'FAIL', code, http_status: result.status, panel, test, response: result });
      dom.globalCode.textContent = code;
      return passed
        ? okLine(test.label || `panel.${panelId}.api`, `HTTP ${result.status}`, code)
        : failLine(test.label || `panel.${panelId}.api`, `HTTP ${result.status}, expected ${expected.join('/')}`, code);
    } catch (err) {
      lastPanelResponses.set(panelId, { state: 'FAIL', code: PANEL_API_ERROR, panel, test, error: err.message });
      return failLine(test.label || `panel.${panelId}.api`, err.message, PANEL_API_ERROR);
    }
  }

  function showContract(panelId) {
    const panel = PANEL_BLUEPRINTS.find(item => item.id === panelId);
    if (!panel) return writeReport(failLine(`panel.${panelId}.contract`, 'panel not registered', PANEL_API_ERROR));
    const contract = {
      id: panel.id,
      title: panel.title,
      dangerous_action: !!panel.dangerous_action,
      endpoints: panel.endpoints || [],
      safe_test: panel.safe_test || {},
      minimum_width_px: panel.minimum_width_px,
      responsive_behavior: panel.responsive_behavior,
    };
    writeReport(`CONTRACT ${panel.id}\n${JSON.stringify(contract, null, 2)}`);
  }

  function showExpected(panelId) {
    const panel = PANEL_BLUEPRINTS.find(item => item.id === panelId);
    if (!panel) return writeReport(failLine(`panel.${panelId}.expected`, 'panel not registered', PANEL_API_ERROR));
    const test = panel.safe_test || {};
    const expected = Array.isArray(test.expected_codes) ? test.expected_codes.join(', ') : 'not set';
    writeReport(okLine(`panel.${panelId}.expected`, `safe test ${test.method || 'NONE'} ${test.path || '(placeholder)'} -> ${expected}`));
  }

  function showLastResponse(panelId) {
    const last = lastPanelResponses.get(panelId);
    if (!last) return writeReport(skipLine(`panel.${panelId}.last_response`, 'no response yet'));
    writeReport(`LAST RESPONSE ${panelId}\n${JSON.stringify(last, null, 2)}`);
  }

  async function runAllPanelChecks() {
    const lines = [
      `Panel testing manifest version: ${manifest.version || 'unknown'}`,
      okLine('panel.registry', `${PANEL_BLUEPRINTS.length} panels registered`),
    ];
    const groups = new Set(PANEL_BLUEPRINTS.map(panel => panel.group));
    lines.push(okLine('panel.groups', `${Array.from(groups).sort().join(', ')}`));
    for (const panel of PANEL_BLUEPRINTS) lines.push(panelSelfTest(panel.id));
    lines.push('-'.repeat(72));
    let failed = lines.filter(line => line.startsWith('FAIL')).length;
    lines.push(failed === 0 ? okLine('panel.structure_summary', 'failed=0') : failLine('panel.structure_summary', `failed=${failed}`, PANEL_GUI_ERROR));
    writeReport(lines);
  }

  async function runAllPanelApiChecks() {
    const lines = ['Running safe panel API contract checks...'];
    for (const panel of PANEL_BLUEPRINTS) lines.push(await runPanelApiTest(panel.id));
    try { await apiCall('POST', '/api/control/stop', {}); } catch (_err) { /* keep summary focused on panel contracts */ }
    const failed = lines.filter(line => line.startsWith('FAIL')).length;
    lines.push('-'.repeat(72));
    lines.push(failed === 0 ? okLine('panel.api_summary', 'failed=0') : failLine('panel.api_summary', `failed=${failed}`, PANEL_API_ERROR));
    writeReport(lines);
  }

  function cycleSizes() {
    const sizes = ['compact', 'standard', 'large', 'wide', 'full'];
    sizeCycleIndex = (sizeCycleIndex + 1) % sizes.length;
    document.querySelectorAll('.pt-panel').forEach(panel => { panel.dataset.size = sizes[sizeCycleIndex]; });
    writeReport(okLine('panel.cycle_sizes', `all panels set to ${sizes[sizeCycleIndex]}`));
  }

  async function stopAll() {
    try {
      const result = await apiCall('POST', '/api/control/stop', {});
      const code = result.payload?.code || OK;
      dom.globalCode.textContent = code;
      writeReport(statusLine(result.status === 200 ? 'OK' : 'FAIL', code, 'api.control.stop', `HTTP ${result.status}`));
    } catch (err) {
      writeReport(failLine('api.control.stop', err.message));
    }
  }

  function exportReport() {
    const report = {
      code: dom.report.textContent.includes('FAIL') ? PANEL_API_ERROR : OK,
      generated_at: new Date().toISOString(),
      settings: collectSettings(),
      panels: PANEL_BLUEPRINTS.map(panel => ({ id: panel.id, title: panel.title, group: panel.group, size: document.getElementById(panel.id)?.dataset.size, dangerous_action: !!panel.dangerous_action })),
      report_text: dom.report.textContent,
      manifest_contract_rules: manifest.contract_rules || {},
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'pisd_panel_testing_report.json';
    link.click();
    URL.revokeObjectURL(url);
  }

  function resetPanels() {
    dom.theme.value = 'dark'; dom.layoutMode.value = 'adaptive'; dom.viewportPreset.value = 'auto'; dom.panelSizePreset.value = 'auto'; dom.density.value = 'comfortable';
    dom.fontScale.value = '1.0'; dom.panelGap.value = '14'; dom.panelRadius.value = '18'; dom.borderStrength.value = '0.35'; dom.shadowStrength.value = '0.35'; dom.minPanelWidth.value = '300'; dom.previewAspect.value = '16/9';
    renderPanels(); applySettings(); writeReport(okLine('panel.reset', 'panel lab reset'));
  }

  function bindEvents() {
    const controlIds = ['ptTheme', 'ptLayoutMode', 'ptViewportPreset', 'ptPanelSizePreset', 'ptDensity', 'ptFontScale', 'ptPanelGap', 'ptPanelRadius', 'ptBorderStrength', 'ptShadowStrength', 'ptMinPanelWidth', 'ptPreviewAspect'];
    for (const id of controlIds) document.getElementById(id)?.addEventListener('input', applySettings);
    document.getElementById('ptApplySettings')?.addEventListener('click', applySettings);
    document.getElementById('ptRefreshStatus')?.addEventListener('click', refreshStatus);
    document.getElementById('ptRunAllChecks')?.addEventListener('click', runAllPanelChecks);
    document.getElementById('ptRunPanelApiChecks')?.addEventListener('click', runAllPanelApiChecks);
    document.getElementById('ptCycleSizes')?.addEventListener('click', cycleSizes);
    document.getElementById('ptStopAll')?.addEventListener('click', stopAll);
    document.getElementById('ptExportPanelReport')?.addEventListener('click', exportReport);
    document.getElementById('ptSavePreset')?.addEventListener('click', savePreset);
    document.getElementById('ptLoadPreset')?.addEventListener('click', loadPreset);
    document.getElementById('ptExportPreset')?.addEventListener('click', exportPreset);
    document.getElementById('ptImportPresetButton')?.addEventListener('click', () => dom.importPreset?.click());
    dom.importPreset?.addEventListener('change', event => importPresetFile(event.target.files?.[0]));
    document.getElementById('ptResetPanels')?.addEventListener('click', resetPanels);
    dom.panelGrid.addEventListener('click', async event => {
      const target = event.target;
      const size = target?.dataset?.panelSize;
      if (size) target.closest('.pt-panel').dataset.size = size;
      const testId = target?.dataset?.panelTest;
      if (testId) writeReport([panelSelfTest(testId), await runPanelApiTest(testId)]);
      const contractId = target?.dataset?.panelContract;
      if (contractId) showContract(contractId);
      const responseId = target?.dataset?.panelResponse;
      if (responseId) showLastResponse(responseId);
      const expectedId = target?.dataset?.panelExpected;
      if (expectedId) showExpected(expectedId);
    });
  }

  renderPanels();
  bindEvents();
  applySettings();
  writeReport([okLine('panel.lab_ready', `${PANEL_BLUEPRINTS.length} flexible panels rendered`), 'Use structure checks for layout and API checks for safe endpoint wiring.']);
})();
