/* UX74: non-modal exact-target confirmation; no STOP control is disabled. */
(function (root) {
  'use strict';
  const pending = new WeakMap();
  function busy(button) { return !!button && pending.has(button); }
  function finish(button) {
    const item = pending.get(button);
    if (!item) return;
    pending.delete(button);
    item.panel.remove();
    button.disabled = item.wasDisabled;
  }
  function confirm(button, message, action = 'Delete permanently') {
    if (!button || button.disabled || busy(button)) return Promise.resolve(false);
    const panel = document.createElement('div');
    panel.setAttribute('role', 'group');
    panel.setAttribute('aria-label', 'Confirm destructive action');
    panel.style.cssText = 'flex-basis:100%;width:100%;padding:8px 0;white-space:normal;overflow-wrap:anywhere';
    const text = document.createElement('p');
    text.textContent = message;
    text.style.whiteSpace = 'pre-wrap';
    const yes = document.createElement('button');
    const no = document.createElement('button');
    yes.type = no.type = 'button';
    yes.textContent = action;
    no.textContent = 'Cancel';
    yes.className = button.className;
    no.style.marginInlineStart = '8px';
    panel.append(text, yes, no);
    const item = {panel, wasDisabled: button.disabled, settled: false};
    pending.set(button, item);
    button.disabled = true;
    button.after(panel);
    return new Promise(resolve => {
      function settle(accepted) {
        if (item.settled) return;
        item.settled = true;
        yes.disabled = no.disabled = true;
        if (accepted) {
          text.textContent = 'Working on confirmed target…';
        } else {
          finish(button);
          button.focus();
        }
        resolve(accepted);
      }
      yes.addEventListener('click', () => settle(true));
      no.addEventListener('click', () => settle(false));
      panel.addEventListener('keydown', event => {
        if (event.key === 'Escape') { event.preventDefault(); settle(false); }
      });
      no.focus();
    });
  }
  root.PiDriveDestructive = {busy, confirm, finish};
})(typeof window !== 'undefined' ? window : globalThis);
