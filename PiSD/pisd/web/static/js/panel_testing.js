(() => {
  'use strict';

  const OK = 'PISD-OK-000';
  const PANEL_CONTRACT_ERROR = 'PISD-TEST-012';

  const PANEL_BLUEPRINTS = [
    {
      id: 'system-status-panel',
      title: 'System Status',
      purpose: 'Show app version, hardware mode, service state, and latest PISD code.',
      group: 'diagnostics',
      defaultSize: 'standard',
      api: [{ method: 'GET', path: '/api/status' }],
      body: 'status',
    },
    {
      id: 'camera-preview-panel',
      title: 'Camera Preview',
      purpose: 'Display the trusted request/PIL visual stream and refresh frames.',
      group: 'camera',
      defaultSize: 'wide',
      api: [{ method: 'POST', path: '/api/camera/start' }, { method: 'GET', path: '/api/camera/frame.jpg' }],
      body: 'cameraPreview',
    },
    {
      id: 'camera-settings-panel',
      title: 'Camera Settings',
      purpose: 'Test size, quality, exposure, WB, buffer, transform, and image tuning controls.',
      group: 'camera',
      defaultSize: 'large',
      api: [{ method: 'GET', path: '/api/camera/config' }, { method: 'POST', path: '/api/camera/apply' }],
      body: 'cameraSettings',
    },
    {
      id: 'motor-settings-panel',
      title: 'Motor Settings',
      purpose: 'Adjust per-car direction, speed limits, bias, and steering mix without moving wheels.',
      group: 'motor',
      defaultSize: 'standard',
      api: [{ method: 'GET', path: '/api/motor/config' }, { method: 'POST', path: '/api/motor/apply' }],
      body: 'motorSettings',
    },
    {
      id: 'motor-channel-panel',
      title: 'Motor Channel Calibration',
      purpose: 'Test left/right motors one by one with direction, speed, duration, and safe arming.',
      group: 'motor',
      defaultSize: 'standard',
      api: [{ method: 'POST', path: '/api/motor/test-channel' }, { method: 'POST', path: '/api/control/stop' }],
      body: 'motorChannel',
    },
    {
      id: 'manual-drive-panel',
      title: 'Manual Drive',
      purpose: 'Low-speed bench control for forward, reverse, left, right, and stop commands.',
      group: 'control',
      defaultSize: 'compact',
      api: [{ method: 'POST', path: '/api/control/manual' }, { method: 'POST', path: '/api/control/stop' }],
      body: 'manualDrive',
    },
    {
      id: 'safety-stop-panel',
      title: 'Safety Stop',
      purpose: 'Always-visible emergency stop, motor-lock state, and safety reminders.',
      group: 'safety',
      defaultSize: 'compact',
      api: [{ method: 'POST', path: '/api/control/stop' }],
      body: 'safetyStop',
    },
    {
      id: 'error-monitor-panel',
      title: 'Error Monitor',
      purpose: 'Show recent app, camera, and motor error codes with clear/refresh actions.',
      group: 'diagnostics',
      defaultSize: 'standard',
      api: [{ method: 'GET', path: '/api/errors' }, { method: 'POST', path: '/api/errors/clear' }],
      body: 'errors',
    },
    {
      id: 'api-inspector-panel',
      title: 'API Inspector',
      purpose: 'Send custom GET/POST requests and verify response codes before wiring final controls.',
      group: 'diagnostics',
      defaultSize: 'large',
      api: [{ method: 'GET', path: '/api/test-gui/manifest' }, { method: 'GET', path: '/api/panel-testing/manifest' }],
      body: 'apiInspector',
    },
    {
      id: 'validation-panel',
      title: 'Validation Checklist',
      purpose: 'Expose simple checks for panel health, responsive behaviour, and local API status.',
      group: 'testing',
      defaultSize: 'standard',
      api: [{ method: 'GET', path: '/api/status' }],
      body: 'validation',
    },
    {
      id: 'recording-panel',
      title: 'Recording and Dataset',
      purpose: 'Reserve final GUI space for frame capture, steering labels, sessions, and dataset export.',
      group: 'future',
      defaultSize: 'compact',
      api: [],
      body: 'placeholder',
    },
    {
      id: 'model-runtime-panel',
      title: 'Model and Lane Runtime',
      purpose: 'Reserve final GUI space for model loading, lane detection, and autonomous runtime status.',
      group: 'future',
      defaultSize: 'compact',
      api: [],
      body: 'placeholder',
    },
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
  };

  let lastStatus = readJson('panelInitialStatusJson') || {};
  const manifest = readJson('panelManifestJson') || {};
  let sizeCycleIndex = 0;

  function readJson(id) {
    const node = document.getElementById(id);
    if (!node) return null;
    try { return JSON.parse(node.textContent || '{}'); }
    catch (_err) { return null; }
  }

  function writeReport(lines, append = false) {
    const text = Array.isArray(lines) ? lines.join('\n') : String(lines);
    dom.report.textContent = append ? `${dom.report.textContent}\n${text}` : text;
    dom.report.scrollTop = dom.report.scrollHeight;
  }

  function okLine(label, message = 'ok') {
    return `OK   ${OK.padEnd(13)} ${label} - ${message}`;
  }

  function failLine(label, message = 'failed') {
    return `FAIL ${PANEL_CONTRACT_ERROR.padEnd(13)} ${label} - ${message}`;
  }

  function apiList(panel) {
    if (!panel.api || panel.api.length === 0) {
      return '<span class="pt-muted">No live API yet. Reserved for final GUI stage.</span>';
    }
    return panel.api.map(item => `<span class="pt-chip"><strong>${item.method}</strong> ${item.path}</span>`).join('');
  }

  function field(label, value) {
    return `<div class="pt-metric"><span>${label}</span><strong>${value}</strong></div>`;
  }

  function bodyHtml(panel) {
    switch (panel.body) {
      case 'status':
        return `<div class="pt-metric-grid">
          ${field('Version', escapeText(lastStatus.version || manifest.version || 'unknown'))}
          ${field('Hardware', lastStatus.hardware_requested ? 'requested' : 'simulation')}
          ${field('Camera', escapeText((lastStatus.camera || {}).backend || 'not started'))}
          ${field('Motor', escapeText((lastStatus.motor || {}).adapter || 'unknown'))}
        </div>`;
      case 'cameraPreview':
        return `<div class="pt-preview-surface"><span>Camera preview surface<br><small>aspect controlled by panel style settings</small></span></div>
          <div class="pt-action-grid">
            <button class="pt-button" data-panel-api="POST /api/camera/start">Start camera</button>
            <button class="pt-button" data-panel-api="GET /api/camera/frame.jpg">Fetch frame</button>
          </div>`;
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
        </div><p class="pt-muted">Real output remains locked unless final GUI explicitly arms it.</p>`;
      case 'manualDrive':
        return `<div class="pt-joystick-pad">
          <button class="pt-button">↑</button><button class="pt-button">←</button><button class="pt-button pt-button-danger">STOP</button><button class="pt-button">→</button><button class="pt-button">↓</button>
        </div>`;
      case 'safetyStop':
        return `<div class="pt-action-tile"><strong class="pt-danger-text">Emergency stop must remain reachable in every layout.</strong><p>Panel should stay readable in compact, phone, and high-contrast modes.</p></div>`;
      case 'errors':
        return `<div class="pt-metric-grid">
          ${field('App errors', ((lastStatus.errors || {}).app || []).length)}
          ${field('Camera errors', ((lastStatus.errors || {}).camera || []).length)}
          ${field('Motor errors', ((lastStatus.errors || {}).motor || []).length)}
        </div>`;
      case 'apiInspector':
        return `<div class="pt-field-grid"><label><span>Method</span><select><option>GET</option><option>POST</option></select></label><label><span>Path</span><input value="/api/status"></label></div><div class="pt-console">Response preview area</div>`;
      case 'validation':
        return `<div class="pt-action-grid"><button class="pt-button" data-panel-check="required-dom">Check DOM</button><button class="pt-button" data-panel-check="responsive">Check responsive</button><button class="pt-button" data-panel-check="api-map">Check API map</button></div>`;
      default:
        return `<div class="pt-placeholder"><strong>${escapeText(panel.title)}</strong><p>${escapeText(panel.purpose)}</p><p class="pt-muted">Placeholder is intentional: this panel space is reserved so the final GUI can be planned without locking the design too early.</p></div>`;
    }
  }

  function renderPanels() {
    dom.panelGrid.innerHTML = PANEL_BLUEPRINTS.map(panel => `
      <article class="pt-panel" id="${panel.id}" data-panel-id="${panel.id}" data-group="${panel.group}" data-size="${panel.defaultSize}">
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
            <button class="pt-mini-button" data-panel-test="${panel.id}" title="test this panel">Test</button>
          </div>
        </header>
        <div class="pt-panel-body">
          ${bodyHtml(panel)}
          <div class="pt-action-grid">${apiList(panel)}</div>
        </div>
        <footer class="pt-panel-foot">
          <span class="pt-muted">Group: ${escapeText(panel.group)}</span>
          <span class="pt-muted">Default: ${escapeText(panel.defaultSize)}</span>
        </footer>
      </article>`).join('');
    dom.panelCount.textContent = `${PANEL_BLUEPRINTS.length} planned panels listed for final GUI design.`;
  }

  function escapeText(value) {
    return String(value).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
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
        panel.dataset.size = blueprint?.defaultSize || 'standard';
      } else if (preset === 'stress') {
        panel.dataset.size = sizes[index % sizes.length];
      } else {
        panel.dataset.size = preset;
      }
    });
  }

  async function apiCall(method, path, body) {
    const options = { method, headers: {} };
    if (body !== undefined) {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(body);
    }
    const response = await fetch(path, options);
    const type = response.headers.get('content-type') || '';
    if (type.includes('application/json')) {
      return { status: response.status, payload: await response.json() };
    }
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
    const panel = document.querySelector(`[data-panel-id="${panelId}"]`);
    const blueprint = PANEL_BLUEPRINTS.find(item => item.id === panelId);
    if (!panel || !blueprint) return failLine(`panel.${panelId}`, 'panel missing');
    const hasTitle = panel.querySelector('h3')?.textContent?.trim() === blueprint.title;
    const hasBody = !!panel.querySelector('.pt-panel-body');
    const hasCode = !!panel.querySelector('.pt-panel-code');
    const hasSizing = ['compact', 'standard', 'large'].every(size => !!panel.querySelector(`[data-panel-size="${size}"]`));
    if (hasTitle && hasBody && hasCode && hasSizing) return okLine(`panel.${panelId}`, 'structure and size controls ok');
    return failLine(`panel.${panelId}`, 'missing title/body/code/size controls');
  }

  function runAllPanelChecks() {
    const lines = [
      `Panel testing manifest version: ${manifest.version || 'unknown'}`,
      okLine('panel.registry', `${PANEL_BLUEPRINTS.length} panels registered`),
    ];
    const groups = new Set(PANEL_BLUEPRINTS.map(panel => panel.group));
    lines.push(okLine('panel.groups', `${Array.from(groups).sort().join(', ')}`));
    for (const panel of PANEL_BLUEPRINTS) lines.push(panelSelfTest(panel.id));
    const failed = lines.filter(line => line.startsWith('FAIL')).length;
    lines.push('-'.repeat(72));
    lines.push(failed === 0 ? okLine('panel.summary', 'failed=0') : failLine('panel.summary', `failed=${failed}`));
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
      writeReport(`${result.status === 200 ? 'OK' : 'FAIL'}   ${String(code).padEnd(13)} api.control.stop - HTTP ${result.status}`);
    } catch (err) {
      writeReport(failLine('api.control.stop', err.message));
    }
  }

  function exportReport() {
    const report = {
      code: dom.report.textContent.includes('FAIL') ? PANEL_CONTRACT_ERROR : OK,
      generated_at: new Date().toISOString(),
      settings: collectSettings(),
      panels: PANEL_BLUEPRINTS.map(panel => ({ id: panel.id, title: panel.title, group: panel.group, size: document.getElementById(panel.id)?.dataset.size })),
      report_text: dom.report.textContent,
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'pisd_panel_testing_report.json';
    link.click();
    URL.revokeObjectURL(url);
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
    };
  }

  function bindEvents() {
    const controlIds = ['ptTheme', 'ptLayoutMode', 'ptViewportPreset', 'ptPanelSizePreset', 'ptDensity', 'ptFontScale', 'ptPanelGap', 'ptPanelRadius', 'ptBorderStrength', 'ptShadowStrength', 'ptMinPanelWidth', 'ptPreviewAspect'];
    for (const id of controlIds) document.getElementById(id)?.addEventListener('input', applySettings);
    document.getElementById('ptApplySettings')?.addEventListener('click', applySettings);
    document.getElementById('ptRefreshStatus')?.addEventListener('click', refreshStatus);
    document.getElementById('ptRunAllChecks')?.addEventListener('click', runAllPanelChecks);
    document.getElementById('ptCycleSizes')?.addEventListener('click', cycleSizes);
    document.getElementById('ptStopAll')?.addEventListener('click', stopAll);
    document.getElementById('ptExportPanelReport')?.addEventListener('click', exportReport);
    document.getElementById('ptResetPanels')?.addEventListener('click', () => {
      dom.theme.value = 'dark'; dom.layoutMode.value = 'adaptive'; dom.viewportPreset.value = 'auto'; dom.panelSizePreset.value = 'auto'; dom.density.value = 'comfortable';
      dom.fontScale.value = '1.0'; dom.panelGap.value = '14'; dom.panelRadius.value = '18'; dom.borderStrength.value = '0.35'; dom.shadowStrength.value = '0.35'; dom.minPanelWidth.value = '300'; dom.previewAspect.value = '16/9';
      renderPanels(); applySettings(); writeReport(okLine('panel.reset', 'panel lab reset'));
    });
    dom.panelGrid.addEventListener('click', event => {
      const size = event.target?.dataset?.panelSize;
      if (size) event.target.closest('.pt-panel').dataset.size = size;
      const testId = event.target?.dataset?.panelTest;
      if (testId) writeReport(panelSelfTest(testId));
    });
  }

  renderPanels();
  bindEvents();
  applySettings();
  writeReport([okLine('panel.lab_ready', `${PANEL_BLUEPRINTS.length} flexible panels rendered`), 'Use the left controls to stress layout, size, density, theme, and responsive behavior.']);
})();
