/* R33: map only backend-observed Mission 1 timeline records to the viewer. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.CustomDriveMissionTimeline = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const validStates = new Set(['current', 'completed', 'failed', 'interrupted', 'left']);
  function safeText(value, fallback = '—') {
    const valueText = String(value == null ? '' : value).replace(/\s+/g, ' ').trim();
    return valueText ? valueText.slice(0, 220) : fallback;
  }
  function project(status) {
    const t = status?.mission_timeline;
    if (!t || t.schema_version !== 1) {
      return {
        available: false, outcome: 'unavailable',
        current: 'Waiting for backend progress', currentState: 'waiting',
        lastCompleted: 'None yet', failure: 'None',
        detail: 'The Mission 1 backend has not supplied stage history.',
        arm: '', items: [], sessionId: ''
      };
    }
    const outcome = safeText(t.outcome || status.mission_outcome, 'idle').toLowerCase();
    const current = t.current_step || null;
    const completed = t.last_completed_step || null;
    const failure = t.last_failure || null;
    const history = Array.isArray(t.recent_steps) ? t.recent_steps : [];
    const entries = history.filter(item => item && item.id && item.label && validStates.has(item.state))
      .slice(-12).map(item => ({
        id: safeText(item.id),
        label: safeText(item.label),
        phase: safeText(item.phase),
        state: item.state,
        cycle: Number.isInteger(item.cycle) && item.cycle > 0 ? item.cycle : null
      }));
    const arm = t.arm_sequence && typeof t.arm_sequence === 'object'
      ? t.arm_sequence : {};
    let currentText = current ? safeText(current.label) : 'Not started';
    if (outcome === 'failed') currentText = current ? 'Failed during ' + currentText : 'Failed';
    if (outcome === 'stopped') currentText = current ? 'Stopped at ' + currentText : 'Stopped';
    if (outcome === 'complete') currentText = 'Complete';
    const failureText = failure ? [safeText(failure.reason), safeText(failure.stage)].join(' · ') : 'None';
    return {
      available: true, outcome,
      current: currentText,
      currentState: current?.state || 'idle',
      lastCompleted: completed ? safeText(completed.label) : 'None yet',
      failure: failureText,
      detail: safeText(t.detail, ''),
      arm: safeText(arm.note, ''),
      items: entries,
      sessionId: safeText(t.session_id, '')
    };
  }
  return { project };
});
