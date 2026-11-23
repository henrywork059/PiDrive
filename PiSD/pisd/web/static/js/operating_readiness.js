/* PiSD R32 — diagnostic-only readiness projection from the existing backend status.
 * Does not authorize, arm, command or stop motors. The server remains authoritative.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.PiSDOperatingReadiness = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const clean = value => String(value || '').replace(/\s+/g, ' ').trim();
  const limit = value => clean(value).slice(0, 170);
  const indicator = (text, tone = 'neutral') => ({ text, tone });

  function projectReadiness(status, options = {}) {
    const screen = options.screen === 'manual' ? 'manual' : 'ai';
    const confirmed = options.confirmed === true;
    const selectedPanel = ['manual','assist','correction','limiter'].includes(options.selectedPanel)
      ? options.selectedPanel : 'limiter';
    if (!status || typeof status !== 'object' || options.offline === true || status.ok === false) {
      return {
        camera: indicator('Unknown', 'warning'),
        model: indicator('Unknown', 'warning'),
        source: indicator('Unconfirmed', 'warning'),
        motor: indicator('Unconfirmed', 'warning'),
        reason: indicator('Backend status unavailable; control state cannot be confirmed.', 'danger'),
        isVerified: false
      };
    }

    const camera = status.camera || {};
    const ai = status.ai_mode || status.ai || {};
    const motor = status.motor || {};
    const safety = status.safety || {};
    const fault = safety.latched === true || ai.camera_frame_fault_latched === true;
    const running = ai.running === true;
    const aiDrive = running && ai.mode === 'drive' && ai.drive_output_enabled === true;
    const aiPreview = running && ai.mode === 'preview';
    const correction = ai.manual_correction || {};
    const command = motor.last_command || {};
    const commandSource = clean(command.control_source);
    // Intent is a diagnostic measurement, not a hardware motion guarantee.
    const requestedMotion = Math.max(Math.abs(Number(motor.last_intended_left || 0)),
      Math.abs(Number(motor.last_intended_right || 0))) > 0.0001;

    const cameraView = camera.running !== true ? indicator('Stopped', 'warning')
      : Number(camera.frame_seq || 0) > 0 ? indicator('Running', 'good')
      : indicator('Starting · no frame yet', 'warning');

    const loadedName = clean(ai.model_id) || 'none';
    const selectedName = clean(options.selectedModel);
    let modelView;
    if (ai.model_ready === true) {
      modelView = indicator('Ready · ' + limit(loadedName), 'good');
    } else if (selectedName && selectedName !== 'none') {
      modelView = indicator('Selected only · ' + limit(selectedName), 'warning');
    } else if (loadedName !== 'none') {
      modelView = indicator('Not ready · ' + limit(loadedName), 'warning');
    } else {
      modelView = indicator('Not loaded', 'warning');
    }
    if (selectedName && selectedName !== 'none' && ai.model_ready === true && selectedName !== loadedName) {
      modelView = indicator('Ready · ' + limit(loadedName) + ' (other selected)', 'warning');
    }

    let sourceView;
    if (fault) {
      sourceView = indicator('Safety stopped', 'danger');
    } else if (aiDrive) {
      sourceView = correction.enabled === true && correction.active === true
        ? indicator('AI + correction', 'good') : indicator('AI drive', 'good');
    } else if (requestedMotion) {
      sourceView = commandSource === 'manual' ? indicator('Manual input', 'good')
        : commandSource === 'manual_assist' ? indicator('Manual + AI assist', 'good')
        : indicator('Other / unverified input', 'warning');
    } else if (aiPreview) {
      sourceView = indicator('AI preview · no drive', 'neutral');
    } else {
      const selection = screen === 'manual' ? 'Manual' : ({
        manual: 'Manual', assist: 'AI assist', correction: 'Correction', limiter: 'AI limiter'
      }[selectedPanel]);
      sourceView = indicator('Idle · ' + selection + ' selected');
    }

    let motorView;
    if (fault) {
      motorView = indicator('Blocked · safety latch', 'danger');
    } else if (motor.hardware_enabled !== true) {
      motorView = indicator('Simulation · no physical output', 'warning');
    } else if (aiDrive) {
      motorView = indicator('AI drive authorized', 'good');
    } else if (!confirmed) {
      motorView = indicator('Locked · confirmation unchecked', 'warning');
    } else if (screen === 'ai') {
      motorView = indicator('Confirmed · drive not started', 'neutral');
    } else {
      motorView = indicator('Confirmed per manual command', 'good');
    }

    let reason;
    if (fault) {
      reason = indicator(limit(safety.reason || 'Camera-frame fault latched; stop AI and rearm with fresh frames.'), 'danger');
    } else if (screen === 'ai' && camera.running !== true) {
      reason = indicator('Start the camera for AI mode.', 'warning');
    } else if (screen === 'ai' && Number(camera.frame_seq || 0) <= 0) {
      reason = indicator('Wait for the first camera frame.', 'warning');
    } else if (screen === 'ai' && ai.model_ready !== true) {
      reason = indicator('Load a compatible AI model to drive.', 'warning');
    } else if (motor.hardware_enabled !== true) {
      reason = indicator('Simulation mode; no physical motor output.', 'warning');
    } else if (!confirmed && !aiDrive) {
      reason = indicator('Check the single motor safety confirmation before driving.', 'warning');
    } else if (aiPreview && screen === 'ai' && selectedPanel !== 'manual' && selectedPanel !== 'assist') {
      reason = indicator('AI preview only; drive output is disabled.', 'neutral');
    } else if (ai.camera_frame_stale === true && aiDrive) {
      reason = indicator('Camera frame stale; AI safety may stop output.', 'danger');
    } else if (motor.last_error && requestedMotion) {
      reason = indicator('Motor error: ' + limit(motor.last_error), 'danger');
    } else if (!aiDrive && !requestedMotion) {
      reason = indicator('No active motor command.', 'neutral');
    } else {
      reason = indicator('No active stop reported.', 'good');
    }

    return { camera: cameraView, model: modelView, source: sourceView,
      motor: motorView, reason, isVerified: true };
  }

  return { projectReadiness };
});
