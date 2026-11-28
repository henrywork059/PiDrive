/* V17 M01: presentation only. Reuse the original DOM and controller.
 * No fetch, settings write, authority change, or additional polling.
 * Mode links use ordinary document navigation, not concurrent controllers.
 */
(() => {
  "use strict";
  const mode = document.body.dataset.pisdV17;
  if (mode !== "manual" && mode !== "ai") return;
  const manual = mode === "manual";
  const byId = id => document.getElementById(id);
  const shell = byId(manual ? "manualDriveShell" : "aiModeShell");
  const panel = byId(manual ? "manualDriveCameraPanel" : "aiPreviewPanel");
  const frame = byId(manual ? "mdrvPreviewFrame" : "aiPreviewFrame");
  const image = frame?.querySelector("img");
  const header = document.querySelector(".mdrv-topbar");
  const reason = byId(manual ? "mdrvReadyReason" : "aiReadyReason")?.closest(".pisd-readiness-reason");
  if (!shell || !panel || !frame || !image || !header || !reason) return;

  // Move existing nodes before page-specific controllers bind. IDs, labels,
  // overlays, focusable controls and state readers remain the original nodes.
  shell.prepend(panel);
  panel.prepend(frame);
  const readiness = document.createElement("div");
  readiness.className = "v17-readiness";
  readiness.setAttribute("role", "status");
  readiness.setAttribute("aria-live", "polite");
  readiness.append(reason);
  panel.prepend(readiness);
  const classicToggle = byId("drivingCockpitToggle");
  if (classicToggle) classicToggle.hidden = true; // reversible via Classic layout
  const active = document.querySelector('#v17ModeNav [aria-current="page"]');
  active?.addEventListener("click", event => event.preventDefault());

  // The existing cockpit aspect observer continues to own decoded ratio.
  // Only the header measurement is new, so large text and narrow widths
  // do not push a nominally full-height camera underneath the sticky STOP.
  const measure = () => {
    document.body.style.setProperty("--v17-header-height", `${Math.ceil(header.getBoundingClientRect().height)}px`);
  };
  measure();
  const observer = new ResizeObserver(measure);
  observer.observe(header);
  window.addEventListener("pagehide", () => observer.disconnect());
  // BFCache restoration must reattach the presentation observer, not a
  // controller or a stream. Existing controllers own lifecycle/STOP.
  window.addEventListener("pageshow", event => {
    if (event.persisted) {
      observer.observe(header);
      measure();
    }
  });
  document.body.dataset.pisdV17Ready = "true";
})();
