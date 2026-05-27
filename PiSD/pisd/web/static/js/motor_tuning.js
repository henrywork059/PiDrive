(() => {
  'use strict';

  const statusScript = document.getElementById('motorTuningInitialStatus');
  const codeElement = document.getElementById('mtunGlobalCode');
  const adapterElement = document.getElementById('mtunMotorAdapter');

  try {
    const initial = statusScript?.textContent ? JSON.parse(statusScript.textContent) : null;
    if (initial && codeElement) codeElement.textContent = initial.code || 'PISD-OK-000';
    if (initial?.motor && adapterElement) adapterElement.textContent = initial.motor.adapter || 'unknown';
  } catch (error) {
    if (codeElement) {
      codeElement.textContent = 'PISD-UI-001';
      codeElement.dataset.state = 'error';
    }
    console.warn('Motor tuning reset page could not parse initial status.', error);
  }
})();
