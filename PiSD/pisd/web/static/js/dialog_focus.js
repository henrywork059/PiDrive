(() => {
  'use strict';
  // Only Tab navigation is handled. Existing Escape and STOP handlers retain
  // ownership; never interpret a key as a motor command here.
  const selector = 'button, input, select, textarea, a[href], [tabindex]';
  function bind(dialog) {
    if (!dialog) return;
    dialog.addEventListener('keydown', event => {
      if (event.key !== 'Tab' || dialog.hidden) return;
      const controls = Array.from(dialog.querySelectorAll(selector)).filter(el =>
        el.tabIndex >= 0 && !el.matches(':disabled') && el.getClientRects().length &&
        getComputedStyle(el).visibility !== 'hidden' && !el.closest('[inert]'));
      if (!controls.length) return;
      const first = controls[0], last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    });
  }
  window.PiSDDialogFocus = { bind };
})();
